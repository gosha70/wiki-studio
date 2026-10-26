# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.7.0 (US4): ``api.review_state`` and the acceptance cases of approval (FR-020, FR-026, FR-027, FR-032)."""

from __future__ import annotations

import hashlib

from tests.test_approve import ApprovalCase, page_text
from wiki_studio import api
from wiki_studio.errors import ContractViolationError, PathOutsideRootError, SourceMissingError
from wiki_studio.proposal import PageEdit, new_page_id
from wiki_studio.review import policy_sha256


class TestAcceptanceCases(ApprovalCase):
    """FR-032: one test per acceptance case on this side."""

    def test_a_draft_is_refused_by_approve_and_reads_draft(self) -> None:
        rel = self.create("draft-page", status="draft")
        self.assertEqual(self.cli("approve", rel).returncode, 9)
        state = self.state(rel)
        self.assertEqual((state.state, state.reason), ("unapproved", "draft"))
        self.assertEqual(self.records(), [])

    def test_status_stable_without_a_record_is_unapproved_and_approved_by_is_refused(self) -> None:
        rel = self.create("stable-page", status="stable")
        state = self.state(rel)
        self.assertEqual((state.state, state.reason), ("unapproved", "no_record"))
        claims = page_text("claims", extra="approved_by: alice\n")
        with self.assertRaises(ContractViolationError) as ctx:
            api.propose([PageEdit("decisions/claims.md", "create", claims, "why")], self.paths, name="claims")
        self.assertIn("'approved_by'", str(ctx.exception))
        self.assertIn("decisions/claims.md", str(ctx.exception))

    def test_a_hand_edit_is_stale_until_its_new_bytes_are_approved(self) -> None:
        rel = self.create("retry-backoff")
        first = api.approve([rel], self.paths).published[0]
        old_sha = api.read_page(rel, self.paths).sha256
        self.hand_edit(rel, page_text("retry-backoff", body="Start at 500 ms."))
        stale = self.state(rel)
        self.assertEqual((stale.state, stale.reason), ("stale", "live_bytes_differ"))
        self.assertEqual((stale.record_path, stale.approved_sha256), (first, old_sha))
        self.assertNotEqual(stale.live_sha256, old_sha)
        api.approve([rel], self.paths)
        again = self.state(rel)
        self.assertEqual(again.state, "approved")
        self.assertEqual(again.approved_sha256, again.live_sha256)

    def test_tightening_approver_required_reopens_only_approver_less_records_and_relaxing_reopens_nothing(self) -> None:
        unnamed, named = self.create("unnamed"), self.create("named")
        api.approve([unnamed], self.paths)
        api.approve([named], self.paths, by="alice")
        self.set_policy(approver_required=True)
        self.assertEqual(self.state(unnamed).state, "policy-changed")
        self.assertEqual(self.state(unnamed).reason, "no_record_satisfies_policy")
        self.assertEqual(self.state(named).state, "approved")
        self.set_policy(approver_required=False)
        self.assertEqual([s.state for s in api.review_state(self.paths)], ["approved", "approved"])


class TestPolicy(ApprovalCase):
    def test_the_policy_hash_covers_approver_required_only(self) -> None:
        def expected(flag: str) -> str:
            return hashlib.sha256(f'{{"approver_required":{flag}}}'.encode()).hexdigest()

        base = {"approval_required": False, "approver_required": False, "auto_approve_on_promote": False}
        self.assertEqual(policy_sha256(base), expected("false"))
        self.assertEqual(policy_sha256({**base, "approver_required": True}), expected("true"))
        for key in ("approval_required", "auto_approve_on_promote"):
            self.assertEqual(policy_sha256({**base, key: True}), expected("false"), key)

    def test_turning_a_managed_wiki_governed_keeps_every_approval(self) -> None:
        pages = [self.create("a"), self.create("b")]
        api.approve(pages, self.paths)
        self.set_policy(approval_required=True)
        self.assertEqual([s.state for s in api.review_state(self.paths)], ["approved", "approved"])

    def test_toggling_auto_approve_on_promote_never_yields_policy_changed(self) -> None:
        rel = self.create("a")
        api.approve([rel], self.paths)
        for value in (True, False):
            self.set_policy(auto_approve_on_promote=value)
            self.assertEqual(self.state(rel).state, "approved")

    def test_an_acknowledged_schema_override_change_leaves_an_approved_page_approved(self) -> None:
        rel = self.create("a")
        api.approve([rel], self.paths)
        (self.wiki / "schema").mkdir()
        (self.wiki / "schema" / "page-types.md").write_text("# local rules\n", encoding="utf-8")
        api.init(self.paths, update_schema=True)
        self.assertFalse(api.info(self.paths).schema_contract.drift)
        self.assertEqual(self.state(rel).state, "approved")


