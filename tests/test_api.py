# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""aiwiki.api — the five library functions, their typed results and the exceptions they raise (FR-008)."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from aiwiki import api
from aiwiki.backends.copilot_cli import CopilotCliBackend
from aiwiki.backends.test import TestBackend
from aiwiki.errors import (
    AuditFlushError,
    BackendNotFoundError,
    PathOutsideRootError,
    PromoteValidationError,
    SourceMissingError,
)
from aiwiki.paths import WikiPaths
from aiwiki.promoter import PromoteResult
from tests.conftest import FIXTURES_DIR, SAMPLE_INCIDENT, make_repo_layout
from tests.test_cli_contract import _proposals_dir, _wiki_with_pages, _write_page


class _LayoutCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="aiwiki-api-")
        self.root = make_repo_layout(Path(self._tmp.name), with_schema=True)
        self.paths = WikiPaths.for_root(self.root)
        self.sample = self.root / "sample-incident.md"

    def tearDown(self) -> None:
        self._tmp.cleanup()


class TestIngest(_LayoutCase):
    def test_multi_page_ingest_writes_patch_set_and_audit_line(self) -> None:
        result = api.ingest(self.sample, self.paths, backend="test")
        self.assertEqual(result.disposition, "accept")
        self.assertIsInstance(result, api.IngestResult)
        assert result.written is not None
        self.assertTrue((result.written / "plan.json").is_file())
        self.assertEqual(result.written.parent, self.paths.proposals_dir)
        self.assertEqual(len(result.edits), 3)
        self.assertIn("log.md", result.edits)
        self.assertIsNotNone(result.patch)
        self.assertIsNone(result.proposal)
        assert result.record is not None
        self.assertEqual(result.record.backend, "test")
        self.assertTrue(self.paths.audit_log.is_file())
        self.assertTrue((result.written / ".ingest-snapshot" / "plan.json").is_file())

    def test_legacy_single_source_writes_a_proposal_file(self) -> None:
        result = api.ingest(self.sample, self.paths, backend="test", legacy_single_source=True)
        assert result.written is not None
        self.assertEqual(result.written.suffix, ".md")
        self.assertIsNotNone(result.proposal)
        self.assertIsNone(result.patch)
        self.assertEqual(result.edits, ("empty-index-commit-after-git-lock-bypass",))

    def test_check_mode_has_no_side_effects(self) -> None:
        for legacy in (False, True):
            with self.subTest(legacy=legacy):
                result = api.ingest(self.sample, self.paths, backend="test", check=True, legacy_single_source=legacy)
                self.assertTrue(result.check)
                self.assertIsNone(result.written)
                self.assertIsNone(result.record)
                self.assertEqual(result.disposition, "accept")
        self.assertFalse(self.paths.audit_log.exists())
        self.assertEqual(list(self.paths.proposals_dir.iterdir()), [])

    def test_legacy_dry_run_strips_the_body_and_hash(self) -> None:
        result = api.ingest(self.sample, self.paths, backend="test", legacy_single_source=True, dry_run=True)
        assert result.proposal is not None and result.record is not None
        self.assertTrue(result.dry_run)
        self.assertIsNone(result.proposal.draft_markdown)
        self.assertIsNone(result.record.proposal_hash)

    def test_check_and_dry_run_are_mutually_exclusive(self) -> None:
        with self.assertRaises(ValueError):
            api.ingest(self.sample, self.paths, backend="test", check=True, dry_run=True)

    def test_missing_source_raises(self) -> None:
        with self.assertRaises(SourceMissingError):
            api.ingest(self.root / "nope.md", self.paths, backend="test")

    def test_source_outside_root_raises_unless_allowed(self) -> None:
        with self.assertRaises(PathOutsideRootError) as ctx:
            api.ingest(SAMPLE_INCIDENT, self.paths, backend="test")
        self.assertEqual(ctx.exception.exit_code, 7)
        self.assertIn("--allow-out-of-repo", str(ctx.exception))
        result = api.ingest(SAMPLE_INCIDENT, self.paths, backend="test", allow_out_of_repo=True)
        assert result.record is not None
        self.assertFalse(result.record.source_repo_relative)

    def test_unknown_backend_name_raises(self) -> None:
        with self.assertRaises(BackendNotFoundError):
            api.ingest(self.sample, self.paths, backend="bogus")

    def test_backend_instance_is_used_as_given(self) -> None:
        result = api.ingest(self.sample, self.paths, backend=TestBackend())
        assert result.record is not None
        self.assertEqual(result.record.backend, "test")

    def test_output_dir_override(self) -> None:
        out = self.root / "inbox"
        result = api.ingest(self.sample, self.paths, backend="test", output_dir=out)
        assert result.written is not None
        self.assertEqual(result.written.parent, out)


