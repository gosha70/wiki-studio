# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wiki_studio.api — the five library functions, their typed results and the exceptions they raise (FR-008)."""

from __future__ import annotations

import contextlib
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.conftest import FIXTURES_DIR, SAMPLE_INCIDENT, make_repo_layout
from tests.test_cli_contract import _proposals_dir, _wiki_with_pages, _write_page
from wiki_studio import api
from wiki_studio.backends.copilot_cli import CopilotCliBackend
from wiki_studio.backends.test import TestBackend
from wiki_studio.errors import (
    AuditFlushError,
    BackendNotFoundError,
    ContractViolationError,
    OutputWriteError,
    PathOutsideRootError,
    PromoteApplyError,
    PromoteValidationError,
    SourceMissingError,
)
from wiki_studio.paths import WikiPaths
from wiki_studio.promoter import PromoteResult
from wiki_studio.proposal import PageEdit
from wiki_studio.wikilock import REASON_LOCK_TIMEOUT, WikiLock


class _LayoutCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-api-")
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

    def test_promote_resolves_escape_links_of_a_wiki_outside_the_root(self) -> None:
        # Regression: the staged copy has no neighbours, so ``../../guide.md`` used to
        # be reported as broken although the live wiki (and api.lint) resolve it. The
        # wiki lies outside the root, so the reference needs ``source_roots`` (FR-012);
        # an index entry may not leave the wiki (FR-013), so a page carries the link.
        with tempfile.TemporaryDirectory() as other:
            elsewhere = Path(other)
            (elsewhere / "guide.md").write_text("# guide\n", encoding="utf-8")
            wiki = elsewhere / "kb"
            (wiki / "concepts").mkdir(parents=True)
            (wiki / "index.md").write_text(
                "---\npage_type: index\nslug: index\ntitle: KB\nstatus: stable\nlast_reviewed: 2026-05-06\n---\n\n"
                "# KB\n\n- [notes](concepts/notes.md)\n",
                encoding="utf-8",
            )
            (wiki / "concepts" / "notes.md").write_text(
                "---\npage_type: concept\nslug: notes\ntitle: Notes\nstatus: stable\nlast_reviewed: 2026-05-06\n"
                "sources:\n  - path: src.md\n    sha: abc\n---\n\n# Notes\n\nSee the [guide](../../guide.md).\n",
                encoding="utf-8",
            )
            (wiki / "log.md").write_text(
                "---\npage_type: log\nslug: log\ntitle: Log\nstatus: stable\nlast_reviewed: 2026-05-06\n---\n\n# Log\n",
                encoding="utf-8",
            )
            unadmitted = WikiPaths.for_root(self.root, wiki_dir=wiki)
            self.assertIn(
                "concepts/notes.md: link target escapes the project root → ../../guide.md",
                api.lint(unadmitted).violations,
            )
            paths = WikiPaths.for_root(self.root, wiki_dir=wiki, source_roots=[elsewhere])
            self.assertTrue(api.lint(paths).passed)
            prop = _proposals_dir(self.root)
            self.assertTrue(api.promote(prop, paths, dry_run=True).dry_run)
            result = api.promote(prop, paths)
            self.assertEqual(len(result.applied_paths), 5)
            self.assertTrue((wiki / "incidents" / "cli-fixture.md").is_file())

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

    def test_health_pass_survives_a_malformed_contradiction_response(self) -> None:
        from wiki_studio.errors import ContractViolationError

        class _ProseBackend:
            calls = 0

            def call(self, prompt: dict) -> dict:
                self.calls += 1
                raise ContractViolationError("no JSON object found in output")

        backend = _ProseBackend()
        result = api.lint(self.paths, health=True, backend=backend)
        assert result.health is not None
        self.assertGreater(backend.calls, 0)
        self.assertFalse(any(f.kind == "contradiction" for f in result.health.findings))

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
        self._git("config", "gc.auto", "0")  # no background gc racing the temp-dir cleanup
        self._git("config", "maintenance.auto", "false")
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


