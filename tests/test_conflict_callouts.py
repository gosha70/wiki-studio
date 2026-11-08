# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.9.0 (US2): the conflict callouts (FR-005..FR-014)."""

from __future__ import annotations

import ast
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.conftest import PACKAGE_ROOT, run_cli
from tests.test_approve import ApprovalCase, page_text
from wiki_studio import api
from wiki_studio.conflicts import CONFLICT_MARKER, CONFLICT_MARKER_RE, conflict_findings, scan_callouts
from wiki_studio.contract import read_packaged_schema
from wiki_studio.errors import BackendNotFoundError
from wiki_studio.paths import WikiPaths
from wiki_studio.proposal import PageEdit

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "conflicts"
CONFLICT_KINDS = ("open-conflict", "conflict-one-sided", "conflict-dangling")

# The fixture wiki's conflict findings, in the order of FR-007: kind, pages and
# (for a dangling callout) the reason words of FR-007. Compared whole.
EXPECTED_FIXTURE_FINDINGS = [
    ("open-conflict", ("concepts/matched-a.md", "decisions/matched-b.md"), ""),
    ("open-conflict", ("decisions/multi-a.md", "decisions/multi-b.md"), ""),
    ("open-conflict", ("decisions/multi-a.md", "decisions/multi-c.md"), ""),
    ("open-conflict", ("decisions/repeat-a.md", "decisions/repeat-b.md"), ""),
    ("open-conflict", ("decisions/source-line-a.md", "decisions/source-line-b.md"), ""),
    ("conflict-one-sided", ("concepts/case-fold.md", "decisions/target.md"), ""),
    ("conflict-one-sided", ("concepts/one-sided.md", "decisions/target.md"), ""),
    ("conflict-one-sided", ("concepts/web-then-page.md", "decisions/target.md"), ""),
    ("conflict-one-sided", ("decisions/repeat-c.md", "decisions/repeat-d.md"), ""),
    ("conflict-one-sided", ("decisions/titled-link.md", "decisions/titled-target.md"), ""),
    ("conflict-dangling", ("concepts/points-at-index.md",), "names index.md, which is not a content page"),
    ("conflict-dangling", ("concepts/self-target.md",), "names the page itself"),
    ("conflict-dangling", ("concepts/web-md-first.md",), "points outside the wiki"),
    ("conflict-dangling", ("decisions/missing-target.md",), "names a missing page"),
    ("conflict-dangling", ("decisions/no-link.md",), "names no wiki page"),
    (
        "conflict-dangling",
        ("decisions/superseded-caller.md",),
        "names decisions/old-target.md, which is superseded by decisions/new-target.md",
    ),
]


def fixture_paths() -> WikiPaths:
    return WikiPaths.for_root(FIXTURE_ROOT, wiki_dir=FIXTURE_ROOT / "wiki")


def callout(target: str, *, extra: str = "") -> str:
    """One complete callout naming ``target``."""
    return f"> [!conflict] Disagrees with [the other page]({target})\n> This page: issue: 12. That page: pr: 22.{extra}"


def _conflict_findings(result: api.FindingsResult) -> list[tuple[str, tuple[str, ...]]]:
    return [(finding.kind, finding.pages) for finding in result.findings if finding.kind in CONFLICT_KINDS]


class ConflictCase(ApprovalCase):
    """A managed wiki with helpers that promote valid pages carrying callouts through the gate."""

    def promote_pages(self, pages: dict[str, str], name: str) -> None:
        edits = [PageEdit(rel, "create", text, "why") for rel, text in pages.items()]
        edits.extend(PageEdit("index.md", "append-index", f"- [{Path(rel).stem}]({rel})", "why") for rel in pages)
        api.promote(api.propose(edits, self.paths, name=name), self.paths)

    def create_pair(self) -> tuple[str, str]:
        """A matched decision pair through ``api.propose``/``api.promote``; returns both paths."""
        left, right = "decisions/retry-budget.md", "decisions/retry-policy.md"
        self.promote_pages(
            {
                left: page_text(
                    "retry-budget",
                    body="A client retries at most 3 times.\n\n"
                    + callout("retry-policy.md", extra=" Capped by `retry_budget`."),
                ).replace("  - path: notes.md\n", "  - issue: 12\n"),
                right: page_text(
                    "retry-policy",
                    body="A client retries at most 5 times.\n\n"
                    + callout("retry-budget.md", extra=" Capped by `retry_policy`."),
                ).replace("  - path: notes.md\n", "  - pr: 22\n"),
            },
            "pair",
        )
        return left, right


