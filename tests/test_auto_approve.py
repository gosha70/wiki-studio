# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.7.0 (US4): auto-approval after a completed promotion, never inside it and never failing it (FR-030)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

from tests.test_approve import ApprovalCase, page_text
from wiki_studio import api, promoter
from wiki_studio.errors import PromoteApplyError
from wiki_studio.proposal import PageEdit

if TYPE_CHECKING:
    from pathlib import Path


class AutoApproveCase(ApprovalCase):
    def setUp(self) -> None:
        super().setUp()
        self.set_policy(auto_approve_on_promote=True)

    def propose_pages(self, name: str, *slugs: str, status: str = "stable") -> Path:
        edits = [PageEdit(f"decisions/{s}.md", "create", page_text(s, status=status), "why") for s in slugs]
        edits += [PageEdit("index.md", "append-index", f"- [{s}](decisions/{s}.md)", "why") for s in slugs]
        return api.propose(edits, self.paths, name=name, by="pat")

    def records_for(self, rel: str) -> list[dict[str, Any]]:
        found = []
        for path in self.records():
            data = json.loads(path.read_text(encoding="utf-8"))
            if data["path"] == rel:
                found.append(data)
        return found


class TestAutoApproval(AutoApproveCase):
    def test_each_content_page_written_is_approved_under_the_promoters_actor(self) -> None:
        result = api.promote(self.propose_pages("two", "a", "b"), self.paths, by="carol")
        self.assertEqual(result.approved_paths, ["decisions/a.md", "decisions/b.md"])
        self.assertEqual(result.warnings, [])
        assert result.archived_dir is not None
        receipt = json.loads((result.archived_dir / "receipt.json").read_text(encoding="utf-8"))
        for rel in result.approved_paths:
            (record,) = self.records_for(rel)
            carol = {"name": "carol", "source": "flag"}
            self.assertEqual((record["approver"], record["promoter"]), (carol, carol))
            self.assertEqual(record["proposer"], {"name": "pat", "source": "flag"})
            self.assertEqual(record["proposal"], {"name": "two", "submission_digest": receipt["submission_digest"]})
            self.assertEqual(self.state(rel).state, "approved")
        self.assertEqual(self.records_for("index.md"), [], "appends are never approved")
        self.assertEqual(receipt["state"], "committed")
        self.assertNotIn("approvals", json.dumps(receipt["planned_writes"]), "outside the receipt protocol")

    def test_the_cli_prints_the_approved_pages(self) -> None:
        result = self.cli("promote", str(self.propose_pages("one", "a")), "--by", "carol")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("approved knowledge/wiki/decisions/a.md", result.stdout)

    def test_an_update_is_approved_and_an_unchanged_existing_record_is_kept(self) -> None:
        api.promote(self.propose_pages("one", "a"), self.paths, by="carol")
        result = self.update("decisions/a.md", page_text("a", body="Start at 500 ms."), by="carol")
        self.assertEqual(result.approved_paths, ["decisions/a.md"])
        self.assertEqual(len(self.records_for("decisions/a.md")), 2)

    def test_a_draft_is_skipped_with_a_warning_and_no_record(self) -> None:
        result = api.promote(self.propose_pages("drafts", "d", status="draft"), self.paths, by="carol")
        self.assertEqual(result.approved_paths, [])
        self.assertTrue(any("decisions/d.md" in w and "draft" in w for w in result.warnings), result.warnings)
        self.assertEqual(self.records(), [])

    def test_an_approver_is_required_when_the_policy_says_so(self) -> None:
        self.set_policy(auto_approve_on_promote=True, approver_required=True)
        unnamed = api.promote(self.propose_pages("unnamed", "a"), self.paths)
        self.assertEqual(unnamed.approved_paths, [])
        self.assertTrue(any("requires an approver" in w for w in unnamed.warnings))
        named = api.promote(self.propose_pages("named", "b"), self.paths, by="carol")
        self.assertEqual(named.approved_paths, ["decisions/b.md"])

    def test_off_by_default_and_on_a_legacy_wiki(self) -> None:
        self.set_policy(auto_approve_on_promote=False)
        self.assertEqual(api.promote(self.propose_pages("off", "a"), self.paths).approved_paths, [])
        self.manifest.unlink()
        self.assertEqual(api.promote(self.propose_pages("legacy", "b"), self.paths).approved_paths, [])
        self.assertEqual(self.records(), [])

    def test_a_dry_run_approves_nothing(self) -> None:
        result = api.promote(self.propose_pages("dry", "a"), self.paths, dry_run=True)
        self.assertEqual(result.approved_paths, [])
        self.assertEqual(self.records(), [])