class TestReadPage(_LayoutCase):
    """``api.read_page``: one read gives bytes, text and the hash of exactly those bytes (FR-006)."""

    def test_returns_bytes_text_and_sha256_of_the_same_read(self) -> None:
        wiki = _wiki_with_pages(self.root)
        rel = "concepts/origin-alignment.md"
        result = api.read_page(rel, self.paths)
        data = (wiki / rel).read_bytes()
        self.assertEqual((result.path, result.data, result.text), (rel, data, data.decode("utf-8")))
        self.assertEqual(result.sha256, hashlib.sha256(data).hexdigest())
        self.assertEqual(api.read_page(Path("./concepts/../concepts/origin-alignment.md"), self.paths).path, rel)
        self.assertIn("read_page", api.__all__)
        self.assertIn("ReadResult", api.__all__)

    def test_boundary_missing_and_encoding_errors(self) -> None:
        wiki = _wiki_with_pages(self.root)
        for bad in ("../README.md", str(self.root / "README.md"), "/etc/hosts"):
            with self.subTest(path=bad), self.assertRaises(PathOutsideRootError):
                api.read_page(bad, self.paths)
        (wiki / "concepts" / "alias.md").symlink_to(wiki / "concepts" / "spec-drift.md")
        with self.assertRaises(PathOutsideRootError):
            api.read_page("concepts/alias.md", self.paths)
        with self.assertRaises(SourceMissingError):
            api.read_page("concepts/missing.md", self.paths)
        (wiki / "concepts" / "binary.md").write_bytes(b"\xff\xfe")
        with self.assertRaises(ContractViolationError) as ctx:
            api.read_page("concepts/binary.md", self.paths)
        self.assertEqual(ctx.exception.exit_code, 4)

    def test_promote_result_fields_default(self) -> None:
        result = PromoteResult([], self.paths.proposals_dir, None, False)
        self.assertEqual((result.unguarded_paths, result.warnings), ([], []))


class TestLintResultPassed(unittest.TestCase):
    def test_matrix(self) -> None:
        def result(violations: int, audit: int, strict: bool) -> api.LintResult:
            return api.LintResult(("v",) * violations, 1, ("a",) * audit, None, strict)

        self.assertTrue(result(0, 0, False).passed)
        self.assertTrue(result(0, 1, False).passed)
        self.assertFalse(result(1, 0, False).passed)
        self.assertTrue(result(0, 0, True).passed)
        self.assertFalse(result(0, 1, True).passed)

    def test_positional_construction_defaults_prose_to_none(self) -> None:
        self.assertIsNone(api.LintResult((), 1, (), None, True).prose)

    def test_prose_findings_fail_only_under_strict(self) -> None:
        from wiki_studio.prose_lint import ProseFinding, ProseLintResult

        prose = ProseLintResult(findings=[ProseFinding("a.md", 1, "semicolon", "m")], pages_checked=1)
        self.assertTrue(api.LintResult((), 1, (), None, False, prose).passed)
        self.assertFalse(api.LintResult((), 1, (), None, True, prose).passed)
        self.assertTrue(api.LintResult((), 1, (), None, True, ProseLintResult([], 1)).passed)


if __name__ == "__main__":
    unittest.main()


_SNAPSHOT = "wiki_studio.api._write_ingest_snapshot"
_APPEND = "wiki_studio.api.append_ingest_log"


