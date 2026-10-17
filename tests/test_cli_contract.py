# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""CLI contract tests: every verb runs in-process through ``wiki_studio.cli.main``.

Pins the exit-code mapping and the per-verb flags against temporary
project layouts. The codes are asserted through the exception classes'
``exit_code`` attributes so the mapping is documented in one place.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.conftest import FIXTURES_DIR, SAMPLE_INCIDENT, make_repo_layout, run_cli
from wiki_studio.cli import EXIT_PATH_OUT_OF_REPO
from wiki_studio.errors import (
    AuditFlushError,
    BackendNotFoundError,
    PromoteValidationError,
    SourceMissingError,
)

_VERBS = ("ingest", "promote", "query", "lint", "audit-flush", "info", "init", "propose", "find")

_PAGE = (
    "---\npage_type: {page_type}\nslug: {slug}\ntitle: {title}\nstatus: stable\n"
    "last_reviewed: 2026-05-06\nsources:\n  - path: {source}\n    sha: abc\n---\n\n# {title}\n\n{body}\n"
)


def _write_page(wiki: Path, rel: str, *, page_type: str, title: str, body: str, source: str = "README.md") -> None:
    target = wiki / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        _PAGE.format(page_type=page_type, slug=target.stem, title=title, body=body, source=source),
        encoding="utf-8",
    )


def _wiki_with_pages(root: Path) -> Path:
    """Add two linked concept pages (and a README they cite) to a layout."""
    (root / "README.md").write_text("# Root\n", encoding="utf-8")
    wiki = root / "knowledge" / "wiki"
    (wiki / "index.md").write_text(
        "---\npage_type: index\nslug: index\ntitle: Index\nstatus: stable\nlast_reviewed: 2026-05-06\n---\n\n"
        "# Index\n\n## Concepts\n\n"
        "- [Origin Alignment](concepts/origin-alignment.md) — the breaker.\n"
        "- [Spec Drift](concepts/spec-drift.md) — when specs diverge.\n",
        encoding="utf-8",
    )
    _write_page(
        wiki,
        "concepts/origin-alignment.md",
        page_type="concept",
        title="Origin Alignment",
        body="Origin alignment and breakers; see [spec drift](spec-drift.md).",
    )
    _write_page(
        wiki,
        "concepts/spec-drift.md",
        page_type="concept",
        title="Spec Drift",
        body="Specs and drift; see [origin alignment](origin-alignment.md).",
    )
    return wiki