class TestFixtureWiki(unittest.TestCase):
    def setUp(self) -> None:
        self.paths = fixture_paths()

    def test_the_expected_findings_are_produced_whole(self) -> None:
        found = conflict_findings(self.paths)
        self.assertEqual(
            [(f.kind, f.pages) for f in found], [(kind, pages) for kind, pages, _ in EXPECTED_FIXTURE_FINDINGS]
        )
        for finding, (_, _, reason) in zip(found, EXPECTED_FIXTURE_FINDINGS, strict=True):
            self.assertEqual(finding.severity, "warning")
            if reason:
                self.assertIn(reason, finding.description)
                self.assertRegex(finding.description, r"^line \d+: ")

    def test_the_scan_reads_the_marker_line_of_each_page_once(self) -> None:
        callouts = scan_callouts(self.paths)
        self.assertEqual(callouts["concepts/matched-a.md"][0].raw_target, "../decisions/matched-b.md")
        self.assertEqual(callouts["concepts/matched-a.md"][0].resolved, "decisions/matched-b.md")
        self.assertEqual(callouts["concepts/web-md-first.md"][0].resolved, None)
        self.assertEqual(callouts["decisions/no-link.md"][0].raw_target, None)
        self.assertNotIn("concepts/fenced.md", callouts)
        self.assertNotIn("decisions/old-target.md", callouts)  # superseded: its text is replaced
        self.assertNotIn("index.md", callouts)
        self.assertNotIn("log.md", callouts)
        self.assertNotIn("decisions/quiet.md", callouts)
        self.assertEqual(callouts["decisions/repeat-a.md"][0].line + 3, callouts["decisions/repeat-a.md"][1].line)

    def test_the_marker_regex_is_built_from_the_constant(self) -> None:
        self.assertEqual(CONFLICT_MARKER, "[!conflict]")
        for line in ("[!conflict]", "[!CONFLICT]+", "[!Conflict]-"):
            self.assertIsNotNone(CONFLICT_MARKER_RE.match(f"> {line}"))
        self.assertIsNotNone(CONFLICT_MARKER_RE.match("   >  [!conflict] text"))
        self.assertIsNone(CONFLICT_MARKER_RE.match("    > [!conflict]"))  # four spaces: code
        self.assertIsNone(CONFLICT_MARKER_RE.match("> [!conflicts] x"))

    def test_the_fixture_minus_its_missing_target_page_lints_clean_with_health(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wiki_studio-conflicts-") as tmp:
            root = Path(tmp) / "conflicts"
            shutil.copytree(FIXTURE_ROOT, root)
            missing = "decisions/missing-target.md"
            (root / "wiki" / missing).unlink()
            for name in ("index.md", "overview.md"):
                page = root / "wiki" / name
                kept = [line for line in page.read_text(encoding="utf-8").splitlines() if missing not in line]
                page.write_text("\n".join(kept) + "\n", encoding="utf-8")
            paths = WikiPaths.for_root(root, wiki_dir=root / "wiki")
            result = api.lint(paths, health=True, strict=True)
            self.assertEqual(result.violations, ())
            self.assertEqual(result.audit_errors, ())
            self.assertIsNotNone(result.health)
            assert result.health is not None
            self.assertEqual([f.kind for f in result.health.findings], [])
            self.assertTrue(result.passed)
            cli = run_cli("lint", "--health", "--strict", "--wiki-dir", str(root / "wiki"), cwd=root)
            self.assertEqual(cli.returncode, 0, cli.stderr)


class TestAcceptanceCases(ConflictCase):
    def test_a_matched_pair_gives_exactly_one_open_conflict(self) -> None:
        left, right = self.create_pair()
        result = api.findings(self.paths)
        self.assertEqual(_conflict_findings(result), [("open-conflict", (left, right))])
        (finding,) = [f for f in result.findings if f.kind == "open-conflict"]
        self.assertIn("citation-rules.md", finding.description)
        self.assertIn(left, finding.description)
        self.assertIn(right, finding.description)

    def test_a_one_sided_callout_names_the_page_and_its_target(self) -> None:
        target = self.create("solo-target")
        caller = self.create("solo-caller", body="One side only.\n\n" + callout("solo-target.md"))
        self.assertEqual(_conflict_findings(api.findings(self.paths)), [("conflict-one-sided", (caller, target))])

    def test_a_callout_naming_the_root_index_is_dangling(self) -> None:
        rel = self.create("points-at-index", body="Bad target.\n\n" + callout("../index.md"))
        (finding,) = _dangling(api.findings(self.paths))
        self.assertEqual(finding.pages, (rel,))
        self.assertIn("names index.md, which is not a content page", finding.description)
        self.assertIn("line 17", finding.description)

    def test_a_callout_naming_the_page_itself_is_dangling(self) -> None:
        rel = self.create("self-target", body="Bad target.\n\n" + callout("self-target.md"))
        (finding,) = _dangling(api.findings(self.paths))
        self.assertEqual(finding.pages, (rel,))
        self.assertIn("names the page itself", finding.description)

    def test_a_callout_naming_a_missing_page_is_dangling(self) -> None:
        rel = self.create("missing-target")
        self.hand_edit(rel, page_text("missing-target", body="Bad target.\n\n" + callout("gone.md")))
        (finding,) = _dangling(api.findings(self.paths))
        self.assertEqual(finding.pages, (rel,))
        self.assertIn("names a missing page", finding.description)

    def test_a_callout_naming_a_superseded_page_is_dangling(self) -> None:
        self.create("replacement")
        replaced = self.create("replaced", extra="superseded_by: decisions/replacement.md\n")
        caller = self.create("superseded-caller", body="Bad target.\n\n" + callout("replaced.md"))
        (finding,) = _dangling(api.findings(self.paths))
        self.assertEqual(finding.pages, (caller,))
        self.assertIn(f"names {replaced}, which is superseded by decisions/replacement.md", finding.description)

    def test_a_callout_naming_an_off_wiki_web_page_is_dangling(self) -> None:
        rel = self.create("web-md-first", body="Bad target.\n\n> [!conflict] [the lookup](https://example.com/b.md)")
        (finding,) = _dangling(api.findings(self.paths))
        self.assertEqual(finding.pages, (rel,))
        self.assertIn("points outside the wiki", finding.description)

    def test_a_marker_line_with_no_md_link_is_dangling(self) -> None:
        self.create("solo-target")
        rel = self.create(
            "no-link",
            body="Bad marker.\n\n> [!conflict] This page disagrees.\n> [the other page](solo-target.md)",
        )
        (finding,) = _dangling(api.findings(self.paths))
        self.assertEqual(finding.pages, (rel,))
        self.assertIn("names no wiki page", finding.description)

    def test_a_page_with_no_callout_gives_no_conflict_finding(self) -> None:
        self.create("quiet")
        self.assertEqual(_conflict_findings(api.findings(self.paths)), [])

    def test_a_fenced_callout_is_not_counted(self) -> None:
        self.create("solo-target")
        self.create(
            "fenced",
            body="An example:\n\n```markdown\n" + callout("solo-target.md") + "\n```",
        )
        self.assertEqual(_conflict_findings(api.findings(self.paths)), [])

    def test_a_callout_whose_target_escapes_the_wiki_is_dangling(self) -> None:
        rel = self.create("escaping")
        body = "Bad.\n\n" + callout("../../../docs/spec.md") + "\n\n" + callout("/etc/passwd.md")
        self.hand_edit(rel, page_text("escaping", body=body))
        findings = _dangling(api.findings(self.paths))
        self.assertEqual([finding.pages for finding in findings], [(rel,), (rel,)])
        for finding in findings:
            self.assertIn("points outside the wiki", finding.description)

    def test_a_web_link_before_the_page_link_is_skipped(self) -> None:
        self.create("solo-target")
        rel = self.create(
            "web-then-page",
            body="See [a page](https://example.com/a) and [the other page](solo-target.md).\n\n"
            "> [!conflict] see [a page](https://example.com/a) and [the other page](solo-target.md)",
        )
        self.assertEqual(
            _conflict_findings(api.findings(self.paths)), [("conflict-one-sided", (rel, "decisions/solo-target.md"))]
        )

    def test_a_titled_link_names_the_page(self) -> None:
        self.create("solo-target")
        rel = self.create(
            "titled-link",
            body='Titled link.\n\n> [!conflict] Disagrees with [the other page](solo-target.md "Title")',
        )
        self.assertEqual(
            _conflict_findings(api.findings(self.paths)), [("conflict-one-sided", (rel, "decisions/solo-target.md"))]
        )

    def test_repeated_callouts_count_once_with_and_without_an_answer(self) -> None:
        left, right = "decisions/repeat-left.md", "decisions/repeat-right.md"
        self.promote_pages(
            {
                left: page_text(
                    "repeat-left", body="Twice.\n\n" + callout("repeat-right.md") + "\n\n" + callout("repeat-right.md")
                ),
                right: page_text("repeat-right", body="Once back.\n\n" + callout("repeat-left.md")),
            },
            "repeat-pair",
        )
        self.assertEqual(_conflict_findings(api.findings(self.paths)), [("open-conflict", (left, right))])
        solo = self.create("solo")
        alone = self.create("repeat-alone", body="Twice.\n\n" + callout("solo.md") + "\n\n" + callout("solo.md"))
        self.assertEqual(
            [found for found in _conflict_findings(api.findings(self.paths)) if alone in found[1]],
            [("conflict-one-sided", (alone, solo))],
        )

    def test_a_page_in_conflict_with_two_pages_pairs_each_side(self) -> None:
        left, first, second = "decisions/multi-left.md", "decisions/multi-first.md", "decisions/multi-second.md"
        self.promote_pages(
            {
                left: page_text(
                    "multi-left", body="Two.\n\n" + callout("multi-first.md") + "\n\n" + callout("multi-second.md")
                ),
                first: page_text("multi-first", body="Back.\n\n" + callout("multi-left.md")),
                second: page_text("multi-second", body="Back too.\n\n" + callout("multi-left.md")),
            },
            "multi-pair",
        )
        self.assertEqual(
            _conflict_findings(api.findings(self.paths)),
            [("open-conflict", (first, left)), ("open-conflict", (left, second))],
        )


def _dangling(result: api.FindingsResult) -> list[api.Finding]:
    return [finding for finding in result.findings if finding.kind == "conflict-dangling"]


class TestScopeAndSurfaces(ConflictCase):
    def test_a_scoped_pair_lists_only_the_in_scope_page(self) -> None:
        left, right = self.create_pair()
        result = api.findings(self.paths, pages=[f"./{left}"])
        self.assertEqual(result.pages_checked, 1)
        (finding,) = [f for f in result.findings if f.kind == "open-conflict"]
        self.assertEqual(finding.pages, (left,))
        self.assertIn(right, finding.description)
        self.assertEqual(result.counts["conflict-one-sided"], 0)
        self.assertEqual(result.counts["conflict-dangling"], 0)

    def test_the_text_form_names_the_kind_and_the_json_names_every_kind(self) -> None:
        self.create_pair()
        text = self.cli("findings")
        self.assertEqual(text.returncode, 0, text.stderr)
        self.assertIn("[open-conflict / warning]", text.stdout)
        data = json.loads(self.cli("findings", "--json").stdout)
        self.assertEqual(data["findings_version"], 1)
        for kind in CONFLICT_KINDS:
            self.assertIn(kind, data["counts"])
        self.assertEqual(data["counts"]["open-conflict"], 1)
        self.assertEqual(data["counts"]["conflict-one-sided"], 0)
        self.assertEqual(data["counts"]["conflict-dangling"], 0)

    def test_the_three_kinds_are_listed_in_their_order(self) -> None:
        self.create("quiet")
        self.promote_pages(
            {
                "decisions/order-a.md": page_text("order-a", body="A.\n\n" + callout("order-b.md")),
                "decisions/order-b.md": page_text("order-b", body="B.\n\n" + callout("order-a.md")),
            },
            "order-pair",
        )
        self.create("order-one-sided", body="One.\n\n" + callout("quiet.md"))
        dangling = self.create("order-dangling", body="Bad.\n\n" + callout("order-dangling.md"))
        result = api.findings(self.paths)
        kinds = [kind for kind, _ in _conflict_findings(result)]
        self.assertEqual(kinds, ["open-conflict", "conflict-one-sided", "conflict-dangling"])
        self.assertEqual({kind: result.counts[kind] for kind in CONFLICT_KINDS}, dict.fromkeys(CONFLICT_KINDS, 1))
        self.assertEqual(_findings_for(result, dangling)[-1].kind, "conflict-dangling")

    def test_no_backend_is_reached_with_a_callout_fixture(self) -> None:
        self.create_pair()
        failing = BackendNotFoundError("backend resolution must not be reached by findings")

        def no_model_check(wiki_dir: object, backend: object) -> list[object]:
            if backend is not None:
                raise AssertionError(f"findings handed a backend to the health pass: {backend!r}")
            return []

        with (
            patch("wiki_studio.backends.resolve_backend", side_effect=failing),
            patch("wiki_studio.api.resolve_backend", side_effect=failing),
            patch("wiki_studio.api.prepare_backend", side_effect=failing),
            patch("wiki_studio.health_lint._check_contradictions", side_effect=no_model_check),
        ):
            result = api.findings(self.paths)
            cli = self.cli("findings", "--json")
        self.assertEqual(result.counts["open-conflict"], 1)
        self.assertEqual(cli.returncode, 0, cli.stderr)

    def test_only_findings_imports_conflicts(self) -> None:
        importers: set[str] = set()
        for py in sorted(PACKAGE_ROOT.rglob("*.py")):
            for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    hit = (bool(node.level) and module == "conflicts") or (
                        not node.level and module == "wiki_studio.conflicts"
                    )
                elif isinstance(node, ast.Import):
                    hit = any(alias.name == "wiki_studio.conflicts" for alias in node.names)
                else:
                    continue
                if hit:
                    importers.add(py.relative_to(PACKAGE_ROOT).as_posix())
        self.assertEqual(importers, {"findings.py"})


def _findings_for(result: api.FindingsResult, page: str) -> list[api.Finding]:
    return [finding for finding in result.findings if page in finding.pages]


class TestDocumentedExample(unittest.TestCase):
    def test_the_packaged_example_pages_pair_without_drift(self) -> None:
        example = _documented_example()
        self.assertEqual([rel for rel, _ in example], ["concepts/retry-budget.md", "decisions/retry-policy.md"])
        with tempfile.TemporaryDirectory(prefix="wiki_studio-example-") as tmp:
            paths = WikiPaths.for_root(Path(tmp))
            api.init(paths)
            for rel, text in example:
                target = paths.wiki_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
            index = paths.wiki_dir / "index.md"
            lines = [f"- [{Path(rel).stem}]({rel})" for rel, _ in example]
            index.write_text(index.read_text(encoding="utf-8") + "\n".join(lines) + "\n", encoding="utf-8")
            result = api.findings(paths)
            self.assertEqual(
                _conflict_findings(result),
                [("open-conflict", ("concepts/retry-budget.md", "decisions/retry-policy.md"))],
            )
            lint = api.lint(paths)
            self.assertEqual(lint.violations, ())
            self.assertEqual(lint.audit_errors, ())
            self.assertTrue(lint.passed)
            cli = run_cli("lint", "--root", str(Path(tmp)), cwd=Path(tmp))
            self.assertEqual(cli.returncode, 0, cli.stderr)


def _documented_example() -> list[tuple[str, str]]:
    """The first two fenced ``markdown`` blocks of "When sources disagree" and the path introducing each."""
    lines = read_packaged_schema("citation-rules").splitlines()
    heading = "## When sources disagree"
    if heading not in lines:
        raise AssertionError(f"citation-rules.md has no {heading!r} section")
    start = lines.index(heading)
    section = [lines[start]]
    in_fence = False
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            section.append(line)
            continue
        if not in_fence and stripped.startswith("## "):
            break
        section.append(line)
    pages: list[tuple[str, str]] = []
    i = 0
    while i < len(section) and len(pages) < 2:
        if section[i].strip() != "```markdown":
            i += 1
            continue
        intro_index = i - 1
        while intro_index >= 0 and not section[intro_index].strip():
            intro_index -= 1
        intro = section[intro_index] if intro_index >= 0 else ""
        match = re.search(r"`([^`]+\.md)`", intro)
        if match is None:
            raise AssertionError(f"the line introducing the fence after {heading!r} names no backticked .md path")
        body: list[str] = []
        i += 1
        while i < len(section) and section[i].strip() != "```":
            body.append(section[i])
            i += 1
        if i >= len(section):
            raise AssertionError(f"a fenced markdown block in {heading!r} is not closed")
        pages.append((match.group(1), "\n".join(body) + "\n"))
        i += 1
    if len(pages) < 2:
        raise AssertionError(f"{heading!r} carries fewer than two fenced markdown blocks")
    return pages


FR004_LOG_LINE = "- 2026-11-07 — resolve retry-budget (decision): conflict with retry-policy, decided by issue: 31"


class TestResolutionRule(ConflictCase):
    def _resolved_pages(self) -> tuple[str, str, str, str]:
        left, right = self.create_pair()
        left_new = page_text("retry-budget", body="A client retries a call at most 5 times.").replace(
            "  - path: notes.md\n", "  - issue: 31\n"
        )
        right_new = page_text("retry-policy", body="A client retries a call at most 5 times.").replace(
            "  - path: notes.md\n", "  - pr: 22\n"
        )
        return left, right, left_new, right_new

    def _draft(self, name: str, pages: dict[str, str], log_line: str) -> Path:
        draft = self.root / name
        for rel, text in pages.items():
            target = draft / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        (draft / "log.md").write_text(log_line + "\n", encoding="utf-8")
        bases = {rel: api.read_page(rel, self.paths).sha256 for rel in pages}
        (draft / ".base.json").write_text(json.dumps(bases) + "\n", encoding="utf-8")
        return draft

    def test_both_callouts_in_one_patch_set_clear_the_pair_through_the_cli(self) -> None:
        left, right, left_new, right_new = self._resolved_pages()
        draft = self._draft("resolve-both", {left: left_new, right: right_new}, FR004_LOG_LINE)
        result = self.cli("propose", "--from", str(draft), "--name", "resolve", "--promote")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"fact-check: {left}: 1 item(s) removed", result.stderr)
        self.assertIn("  - retry_budget", result.stderr)
        self.assertIn(f"fact-check: {right}: 1 item(s) removed", result.stderr)
        self.assertIn("  - retry_policy", result.stderr)
        self.assertIn("applied", result.stdout)

        plan = json.loads((self.paths.applied_dir / "resolve" / "plan.json").read_text(encoding="utf-8"))
        updates = [edit for edit in plan["edits"] if edit["action"] == "update"]
        self.assertEqual(len(updates), 2)
        self.assertEqual([edit["fact_warnings"] for edit in updates], [["retry_budget"], ["retry_policy"]])
        self.assertTrue(all(edit["base_sha256"] for edit in updates))
        self.assertTrue((self.paths.applied_dir / "resolve" / "receipt.json").is_file())

        self.assertIn("  - issue: 31\n", (self.wiki / left).read_text(encoding="utf-8"))
        log_lines = (self.wiki / "log.md").read_text(encoding="utf-8").splitlines()
        self.assertEqual(log_lines[-1], FR004_LOG_LINE)
        self.assertEqual(_conflict_findings(api.findings(self.paths)), [])

    def test_removing_one_callout_leaves_one_one_sided_conflict(self) -> None:
        left, right, left_new, _ = self._resolved_pages()
        base = api.read_page(left, self.paths).sha256
        edit = PageEdit(left, "update", left_new, "half the resolution", base_sha256=base)
        api.promote(api.propose([edit], self.paths, name="resolve-one"), self.paths)
        self.assertEqual(_conflict_findings(api.findings(self.paths)), [("conflict-one-sided", (right, left))])