class TestPromote(_LayoutCase):
    def test_promote_applies_and_archives(self) -> None:
        prop = _proposals_dir(self.root)
        result = api.promote(prop, self.paths)
        self.assertIsInstance(result, PromoteResult)
        self.assertEqual(len(result.applied_paths), 5)
        self.assertTrue((self.paths.wiki_dir / "incidents" / "cli-fixture.md").is_file())
        self.assertEqual(result.archived_dir, self.paths.applied_dir / prop.name)

    def test_promote_dry_run(self) -> None:
        prop = _proposals_dir(self.root)
        result = api.promote(prop, self.paths, dry_run=True)
        self.assertTrue(result.dry_run)
        self.assertFalse((self.paths.wiki_dir / "incidents").exists())

    def test_missing_dir_raises_source_missing(self) -> None:
        with self.assertRaises(SourceMissingError):
            api.promote(self.paths.proposals_dir / "nope", self.paths)

    def test_outside_root_raises_unless_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as other:
            prop = _proposals_dir(Path(other))
            with self.assertRaises(PathOutsideRootError):
                api.promote(prop, self.paths)
            result = api.promote(prop, self.paths, allow_out_of_repo=True)
            self.assertEqual(len(result.applied_paths), 5)

    def test_validation_failure_raises(self) -> None:
        prop = _proposals_dir(self.root, slug="bad-fixture")
        preview = prop / "preview" / "incidents" / "bad-fixture.md"
        preview.write_text(preview.read_text().replace("slug: bad-fixture", "slug: wrong"), encoding="utf-8")
        with self.assertRaises(PromoteValidationError):
            api.promote(prop, self.paths)


class TestQuery(_LayoutCase):
    def setUp(self) -> None:
        super().setUp()
        _wiki_with_pages(self.root)

    def test_query_returns_answer_with_citations(self) -> None:
        result = api.query("origin alignment breaker", self.paths, backend="test")
        self.assertIsInstance(result, api.QueryResult)
        self.assertTrue(result.answer.answer)
        self.assertIn("concepts/origin-alignment.md", result.answer.pages_loaded)
        self.assertIsNone(result.patch)
        self.assertTrue(self.paths.query_log.is_file())

    def test_max_pages_limits_the_selection(self) -> None:
        result = api.query("origin alignment drift", self.paths, backend="test", max_pages=1)
        self.assertEqual(len(result.answer.pages_loaded), 1)

    def test_file_back_writes_a_patch_set(self) -> None:
        result = api.query("origin alignment breaker", self.paths, backend="test", file_back=True)
        assert result.patch is not None and result.file_back_dir is not None
        self.assertEqual(len(result.patch.edits), 3)
        self.assertTrue((result.file_back_dir / "plan.json").is_file())
        self.assertEqual(result.file_back_dir.parent, self.paths.proposals_dir)

    def test_missing_index_raises(self) -> None:
        (self.paths.wiki_dir / "index.md").unlink()
        with self.assertRaises(SourceMissingError):
            api.query("anything", self.paths, backend="test")


