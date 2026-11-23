# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.11.0: ``source-not-at-revision``, the ``revision_check`` run state and ``source-revision-changed``.

US5 (FR-025 to FR-029) and US6 (FR-032 to FR-034). Each git case builds a
managed wiki inside a temporary git repository (and, where it needs one, a
source root beside it) and runs ``findings`` through the API, the CLI,
``nightly`` and the MCP ``findings`` tool; those cases are skipped only when
git is not on PATH. The study replay reads the committed record of
``eval/revisions/`` and runs no git.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest import mock

from eval.revisions import candidates
from tests.conftest import make_repo_layout, run_cli
from tests.test_approve import ApprovalCase, page_text
from tests.test_revisions import ABSENT_COMMIT, UPPERCASE_SHA, Spy, commit_file, git, make_repo, write_page
from wiki_studio import api, revisions
from wiki_studio.findings import KIND_SOURCE_NOT_AT_REVISION, KIND_SOURCE_REVISION_CHANGED
from wiki_studio.mcp_adapter.config import parse_launch
from wiki_studio.mcp_adapter.tools import WikiTools
from wiki_studio.mcp_adapter.trace import TOOL_RESULT_KEYS
from wiki_studio.paths import WikiPaths
from wiki_studio.proposal import PageEdit
from wiki_studio.review import STATE_APPROVED
from wiki_studio.wikilock import lock_path_for

if TYPE_CHECKING:
    from collections.abc import Sequence

    from wiki_studio.findings import Finding, FindingsResult

GIT = shutil.which("git")
OPTION_SHA = "--output=x"
REVISION_CHECK_KEYS = {"state", "reason", "repositories", "sources_checked", "sources_not_checked", "not_checked"}
TOOL_FINDINGS = "findings"


