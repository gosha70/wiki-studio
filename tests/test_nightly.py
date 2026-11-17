# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.10.0 (US1): the model-free nightly pass, its report and the no-side-effect proof (FR-001 - FR-008)."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.conftest import make_repo_layout
from wiki_studio import __version__, api, nightly
from wiki_studio.errors import BackendNotFoundError, ContractViolationError
from wiki_studio.paths import WikiPaths
from wiki_studio.wikilock import lock_path_for

_PAGE = (
    "---\n"
    "page_type: decision\n"
    "slug: {slug}\n"
    "title: {title}\n"
    "status: stable\n"
    "last_reviewed: 2026-11-16\n"
    "sources:\n"
    "  - path: {source}\n"
    "---\n\n"
    "# {title}\n\n"
    "## Decision\n\n{body}\n\n"
    "## Context\n\nAgreed with the platform team.\n\n"
    "## Alternatives considered\n\nFixed 1 s delay.\n\n"
    "## Consequences\n\nLong outages wait at most 8 s between tries.\n"
)

_INDEX = (
    "---\npage_type: index\nslug: index\ntitle: Test Wiki\nstatus: stable\nlast_reviewed: 2026-11-16\n---\n"
    "\n# Test Wiki\n\n{links}\n"
)


def _page(slug: str, *, body: str = "Start at 250 ms.", source: str = "notes.md") -> str:
    """A valid decision page under ``decisions/``."""
    return _PAGE.format(slug=slug, title=slug.replace("-", " ").title(), source=source, body=body)


