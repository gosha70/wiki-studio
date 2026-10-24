# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Receipts, the commit protocol and recovery of an interrupted promotion (0.6.0 FR-003, FR-004).

Faults are injected at the promoter's protocol steps (patchable module
functions), never through an environment variable in shipped code.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.conftest import make_repo_layout, run_cli
from tests.test_audit_lint import _valid_record, _write_audit
from tests.test_cli_contract import _proposals_dir
from wiki_studio import __version__, api, promoter
from wiki_studio.audit import payload_digest, proposal_hash
from wiki_studio.audit_lint import validate_audit_dir
from wiki_studio.errors import (
    REASON_PAYLOAD_CHANGED,
    REASON_UNCERTAIN_OUTCOME,
    REASON_WIKI_IDENTITY_UNAVAILABLE,
    REASON_WIKI_MISMATCH,
    OutputWriteError,
    PromoteApplyError,
    PromoteValidationError,
)
from wiki_studio.paths import ENV_WIKI_DIR, WikiPaths

RECEIPT = "receipt.json"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _tree(root: Path) -> dict[str, bytes | None]:
    """Every entry under ``root``: files by bytes, directories as None."""
    return {p.relative_to(root).as_posix(): (None if p.is_dir() else p.read_bytes()) for p in root.rglob("*")}


def _receipt(directory: Path) -> dict:
    return json.loads((directory / RECEIPT).read_text(encoding="utf-8"))


def _log_lines(wiki: Path) -> list[str]:
    return [ln for ln in (wiki / "log.md").read_text(encoding="utf-8").splitlines() if ln.startswith("- 2026")]


class _Fail:
    """Raise ``exc`` on the ``n``-th call of a patched function, otherwise call the original."""

    def __init__(self, original: object, n: int, exc: BaseException) -> None:
        self.original = original
        self.n = n
        self.exc = exc
        self.calls = 0

    def __call__(self, *args: object, **kwargs: object) -> object:
        self.calls += 1
        if self.calls == self.n:
            raise self.exc
        return self.original(*args, **kwargs)  # type: ignore[operator]


class _LayoutCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-recovery-")
        self.root = make_repo_layout(Path(self._tmp.name), with_schema=True, with_sample=False)
        self.paths = WikiPaths.for_root(self.root)
        self.wiki = self.paths.wiki_dir

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ── interruptions ─────────────────────────────────────────

    def interrupt_after_committing_receipt(self, prop: Path) -> None:
        """Step 1 done, step 2 never started: wiki untouched, receipt ``committing``."""
        with (
            patch("wiki_studio.promoter._apply_planned", side_effect=RuntimeError("killed before the commit")),
            self.assertRaises(RuntimeError),
        ):
            api.promote(prop, self.paths)
        self.assertEqual(_receipt(prop)["state"], "committing")

    def interrupt_after_commit(self, prop: Path) -> None:
        """Steps 1 and 2 done, step 3 failed: wiki updated, receipt still ``committing``."""
        fail = _Fail(promoter._write_receipt, 2, OSError("disk full during the committed rewrite"))
        with patch("wiki_studio.promoter._write_receipt", side_effect=fail), self.assertRaises(OutputWriteError) as ctx:
            api.promote(prop, self.paths)
        self.assertIn("Promote the directory again", str(ctx.exception))
        self.assertEqual(_receipt(prop)["state"], "committing")

    def interrupt_before_archive(self, prop: Path) -> api.PromoteResult:
        """Steps 1 to 3 done, step 4 failed before publishing: receipt ``committed``, no archive."""
        with patch("wiki_studio.promoter._write_archive_file", side_effect=OSError("disk full")):
            result = api.promote(prop, self.paths)
        self.assertIsNone(result.archived_dir)
        self.assertEqual(_receipt(prop)["state"], "committed")
        self.assertFalse((self.paths.applied_dir / prop.name).exists())
        return result