class TestApprovalThroughTheGate(ConflictCase):
    """FR-019: a callout pair is not a lint or approval rule; the kinds live in ``findings`` only."""

    def test_a_matched_pair_lints_clean_and_both_pages_approve(self) -> None:
        left, right = self.create_pair()
        approved = api.approve([left, right], self.paths, by="alice")
        self.assertEqual(len(approved.published), 2)
        for rel in (left, right):
            self.assertEqual(self.state(rel).state, "approved")

        lint = api.lint(self.paths, health=True, strict=True)
        self.assertEqual((lint.violations, lint.audit_errors), ((), ()))
        self.assertIsNotNone(lint.health)
        assert lint.health is not None
        self.assertEqual([finding.kind for finding in lint.health.findings], [])
        self.assertTrue(lint.passed)
        for argv in (("lint",), ("lint", "--health", "--strict")):
            result = self.cli(*argv)
            self.assertEqual(result.returncode, 0, result.stderr)

        self.assertEqual(_conflict_findings(api.findings(self.paths)), [("open-conflict", (left, right))])

    def test_a_marker_line_without_a_page_link_promotes_and_is_dangling(self) -> None:
        self.create("solo-target")
        rel = self.create(
            "no-link-marker",
            body="A bad marker.\n\n> [!conflict] This page disagrees.\n> [the other page](solo-target.md)",
        )
        self.assertTrue((self.wiki / rel).is_file(), "the page did not promote")
        lint = self.cli("lint")
        self.assertEqual(lint.returncode, 0, lint.stderr)
        (finding,) = _dangling(api.findings(self.paths))
        self.assertEqual(finding.pages, (rel,))
        self.assertIn("names no wiki page", finding.description)


if __name__ == "__main__":
    unittest.main()