def _proposals_dir(root: Path, slug: str = "cli-fixture") -> Path:
    """A three-edit patch-set (create + append-log + append-index) under the layout."""
    prop = root / "doc_internal" / "proposals" / f"2026-05-06-{slug}"
    (prop / "preview" / "incidents").mkdir(parents=True)
    (prop / "preview" / "incidents" / f"{slug}.md").write_text(
        "---\n"
        f"page_type: incident\nslug: {slug}\ntitle: CLI Fixture\nstatus: draft\nlast_reviewed: 2026-05-06\n"
        "sources:\n  - path: src.md\n    sha: abc1234\n---\n\n# CLI Fixture\n\nBody.\n",
        encoding="utf-8",
    )
    (prop / "preview" / "log.md").write_text(f"- 2026-05-06 — promote {slug} (incident).", encoding="utf-8")
    (prop / "preview" / "index.md").write_text(f"- [CLI Fixture](incidents/{slug}.md) — fixture.", encoding="utf-8")
    plan = {
        "version": 1,
        "source_path": "src.md",
        "backend": "test",
        "rationale": "fixture",
        "edits": [
            {
                "path": f"incidents/{slug}.md",
                "action": "create",
                "rationale": "r",
                "preview": f"preview/incidents/{slug}.md",
            },
            {"path": "log.md", "action": "append-log", "rationale": "r", "preview": "preview/log.md"},
            {"path": "index.md", "action": "append-index", "rationale": "r", "preview": "preview/index.md"},
        ],
    }
    (prop / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return prop


class _LayoutCase(unittest.TestCase):
    """A fresh layout (schema + bash linter + sample source) per test."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-cli-")
        self.root = make_repo_layout(Path(self._tmp.name), with_schema=True)
        self.sample = self.root / "sample-incident.md"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_cli(self, *argv: str):
        return run_cli(*argv, cwd=self.root)


class TestCliHelp(_LayoutCase):
    def test_top_level_help_lists_verbs_and_exit_codes(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        for verb in _VERBS:
            self.assertIn(verb, result.stdout)
        self.assertIn("Exit codes", result.stdout)

    def test_version_prints_the_package_version(self) -> None:
        from wiki_studio import __version__

        result = self.run_cli("--version")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), __version__)
        self.assertEqual(__version__, "0.4.1")

    def test_each_verb_help_exits_zero(self) -> None:
        for verb in _VERBS:
            with self.subTest(verb=verb):
                result = self.run_cli(verb, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(verb, result.stdout)

    def test_unknown_verb_falls_back_to_legacy_shape(self) -> None:
        # No known verb in argv is the legacy v1 shape (``ingest --legacy-single-source <source>``);
        # the extra positional is then an argparse usage error (exit 2).
        result = self.run_cli("frobnicate", "x")
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage:", result.stderr)


class TestCliIngest(_LayoutCase):
    def test_check_and_dry_run_are_mutually_exclusive(self) -> None:
        # Multi-page path (no --legacy-single-source): the check runs before dispatch.
        result = self.run_cli("ingest", str(self.sample), "--backend", "test", "--check", "--dry-run")
        self.assertEqual(result.returncode, 1)
        self.assertIn("mutually exclusive", result.stderr)

    def test_check_and_dry_run_are_mutually_exclusive_on_legacy_path(self) -> None:
        result = self.run_cli(
            "ingest", "--legacy-single-source", str(self.sample), "--backend", "test", "--check", "--dry-run"
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("mutually exclusive", result.stderr)

    def test_legacy_check_mode_has_no_side_effects(self) -> None:
        result = self.run_cli("ingest", "--legacy-single-source", str(self.sample), "--backend", "test", "--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / "knowledge" / "wiki" / ".audit").exists())
        self.assertEqual(list((self.root / "doc_internal" / "proposals").iterdir()), [])

    def test_multi_page_check_mode_has_no_side_effects(self) -> None:
        result = self.run_cli("ingest", str(self.sample), "--backend", "test", "--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / "knowledge" / "wiki" / ".audit").exists())
        self.assertEqual(list((self.root / "doc_internal" / "proposals").iterdir()), [])

    def test_default_output_dir_is_doc_internal_proposals(self) -> None:
        result = self.run_cli("ingest", str(self.sample), "--backend", "test")
        self.assertEqual(result.returncode, 0, result.stderr)
        written = Path(result.stdout.strip())
        self.assertEqual(written.parent, self.root / "doc_internal" / "proposals")
        self.assertTrue((self.root / "knowledge" / "wiki" / ".audit" / "ingest-log.md").is_file())

    def test_multi_page_dry_run_writes_dir_and_audit_line(self) -> None:
        result = self.run_cli("ingest", str(self.sample), "--backend", "test", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((Path(result.stdout.strip()) / "plan.json").is_file())

    def test_out_of_repo_source_exits_7_unless_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as out:
            refused = self.run_cli("ingest", str(SAMPLE_INCIDENT), "--backend", "test", "--output-dir", out)
            self.assertEqual(refused.returncode, EXIT_PATH_OUT_OF_REPO)
            self.assertIn("--allow-out-of-repo", refused.stderr)
            allowed = self.run_cli(
                "ingest", str(SAMPLE_INCIDENT), "--backend", "test", "--output-dir", out, "--allow-out-of-repo"
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)

    def test_legacy_out_of_repo_source_exits_7(self) -> None:
        with tempfile.TemporaryDirectory() as out:
            result = self.run_cli(
                "ingest", "--legacy-single-source", str(SAMPLE_INCIDENT), "--backend", "test", "--output-dir", out
            )
        self.assertEqual(result.returncode, EXIT_PATH_OUT_OF_REPO)

    def test_backend_cli_missing_from_path_exits_2(self) -> None:
        with patch("wiki_studio.backends.shutil.which", return_value=None):
            result = self.run_cli("ingest", str(self.sample), "--backend", "claude")
        self.assertEqual(result.returncode, BackendNotFoundError.exit_code)

    def test_debug_unsafe_output_flag_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as out:
            result = self.run_cli(
                "ingest", str(self.sample), "--backend", "test", "--output-dir", out, "--debug-unsafe-output"
            )
        self.assertEqual(result.returncode, 0, result.stderr)


class TestCliPromote(_LayoutCase):
    def test_promote_applies_patch_set(self) -> None:
        prop = _proposals_dir(self.root)
        result = self.run_cli("promote", str(prop))
        self.assertEqual(result.returncode, 0, result.stderr)
        # 3 patch-set edits + the 2 audit-archive files staged under .audit/proposals/.
        self.assertIn("applied 5 edit(s)", result.stdout)
        self.assertTrue((self.root / "knowledge" / "wiki" / "incidents" / "cli-fixture.md").is_file())

    def test_promote_dry_run_leaves_wiki_unchanged(self) -> None:
        prop = _proposals_dir(self.root)
        result = self.run_cli("promote", str(prop), "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dry-run", result.stdout)
        self.assertFalse((self.root / "knowledge" / "wiki" / "incidents").exists())

    def test_promote_already_applied_is_a_noop(self) -> None:
        prop = _proposals_dir(self.root)
        self.assertEqual(self.run_cli("promote", str(prop)).returncode, 0)
        archived = self.root / "doc_internal" / "proposals" / ".applied" / prop.name
        result = self.run_cli("promote", str(archived))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no-op", result.stdout)

    def test_promote_missing_dir_exits_5(self) -> None:
        result = self.run_cli("promote", str(self.root / "doc_internal" / "proposals" / "nope"))
        self.assertEqual(result.returncode, SourceMissingError.exit_code)

    def test_promote_validation_failure_exits_9(self) -> None:
        prop = _proposals_dir(self.root, slug="bad-fixture")
        preview = prop / "preview" / "incidents" / "bad-fixture.md"
        preview.write_text(preview.read_text().replace("slug: bad-fixture", "slug: wrong"), encoding="utf-8")
        result = self.run_cli("promote", str(prop))
        self.assertEqual(result.returncode, PromoteValidationError.exit_code)
        self.assertIn("promote validation failed", result.stderr)


class TestCliQuery(_LayoutCase):
    def setUp(self) -> None:
        super().setUp()
        _wiki_with_pages(self.root)

    def test_query_prints_answer_and_citations(self) -> None:
        result = self.run_cli("query", "origin alignment breaker", "--backend", "test")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.strip())
        self.assertIn("--- citations ---", result.stderr)
        self.assertTrue((self.root / "doc_internal" / "wiki-query-log.jsonl").is_file())

    def test_query_max_pages_flag(self) -> None:
        result = self.run_cli("query", "origin alignment", "--backend", "test", "--max-pages", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("pages loaded: 1", result.stderr)

    def test_query_file_back_writes_patch_set(self) -> None:
        with tempfile.TemporaryDirectory() as out:
            result = self.run_cli(
                "query", "origin alignment breaker", "--backend", "test", "--file-back", "--output-dir", out
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("file-back patch-set", result.stderr)
            self.assertTrue(any(p.name.endswith("query-fileback") for p in Path(out).iterdir()))

    def test_query_backend_not_found_exits_2(self) -> None:
        result = self.run_cli("query", "anything", "--backend", "bogus")
        self.assertEqual(result.returncode, BackendNotFoundError.exit_code)

    def test_query_without_index_exits_5(self) -> None:
        (self.root / "knowledge" / "wiki" / "index.md").unlink()
        result = self.run_cli("query", "anything", "--backend", "test")
        self.assertEqual(result.returncode, SourceMissingError.exit_code)


class TestCliLint(_LayoutCase):
    def setUp(self) -> None:
        super().setUp()
        _wiki_with_pages(self.root)

    def test_structural_clean_exits_zero(self) -> None:
        result = self.run_cli("lint")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("audit-format: clean", result.stdout)

    def test_audit_format_violation_is_advisory_unless_strict(self) -> None:
        shutil.copytree(
            FIXTURES_DIR / "wiki_audit" / "invalid-missing-marker", self.root / "knowledge" / "wiki" / ".audit"
        )
        advisory = self.run_cli("lint")
        self.assertEqual(advisory.returncode, 0, advisory.stderr)
        self.assertIn("audit-format:", advisory.stderr)
        strict = self.run_cli("lint", "--strict")
        self.assertEqual(strict.returncode, 1)

    def test_health_without_backend_is_advisory(self) -> None:
        _write_page(
            self.root / "knowledge" / "wiki",
            "concepts/stale.md",
            page_type="concept",
            title="Stale",
            body="Cites a source that is gone.",
            source="docs/this-file-does-not-exist.md",
        )
        index = self.root / "knowledge" / "wiki" / "index.md"
        index.write_text(index.read_text() + "- [Stale](concepts/stale.md) — stale.\n", encoding="utf-8")
        advisory = self.run_cli("lint", "--health")
        self.assertEqual(advisory.returncode, 0, advisory.stderr)
        self.assertIn("stale-claim", advisory.stderr)
        strict = self.run_cli("lint", "--health", "--strict", "--paths", "concepts/stale.md")
        self.assertEqual(strict.returncode, 1)

    def test_health_clean_reports_pages_checked(self) -> None:
        result = self.run_cli("lint", "--health")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("knowledge-health: clean", result.stdout)

    def test_health_backend_not_found_exits_2(self) -> None:
        result = self.run_cli("lint", "--health", "--backend", "bogus")
        self.assertEqual(result.returncode, BackendNotFoundError.exit_code)


class TestCliAuditFlush(_LayoutCase):
    def test_outside_a_git_work_tree_exits_11(self) -> None:
        result = self.run_cli("audit-flush", "--dry-run")
        self.assertEqual(result.returncode, AuditFlushError.exit_code)
        self.assertIn("not a git work tree", result.stderr)

    def test_dry_run_reports_pending_lines(self) -> None:
        git = ["git", "-C", str(self.root)]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "config", "user.email", "t@example.com"], check=True)
        subprocess.run([*git, "config", "user.name", "T"], check=True)
        subprocess.run([*git, "add", "."], check=True)
        subprocess.run([*git, "commit", "-q", "-m", "init"], check=True)
        self.assertEqual(self.run_cli("ingest", str(self.sample), "--backend", "test").returncode, 0)
        result = self.run_cli("audit-flush", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 pending", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