class TestReceiptContents(_LayoutCase):
    def test_receipt_records_identity_writes_wiki_target_and_promoter(self) -> None:
        prop = _proposals_dir(self.root)
        (prop / "review-notes.md").write_text("note before capture\n", encoding="utf-8")
        submitted = _tree(prop)
        plan_bytes = (prop / "plan.json").read_bytes()
        wiki_stat = os.stat(self.wiki)
        result = run_cli("promote", str(prop), cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        archive = self.paths.applied_dir / prop.name
        receipt = _receipt(archive)
        self.assertEqual(receipt["receipt_version"], 1)
        self.assertEqual(receipt["state"], "committed")
        self.assertEqual(receipt["proposal"], prop.name)
        self.assertEqual(receipt["digest_recipe"], 2)
        self.assertEqual(receipt["plan_sha256"], _sha(plan_bytes))
        self.assertEqual(
            receipt["submission_manifest"],
            [{"path": rel, "sha256": _sha(data)} for rel, data in sorted(submitted.items()) if data is not None],
        )
        self.assertEqual(receipt["wiki_target"]["st_dev"], wiki_stat.st_dev)
        self.assertEqual(receipt["wiki_target"]["st_ino"], wiki_stat.st_ino)
        self.assertEqual(receipt["wiki_target"]["path"], str(self.wiki.resolve()))
        planned = {w["path"]: w for w in receipt["planned_writes"]}
        self.assertIsNone(planned["incidents/cli-fixture.md"]["pre_sha256"])
        self.assertEqual(planned["log.md"]["post_sha256"], _sha((self.wiki / "log.md").read_bytes()))
        self.assertEqual(sorted(receipt["written_paths"]), sorted(planned))
        self.assertEqual(receipt["unguarded_paths"], [])
        self.assertGreaterEqual(receipt["lock_wait_seconds"], 0)
        for key in ("started_at", "committing_at", "committed_at"):
            self.assertRegex(receipt[key], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(receipt["promoter"], {"package": "wiki-studio", "version": __version__, "entry_point": "cli"})
        # The archive holds the submitted bytes (plan, previews, note) plus the receipt, byte for byte.
        archived = _tree(archive)
        archived.pop(RECEIPT)
        self.assertEqual(archived, submitted)
        self.assertFalse(prop.exists())
        self.assertEqual(receipt["submission_digest"], payload_digest(archive))

    def test_api_entry_point_and_snapshot_copied_byte_identical(self) -> None:
        prop = _proposals_dir(self.root)
        snapshot = prop / ".ingest-snapshot" / "preview"
        snapshot.mkdir(parents=True)
        (snapshot / "log.md").write_bytes(b"- draft line\r\n")
        result = api.promote(prop, self.paths)
        assert result.archived_dir is not None
        self.assertEqual(
            (result.archived_dir / ".ingest-snapshot" / "preview" / "log.md").read_bytes(), b"- draft line\r\n"
        )
        self.assertEqual(_receipt(result.archived_dir)["promoter"]["entry_point"], "api")

    def test_dry_run_and_failed_validation_persist_no_receipt(self) -> None:
        prop = _proposals_dir(self.root)
        api.promote(prop, self.paths, dry_run=True)
        self.assertFalse((prop / RECEIPT).exists())
        bad = _proposals_dir(self.root, slug="bad")
        page = bad / "preview" / "incidents" / "bad.md"
        page.write_text(page.read_text(encoding="utf-8").replace("slug: bad", "slug: wrong"), encoding="utf-8")
        with self.assertRaises(PromoteValidationError):
            api.promote(bad, self.paths)
        self.assertFalse((bad / RECEIPT).exists())


class TestCleanupAndPayloadChanges(_LayoutCase):
    def test_a_successful_promotion_removes_the_source_without_payload_changed(self) -> None:
        prop = _proposals_dir(self.root)
        result = api.promote(prop, self.paths)
        self.assertFalse(prop.exists())
        self.assertEqual(result.archived_dir, self.paths.applied_dir / prop.name)
        self.assertEqual(len(_log_lines(self.wiki)), 1)

    def test_a_directory_changed_after_commit_leaves_a_complete_archive_and_exits_payload_changed(self) -> None:
        prop = _proposals_dir(self.root)
        real_publish = promoter._publish_archive

        def change_then_publish(tmp: Path, target: Path) -> None:
            (prop / "preview" / "log.md").write_text("- edited after capture\n", encoding="utf-8")
            real_publish(tmp, target)

        with (
            patch("wiki_studio.promoter._publish_archive", side_effect=change_then_publish),
            self.assertRaises(PromoteApplyError) as ctx,
        ):
            api.promote(prop, self.paths)
        self.assertEqual(ctx.exception.reason, REASON_PAYLOAD_CHANGED)
        self.assertIn("preview/log.md (changed)", str(ctx.exception))
        self.assertIn("delete the leftover directory", str(ctx.exception))
        archive = self.paths.applied_dir / prop.name
        self.assertIn(str(archive), str(ctx.exception))
        self.assertEqual(
            (archive / "preview" / "log.md").read_text(encoding="utf-8"),
            "- 2026-05-06 — promote cli-fixture (incident).",
        )
        self.assertEqual(_receipt(archive)["state"], "committed")
        self.assertTrue(prop.is_dir(), "the directory is left in place")
        self.assertIn("promote cli-fixture (incident)", (self.wiki / "log.md").read_text(encoding="utf-8"))
        # A retry finds the complete archive; the directory still differs, so it stays.
        with self.assertRaises(PromoteApplyError) as again:
            api.promote(prop, self.paths)
        self.assertEqual(again.exception.reason, REASON_PAYLOAD_CHANGED)
        self.assertEqual(len(list(self.paths.applied_dir.iterdir())), 1, "no second archive")
        self.assertEqual(len(_log_lines(self.wiki)), 1, "nothing applied twice")

    def test_a_note_present_before_capture_is_archived_and_removed_with_the_source(self) -> None:
        prop = _proposals_dir(self.root)
        (prop / "review-notes.md").write_text("reviewed\n", encoding="utf-8")
        result = api.promote(prop, self.paths)
        assert result.archived_dir is not None
        self.assertEqual((result.archived_dir / "review-notes.md").read_text(encoding="utf-8"), "reviewed\n")
        self.assertFalse(prop.exists())

    def _promote_with_change_after_capture(self, prop: Path, change: object) -> PromoteApplyError:
        real_apply = promoter._apply_planned

        def change_then_apply(planned: object, paths: object) -> object:
            change()  # type: ignore[operator]
            return real_apply(planned, paths)  # type: ignore[arg-type]

        with (
            patch("wiki_studio.promoter._apply_planned", side_effect=change_then_apply),
            self.assertRaises(PromoteApplyError) as ctx,
        ):
            api.promote(prop, self.paths)
        self.assertEqual(ctx.exception.reason, REASON_PAYLOAD_CHANGED)
        return ctx.exception

    def test_a_note_added_after_capture_is_left_in_the_source_and_absent_from_the_archive(self) -> None:
        prop = _proposals_dir(self.root)
        exc = self._promote_with_change_after_capture(
            prop, lambda: (prop / "review-notes.md").write_text("late note\n", encoding="utf-8")
        )
        self.assertIn("review-notes.md (new)", str(exc))
        archive = self.paths.applied_dir / prop.name
        self.assertFalse((archive / "review-notes.md").exists())
        self.assertTrue((archive / RECEIPT).is_file())
        self.assertEqual((prop / "review-notes.md").read_text(encoding="utf-8"), "late note\n")
        self.assertTrue((prop / "plan.json").is_file(), "the source is left intact")

    def test_a_snapshot_changed_after_capture_keeps_the_captured_snapshot_in_the_archive(self) -> None:
        prop = _proposals_dir(self.root)
        snapshot = prop / ".ingest-snapshot" / "preview"
        snapshot.mkdir(parents=True)
        (snapshot / "log.md").write_text("captured\n", encoding="utf-8")
        exc = self._promote_with_change_after_capture(
            prop, lambda: (snapshot / "log.md").write_text("changed\n", encoding="utf-8")
        )
        self.assertIn(".ingest-snapshot/preview/log.md (changed)", str(exc))
        archive = self.paths.applied_dir / prop.name
        self.assertEqual(
            (archive / ".ingest-snapshot" / "preview" / "log.md").read_text(encoding="utf-8"), "captured\n"
        )
        self.assertEqual((snapshot / "log.md").read_text(encoding="utf-8"), "changed\n")
        self.assertEqual(_tree(prop).keys() - {RECEIPT}, _tree(archive).keys() - {RECEIPT})


class TestArchiveFaults(_LayoutCase):
    """Failure during each archive file write, during the rename and after each source-file deletion."""

    def _assert_recovered(self, prop: Path) -> None:
        archive = self.paths.applied_dir / prop.name
        self.assertFalse(prop.exists(), "cleanup finished")
        self.assertTrue((archive / RECEIPT).is_file())
        self.assertEqual(_receipt(archive)["state"], "committed")
        entries = [p.name for p in self.paths.applied_dir.iterdir()]
        self.assertEqual(entries, [prop.name], "exactly one archive, no leftover .tmp")
        self.assertEqual(len(_log_lines(self.wiki)), 1, "nothing applied twice")
        self.assertEqual(payload_digest(archive), _receipt(archive)["submission_digest"])

    def test_failure_during_each_archive_file_write(self) -> None:
        probe = _proposals_dir(self.root, slug="probe")
        count = sum(1 for data in _tree(probe).values() if data is not None)  # files only
        shutil.rmtree(probe)
        for n in range(1, count + 2):  # +1 for receipt.json
            with self.subTest(failing_write=n):
                prop = _proposals_dir(self.root, slug=f"w{n}")
                fail = _Fail(promoter._write_archive_file, n, OSError("disk full"))
                with patch("wiki_studio.promoter._write_archive_file", side_effect=fail):
                    first = api.promote(prop, self.paths)
                self.assertIsNone(first.archived_dir)
                self.assertEqual(len(first.applied_paths), 5)
                self.assertFalse((self.paths.applied_dir / prop.name).exists(), "no partial archive at an applied name")
                self.assertTrue((prop / RECEIPT).is_file())
                retry = api.promote(prop, self.paths)
                self.assertEqual(retry.archived_dir, self.paths.applied_dir / prop.name)
                self.assertEqual(sorted(retry.applied_paths), sorted(first.applied_paths))
                self.assertFalse(prop.exists())
                self.assertEqual(len([ln for ln in _log_lines(self.wiki) if f"promote w{n} " in ln]), 1)

    def test_failure_during_the_rename(self) -> None:
        prop = _proposals_dir(self.root)
        with patch("wiki_studio.promoter._publish_archive", side_effect=OSError("rename failed")):
            first = api.promote(prop, self.paths)
        self.assertIsNone(first.archived_dir)
        self.assertEqual([p.name for p in self.paths.applied_dir.iterdir()], [], "no partial archive, no leftover tmp")
        retry = run_cli("promote", str(prop), cwd=self.root)
        self.assertEqual(retry.returncode, 0, retry.stderr)
        self.assertIn("applied 5 edit(s)", retry.stdout)
        self._assert_recovered(prop)

    def test_failure_after_each_source_file_deletion(self) -> None:
        probe = _proposals_dir(self.root, slug="probe")
        deletions = len(_tree(probe)) + 2  # files and dirs, plus receipt.json and the directory itself
        shutil.rmtree(probe)
        for n in range(1, deletions + 1):
            with self.subTest(failing_deletion=n):
                prop = _proposals_dir(self.root, slug=f"d{n}")
                fail = _Fail(promoter._remove_source_entry, n, OSError("deletion failed"))
                with patch("wiki_studio.promoter._remove_source_entry", side_effect=fail):
                    first = api.promote(prop, self.paths)
                self.assertIsNone(first.archived_dir)
                self.assertEqual(fail.calls, n, "the injected deletion failure fired")
                self.assertTrue(prop.exists(), "the partly cleaned directory remains")
                retry = api.promote(prop, self.paths)
                if retry.applied_paths:
                    self.assertEqual(retry.archived_dir, self.paths.applied_dir / prop.name)
                else:
                    # Only the empty directory was left (receipt.json already gone): removed, nothing to report.
                    self.assertEqual(n, deletions)
                self.assertFalse(prop.exists())
                self.assertEqual(len([ln for ln in _log_lines(self.wiki) if f"promote d{n} " in ln]), 1)
                archive = self.paths.applied_dir / prop.name
                self.assertEqual(_receipt(archive)["state"], "committed")
                self.assertEqual(payload_digest(archive), _receipt(archive)["submission_digest"])

    def test_failure_after_deleting_plan_json_and_after_deleting_receipt_json(self) -> None:
        real_remove = promoter._remove_source_entry
        for last_deleted in ("plan.json", RECEIPT):
            with self.subTest(after=last_deleted):
                prop = _proposals_dir(self.root, slug=f"after-{last_deleted.split('.')[0]}")

                def remove_then_fail(path: Path, _name: str = last_deleted) -> None:
                    real_remove(path)
                    if path.name == _name:
                        raise OSError(f"failed after deleting {_name}")

                with patch("wiki_studio.promoter._remove_source_entry", side_effect=remove_then_fail):
                    first = api.promote(prop, self.paths)
                self.assertIsNone(first.archived_dir)
                self.assertTrue(prop.exists())
                self.assertFalse((prop / last_deleted).exists())
                retry = api.promote(prop, self.paths)
                self.assertFalse(prop.exists())
                if last_deleted == RECEIPT:
                    # Only the empty directory was left: removed, nothing to report.
                    self.assertEqual(retry.applied_paths, [])
                else:
                    self.assertEqual(retry.archived_dir, self.paths.applied_dir / prop.name)
                self.assertTrue((self.paths.applied_dir / prop.name / RECEIPT).is_file())

    def test_a_retry_that_finds_only_a_tmp_sibling_publishes_the_archive(self) -> None:
        prop = _proposals_dir(self.root)
        self.interrupt_before_archive(prop)
        leftover = self.paths.applied_dir / f".{prop.name}.999{promoter._ARCHIVE_TMP_SUFFIX}"
        (leftover / "preview").mkdir(parents=True)
        (leftover / "plan.json").write_text("partial", encoding="utf-8")
        retry = api.promote(prop, self.paths)
        self.assertEqual(retry.archived_dir, self.paths.applied_dir / prop.name)
        self.assertFalse(leftover.exists(), "the leftover tmp is removed, never published")
        self._assert_recovered(prop)

    def test_a_retry_that_finds_a_complete_archive_finishes_cleanup(self) -> None:
        prop = _proposals_dir(self.root)
        with patch("wiki_studio.promoter._remove_source_dir", side_effect=OSError("cleanup failed")):
            first = api.promote(prop, self.paths)
        self.assertIsNone(first.archived_dir)
        self.assertTrue((self.paths.applied_dir / prop.name / RECEIPT).is_file())
        retry = run_cli("promote", str(prop), cwd=self.root)
        self.assertEqual(retry.returncode, 0, retry.stderr)
        self._assert_recovered(prop)

    def test_a_source_receipt_whose_bytes_differ_from_the_archived_copy_is_still_cleaned_up(self) -> None:
        # The receipt is the promoter's file, outside the submission identity: its
        # bytes are never a reason to refuse the cleanup of a completely archived directory.
        prop = _proposals_dir(self.root)
        with patch("wiki_studio.promoter._remove_source_dir", side_effect=OSError("cleanup failed")):
            first = api.promote(prop, self.paths)
        self.assertIsNone(first.archived_dir)
        archive = self.paths.applied_dir / prop.name
        reserialised = json.dumps(_receipt(prop)).encode("utf-8")  # same record, different bytes
        self.assertNotEqual(reserialised, (archive / RECEIPT).read_bytes())
        (prop / RECEIPT).write_bytes(reserialised)
        retry = api.promote(prop, self.paths)
        self.assertEqual(retry.archived_dir, archive)
        self.assertFalse(prop.exists())
        self.assertEqual(_receipt(archive)["state"], "committed")


class TestCommittedReceipts(_LayoutCase):
    def test_killed_between_committed_rewrite_and_archive_then_edited_exits_payload_changed(self) -> None:
        prop = _proposals_dir(self.root)
        self.interrupt_before_archive(prop)
        post_hashes = [w["post_sha256"] for w in _receipt(prop)["planned_writes"]]
        (prop / "preview" / "log.md").write_text("- edited\n", encoding="utf-8")
        with self.assertRaises(PromoteApplyError) as ctx:
            api.promote(prop, self.paths)
        self.assertEqual(ctx.exception.reason, REASON_PAYLOAD_CHANGED)
        message = str(ctx.exception)
        self.assertIn("No archive could be written", message)
        self.assertIn("changed ['preview/log.md']", message)
        for digest in post_hashes:
            self.assertIn(digest, message)
        self.assertIn("move the directory aside", message)
        self.assertEqual([p.name for p in self.paths.applied_dir.iterdir()], [], "no archive")
        self.assertTrue((prop / RECEIPT).is_file())
        self.assertEqual(len(_log_lines(self.wiki)), 1)

    def test_committed_receipt_with_an_unchanged_directory_archives_from_its_bytes(self) -> None:
        prop = _proposals_dir(self.root)
        submitted = _tree(prop)
        self.interrupt_before_archive(prop)
        receipt_bytes = (prop / RECEIPT).read_bytes()
        result = run_cli("promote", str(prop), cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("applied 5 edit(s)", result.stdout)
        archive = self.paths.applied_dir / prop.name
        archived = _tree(archive)
        self.assertEqual(archived.pop(RECEIPT), receipt_bytes, "the committed receipt's exact bytes")
        self.assertEqual(archived, submitted)
        self.assertFalse(prop.exists())
        self.assertEqual(len(_log_lines(self.wiki)), 1, "no replayed append")

    def test_a_proposal_under_applied_returns_the_recorded_outcome_without_writes(self) -> None:
        prop = _proposals_dir(self.root)
        archive = api.promote(prop, self.paths).archived_dir
        assert archive is not None
        before = _tree(self.wiki)
        result = api.promote(archive, self.paths)
        self.assertEqual(result.applied_paths, [])
        self.assertEqual(result.archived_dir, archive)
        self.assertEqual(_tree(self.wiki), before)
        # A pre-0.6.0 archive without a receipt is a no-op too.
        (archive / RECEIPT).unlink()
        self.assertEqual(api.promote(archive, self.paths).applied_paths, [])

    def test_a_dry_run_refuses_a_directory_with_a_receipt(self) -> None:
        prop = _proposals_dir(self.root)
        self.interrupt_before_archive(prop)
        before = _tree(prop)
        with self.assertRaises(PromoteValidationError) as ctx:
            api.promote(prop, self.paths, dry_run=True)
        self.assertIn("dry run cannot resolve", str(ctx.exception))
        self.assertEqual(_tree(prop), before)


class TestCommittingReceipts(_LayoutCase):
    def test_fault_after_the_committing_receipt_recovers_as_not_committed(self) -> None:
        prop = _proposals_dir(self.root)
        wiki_before = _tree(self.wiki)
        self.interrupt_after_committing_receipt(prop)
        self.assertEqual(_tree(self.wiki), wiki_before)
        retry = api.promote(prop, self.paths)
        self.assertEqual(retry.archived_dir, self.paths.applied_dir / prop.name)
        self.assertEqual(len(_log_lines(self.wiki)), 1)
        self.assertEqual(_receipt(self.paths.applied_dir / prop.name)["state"], "committed")

    def test_fault_during_the_committing_write_commits_nothing_and_exits_6(self) -> None:
        prop = _proposals_dir(self.root)
        wiki_before = _tree(self.wiki)
        with (
            patch("wiki_studio.promoter._write_receipt", side_effect=OSError("disk full")),
            self.assertRaises(OutputWriteError) as ctx,
        ):
            api.promote(prop, self.paths)
        self.assertEqual(ctx.exception.exit_code, 6)
        self.assertIn("nothing was committed", str(ctx.exception))
        self.assertEqual(_tree(self.wiki), wiki_before)
        self.assertFalse((prop / RECEIPT).exists())
        self.assertFalse((prop / promoter._RECEIPT_TMP_NAME).exists())
        retry = api.promote(prop, self.paths)
        self.assertEqual(retry.archived_dir, self.paths.applied_dir / prop.name)

    def test_fault_during_the_committed_rewrite_recovers_without_a_replayed_append(self) -> None:
        prop = _proposals_dir(self.root)
        self.interrupt_after_commit(prop)
        self.assertEqual(len(_log_lines(self.wiki)), 1)
        retry = run_cli("promote", str(prop), cwd=self.root)
        self.assertEqual(retry.returncode, 0, retry.stderr)
        self.assertIn("applied 5 edit(s)", retry.stdout)
        self.assertEqual(len(_log_lines(self.wiki)), 1, "the append was not replayed")
        archive = self.paths.applied_dir / prop.name
        self.assertEqual(_receipt(archive)["state"], "committed")
        self.assertEqual(
            sorted(_receipt(archive)["written_paths"]), sorted(w["path"] for w in _receipt(archive)["planned_writes"])
        )
        self.assertFalse(prop.exists())

    def test_fault_during_the_archive_move_recovers(self) -> None:
        prop = _proposals_dir(self.root)
        with patch("wiki_studio.promoter._publish_archive", side_effect=OSError("move failed")):
            api.promote(prop, self.paths)
        retry = api.promote(prop, self.paths)
        self.assertEqual(retry.archived_dir, self.paths.applied_dir / prop.name)
        self.assertEqual(len(_log_lines(self.wiki)), 1)

    def test_a_no_op_update_is_excluded_from_tracking_and_recovers_as_not_committed(self) -> None:
        first = _proposals_dir(self.root)
        api.promote(first, self.paths)
        live = (self.wiki / "incidents" / "cli-fixture.md").read_bytes()
        prop = _proposals_dir(self.root, slug="noop")
        (prop / "preview" / "same.md").write_bytes(live)
        plan = json.loads((prop / "plan.json").read_text(encoding="utf-8"))
        plan["edits"] = [
            {
                "path": "incidents/cli-fixture.md",
                "action": "update",
                "rationale": "r",
                "preview": "preview/same.md",
                "base_sha256": _sha(live),
            },
            {"path": "log.md", "action": "append-log", "rationale": "r", "preview": "preview/log.md"},
        ]
        (prop / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        self.interrupt_after_committing_receipt(prop)
        tracked = [w["path"] for w in _receipt(prop)["planned_writes"]]
        self.assertNotIn("incidents/cli-fixture.md", tracked)
        self.assertIn("log.md", tracked)
        self.assertTrue(any(p.startswith(".audit/proposals/") for p in tracked))
        retry = api.promote(prop, self.paths)
        self.assertNotIn("incidents/cli-fixture.md", retry.applied_paths)
        self.assertEqual(retry.archived_dir, self.paths.applied_dir / prop.name)
        self.assertEqual(len([ln for ln in _log_lines(self.wiki) if "promote noop" in ln]), 1)

    def test_a_mixed_state_is_refused_as_uncertain_outcome(self) -> None:
        prop = _proposals_dir(self.root)
        self.interrupt_after_committing_receipt(prop)
        # One tracked write at its post-commit state, the others at pre-commit.
        (self.wiki / "incidents").mkdir()
        (self.wiki / "incidents" / "cli-fixture.md").write_bytes(
            (prop / "preview" / "incidents" / "cli-fixture.md").read_bytes()
        )
        before = _tree(self.wiki)
        with self.assertRaises(PromoteApplyError) as ctx:
            api.promote(prop, self.paths)
        self.assertEqual(ctx.exception.reason, REASON_UNCERTAIN_OUTCOME)
        self.assertIn("incidents/cli-fixture.md: post-commit", str(ctx.exception))
        self.assertIn("log.md: pre-commit", str(ctx.exception))
        self.assertEqual(_tree(self.wiki), before)
        self.assertTrue((prop / RECEIPT).is_file())
        # A tracked path matching neither state is refused the same way.
        (self.wiki / "incidents" / "cli-fixture.md").write_bytes(b"something else\n")
        with self.assertRaises(PromoteApplyError) as neither:
            api.promote(prop, self.paths)
        self.assertEqual(neither.exception.reason, REASON_UNCERTAIN_OUTCOME)
        self.assertIn("incidents/cli-fixture.md: neither", str(neither.exception))

    def test_an_unreadable_or_non_regular_tracked_path_is_refused_as_uncertain_outcome(self) -> None:
        prop = _proposals_dir(self.root)
        self.interrupt_after_committing_receipt(prop)
        # A directory where the tracked create expects a file is not "absent" (pre-commit).
        (self.wiki / "incidents" / "cli-fixture.md").mkdir(parents=True)
        before = _tree(self.wiki)
        with self.assertRaises(PromoteApplyError) as as_dir:
            api.promote(prop, self.paths)
        self.assertEqual(as_dir.exception.reason, REASON_UNCERTAIN_OUTCOME)
        self.assertIn("incidents/cli-fixture.md: neither (live not a regular file)", str(as_dir.exception))
        self.assertEqual(_tree(self.wiki), before)
        self.assertTrue((prop / RECEIPT).is_file(), "the receipt is kept for the repair")
        shutil.rmtree(self.wiki / "incidents")
        before = _tree(self.wiki)
        # A tracked page that cannot be read is refused the same way, not reported as a raw OSError.
        real_read = Path.read_bytes

        def failing_read(self_: Path) -> bytes:
            if self_.name == "log.md" and self_.is_relative_to(self.wiki):
                raise PermissionError("permission denied")
            return real_read(self_)

        with patch.object(Path, "read_bytes", failing_read), self.assertRaises(PromoteApplyError) as unreadable:
            api.promote(prop, self.paths)
        self.assertEqual(unreadable.exception.reason, REASON_UNCERTAIN_OUTCOME)
        self.assertIn("log.md: neither (live unreadable: permission denied)", str(unreadable.exception))
        self.assertEqual(_tree(self.wiki), before)
        self.assertTrue((prop / RECEIPT).is_file())

    def test_committing_receipt_with_everything_at_post_state_completes(self) -> None:
        prop = _proposals_dir(self.root)
        self.interrupt_after_commit(prop)
        retry = api.promote(prop, self.paths)
        self.assertEqual(len(retry.applied_paths), 5)
        self.assertEqual(retry.archived_dir, self.paths.applied_dir / prop.name)


class TestMissingAndCorruptReceipts(_LayoutCase):
    def test_a_corrupt_receipt_is_refused_with_nothing_written(self) -> None:
        for i, body in enumerate(("{not json", '{"state": "committed"}', '{"state": "done"}', "[]")):
            with self.subTest(body=body):
                prop = _proposals_dir(self.root, slug=f"c{i}")
                (prop / RECEIPT).write_text(body, encoding="utf-8")
                before = _tree(self.wiki)
                result = run_cli("promote", str(prop), cwd=self.root)
                self.assertEqual(result.returncode, 10, result.stderr)
                self.assertIn(f"[reason={REASON_UNCERTAIN_OUTCOME}]", result.stderr)
                self.assertIn("never taken to mean the proposal was committed", result.stderr)
                self.assertEqual(_tree(self.wiki), before)
                self.assertEqual(
                    [p.name for p in self.paths.applied_dir.iterdir()] if self.paths.applied_dir.exists() else [], []
                )

    def test_a_receipt_with_a_malformed_digest_is_refused(self) -> None:
        prop = _proposals_dir(self.root)
        self.interrupt_before_archive(prop)
        good = _receipt(prop)
        for field, broken in (
            ("submission_digest", "abc"),
            ("submission_manifest", [{"path": "plan.json", "sha256": "ABCDEF"}]),
            (
                "planned_writes",
                [{"path": "log.md", "pre_sha256": "x", "post_sha256": good["planned_writes"][0]["post_sha256"]}],
            ),
        ):
            with self.subTest(field=field):
                (prop / RECEIPT).write_text(json.dumps({**good, field: broken}), encoding="utf-8")
                with self.assertRaises(PromoteApplyError) as ctx:
                    api.promote(prop, self.paths)
                self.assertEqual(ctx.exception.reason, REASON_UNCERTAIN_OUTCOME)
                self.assertIn(f"malformed {field}", str(ctx.exception))

    def test_a_missing_receipt_never_means_committed_and_never_reapplies_silently(self) -> None:
        prop = _proposals_dir(self.root)
        self.interrupt_before_archive(prop)
        (prop / RECEIPT).unlink()
        before = _tree(self.wiki)
        with self.assertRaises(PromoteValidationError) as ctx:
            api.promote(prop, self.paths)
        self.assertIn("create target already exists", str(ctx.exception))
        self.assertEqual(_tree(self.wiki), before)
        self.assertEqual(len(_log_lines(self.wiki)), 1)

    def test_a_receipt_that_is_a_symlink_is_refused(self) -> None:
        prop = _proposals_dir(self.root)
        elsewhere = self.root / "elsewhere.json"
        elsewhere.write_text("{}", encoding="utf-8")
        (prop / RECEIPT).symlink_to(elsewhere)
        with self.assertRaises(PromoteValidationError):
            api.promote(prop, self.paths)


class TestWikiIdentity(_LayoutCase):
    def _other_wiki(self) -> Path:
        other = self.root / "other-wiki"
        api.init(WikiPaths.for_root(self.root, wiki_dir=other))
        return other

    def test_interrupted_promotion_retried_against_another_wiki_is_refused(self) -> None:
        other = self._other_wiki()
        for state in ("committing", "committed"):
            with self.subTest(state=state):
                prop = _proposals_dir(self.root, slug=state)
                if state == "committing":
                    self.interrupt_after_committing_receipt(prop)
                else:
                    self.interrupt_before_archive(prop)
                a_before, b_before = _tree(self.wiki), _tree(other)
                by_flag = run_cli("promote", str(prop), "--wiki-dir", str(other), cwd=self.root)
                self.assertEqual(by_flag.returncode, 10, by_flag.stderr)
                self.assertIn(f"[reason={REASON_WIKI_MISMATCH}]", by_flag.stderr)
                self.assertIn(str(self.wiki.resolve()), by_flag.stderr)
                self.assertIn(str(other.resolve()), by_flag.stderr)
                with patch.dict(os.environ, {ENV_WIKI_DIR: str(other)}):
                    by_env = run_cli("promote", str(prop), cwd=self.root)
                self.assertEqual(by_env.returncode, 10, by_env.stderr)
                self.assertIn(f"[reason={REASON_WIKI_MISMATCH}]", by_env.stderr)
                self.assertEqual(_tree(self.wiki), a_before, "nothing written to wiki A")
                self.assertEqual(_tree(other), b_before, "nothing written to wiki B")
                self.assertTrue((prop / RECEIPT).is_file())
                self.assertFalse((self.root / "doc_internal" / "proposals" / ".applied" / prop.name).exists())

    def test_a_different_directory_at_the_same_path_is_refused(self) -> None:
        for state in ("committing", "committed"):
            with self.subTest(state=state):
                prop = _proposals_dir(self.root, slug=state)
                if state == "committing":
                    self.interrupt_after_committing_receipt(prop)
                else:
                    self.interrupt_before_archive(prop)
                moved = self.root / "knowledge" / f"wiki-moved-{state}"
                os.rename(self.wiki, moved)
                shutil.copytree(moved, self.wiki)  # wiki B at A's old path: same files, new inode
                b_before = _tree(self.wiki)
                with self.assertRaises(PromoteApplyError) as ctx:
                    api.promote(prop, self.paths)
                self.assertEqual(ctx.exception.reason, REASON_WIKI_MISMATCH)
                self.assertIn("restored or re-cloned at the same path", str(ctx.exception))
                self.assertEqual(_tree(self.wiki), b_before)
                shutil.rmtree(self.wiki)
                os.rename(moved, self.wiki)

    def test_an_archived_receipt_from_another_wiki_is_refused_before_the_outcome_report(self) -> None:
        prop = _proposals_dir(self.root)
        archive = api.promote(prop, self.paths).archived_dir
        assert archive is not None
        other = self._other_wiki()
        with self.assertRaises(PromoteApplyError) as ctx:
            api.promote(archive, WikiPaths.for_root(self.root, wiki_dir=other))
        self.assertEqual(ctx.exception.reason, REASON_WIKI_MISMATCH)

    def test_no_usable_identity_is_refused_without_a_path_fallback(self) -> None:
        prop = _proposals_dir(self.root)
        self.interrupt_before_archive(prop)
        receipt = _receipt(prop)
        receipt["wiki_target"]["st_ino"] = 0
        (prop / RECEIPT).write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaises(PromoteApplyError) as recorded:
            api.promote(prop, self.paths)
        self.assertEqual(recorded.exception.reason, REASON_WIKI_IDENTITY_UNAVAILABLE)
        self.assertIn(str(prop / RECEIPT), str(recorded.exception))
        self.assertIn("stable inode identity", str(recorded.exception))
        # The live side reporting zero (some Windows and network filesystems) is refused the same way.
        receipt["wiki_target"]["st_ino"] = os.stat(self.wiki).st_ino
        (prop / RECEIPT).write_text(json.dumps(receipt), encoding="utf-8")
        real_open = promoter._open_wiki

        def zero_identity(wiki_dir: Path) -> promoter._WikiHandle:
            handle = real_open(wiki_dir)
            handle.st_dev = 0
            return handle

        with (
            patch("wiki_studio.promoter._open_wiki", side_effect=zero_identity),
            self.assertRaises(PromoteApplyError) as live,
        ):
            api.promote(prop, self.paths)
        self.assertEqual(live.exception.reason, REASON_WIKI_IDENTITY_UNAVAILABLE)
        self.assertTrue((prop / RECEIPT).is_file())
        self.assertEqual(
            [p.name for p in self.paths.applied_dir.iterdir()] if self.paths.applied_dir.exists() else [], []
        )

    def test_path_based_fallbacks_when_a_directory_descriptor_is_unavailable(self) -> None:
        # Where a directory cannot be opened (Windows): identity from os.stat, staging by path.
        real_open = os.open

        def refuse_directories(path: object, flags: int, *args: object, **kwargs: object) -> int:
            if path == self.wiki:
                raise PermissionError("directories cannot be opened here")
            return real_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        with patch("wiki_studio.promoter.os.open", side_effect=refuse_directories):
            handle = promoter._open_wiki(self.wiki)
        self.assertIsNone(handle.fd)
        self.assertEqual((handle.st_dev, handle.st_ino), (os.stat(self.wiki).st_dev, os.stat(self.wiki).st_ino))
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp) / "wiki"
            promoter._stage_wiki(handle, self.wiki, stage)
            self.assertEqual(_tree(stage), _tree(self.wiki))
            with patch("wiki_studio.promoter._FD_STAGING", False):
                promoter._stage_wiki(promoter._open_wiki(self.wiki), self.wiki, stage)  # replaces the stage
            self.assertEqual(_tree(stage), _tree(self.wiki))
        handle.close()

    def test_identity_comes_from_the_open_descriptor_and_staging_reads_through_it(self) -> None:
        handle = promoter._open_wiki(self.wiki)
        try:
            self.assertIsNotNone(handle.fd)
            self.assertEqual((handle.st_dev, handle.st_ino), (os.stat(self.wiki).st_dev, os.stat(self.wiki).st_ino))
            self.assertEqual(handle.resolved, str(self.wiki.resolve()))
            with tempfile.TemporaryDirectory() as tmp:
                stage = Path(tmp) / "wiki"
                promoter._stage_wiki(handle, self.wiki, stage)
                self.assertEqual(_tree(stage), _tree(self.wiki))
        finally:
            handle.close()
        self.assertIsNone(handle.fd)


class TestDigestRecipes(_LayoutCase):
    def test_a_pre_0_6_0_record_verifies_with_recipe_1_and_a_new_record_with_recipe_2(self) -> None:
        prop = _proposals_dir(self.root)
        (prop / "preview" / ".line.md").write_text("hidden\n", encoding="utf-8")
        files = {
            p.relative_to(prop).as_posix(): p.read_bytes()
            for p in prop.rglob("*")
            if p.is_file() and not any(part.startswith(".") for part in p.relative_to(prop).parts)
        }
        buf = b"".join(rel.encode() + b"\n" + files[rel] + b"\n--\n" for rel in sorted(files, key=str.encode))
        self.assertEqual(proposal_hash(prop), hashlib.sha256(buf).hexdigest(), "recipe 1 as documented")
        self.assertNotEqual(payload_digest(prop), proposal_hash(prop))
        with tempfile.TemporaryDirectory() as tmp:
            old = _write_audit(Path(tmp) / "old", [_valid_record(proposal_hash=proposal_hash(prop))])
            self.assertEqual(validate_audit_dir(old), [])
            new = _write_audit(Path(tmp) / "new", [_valid_record(proposal_hash=payload_digest(prop), hash_recipe=2)])
            self.assertEqual(validate_audit_dir(new), [])
            errors = validate_audit_dir(_write_audit(Path(tmp) / "bad", [_valid_record(hash_recipe="2")]))
            self.assertTrue(any("'hash_recipe' must be int" in e for e in errors))
            errors = validate_audit_dir(_write_audit(Path(tmp) / "unknown", [_valid_record(hash_recipe=3)]))
            self.assertTrue(any("unknown hash_recipe 3" in e for e in errors))
            errors = validate_audit_dir(_write_audit(Path(tmp) / "extra", [_valid_record(other=1)]))
            self.assertTrue(any("unexpected keys ['other']" in e for e in errors))

    def test_run2_protocol_archive_path_still_resolves(self) -> None:
        prop = _proposals_dir(self.root)
        plan_bytes = (prop / "plan.json").read_bytes()
        api.promote(prop, self.paths)
        archived_plan = self.root / "doc_internal" / "proposals" / ".applied" / prop.name / "plan.json"
        self.assertEqual(archived_plan.read_bytes(), plan_bytes)
        self.assertEqual(
            [e["path"] for e in json.loads(archived_plan.read_text(encoding="utf-8"))["edits"]][0],
            "incidents/cli-fixture.md",
        )


class TestDurabilityFailures(_LayoutCase):
    """PR #41 review: a directory fsync that fails with a real I/O error stops the promotion (FR-003, FR-004)."""

    def test_io_errors_propagate_and_unsupported_filesystems_are_skipped(self) -> None:
        directory = self.root / "fsync-probe"
        directory.mkdir()
        with (
            patch("wiki_studio.promoter.os.fsync", side_effect=OSError(errno.EIO, "I/O error")),
            self.assertRaises(OSError),
        ):
            promoter._fsync_dir(directory)
        for code in (errno.EINVAL, getattr(errno, "ENOTSUP", errno.EINVAL)):
            with patch("wiki_studio.promoter.os.fsync", side_effect=OSError(code, "not supported")):
                promoter._fsync_dir(directory)

    def test_a_lost_receipt_fsync_commits_nothing(self) -> None:
        prop = _proposals_dir(self.root)
        before = _tree(self.wiki)
        with (
            patch("wiki_studio.promoter.os.fsync", side_effect=OSError(errno.ENOSPC, "no space left on device")),
            self.assertRaises(OutputWriteError),
        ):
            api.promote(prop, self.paths)
        self.assertEqual(_tree(self.wiki), before)
        self.assertFalse((self.paths.applied_dir / prop.name).exists())


class TestReceiptPathContainment(_LayoutCase):
    """PR #41 review: a receipt's tracked paths are validated at load and contained before every recovery read."""

    def _forge(self, prop: Path, path: str, post: str) -> None:
        receipt = _receipt(prop)
        receipt["planned_writes"][0]["path"] = path
        receipt["planned_writes"][0]["post_sha256"] = post
        (prop / RECEIPT).write_text(json.dumps(receipt), encoding="utf-8")

    def test_a_tracked_path_that_leaves_the_wiki_is_never_read(self) -> None:
        outside_file = self.root / "outside.txt"
        outside_file.write_bytes(b"outside bytes\n")
        prop = _proposals_dir(self.root)
        self.interrupt_after_committing_receipt(prop)
        self._forge(prop, "../../outside.txt", _sha(b"outside bytes\n"))
        hashed: list[bytes] = []
        real = promoter._sha256

        def spy(data: bytes) -> str:
            hashed.append(data)
            return real(data)

        before = _tree(self.wiki)
        with patch("wiki_studio.promoter._sha256", spy), self.assertRaises(PromoteApplyError) as ctx:
            api.promote(prop, self.paths)
        self.assertEqual(ctx.exception.reason, REASON_UNCERTAIN_OUTCOME)
        self.assertNotIn(b"outside bytes\n", hashed, "the outside file was never read")
        self.assertEqual(_tree(self.wiki), before)
        self.assertTrue((prop / RECEIPT).is_file())

    def test_absolute_and_symlinked_tracked_paths_are_refused(self) -> None:
        outside_file = self.root / "outside.txt"
        outside_file.write_bytes(b"outside bytes\n")
        prop = _proposals_dir(self.root)
        self.interrupt_after_committing_receipt(prop)
        self._forge(prop, str(outside_file), _sha(b"outside bytes\n"))
        with self.assertRaises(PromoteApplyError) as absolute:
            api.promote(prop, self.paths)
        self.assertEqual(absolute.exception.reason, REASON_UNCERTAIN_OUTCOME)
        # A symlink planted at a well-formed tracked path matches neither state and is not followed.
        self._forge(prop, "incidents/link.md", _sha(b"outside bytes\n"))
        (self.wiki / "incidents").mkdir(exist_ok=True)
        (self.wiki / "incidents" / "link.md").symlink_to(outside_file)
        with self.assertRaises(PromoteApplyError) as linked:
            api.promote(prop, self.paths)
        self.assertEqual(linked.exception.reason, REASON_UNCERTAIN_OUTCOME)
        self.assertIn("incidents/link.md: neither", str(linked.exception))


if __name__ == "__main__":
    unittest.main()