class TestLookup(ApprovalCase):
    def test_the_default_set_skips_the_root_index_and_log_and_an_explicit_list_is_exact(self) -> None:
        a, b = self.create("a"), self.create("b")
        self.assertEqual([s.path for s in api.review_state(self.paths)], [a, b])
        self.assertEqual(
            [s.path for s in api.review_state(self.paths, pages=["index.md", f"./{b}", b])], ["index.md", b]
        )

    def test_an_explicit_page_is_read_through_the_wiki_boundary(self) -> None:
        with self.assertRaises(SourceMissingError):
            api.review_state(self.paths, pages=["decisions/nope.md"])
        with self.assertRaises(PathOutsideRootError):
            api.review_state(self.paths, pages=["../notes.md"])

    def test_a_satisfying_record_is_found_in_any_policy_directory(self) -> None:
        rel = self.create("a")
        written = api.approve([rel], self.paths, by="alice").published[0]
        self.set_policy(approver_required=True)
        state = self.state(rel)
        self.assertEqual((state.state, state.record_path), ("approved", written))
        self.assertNotIn(policy_sha256({"approver_required": True}), written)

    def test_approve_reports_a_satisfying_record_under_another_policy_hash_and_writes_nothing(self) -> None:
        rel = self.create("a")
        written = api.approve([rel], self.paths, by="alice").published[0]
        self.set_policy(approver_required=True)
        again = api.approve([rel], self.paths, by="bob")
        self.assertEqual((again.published, again.existing), ([], [written]))

    def test_approve_writes_under_the_current_hash_when_no_record_satisfies_the_policy(self) -> None:
        rel = self.create("a")
        api.approve([rel], self.paths)
        self.set_policy(approver_required=True)
        again = api.approve([rel], self.paths, by="bob")
        self.assertEqual(len(again.published), 1)
        self.assertIn(policy_sha256({"approver_required": True}), again.published[0])
        self.assertEqual(self.state(rel).state, "approved")
        self.assertEqual(len(self.records()), 2, "the earlier record stays")

    def test_the_newest_matching_record_is_reported(self) -> None:
        rel = self.create("a")
        api.approve([rel], self.paths)
        self.set_policy(approver_required=True)
        newer = api.approve([rel], self.paths, by="bob").published[0]
        self.set_policy(approver_required=False)
        self.assertEqual(self.state(rel).record_path, newer)

    def test_a_superseded_page_reads_superseded_whatever_its_records_say(self) -> None:
        target, rel = self.create("new"), self.create("old")
        api.approve([rel], self.paths)
        self.hand_edit(rel, page_text("old", extra=f"superseded_by: {target}\n"))
        state = self.state(rel)
        self.assertEqual((state.state, state.reason), ("superseded", "superseded_by"))


class TestRecreatedAndRekeyedPages(ApprovalCase):
    """FR-027: a path-keyed approval is a fact about this path and these exact bytes."""

    def _delete(self, rel: str) -> None:
        (self.wiki / rel).unlink()

    def test_a_deleted_path_keyed_page_recreated_with_different_bytes_reads_stale_never_approved(self) -> None:
        rel = self.create("a")
        old = api.approve([rel], self.paths).published[0]
        self._delete(rel)
        self.hand_edit(rel, page_text("a", body="Something else entirely."))
        state = self.state(rel)
        self.assertEqual((state.state, state.record_path), ("stale", old))

    def test_a_deleted_path_keyed_page_recreated_with_identical_bytes_reads_approved(self) -> None:
        rel = self.create("a")
        original = (self.wiki / rel).read_bytes()
        api.approve([rel], self.paths)
        self._delete(rel)
        (self.wiki / rel).write_bytes(original)
        self.assertEqual(self.state(rel).state, "approved")

    def test_a_recreated_page_with_a_fresh_page_id_reads_unapproved(self) -> None:
        rel = self.create("a", page_id=new_page_id())
        api.approve([rel], self.paths)
        self._delete(rel)
        self.hand_edit(rel, page_text("a", page_id=new_page_id()))
        state = self.state(rel)
        self.assertEqual((state.state, state.reason), ("unapproved", "no_record"))

    def test_a_page_gaining_a_page_id_by_update_reads_stale_with_its_path_record(self) -> None:
        rel = self.create("a")
        path_record = api.approve([rel], self.paths).published[0]
        self.update(rel, page_text("a", page_id=new_page_id()))
        state = self.state(rel)
        self.assertEqual((state.state, state.record_path), ("stale", path_record))
        self.assertTrue(state.page_key.startswith("pg-"))
        self.assertIn("/path/", path_record)
        rekeyed = api.approve([rel], self.paths).published[0]
        self.assertIn(f"/id/{state.page_key}/", rekeyed)
        self.assertEqual(self.state(rel).state, "approved")

    def test_a_renamed_page_with_a_page_id_reads_stale_with_its_earlier_record(self) -> None:
        page_id = new_page_id()
        rel = self.create("a", page_id=page_id)
        record = api.approve([rel], self.paths).published[0]
        self._delete(rel)
        self.hand_edit("decisions/b.md", page_text("b", page_id=page_id))
        state = self.state("decisions/b.md")
        self.assertEqual((state.state, state.page_key, state.record_path), ("stale", page_id, record))