class TestPublicationUnderOneLock(_LayoutCase):
    """PR #41 review: the proposal files, the snapshot and the audit record are published under one wiki lock.

    A concurrent promote must never see a proposal directory that is still
    being published; it would archive the partial proposal and remove its
    source, after which the ingest would recreate an orphan snapshot.
    """

    def _assert_lock_held(self) -> None:
        with self.assertRaises(PromoteApplyError) as ctx:
            WikiLock(self.paths.wiki_dir, timeout=0).acquire()
        self.assertEqual(ctx.exception.reason, REASON_LOCK_TIMEOUT)

    def _assert_lock_free(self) -> None:
        WikiLock(self.paths.wiki_dir, timeout=0).acquire().release()

    def _patched(self, seen: list[str]) -> tuple[object, object]:
        real_snapshot, real_append = api._write_ingest_snapshot, api.append_ingest_log

        def snapshot(directory: Path) -> None:
            self._assert_lock_held()
            seen.append("snapshot")
            real_snapshot(directory)

        def append(paths: WikiPaths, record: object, *, lock: WikiLock | None = None) -> None:
            self._assert_lock_held()
            self.assertIsNotNone(lock, "the audit append reuses the publication lock")
            seen.append("audit")
            real_append(paths, record, lock=lock)  # type: ignore[arg-type]

        return snapshot, append

    def test_multi_page_ingest_publishes_under_one_lock(self) -> None:
        seen: list[str] = []
        snapshot, append = self._patched(seen)
        with patch(_SNAPSHOT, snapshot), patch(_APPEND, append):
            result = api.ingest(self.sample, self.paths, backend="test")
        self.assertEqual(seen, ["snapshot", "audit"])
        assert result.written is not None
        self.assertTrue((result.written / ".ingest-snapshot" / "plan.json").is_file())
        self._assert_lock_free()

    def test_legacy_ingest_publishes_under_one_lock(self) -> None:
        seen: list[str] = []
        snapshot, append = self._patched(seen)
        with patch(_SNAPSHOT, snapshot), patch(_APPEND, append):
            api.ingest(self.sample, self.paths, backend="test", legacy_single_source=True)
        self.assertEqual(seen, ["snapshot", "audit"])
        self._assert_lock_free()

    def test_a_failed_publication_is_removed_before_the_lock_is_released(self) -> None:
        """PR #41 review: cleanup of a half-published proposal happens while the lock is still held."""
        real_discard = api._discard_partial_proposal
        discarded: list[str] = []

        def discard(output_dir: Path, paths: WikiPaths, existed: bool) -> None:
            self._assert_lock_held()
            discarded.append(output_dir.name)
            real_discard(output_dir, paths, existed)

        def failing_snapshot(directory: Path) -> None:
            (directory / ".ingest-snapshot").mkdir()
            raise OSError("disk full after the snapshot directory")

        page = (
            "---\npage_type: concept\nslug: half\ntitle: Half\nstatus: draft\nlast_reviewed: 2026-10-24\n"
            "sources:\n  - path: sample-incident.md\n---\n\n# Half\n\n## Summary\n\nHalf.\n"
        )
        with (
            patch(_SNAPSHOT, failing_snapshot),
            patch("wiki_studio.api._discard_partial_proposal", discard),
            self.assertRaises(OutputWriteError),
        ):
            api.propose([PageEdit("concepts/half.md", "create", page, "r")], self.paths, name="half")
        self.assertEqual(discarded, ["half"])
        self.assertFalse((self.paths.proposals_dir / "half").exists())
        self._assert_lock_free()

    def test_a_failed_audit_record_removes_the_ingest_proposal_under_the_lock(self) -> None:
        removed_while_locked: list[bool] = []
        real_rmtree = api.shutil.rmtree

        def rmtree(path: object, *args: object, **kwargs: object) -> None:
            with contextlib.suppress(AssertionError):
                self._assert_lock_held()
                removed_while_locked.append(True)
            real_rmtree(path, *args, **kwargs)

        def failing_append(paths: WikiPaths, record: object, *, lock: WikiLock | None = None) -> None:
            raise OutputWriteError("audit log append failed")

        with (
            patch(_APPEND, failing_append),
            patch("wiki_studio.api.shutil.rmtree", rmtree),
            self.assertRaises(OutputWriteError),
        ):
            api.ingest(self.sample, self.paths, backend="test")
        self.assertEqual(removed_while_locked, [True])
        leftovers = [p.name for p in self.paths.proposals_dir.iterdir()] if self.paths.proposals_dir.is_dir() else []
        self.assertEqual(leftovers, [], "no half-published proposal is left for a promote to find")
        self._assert_lock_free()

    def test_a_failed_legacy_publication_restores_the_proposal_it_overwrote(self) -> None:
        """PR #41 review: cleanup restores a legacy proposal it overwrote instead of deleting it."""
        first = api.ingest(self.sample, self.paths, backend="test", legacy_single_source=True)
        assert first.written is not None
        original = first.written.read_bytes()

        def failing_append(paths: WikiPaths, record: object, *, lock: WikiLock | None = None) -> None:
            raise OutputWriteError("audit log append failed")

        with patch(_APPEND, failing_append), self.assertRaises(OutputWriteError):
            api.ingest(self.sample, self.paths, backend="test", legacy_single_source=True)
        self.assertTrue(first.written.is_file(), "the earlier proposal still exists")
        self.assertEqual(first.written.read_bytes(), original)
        self._assert_lock_free()

    def test_a_symlinked_legacy_proposal_path_is_refused_and_its_target_untouched(self) -> None:
        """PR #41 review: the deterministic legacy path is never read or written through a symlink."""
        probe = api.ingest(self.sample, self.paths, backend="test", legacy_single_source=True)
        assert probe.written is not None
        name = probe.written.name
        probe.written.unlink()
        outside = self.root / "outside.md"
        outside.write_text("untouched\n", encoding="utf-8")
        (self.paths.proposals_dir / name).symlink_to(outside)
        with self.assertRaises(OutputWriteError) as ctx:
            api.ingest(self.sample, self.paths, backend="test", legacy_single_source=True)
        self.assertIn(name, str(ctx.exception))
        self.assertEqual(outside.read_text(encoding="utf-8"), "untouched\n")
        self.assertTrue((self.paths.proposals_dir / name).is_symlink(), "the planted link is left for the curator")
        self._assert_lock_free()

    def test_a_failed_restoration_is_reported_and_the_backup_kept(self) -> None:
        """PR #41 review: when putting the previous proposal back fails, the error says so and the backup survives."""
        first = api.ingest(self.sample, self.paths, backend="test", legacy_single_source=True)
        assert first.written is not None
        original = first.written.read_bytes()
        real_replace = os.replace

        def replace(src: object, dst: object, *args: object, **kwargs: object) -> None:
            if ".bak-" in str(src):
                raise OSError("rename back failed")
            real_replace(src, dst, *args, **kwargs)  # type: ignore[arg-type]

        def failing_append(paths: WikiPaths, record: object, *, lock: WikiLock | None = None) -> None:
            raise OutputWriteError("audit log append failed")

        with (
            patch(_APPEND, failing_append),
            patch("wiki_studio.api.os.replace", replace),
            self.assertRaises(OutputWriteError) as ctx,
        ):
            api.ingest(self.sample, self.paths, backend="test", legacy_single_source=True)
        self.assertIn("rollback also raised", str(ctx.exception))
        self.assertIn("audit log append failed", str(ctx.exception))
        backups = list(self.paths.proposals_dir.glob("*.bak-*"))
        self.assertEqual(len(backups), 1, "the previous proposal's bytes survive in the backup")
        self.assertEqual(backups[0].read_bytes(), original)
        self._assert_lock_free()

    def test_a_surviving_backup_is_never_overwritten_by_a_retry(self) -> None:
        """PR #41 review: a backup left by a failed restoration is the only copy of that proposal; a retry keeps it."""
        first = api.ingest(self.sample, self.paths, backend="test", legacy_single_source=True)
        assert first.written is not None
        original = first.written.read_bytes()
        real_replace = os.replace

        def replace(src: object, dst: object, *args: object, **kwargs: object) -> None:
            if ".bak-" in str(src):
                raise OSError("rename back failed")
            real_replace(src, dst, *args, **kwargs)  # type: ignore[arg-type]

        def failing_append(paths: WikiPaths, record: object, *, lock: WikiLock | None = None) -> None:
            raise OutputWriteError("audit log append failed")

        with (
            patch(_APPEND, failing_append),
            patch("wiki_studio.api.os.replace", replace),
            self.assertRaises(OutputWriteError),
        ):
            api.ingest(self.sample, self.paths, backend="test", legacy_single_source=True)
        [backup] = list(self.paths.proposals_dir.glob("*.bak-*"))
        self.assertEqual(backup.read_bytes(), original)
        # The proposal path is free again (the created file was removed), so a retry publishes
        # a new proposal and must reserve a different backup name, leaving the survivor intact.
        self.assertFalse(first.written.exists())
        retry = api.ingest(self.sample, self.paths, backend="test", legacy_single_source=True)
        assert retry.written is not None
        self.assertEqual(backup.read_bytes(), original, "the surviving backup was not overwritten")
        again = api.ingest(self.sample, self.paths, backend="test", legacy_single_source=True)
        assert again.written is not None
        self.assertEqual(backup.read_bytes(), original)
        self.assertEqual(sorted(p.name for p in self.paths.proposals_dir.glob("*.bak-*")), [backup.name])

    def test_a_directory_at_the_legacy_name_is_refused_without_mutation(self) -> None:
        """PR #41 review: only a regular file is a previous proposal; anything else is refused before any move."""
        probe = api.ingest(self.sample, self.paths, backend="test", legacy_single_source=True)
        assert probe.written is not None
        name = probe.written.name
        probe.written.unlink()
        blocker = self.paths.proposals_dir / name
        blocker.mkdir()
        (blocker / "curator.md").write_text("curated\n", encoding="utf-8")
        log_before = self.paths.audit_log.read_bytes() if self.paths.audit_log.exists() else b""
        with self.assertRaises(OutputWriteError) as ctx:
            api.ingest(self.sample, self.paths, backend="test", legacy_single_source=True)
        self.assertIn("not a regular file", str(ctx.exception))
        self.assertTrue((blocker / "curator.md").is_file(), "the directory and its content are untouched")
        self.assertEqual(list(self.paths.proposals_dir.glob("*.bak-*")), [])
        self.assertEqual(self.paths.audit_log.read_bytes() if self.paths.audit_log.exists() else b"", log_before)
        self._assert_lock_free()

    def test_a_failed_legacy_publication_removes_a_proposal_it_created(self) -> None:
        def failing_append(paths: WikiPaths, record: object, *, lock: WikiLock | None = None) -> None:
            raise OutputWriteError("audit log append failed")

        with patch(_APPEND, failing_append), self.assertRaises(OutputWriteError):
            api.ingest(self.sample, self.paths, backend="test", legacy_single_source=True)
        leftovers = [p.name for p in self.paths.proposals_dir.glob("*.md")] if self.paths.proposals_dir.is_dir() else []
        self.assertEqual(leftovers, [])

    def test_propose_writes_the_snapshot_under_the_same_lock(self) -> None:
        seen: list[str] = []
        snapshot, _append = self._patched(seen)
        page = (
            "---\npage_type: concept\nslug: one-lock\ntitle: One lock\nstatus: draft\nlast_reviewed: 2026-10-24\n"
            "sources:\n  - path: sample-incident.md\n---\n\n# One lock\n\n## Summary\n\nOne lock.\n"
        )
        with patch(_SNAPSHOT, snapshot):
            written = api.propose([PageEdit("concepts/one-lock.md", "create", page, "r")], self.paths, name="one-lock")
        self.assertEqual(seen, ["snapshot"])
        self.assertTrue((written / ".ingest-snapshot" / "plan.json").is_file())
        self._assert_lock_free()


if __name__ == "__main__":
    unittest.main()