class TestLint(_LayoutCase):
    def setUp(self) -> None:
        super().setUp()
        _wiki_with_pages(self.root)

    def test_clean_wiki_passes(self) -> None:
        result = api.lint(self.paths)
        self.assertIsInstance(result, api.LintResult)
        self.assertEqual(result.violations, ())
        self.assertEqual(result.pages_checked, 4)
        self.assertEqual(result.audit_errors, ())
        self.assertIsNone(result.health)
        self.assertTrue(result.passed)

    def test_structural_violation_always_fails(self) -> None:
        (self.paths.wiki_dir / "concepts" / "orphan.md").write_text("no frontmatter\n", encoding="utf-8")
        self.assertFalse(api.lint(self.paths).passed)
        self.assertFalse(api.lint(self.paths, strict=True).passed)

    def test_audit_violation_fails_only_under_strict(self) -> None:
        shutil.copytree(FIXTURES_DIR / "wiki_audit" / "invalid-missing-marker", self.paths.wiki_dir / ".audit")
        advisory = api.lint(self.paths)
        self.assertTrue(advisory.audit_errors)
        self.assertTrue(advisory.passed)
        self.assertFalse(api.lint(self.paths, strict=True).passed)

    def test_health_findings_fail_only_under_strict(self) -> None:
        _write_page(
            self.paths.wiki_dir,
            "concepts/stale.md",
            page_type="concept",
            title="Stale",
            body="Cites a missing source.",
            source="docs/missing.md",
        )
        index = self.paths.wiki_dir / "index.md"
        index.write_text(index.read_text() + "- [Stale](concepts/stale.md) — stale.\n", encoding="utf-8")
        advisory = api.lint(self.paths, health=True)
        assert advisory.health is not None
        self.assertTrue(any(f.kind == "stale-claim" for f in advisory.health.findings))
        self.assertTrue(advisory.passed)
        strict = api.lint(self.paths, health=True, strict=True, only=["concepts/stale.md"])
        self.assertFalse(strict.passed)

    def test_health_with_unknown_backend_raises(self) -> None:
        with self.assertRaises(BackendNotFoundError):
            api.lint(self.paths, health=True, backend="bogus")


class TestAuditFlush(_LayoutCase):
    def _git(self, *args: str) -> None:
        subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)

    def test_outside_git_raises(self) -> None:
        with self.assertRaises(AuditFlushError) as ctx:
            api.audit_flush(self.paths, dry_run=True)
        self.assertEqual(ctx.exception.exit_code, 11)

    def test_dry_run_then_commit(self) -> None:
        self._git("init", "-q")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "T")
        self._git("add", ".")
        self._git("commit", "-q", "-m", "init")
        api.ingest(self.sample, self.paths, backend="test")

        dry = api.audit_flush(self.paths, dry_run=True)
        self.assertIsInstance(dry, api.AuditFlushResult)
        self.assertEqual(dry.state.pending, 1)
        self.assertFalse(dry.committed)

        real = api.audit_flush(self.paths)
        self.assertTrue(real.committed)
        log = subprocess.run(["git", "-C", str(self.root), "log", "--oneline"], capture_output=True, text=True)
        self.assertIn("audit: flush 1 pending ingest-log line", log.stdout)

        again = api.audit_flush(self.paths)
        self.assertFalse(again.committed)
        self.assertEqual(again.state.pending, 0)


class TestPrepareBackend(_LayoutCase):
    def test_copilot_backend_gets_a_configured_copy(self) -> None:
        original = CopilotCliBackend("claude", timeout_seconds=7)
        prepared = api.prepare_backend(original, self.paths, redact_output=False)
        assert isinstance(prepared, CopilotCliBackend)
        self.assertIsNot(prepared, original)
        self.assertEqual(prepared._wiki_label, "knowledge/wiki")
        self.assertFalse(prepared._redact_output)
        self.assertEqual(prepared._timeout_seconds, 7)
        # The receiver is unchanged.
        self.assertTrue(original._redact_output)

    def test_test_backend_passes_through(self) -> None:
        backend = TestBackend()
        self.assertIs(api.prepare_backend(backend, self.paths), backend)
        self.assertIsInstance(api.prepare_backend("test", self.paths), TestBackend)

    def test_display_name(self) -> None:
        self.assertEqual(api.backend_display_name(TestBackend(), None), "test")
        self.assertEqual(api.backend_display_name(CopilotCliBackend("codex"), None), "codex")
        self.assertEqual(api.backend_display_name(TestBackend(), "requested"), "requested")


class TestLintResultPassed(unittest.TestCase):
    def test_matrix(self) -> None:
        def result(violations: int, audit: int, strict: bool) -> api.LintResult:
            return api.LintResult(("v",) * violations, 1, ("a",) * audit, None, strict)

        self.assertTrue(result(0, 0, False).passed)
        self.assertTrue(result(0, 1, False).passed)
        self.assertFalse(result(1, 0, False).passed)
        self.assertTrue(result(0, 0, True).passed)
        self.assertFalse(result(0, 1, True).passed)


if __name__ == "__main__":
    unittest.main()