class NightlyCase(unittest.TestCase):
    """A managed wiki in a temporary project layout, built with ``make_repo_layout``."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-nightly-")
        self.root = make_repo_layout(Path(self._tmp.name))
        (self.root / "notes.md").write_text("# notes\n", encoding="utf-8")
        self.paths = WikiPaths.for_root(self.root)
        api.init(self.paths)
        self.wiki = self.paths.wiki_dir
        self.proposals = self.paths.proposals_dir

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # -- fixtures -------------------------------------------------

    def write_page(self, rel: str, text: str) -> None:
        target = self.wiki / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def write_index(self, *rels: str) -> None:
        links = "\n".join(f"- [{Path(rel).stem}]({rel})" for rel in rels)
        (self.wiki / "index.md").write_text(_INDEX.format(links=links), encoding="utf-8")

    def build_findings_wiki(self) -> None:
        """A lint-clean wiki with a stale claim, weak orphans, a missing cross-link and unapproved pages."""
        self.write_index("decisions/alpha.md", "decisions/beta.md", "decisions/gamma.md", "decisions/delta.md")
        self.write_page("decisions/alpha.md", _page("alpha", body="Use gamma first."))
        self.write_page("decisions/beta.md", _page("beta", body="Then gamma."))
        self.write_page("decisions/gamma.md", _page("gamma", body="Gamma is the plan."))
        self.write_page("decisions/delta.md", _page("delta", body="Gamma again.", source="gone.md"))

    # -- the model-free proof (FR-007) ----------------------------

    def wiki_snapshot(self) -> dict[str, str]:
        """Every file under the wiki: relative path -> sha256, ``.audit/`` included."""
        return {
            path.relative_to(self.wiki).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(self.wiki.rglob("*"))
            if path.is_file()
        }

    def assert_model_free(self, before: dict[str, str]) -> None:
        """FR-007: the wiki is unchanged, no lock sits beside it and no proposal directory appears."""
        self.assertEqual(self.wiki_snapshot(), before, "a model-free run writes nothing under the wiki")
        self.assertFalse(lock_path_for(self.wiki).exists(), "a model-free run takes no wiki lock")
        self.assertEqual(sorted(self.proposals.iterdir()), [], "a model-free run writes no proposal directory")


class TestTheReport(NightlyCase):
    def test_a_clean_wiki_reports_nothing_and_exits_zero(self) -> None:
        before = self.wiki_snapshot()
        result = api.nightly(self.paths)
        self.assert_model_free(before)
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.lint.passed)
        report = result.render_markdown()
        self.assertIn("## Lint\n\nclean", report)
        self.assertIn("## Findings\n\nnone", report)
        self.assertIn("### Findings\n\nnone", report)
        self.assertIn("### Pending proposals\n\nnone", report)

    def test_the_report_has_the_fixed_headings_and_the_header_list(self) -> None:
        result = api.nightly(self.paths)
        report = result.render_markdown()
        self.assertEqual(
            [line for line in report.splitlines() if line.startswith("#")],
            [
                "# wiki-studio nightly report",
                "## Lint",
                "## Findings",
                "## Needs a curator",
                "### Findings",
                "### Pending proposals",
            ],
        )
        self.assertIn(f"- Run time (UTC): {result.run_at}", report)
        self.assertIn(f"- Wiki directory: {self.wiki.resolve()}", report)
        self.assertIn(f"- Proposals directory: {self.proposals.resolve()}", report)
        self.assertIn(f"- Package version: {__version__}", report)
        self.assertRegex(result.run_at, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertNotIn("## Proposals", report)
        self.assertNotIn("drafting", report)

    def test_a_structurally_broken_wiki_exits_one_and_still_lists_the_findings(self) -> None:
        self.write_page("decisions/orphan.md", _page("orphan"))
        before = self.wiki_snapshot()
        result = api.nightly(self.paths)
        self.assert_model_free(before)
        self.assertFalse(result.lint.passed)
        self.assertEqual(result.exit_code, 1)
        report = result.render_markdown()
        self.assertIn("Lint failed with structural violations:", report)
        violation = "decisions/orphan.md: orphan — not reachable from index.md"
        self.assertIn(violation, report)
        self.assertIn("[unapproved / warning] decisions/orphan.md:", report)
        self.assertIn("- [unapproved] decisions/orphan.md", report)
        self.assertLess(report.index(violation), report.index("## Findings"))

    def test_audit_format_errors_are_listed_and_do_not_fail_lint(self) -> None:
        (self.wiki / ".audit").mkdir()
        (self.wiki / ".audit" / "notes.md").write_text("stray\n", encoding="utf-8")
        before = self.wiki_snapshot()
        result = api.nightly(self.paths)
        self.assert_model_free(before)
        self.assertTrue(result.lint.passed)
        self.assertTrue(result.lint.audit_errors)
        self.assertEqual(result.exit_code, 0)
        report = result.render_markdown()
        self.assertIn("Lint passed.", report)
        self.assertIn("Audit-format errors (reported; they do not fail lint):", report)
        self.assertIn("unexpected entry under .audit/", report)

    def test_health_and_review_findings_are_listed_with_no_backend_and_no_proposal(self) -> None:
        self.build_findings_wiki()
        before = self.wiki_snapshot()
        result = api.nightly(self.paths)
        self.assert_model_free(before)
        self.assertEqual(result.exit_code, 0)
        kinds = {finding.kind for finding in result.findings.findings}
        self.assertTrue({"stale-claim", "weak-orphan", "missing-cross-link", "unapproved"} <= kinds, kinds)
        self.assertEqual(result.needs_curator, result.findings.findings)
        report = result.render_markdown()
        self.assertIn("[stale-claim / warning] decisions/delta.md:", report)
        self.assertIn(
            "[missing-cross-link / warning] decisions/gamma.md, decisions/alpha.md, decisions/beta.md, "
            "decisions/delta.md:",
            report,
        )
        self.assertIn("- [weak-orphan] decisions/alpha.md", report)
        self.assertIn("- [unapproved] decisions/alpha.md", report)
        self.assertIn("stale-claim 1", report)
        self.assertIn("weak-orphan 4", report)
        self.assertIn("missing-cross-link 1", report)
        self.assertIn("unapproved 4", report)


class TestPendingProposals(NightlyCase):
    def test_pending_directories_list_their_edit_counts(self) -> None:
        (self.proposals / "nightly-b").mkdir()
        (self.proposals / "nightly-b" / "plan.json").write_text(
            json.dumps({"edits": [{"path": "a.md"}, {"path": "b.md"}]}), encoding="utf-8"
        )
        (self.proposals / "nightly-a").mkdir()
        (self.proposals / "nightly-a" / "plan.json").write_text(
            json.dumps({"edits": [{"path": "a.md"}]}), encoding="utf-8"
        )
        (self.proposals / "nightly-bad").mkdir()
        (self.proposals / "nightly-bad" / "plan.json").write_text("not json", encoding="utf-8")
        (self.proposals / "nightly-noplan").mkdir()
        (self.proposals / ".applied").mkdir()
        (self.proposals / "loose.txt").write_text("not a proposal\n", encoding="utf-8")
        before = self.wiki_snapshot()
        result = api.nightly(self.paths)
        self.assertEqual(self.wiki_snapshot(), before)
        self.assertFalse(lock_path_for(self.wiki).exists())
        self.assertEqual(
            [(pending.name, pending.edits) for pending in result.pending],
            [("nightly-a", 1), ("nightly-b", 2), ("nightly-bad", None), ("nightly-noplan", None)],
        )
        report = result.render_markdown()
        self.assertIn("- nightly-a (edits: 1)", report)
        self.assertIn("- nightly-b (edits: 2)", report)
        self.assertIn("- nightly-bad (edits unknown)", report)
        self.assertIn("- nightly-noplan (edits unknown)", report)
        self.assertNotIn(".applied", report)
        self.assertNotIn("loose.txt", report)
        self.assertEqual(
            result.as_dict()["needs_curator"]["pending"],
            [
                {"name": "nightly-a", "edits": 1},
                {"name": "nightly-b", "edits": 2},
                {"name": "nightly-bad", "edits": None},
                {"name": "nightly-noplan", "edits": None},
            ],
        )

    def test_a_missing_proposals_directory_lists_none(self) -> None:
        paths = WikiPaths.for_root(self.root, proposals_dir=self.root / "doc_internal" / "absent")
        result = api.nightly(paths)
        self.assertEqual(result.pending, ())
        self.assertIn("### Pending proposals\n\nnone", result.render_markdown())


class TestTheJsonForm(NightlyCase):
    def test_the_public_api_names_the_pass_and_its_result(self) -> None:
        self.assertIn("nightly", api.__all__)
        self.assertIn("NightlyResult", api.__all__)

    def test_as_dict_has_the_versioned_keys_and_the_findings_json_verbatim(self) -> None:
        self.build_findings_wiki()
        result = api.nightly(self.paths)
        data = result.as_dict()
        self.assertEqual(
            set(data),
            {
                "nightly_version",
                "package_version",
                "run_at",
                "wiki_dir",
                "proposals_dir",
                "lint",
                "findings",
                "needs_curator",
                "warnings",
                "exit_code",
            },
        )
        self.assertEqual(data["nightly_version"], 1)
        self.assertEqual(data["package_version"], __version__)
        self.assertEqual(data["run_at"], result.run_at)
        self.assertEqual(data["wiki_dir"], str(self.wiki.resolve()))
        self.assertEqual(data["proposals_dir"], str(self.proposals.resolve()))
        self.assertEqual(data["findings"], api.findings(self.paths).as_dict())
        self.assertEqual(data["lint"], {"passed": True, "violations": [], "audit_errors": []})
        self.assertEqual(set(data["needs_curator"]), {"findings", "pending"})
        self.assertEqual(data["needs_curator"]["findings"], [finding.as_dict() for finding in result.findings.findings])
        self.assertEqual(data["warnings"], [])
        self.assertEqual(data["exit_code"], 0)
        self.assertNotIn("drafting", data)
        self.assertNotIn("proposals", data)


class TestTheReportPath(NightlyCase):
    def test_a_path_inside_the_wiki_is_refused_naming_both(self) -> None:
        target = self.wiki / "report.md"
        with self.assertRaises(ValueError) as caught:
            nightly.check_report_path(target, self.paths)
        self.assertIn(str(target.resolve()), str(caught.exception))
        self.assertIn(str(self.wiki.resolve()), str(caught.exception))

    def test_the_wiki_directory_itself_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            nightly.check_report_path(self.wiki, self.paths)

    def test_a_symlinked_parent_reaching_into_the_wiki_is_refused(self) -> None:
        subdir = self.wiki / "decisions"
        subdir.mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "linked").symlink_to(subdir, target_is_directory=True)
        with self.assertRaises(ValueError):
            nightly.check_report_path(outside / "linked" / "report.md", self.paths)

    def test_a_path_outside_the_wiki_resolves(self) -> None:
        target = self.root / "reports" / "nightly.md"
        self.assertEqual(nightly.check_report_path(target, self.paths), target.resolve())

    def test_write_report_creates_parents_and_writes_utf8(self) -> None:
        target = self.root / "reports" / "deep" / "nightly.md"
        nightly.write_report("# rapport — é\n", target)
        self.assertEqual(target.read_text(encoding="utf-8"), "# rapport — é\n")
        self.assertEqual([path.name for path in target.parent.iterdir()], ["nightly.md"])

    def test_write_report_replaces_an_existing_file(self) -> None:
        target = self.root / "reports" / "nightly.md"
        target.parent.mkdir()
        target.write_text("old\n", encoding="utf-8")
        nightly.write_report("new\n", target)
        self.assertEqual(target.read_text(encoding="utf-8"), "new\n")
        self.assertEqual([path.name for path in target.parent.iterdir()], ["nightly.md"])

    def test_a_failed_write_leaves_no_temporary_file(self) -> None:
        target = self.root / "reports" / "nightly.md"
        target.parent.mkdir()
        target.write_text("old\n", encoding="utf-8")
        with patch("wiki_studio.nightly.os.replace", side_effect=OSError("disk full")), self.assertRaises(OSError):
            nightly.write_report("new\n", target)
        self.assertEqual([path.name for path in target.parent.iterdir()], ["nightly.md"])
        self.assertEqual(target.read_text(encoding="utf-8"), "old\n")


class TestNoWriteUnderTheWiki(NightlyCase):
    def test_the_wiki_is_byte_identical_and_no_lock_appears(self) -> None:
        self.build_findings_wiki()
        before = self.wiki_snapshot()
        result = api.nightly(self.paths)
        self.assertEqual(self.wiki_snapshot(), before)
        self.assertFalse(lock_path_for(self.wiki).exists())
        self.assertEqual(result.exit_code, 0)


class TestNoBackend(NightlyCase):
    def test_every_kind_of_run_completes_with_backend_resolution_patched_to_fail(self) -> None:
        failing = BackendNotFoundError("backend resolution must not be reached by nightly")
        with (
            patch("wiki_studio.backends.resolve_backend", side_effect=failing),
            patch("wiki_studio.api.resolve_backend", side_effect=failing),
            patch("wiki_studio.api.prepare_backend", side_effect=failing),
        ):
            clean = api.nightly(self.paths)
            self.build_findings_wiki()
            with_findings = api.nightly(self.paths)
            self.write_page("decisions/orphan.md", _page("orphan"))
            broken = api.nightly(self.paths)
        self.assertEqual((clean.exit_code, with_findings.exit_code, broken.exit_code), (0, 0, 1))
        self.assertTrue(with_findings.findings.findings)

    def test_the_pass_calls_lint_without_the_extra_tiers_and_findings_without_pages(self) -> None:
        with (
            patch("wiki_studio.api.lint", wraps=api.lint) as lint_mock,
            patch("wiki_studio.api.findings", wraps=api.findings) as findings_mock,
        ):
            nightly.run(self.paths)
        lint_mock.assert_called_once_with(self.paths)
        findings_mock.assert_called_once_with(self.paths)


class TestFailuresPropagate(NightlyCase):
    def test_an_exception_from_the_lint_read_propagates(self) -> None:
        with (
            patch("wiki_studio.api.lint", side_effect=ContractViolationError("newer manifest")),
            self.assertRaises(ContractViolationError),
        ):
            nightly.run(self.paths)

    def test_an_exception_from_the_findings_read_propagates(self) -> None:
        with (
            patch("wiki_studio.api.findings", side_effect=ContractViolationError("newer manifest")),
            self.assertRaises(ContractViolationError),
        ):
            nightly.run(self.paths)