class TestAutoApprovalNeverFailsThePromotion(AutoApproveCase):
    def test_a_publication_failure_is_a_warning_and_the_promotion_stays_committed(self) -> None:
        with patch.object(promoter, "_publish_record", side_effect=OSError(28, "No space left on device")):
            result = api.promote(self.propose_pages("full", "a", "b"), self.paths, by="carol")
        self.assertEqual(result.approved_paths, [])
        self.assertEqual(sum("auto-approval: decisions/" in w and "failed" in w for w in result.warnings), 2)
        self.assertTrue((self.wiki / "decisions/a.md").is_file())
        self.assertEqual(self.state("decisions/a.md").state, "unapproved")
        # Recovered by running approve.
        self.assertEqual(len(api.approve(["decisions/a.md", "decisions/b.md"], self.paths).published), 2)

    def test_a_lock_timeout_is_a_warning(self) -> None:
        real = promoter.WikiLock
        calls = {"n": 0}

        class SecondAcquisitionTimesOut(real):  # type: ignore[misc, valid-type]
            def __enter__(self):  # noqa: ANN204
                calls["n"] += 1
                if calls["n"] == 2:
                    raise PromoteApplyError("lock timeout", reason="lock_timeout")
                return super().__enter__()

        with patch.object(promoter, "WikiLock", SecondAcquisitionTimesOut):
            result = api.promote(self.propose_pages("busy", "a"), self.paths, by="carol")
        self.assertEqual(result.approved_paths, [])
        self.assertTrue(any("auto-approval did not run to the end" in w for w in result.warnings))
        self.assertTrue((self.wiki / "decisions/a.md").is_file())

    def test_an_unfinished_archive_skips_auto_approval_with_a_warning(self) -> None:
        with patch.object(promoter, "_archive_submission", side_effect=OSError(5, "I/O error")):
            result = api.promote(self.propose_pages("noarchive", "a"), self.paths, by="carol")
        self.assertIsNone(result.archived_dir)
        self.assertEqual(result.approved_paths, [])
        self.assertTrue(any("archive step did not complete" in w for w in result.warnings))
        finished = api.promote(self.paths.proposals_dir / "noarchive", self.paths, by="carol")
        self.assertEqual(finished.approved_paths, ["decisions/a.md"], "the finishing promote auto-approves")

    def test_the_archive_on_disk_is_never_reread(self) -> None:
        """PR #47 review: auto-approval uses the plan and receipt validated under the lock, not the mutable archive."""
        with patch.object(promoter, "_read_json", side_effect=OSError(5, "I/O error")):
            result = api.promote(self.propose_pages("unreadable", "a"), self.paths, by="carol")
        self.assertEqual(result.approved_paths, ["decisions/a.md"])

    def test_the_handoff_never_reaches_the_public_result(self) -> None:
        """PR #47 review: the validated plan and receipt travel privately, not on PromoteResult."""
        import dataclasses

        result = api.promote(self.propose_pages("public", "a"), self.paths, by="carol")
        self.assertEqual(result.approved_paths, ["decisions/a.md"])
        fields = {f.name for f in dataclasses.fields(result)}
        self.assertFalse(any(name.startswith("_") for name in fields), fields)
        dumped = json.dumps(dataclasses.asdict(result), default=str)
        self.assertNotIn("planned_writes", dumped)
        self.assertNotIn("submission_digest", dumped)

    def test_an_archive_edited_after_the_lock_cannot_add_or_reattribute_a_target(self) -> None:
        """PR #47 review: rewriting plan.json and receipt.json in the gap approves nothing extra under this promoter."""
        self.create("c", by="erin")
        before_c = self.records_for("decisions/c.md")
        real = promoter._auto_approve

        def tamper_then_approve(archive: Path, paths: Any, *basis: Any) -> tuple[list[str], list[str]]:
            plan = json.loads((archive / "plan.json").read_text(encoding="utf-8"))
            receipt = json.loads((archive / "receipt.json").read_text(encoding="utf-8"))
            live_c = api.read_page("decisions/c.md", self.paths).sha256
            plan["edits"].append(
                {"path": "decisions/c.md", "action": "update", "preview": "preview/x", "rationale": "x"}
            )
            receipt["planned_writes"].append({"path": "decisions/c.md", "pre_sha256": None, "post_sha256": live_c})
            receipt["actor"] = {"name": "mallory", "source": "flag"}
            (archive / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
            (archive / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
            return real(archive, paths, *basis)

        with patch.object(promoter, "_auto_approve", tamper_then_approve):
            result = api.promote(self.propose_pages("tamper", "a"), self.paths, by="carol")
        self.assertEqual(result.approved_paths, ["decisions/a.md"])
        self.assertEqual(self.records_for("decisions/c.md"), before_c, "no record added for the injected page")
        for record in self.records_for("decisions/a.md"):
            self.assertEqual(record["promoter"], {"name": "carol", "source": "flag"})


class TestInterleaving(AutoApproveCase):
    def test_a_second_writer_between_archive_and_auto_approval_gets_no_record_under_the_promoter(self) -> None:
        """FR-030: no record for the intervening revision under the first promoter; the unchanged page is approved."""
        real = promoter._auto_approve
        state = {"injected": False}

        def second_writer_first(archive: Path, paths: Any, *basis: Any) -> tuple[list[str], list[str]]:
            if not state["injected"]:
                state["injected"] = True
                # Another writer lands between the archive and the auto-approval (the lock is free).
                self.update("decisions/b.md", page_text("b", body="Changed by dave."), by="dave")
            return real(archive, paths, *basis)

        with patch.object(promoter, "_auto_approve", second_writer_first):
            result = api.promote(self.propose_pages("two", "a", "b"), self.paths, by="carol")
        self.assertEqual(result.approved_paths, ["decisions/a.md"])
        self.assertTrue(any("decisions/b.md" in w and "changed after this promotion" in w for w in result.warnings))
        live_b = api.read_page("decisions/b.md", self.paths).sha256
        carol = {"name": "carol", "source": "flag"}
        self.assertEqual(len(self.records_for("decisions/b.md")), 1, "only dave's own auto-approval")
        for record in self.records_for("decisions/b.md"):
            self.assertNotEqual(record["promoter"], carol, "no attribution of bytes carol did not promote")
            self.assertEqual(record["sha256"], live_b)
            self.assertEqual(record["approver"], {"name": "dave", "source": "flag"})
        self.assertEqual(self.records_for("decisions/a.md")[0]["approver"], carol)