@unittest.skipUnless(GIT, "git is not installed")
class RevisionFindingsCase(unittest.TestCase):
    """A managed wiki in a git repository whose first commit lacks ``notes.md`` and whose HEAD has it."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-revision-findings-")
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name).resolve()
        self.root = make_repo_layout(self.base / "root")
        (self.root / "notes.md").write_text("# notes\n", encoding="utf-8")
        self.paths = WikiPaths.for_root(self.root)
        api.init(self.paths)
        self.wiki = self.paths.wiki_dir
        make_repo(self.root)
        self.before = commit_file(self.root, "README.md", "root\n")
        self.head = commit_file(self.root, "notes.md", "# notes\n")

    def page(self, name: str, sources: Sequence[tuple[str, str | None]], *, superseded_by: str | None = None) -> str:
        rel = write_page(self.wiki, name, sources)
        if superseded_by is not None:
            target = self.wiki / rel
            text = target.read_text(encoding="utf-8")
            target.write_text(
                text.replace("status: stable\n", f"status: stable\nsuperseded_by: {superseded_by}\n"), encoding="utf-8"
            )
        return rel

    def source_root(self, name: str = "src") -> tuple[Path, str, str]:
        """A source root whose first commit lacks ``lib/b.txt`` and whose HEAD has it: (path, first, HEAD)."""
        source = make_repo(self.base / name)
        first = commit_file(source, "a.txt", "a\n")
        head = commit_file(source, "lib/b.txt", "b\n")
        return source, first, head

    def revision_findings(self, result: FindingsResult) -> list[Finding]:
        return [finding for finding in result.findings if finding.kind == KIND_SOURCE_NOT_AT_REVISION]

    def only_finding(self, result: FindingsResult, page: str) -> Finding:
        found = self.revision_findings(result)
        self.assertEqual(len(found), 1, found)
        self.assertEqual(found[0].pages, (page,))
        self.assertEqual(found[0].severity, "warning")
        self.assertEqual(result.counts[KIND_SOURCE_NOT_AT_REVISION], 1)
        return found[0]

    def snapshot(self) -> dict[str, str]:
        """Path and sha256 of every file under the base: the wiki, the proposals directory, each work tree and .git."""
        return {
            path.relative_to(self.base).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(self.base.rglob("*"))
            if path.is_file()
        }


class TestTheThreeCauses(RevisionFindingsCase):
    """FR-025: one warning per source for each cause, naming the repository."""

    def test_a_path_absent_at_its_sha_in_the_root(self) -> None:
        rel = self.page("pinned", [("notes.md", self.before)])
        finding = self.only_finding(api.findings(self.paths), rel)
        for part in ("notes.md", self.before, str(self.root), self.head, "does not contain it"):
            self.assertIn(part, finding.description)

    def test_a_commit_no_repository_has_with_every_repository_usable(self) -> None:
        rel = self.page("unknown", [("notes.md", ABSENT_COMMIT)])
        finding = self.only_finding(api.findings(self.paths), rel)
        self.assertIn(ABSENT_COMMIT, finding.description)
        self.assertIn(f"none of the repositories searched has ({self.root})", finding.description)

    def test_a_malformed_sha_is_named_with_its_repr(self) -> None:
        for value in (OPTION_SHA, UPPERCASE_SHA):
            with self.subTest(sha=value):
                rel = self.page("malformed", [("notes.md", value)])
                finding = self.only_finding(api.findings(self.paths), rel)
                self.assertIn(f"malformed sha: {value!r}", finding.description)

    def test_the_three_causes_in_a_source_root(self) -> None:
        source, first, head = self.source_root()
        other, _, _ = self.source_root("other")
        paths = WikiPaths.for_root(self.root, source_roots=[source, other])
        added = self.page("added", [("lib/b.txt", first)])
        unknown = self.page("unknown", [("lib/b.txt", ABSENT_COMMIT)])
        malformed = self.page("malformed", [("lib/b.txt", OPTION_SHA)])
        result = api.findings(paths)
        by_page = {finding.pages: finding.description for finding in self.revision_findings(result)}
        self.assertEqual(set(by_page), {(added,), (unknown,), (malformed,)})
        for part in ("lib/b.txt", first, str(source), head):
            self.assertIn(part, by_page[(added,)])
        self.assertIn(f"({self.root}, {source}, {other})", by_page[(unknown,)])
        self.assertIn(repr(OPTION_SHA), by_page[(malformed,)])
        self.assertEqual(result.counts[KIND_SOURCE_NOT_AT_REVISION], 3)


class TestWhatIsNotAFinding(RevisionFindingsCase):
    def test_a_superseded_page_is_never_examined(self) -> None:
        live = self.page("live", [("notes.md", self.head)])
        self.page("old", [("notes.md", self.before)], superseded_by=live)
        result = api.findings(self.paths)
        self.assertEqual(self.revision_findings(result), [])
        self.assertEqual([source.page for source in result.revision_check.sources], [live])

    def test_a_path_without_a_sha_is_counted_and_is_no_finding(self) -> None:
        self.page("unpinned", [("notes.md", None)])
        result = api.findings(self.paths)
        self.assertEqual(self.revision_findings(result), [])
        data = result.revision_check.as_dict()
        self.assertEqual((data["sources_checked"], data["sources_not_checked"]), (0, 1))
        self.assertEqual(data["not_checked"], {"no sha": 1})

    def test_a_scoped_run_checks_only_its_pages(self) -> None:
        first = self.page("first", [("notes.md", self.before)])
        self.page("second", [("notes.md", ABSENT_COMMIT)])
        cli = run_cli("findings", "--json", "--paths", first, cwd=self.root)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        data = json.loads(cli.stdout)
        found = [f for f in data["findings"] if f["kind"] == KIND_SOURCE_NOT_AT_REVISION]
        self.assertEqual([f["pages"] for f in found], [[first]])
        self.assertEqual(data["revision_check"]["sources_checked"], 1)

    def test_a_commit_missing_while_a_repository_is_skipped_is_not_checked(self) -> None:
        plain = self.base / "plain"
        plain.mkdir()
        self.page("unknown", [("notes.md", ABSENT_COMMIT)])
        result = api.findings(WikiPaths.for_root(self.root, source_roots=[plain]))
        self.assertEqual(self.revision_findings(result), [])
        self.assertEqual(result.revision_check.as_dict()["not_checked"], {revisions.REASON_NOT_FOUND_SKIPPED: 1})


class TestTheRunState(RevisionFindingsCase):
    """FR-026: the ``revision_check`` object, additive within ``findings_version`` 1."""

    def test_a_used_root(self) -> None:
        self.page("pinned", [("notes.md", self.before)])
        data = api.findings(self.paths).as_dict()
        self.assertEqual(data["findings_version"], 1)
        check = data["revision_check"]
        self.assertEqual(set(check), REVISION_CHECK_KEYS)
        self.assertEqual(
            check,
            {
                "state": "on",
                "reason": None,
                "repositories": [
                    {"path": str(self.root), "role": "root", "status": "used", "reason": None, "head": self.head}
                ],
                "sources_checked": 1,
                "sources_not_checked": 0,
                "not_checked": {},
            },
        )

    def test_a_skipped_source_root(self) -> None:
        plain = self.base / "plain"
        plain.mkdir()
        check = api.findings(WikiPaths.for_root(self.root, source_roots=[plain])).as_dict()["revision_check"]
        self.assertEqual(check["state"], "on")
        self.assertEqual(
            check["repositories"][1],
            {
                "path": str(plain),
                "role": "source-root",
                "status": "skipped",
                "reason": revisions.REASON_NOT_A_WORK_TREE,
                "head": None,
            },
        )

    def test_git_missing_turns_the_check_off_with_no_revision_kind_and_exit_zero(self) -> None:
        self.page("pinned", [("notes.md", self.before)])
        self.page("malformed", [("notes.md", OPTION_SHA)])
        with mock.patch.object(revisions.subprocess, "run", side_effect=FileNotFoundError("git")):
            result = api.findings(self.paths)
            cli = run_cli("findings", "--root", str(self.root), cwd=self.root)
        check = result.revision_check.as_dict()
        self.assertEqual((check["state"], check["reason"]), ("off", revisions.REASON_GIT_NOT_FOUND))
        self.assertEqual(
            check["repositories"],
            [
                {
                    "path": str(self.root),
                    "role": "root",
                    "status": "skipped",
                    "reason": revisions.REASON_GIT_NOT_FOUND,
                    "head": None,
                }
            ],
        )
        self.assertEqual(result.counts[KIND_SOURCE_NOT_AT_REVISION], 0)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        self.assertEqual(cli.stdout.splitlines()[1], "revision check: off (git not found)")

    def test_outside_any_repository_the_check_is_off_and_findings_exits_zero(self) -> None:
        plain_root = make_repo_layout(self.base / "plain-project")
        (plain_root / "notes.md").write_text("# notes\n", encoding="utf-8")
        plain_paths = WikiPaths.for_root(plain_root)
        api.init(plain_paths)
        write_page(plain_paths.wiki_dir, "pinned", [("notes.md", self.before)])
        cli = run_cli("findings", "--json", cwd=plain_root)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        data = json.loads(cli.stdout)
        self.assertEqual(data["revision_check"]["state"], "off")
        self.assertEqual(data["revision_check"]["reason"], revisions.REASON_NO_USABLE_REPOSITORY)
        self.assertEqual(data["counts"][KIND_SOURCE_NOT_AT_REVISION], 0)


class TestSurfaces(RevisionFindingsCase):
    """FR-027: the text line, the nightly header line and JSON, and the MCP tool."""

    def test_the_text_output_prints_the_line_after_the_counts(self) -> None:
        rel = self.page("pinned", [("notes.md", self.before)])
        self.page("unpinned", [("notes.md", None)])
        cli = run_cli("findings", cwd=self.root)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        lines = cli.stdout.splitlines()
        self.assertTrue(lines[0].startswith("findings: "), lines[0])
        self.assertIn(f"{KIND_SOURCE_NOT_AT_REVISION} 1", lines[0])
        self.assertEqual(lines[1], "revision check: on (1 of 1 repositories used); 1 sources checked, 1 not checked")
        self.assertIn(f"  [{KIND_SOURCE_NOT_AT_REVISION} / warning] {rel}: ", cli.stdout)

    def test_the_text_line_counts_a_skipped_repository(self) -> None:
        plain = self.base / "plain"
        plain.mkdir()
        cli = run_cli("findings", "--source-root", str(plain), cwd=self.root)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        self.assertEqual(
            cli.stdout.splitlines()[1],
            "revision check: on (1 of 2 repositories used); 0 sources checked, 0 not checked",
        )

    def test_the_nightly_report_carries_the_line_and_the_kind_is_report_only(self) -> None:
        rel = self.page("pinned", [("notes.md", self.before)])
        result = api.nightly(self.paths)
        report = result.render_markdown()
        self.assertIn(
            "\n- Drafting: off (no --backend)\n"
            "- Revision check: on (1 of 1 repositories used); 1 sources checked, 0 not checked\n",
            report,
        )
        self.assertIn(f"- [{KIND_SOURCE_NOT_AT_REVISION} / warning] {rel}: ", report)
        self.assertIn(KIND_SOURCE_NOT_AT_REVISION, {finding.kind for finding in result.needs_curator})
        self.assertNotIn(KIND_SOURCE_NOT_AT_REVISION, {entry.kind for entry in result.not_drafted})
        data = result.as_dict()
        self.assertEqual(data["findings"]["revision_check"], result.findings.revision_check.as_dict())
        self.assertEqual(data["findings"]["revision_check"]["state"], "on")

    def test_the_mcp_findings_tool_carries_the_object(self) -> None:
        # The in-process tool layer is standard library, tested with or without the ``mcp`` extra, as
        # tests/test_mcp_adapter.py tests it; only the stdio server needs the SDK.
        self.page("pinned", [("notes.md", self.before)])
        config = parse_launch(["--root", str(self.root)], env={}, cwd=self.root)
        result = WikiTools(config, protocol_version=lambda: "2025-06-18").findings()
        self.assertEqual(set(result), set(TOOL_RESULT_KEYS[TOOL_FINDINGS]))
        self.assertEqual(result["revision_check"], api.findings(self.paths).as_dict()["revision_check"])
        self.assertEqual(result["counts"][KIND_SOURCE_NOT_AT_REVISION], 1)


class TestInvariants(RevisionFindingsCase):
    """FR-028: lint is unchanged, and findings writes nothing anywhere."""

    def test_lint_health_strict_exits_as_it_did_before(self) -> None:
        rel = self.page("pinned", [("notes.md", self.before)])
        self.assertEqual(len(self.revision_findings(api.findings(self.paths))), 1)
        with_cause = run_cli("lint", "--health", "--strict", cwd=self.root)
        self.assertNotIn(KIND_SOURCE_NOT_AT_REVISION, with_cause.stdout + with_cause.stderr)
        target = self.wiki / rel
        target.write_text(target.read_text(encoding="utf-8").replace(f"    sha: {self.before}\n", ""), encoding="utf-8")
        self.assertEqual(self.revision_findings(api.findings(self.paths)), [])
        without_cause = run_cli("lint", "--health", "--strict", cwd=self.root)
        self.assertEqual(with_cause.returncode, without_cause.returncode)

    def test_a_run_changes_no_file_in_the_wiki_the_proposals_directory_or_any_repository(self) -> None:
        source, first, _ = self.source_root()
        self.page("pinned", [("notes.md", self.before)])
        self.page("added", [("lib/b.txt", first)])
        paths = WikiPaths.for_root(self.root, source_roots=[source])
        before = self.snapshot()
        self.assertEqual(len(self.revision_findings(api.findings(paths))), 2)
        cli = run_cli("findings", "--json", "--source-root", str(source), cwd=self.root)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        api.nightly(paths)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(lock_path_for(self.wiki).exists())
        self.assertEqual(sorted(self.paths.proposals_dir.iterdir()), [])


# ── US6: source-revision-changed (C2 with the post-hoc anchor rule) ─────────

CEILING_V1 = "RETRY_CEILING = 8\nTIMEOUT = 1\n"
CEILING_V2 = "RETRY_CEILING = 16\nTIMEOUT = 1\n"
REVISIT_LINE = "Revisit when: the ceiling passes 32."
GUIDE_V1 = "# Guide\n\n## Retry policy\n\nWait 1 s.\n"
GUIDE_V2 = "# Guide\n\n## Retry policy\n\nWait 2 s.\n"


class RevisionChangedCase(RevisionFindingsCase):
    def body_page(self, name: str, path: str, sha: str, body: str) -> str:
        """A page citing ``path`` at ``sha`` whose body adds ``body`` after its heading."""
        rel = write_page(self.wiki, name, [(path, sha)])
        target = self.wiki / rel
        target.write_text(target.read_text(encoding="utf-8") + "\n" + body + "\n", encoding="utf-8")
        return rel

    def changed_findings(self, result: FindingsResult) -> list[Finding]:
        return [finding for finding in result.findings if finding.kind == KIND_SOURCE_REVISION_CHANGED]

    def changed_pages(self, result: FindingsResult) -> list[tuple[str, ...]]:
        return [finding.pages for finding in self.changed_findings(result)]


class TestSourceRevisionChanged(RevisionChangedCase):
    """FR-032: one warning per live page and changed source C2 flags, quoting ``Revisit when:``."""

    def test_a_changed_line_naming_an_anchor_flags_the_page_and_quotes_its_revisit_line(self) -> None:
        cited = commit_file(self.root, "retry.py", CEILING_V1)
        head = commit_file(self.root, "retry.py", CEILING_V2)
        rel = self.body_page("ceiling", "retry.py", cited, f"Waits stop at `RETRY_CEILING`.\n\n- {REVISIT_LINE}")
        result = api.findings(self.paths)
        (finding,) = self.changed_findings(result)
        self.assertEqual((finding.pages, finding.severity), ((rel,), "warning"))
        for part in ("retry.py", cited, str(self.root), head, f'"{REVISIT_LINE}"'):
            self.assertIn(part, finding.description)
        self.assertEqual(result.counts[KIND_SOURCE_REVISION_CHANGED], 1)
        self.assertEqual(self.revision_findings(result), [])

    def test_a_page_without_a_revisit_line_says_it_records_none(self) -> None:
        cited = commit_file(self.root, "retry.py", CEILING_V1)
        commit_file(self.root, "retry.py", CEILING_V2)
        self.body_page("ceiling", "retry.py", cited, "Waits stop at `RETRY_CEILING`.")
        (finding,) = self.changed_findings(api.findings(self.paths))
        self.assertIn("the page records no `Revisit when:` line", finding.description)

    def test_a_change_that_names_no_anchor_is_no_finding(self) -> None:
        cited = commit_file(self.root, "retry.py", CEILING_V1)
        commit_file(self.root, "retry.py", CEILING_V2)
        self.body_page("timeout", "retry.py", cited, "Each try waits `TIMEOUT` seconds.")
        result = api.findings(self.paths)
        self.assertEqual(self.changed_findings(result), [])
        self.assertEqual(result.revision_check.as_dict()["sources_checked"], 1)

    def test_fragment_anchors_are_ignored(self) -> None:
        # Under FR-032's rule `max`, `8` and the `py` of a backticked path name nothing a change can touch.
        cited = commit_file(self.root, "retry.py", CEILING_V1)
        commit_file(self.root, "retry.py", "RETRY_CEILING = 8\nTIMEOUT = 1\nmax = 8\npy = 1\n")
        rel = self.body_page("fragments", "retry.py", cited, "Use `max`, `8` and `lib/retry.py`.")
        self.assertEqual(revisions.page_anchors((self.wiki / rel).read_text(encoding="utf-8")), {"lib/retry.py"})
        self.assertEqual(self.changed_findings(api.findings(self.paths)), [])

    def test_a_page_naming_no_anchor_falls_back_to_a_change_beyond_whitespace(self) -> None:
        cited = commit_file(self.root, "retry.py", CEILING_V1)
        commit_file(self.root, "retry.py", "RETRY_CEILING  =  8\n\nTIMEOUT = 1\n")
        rel = self.body_page("plain", "retry.py", cited, "No identifiers here.")
        self.assertEqual(self.changed_findings(api.findings(self.paths)), [])
        commit_file(self.root, "retry.py", CEILING_V2)
        self.assertEqual(self.changed_pages(api.findings(self.paths)), [(rel,)])

    def test_a_markdown_hunk_under_a_heading_the_page_names_flags_it(self) -> None:
        cited = commit_file(self.root, "guide.md", GUIDE_V1)
        commit_file(self.root, "guide.md", GUIDE_V2)
        named = self.body_page("named", "guide.md", cited, "Follow the retry policy; see `unrelated_name`.")
        self.body_page("unnamed", "guide.md", cited, "See `unrelated_name` only.")
        self.assertEqual(self.changed_pages(api.findings(self.paths)), [(named,)])

    def test_in_a_source_root_the_finding_names_it(self) -> None:
        source = make_repo(self.base / "src")
        cited = commit_file(source, "retry.py", CEILING_V1)
        head = commit_file(source, "retry.py", CEILING_V2)
        self.body_page("ceiling", "retry.py", cited, "Waits stop at `RETRY_CEILING`.")
        (finding,) = self.changed_findings(api.findings(WikiPaths.for_root(self.root, source_roots=[source])))
        self.assertIn(f"in {source} the file changed", finding.description)
        self.assertIn(head, finding.description)

    def test_the_calls_follow_the_plan(self) -> None:
        cited = commit_file(self.root, "retry.py", CEILING_V1)
        commit_file(self.root, "retry.py", CEILING_V2)
        md_cited = commit_file(self.root, "guide.md", GUIDE_V1)
        commit_file(self.root, "guide.md", GUIDE_V2)
        self.body_page("anchored", "retry.py", cited, "Waits stop at `RETRY_CEILING`.")
        self.body_page("again", "retry.py", cited, "Also `RETRY_CEILING`.")
        self.body_page("plain", "retry.py", cited, "No identifiers here.")
        self.body_page("guided", "guide.md", md_cited, "Follow the retry policy; see `unrelated_name`.")
        spy = Spy()
        with mock.patch.object(revisions.subprocess, "run", spy):
            api.findings(self.paths)
        calls = spy.in_directory(self.root)
        quiet = [args for args in calls if "--quiet" in args]
        unified = [args for args in calls if "-U0" in args]
        blobs = [args for args in calls if args[:2] == ["cat-file", "blob"]]
        # p6 once per changed (commit, path) a page with an anchor needs, p5 only for the page naming none,
        # p7 only for the Markdown file.
        self.assertCountEqual([args[-1] for args in unified], ["retry.py", "guide.md"])
        self.assertEqual([args[-1] for args in quiet], ["retry.py"])
        self.assertEqual(blobs, [["cat-file", "blob", f"{md_cited}:./guide.md"]])


class TestWhatGetsNoRevisionKind(RevisionChangedCase):
    """FR-032: no ``source-revision-changed`` beside ``source-not-at-revision``, at HEAD absence or when superseded."""

    def test_a_path_missing_at_its_sha_gets_only_the_exact_kind(self) -> None:
        commit_file(self.root, "notes.md", "# notes\n\n`notes_marker` changed\n")
        rel = self.body_page("pinned", "notes.md", self.before, "Mentions `notes_marker`.")
        result = api.findings(self.paths)
        self.assertEqual([finding.pages for finding in self.revision_findings(result)], [(rel,)])
        self.assertEqual(self.changed_findings(result), [])

    def test_a_path_missing_at_head_gets_no_revision_kind(self) -> None:
        cited = commit_file(self.root, "gone.py", CEILING_V1)
        git(self.root, "rm", "-q", "--", "gone.py")
        git(self.root, "commit", "-q", "-m", "remove gone.py")
        self.body_page("gone", "gone.py", cited, "Waits stop at `RETRY_CEILING`.")
        result = api.findings(self.paths)
        self.assertEqual(self.changed_findings(result), [])
        self.assertEqual(self.revision_findings(result), [])

    def test_a_superseded_page_is_never_flagged(self) -> None:
        cited = commit_file(self.root, "retry.py", CEILING_V1)
        commit_file(self.root, "retry.py", CEILING_V2)
        live = self.body_page("live", "retry.py", cited, "No identifiers here.")
        old = self.body_page("old", "retry.py", cited, "Waits stop at `RETRY_CEILING`.")
        target = self.wiki / old
        target.write_text(
            target.read_text(encoding="utf-8").replace("status: stable\n", f"status: stable\nsuperseded_by: {live}\n"),
            encoding="utf-8",
        )
        self.assertEqual(self.changed_pages(api.findings(self.paths)), [(live,)])

    def test_the_cap_reached_before_the_decision_leaves_the_source_not_checked(self) -> None:
        cited = commit_file(self.root, "retry.py", CEILING_V1)
        commit_file(self.root, "retry.py", CEILING_V2)
        self.body_page("ceiling", "retry.py", cited, "Waits stop at `RETRY_CEILING`.")
        limit = 4  # p1, p2, p3 and p4 in the root: the p6 the decision needs is refused
        result = api.findings(WikiPaths.for_root(self.root, git_call_limit=limit))
        self.assertEqual(self.changed_findings(result), [])
        reason = revisions.REASON_CALL_LIMIT.format(limit=limit)
        self.assertEqual(result.revision_check.as_dict()["not_checked"], {reason: 1})


@unittest.skipUnless(GIT, "git is not installed")
class TestFlagStillReturn(ApprovalCase):
    """FR-033 (D13): a flagged page keeps its review state, can be approved and is still selected."""

    def setUp(self) -> None:
        super().setUp()
        make_repo(self.root)
        self.cited = commit_file(self.root, "retry.txt", "retry_ceiling = 8\n")
        commit_file(self.root, "retry.txt", "retry_ceiling = 16\n")
        text = page_text("retry-ceiling", body=f"Cap the retry waits with `retry_ceiling`.\n\n{REVISIT_LINE}")
        text = text.replace("  - path: notes.md\n", f"  - path: retry.txt\n    sha: {self.cited}\n")
        edits = [
            PageEdit("decisions/retry-ceiling.md", "create", text, "why"),
            PageEdit("index.md", "append-index", "- [retry-ceiling](decisions/retry-ceiling.md)", "why"),
        ]
        api.promote(api.propose(edits, self.paths, name="retry-ceiling"), self.paths)
        self.rel = "decisions/retry-ceiling.md"

    def flagged(self, result: FindingsResult) -> list[tuple[str, ...]]:
        return [finding.pages for finding in result.findings if finding.kind == KIND_SOURCE_REVISION_CHANGED]

    def test_review_state_is_unchanged_and_approve_still_works(self) -> None:
        before = api.review_state(self.paths, pages=[self.rel])
        self.assertEqual(self.flagged(api.findings(self.paths)), [(self.rel,)])
        self.assertEqual(api.review_state(self.paths, pages=[self.rel]), before)
        api.approve([self.rel], self.paths)
        (approved,) = api.review_state(self.paths, pages=[self.rel])
        self.assertEqual(approved.state, STATE_APPROVED)
        self.assertEqual(self.flagged(api.findings(self.paths)), [(self.rel,)])
        self.assertEqual(api.review_state(self.paths, pages=[self.rel]), [approved])

    def test_find_still_selects_the_flagged_page(self) -> None:
        self.assertEqual(self.flagged(api.findings(self.paths)), [(self.rel,)])
        self.assertIn(self.rel, [page.path for page in api.find("retry ceiling", self.paths).pages])

    def test_nightly_lists_the_kind_in_its_report_and_json_and_drafts_nothing_for_it(self) -> None:
        result = api.nightly(self.paths)
        self.assertIn(f"- [{KIND_SOURCE_REVISION_CHANGED} / warning] {self.rel}: ", result.render_markdown())
        self.assertEqual(result.as_dict()["findings"]["counts"][KIND_SOURCE_REVISION_CHANGED], 1)
        self.assertIn(KIND_SOURCE_REVISION_CHANGED, {finding.kind for finding in result.needs_curator})
        self.assertNotIn(KIND_SOURCE_REVISION_CHANGED, {entry.kind for entry in result.not_drafted})

    def test_the_mcp_findings_tool_carries_the_kind(self) -> None:
        config = parse_launch(["--root", str(self.root)], env={}, cwd=self.root)
        result = WikiTools(config, protocol_version=lambda: "2025-06-18").findings()
        self.assertEqual(result["counts"][KIND_SOURCE_REVISION_CHANGED], 1)
        kinds = {(finding["kind"], tuple(finding["pages"])) for finding in result["findings"]}
        self.assertIn((KIND_SOURCE_REVISION_CHANGED, (self.rel,)), kinds)

    def test_lint_health_strict_is_unaffected(self) -> None:
        with_cause = self.cli("lint", "--health", "--strict")
        self.assertNotIn(KIND_SOURCE_REVISION_CHANGED, with_cause.stdout + with_cause.stderr)
        target = self.wiki / self.rel
        target.write_text(target.read_text(encoding="utf-8").replace(f"    sha: {self.cited}\n", ""), encoding="utf-8")
        self.assertEqual(self.flagged(api.findings(self.paths)), [])
        without_cause = self.cli("lint", "--health", "--strict")
        self.assertEqual(with_cause.returncode, without_cause.returncode)


# ── FR-034: the study replayed through the shipped decision ────────────────

STEP_STATE_CHECKED = "checked"
CHANGED_STATUSES = frozenset({"M", "T"})
SHIPPED = "C2"


def shipped_flags(run: dict[str, Any], texts: dict[str, str]) -> set[tuple[str, str, str]]:
    """The (page, path, sha) entries ``revisions.revision_changed`` flags in one recorded run."""
    recorded = {(entry["repository"], entry["commit"], entry["path"]): entry for entry in run["paths"]}
    flagged: set[tuple[str, str, str]] = set()
    for page in run["pages"]:
        if page["superseded"]:
            continue
        for source in page["sources"]:
            if source["state"] != STEP_STATE_CHECKED or source["status"] not in CHANGED_STATUSES:
                continue
            entry = recorded[(source["repository"], source["commit"], posixpath.normpath(source["path"]))]
            hunks = [
                revisions.Hunk(hunk["old_start"], tuple(hunk["lines"]), hunk["heading"]) for hunk in entry["hunks"]
            ]
            if revisions.revision_changed(
                texts[page["page"]], hunks, markdown=entry["markdown"], whitespace_differs=entry["p5_differs"]
            ):
                flagged.add((page["page"], source["path"], source["sha"]))
    return flagged


class TestTheStudyReplayed(unittest.TestCase):
    """The shipped rule over the committed hunks reproduces the post-hoc C2 figures of ``results/candidates.json``."""

    protocol: dict[str, Any]
    case_runs: dict[str, dict[str, Any]]
    cases: dict[str, dict[str, Any]]
    study: set[tuple[str, str, str]]
    pre_successor: set[tuple[str, str, str]]
    flagged_cases: list[str]
    expected: dict[str, Any]
    rule: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol, hunks, cls.case_runs, cls.cases = candidates.load_inputs()
        texts = candidates._page_texts(cls.protocol, hunks)
        cls.study = shipped_flags(hunks["runs"][candidates.RUN_STUDY], texts)
        cls.pre_successor = shipped_flags(hunks["runs"][candidates.RUN_PRE_SUCCESSOR], texts)
        cls.flagged_cases = []
        for case_id, case in cls.cases.items():
            page = (candidates.REPO_ROOT / case["directory"] / "page.md").read_text(encoding="utf-8")
            if (case_id, case["path"], case["sha"]) in shipped_flags(cls.case_runs[case_id], {case_id: page}):
                cls.flagged_cases.append(case_id)
        results = json.loads(candidates.DEFAULT_OUT.read_text(encoding="utf-8"))
        cls.expected = results["post_hoc"]["candidates"][SHIPPED]
        cls.rule = results["post_hoc"]["rule"]

    def test_the_shipped_anchor_rule_is_the_measured_one(self) -> None:
        self.assertEqual(self.rule, candidates.POST_HOC_RULE)
        self.assertEqual(revisions.MIN_ANCHOR_LENGTH, candidates.POST_HOC_MIN_ANCHOR_LENGTH)

    def test_false_pages_and_entries(self) -> None:
        false_pages = set(self.protocol["false_pages"])
        false_entries = {(e["page"], e["path"], e["sha"]) for e in self.protocol["false_entries"]}
        flagged_pages = {entry[0] for entry in self.study}
        self.assertEqual(len(flagged_pages & false_pages), self.expected["false_pages_flagged_count"])
        self.assertEqual(len(self.study & false_entries), self.expected["false_entries_flagged_count"])

    def test_the_merge_entry_is_kept_on_the_pre_successor_copy(self) -> None:
        true_entry = self.protocol["true_entry"]
        key = (
            Path(true_entry["read_on"]).relative_to("eval/revisions").as_posix(),
            true_entry["path"],
            true_entry["sha"],
        )
        self.assertEqual(self.expected["true_entry"], candidates.KEPT)
        self.assertIn(key, self.pre_successor)

    def test_the_supplementary_positives_and_the_reported_only_cases(self) -> None:
        positives = [cid for cid, case in self.cases.items() if case["should_flag"] and not case["negative"]]
        reported = [cid for cid, case in self.cases.items() if not case["should_flag"] and not case["negative"]]
        self.assertEqual(len(positives), self.expected["supplementary_of"])
        self.assertEqual(
            len([cid for cid in positives if cid in self.flagged_cases]), self.expected["supplementary_kept"]
        )
        self.assertEqual({cid: cid in self.flagged_cases for cid in reported}, self.expected["reported_only"])

    def test_nothing_flagged_only_through_a_fragment_anchor_is_flagged(self) -> None:
        dropped = self.expected["flags_from_fragments_only"]
        for page, path, sha in dropped["study_entries"]:
            self.assertNotIn((page, path, sha), self.study)
        for case_id in dropped["cases"]:
            self.assertNotIn(case_id, self.flagged_cases)

    def test_the_shipped_decision_equals_the_scorer_without_fragments(self) -> None:
        protocol, hunks, _, _ = candidates.load_inputs()
        texts = candidates._page_texts(protocol, hunks)
        scored, _ = candidates.score_run(SHIPPED, hunks["runs"][candidates.RUN_STUDY], texts, fragments=False)
        self.assertEqual(self.study, scored)
