# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.11.0 (US5): ``source-not-at-revision`` and the ``revision_check`` run state (FR-025 to FR-029).

Each case builds a managed wiki inside a temporary git repository (and, where
it needs one, a source root beside it) and runs ``findings`` through the API,
the CLI, ``nightly`` and the MCP ``findings`` tool. The cases are skipped only
when git is not on PATH.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

from tests.conftest import make_repo_layout, run_cli
from tests.test_revisions import ABSENT_COMMIT, UPPERCASE_SHA, commit_file, make_repo, write_page
from wiki_studio import api, revisions
from wiki_studio.findings import KIND_SOURCE_NOT_AT_REVISION
from wiki_studio.mcp_adapter.config import parse_launch
from wiki_studio.mcp_adapter.tools import WikiTools
from wiki_studio.mcp_adapter.trace import TOOL_RESULT_KEYS
from wiki_studio.paths import WikiPaths
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
