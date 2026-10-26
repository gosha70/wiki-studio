# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.7.0 (US4): ``approve`` and ``api.approve``: batch preflight, ``--revision``, partial publication, drift (FR-021)"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

from tests.test_manifest import ManifestCase
from wiki_studio import api, promoter
from wiki_studio.errors import ContractViolationError, OutputWriteError, PromoteValidationError
from wiki_studio.proposal import PageEdit
from wiki_studio.review import APPROVALS_REL, ReviewState

if TYPE_CHECKING:
    from pathlib import Path

PAGE = (
    "---\npage_type: decision\nslug: {slug}\ntitle: {title}\nstatus: {status}\nlast_reviewed: 2026-10-16\n"
    "{extra}sources:\n  - path: notes.md\n---\n\n# {title}\n\n"
    "## Decision\n\n{body}\n\n"
    "## Context\n\nAgreed with the platform team.\n\n## Alternatives considered\n\nFixed 1 s delay.\n\n"
    "## Consequences\n\nLong outages wait at most 8 s between tries.\n"
)


def page_text(
    slug: str, *, status: str = "stable", page_id: str | None = None, body: str = "Start at 250 ms.", extra: str = ""
) -> str:
    """A valid decision page; ``page_id`` and ``extra`` frontmatter lines go before ``sources:``."""
    lines = extra + (f"page_id: {page_id}\n" if page_id else "")
    return PAGE.format(slug=slug, title=slug.replace("-", " ").title(), status=status, extra=lines, body=body)


class ApprovalCase(ManifestCase):
    """A managed wiki (``init`` ran) with helpers to create, edit and inspect pages and their records."""

    def setUp(self) -> None:
        super().setUp()
        api.init(self.paths)
        self._count = 0

    def create(self, slug: str, *, by: str | None = None, **kwargs: object) -> str:
        """Promote a create of ``decisions/<slug>.md`` (and its index line); return the wiki path."""
        rel = f"decisions/{slug}.md"
        self._count += 1
        edits = [
            PageEdit(rel, "create", page_text(slug, **kwargs), "why"),  # type: ignore[arg-type]
            PageEdit("index.md", "append-index", f"- [{slug}]({rel})", "why"),
        ]
        api.promote(api.propose(edits, self.paths, name=f"create-{self._count}"), self.paths, by=by)
        return rel

    def update(self, rel: str, text: str, *, by: str | None = None) -> api.PromoteResult:
        """Promote a guarded update of ``rel`` to ``text``."""
        self._count += 1
        base = api.read_page(rel, self.paths).sha256
        edit = PageEdit(rel, "update", text, "why", base_sha256=base)
        return api.promote(api.propose([edit], self.paths, name=f"update-{self._count}"), self.paths, by=by)

    def hand_edit(self, rel: str, text: str) -> None:
        (self.wiki / rel).write_text(text, encoding="utf-8")

    def records(self) -> list[Path]:
        """Every file under ``.audit/approvals/``."""
        root = self.wiki / APPROVALS_REL
        return sorted(p for p in root.rglob("*") if p.is_file()) if root.is_dir() else []

    def record(self, rel: str) -> dict[str, object]:
        return json.loads((self.wiki / rel).read_text(encoding="utf-8"))

    def state(self, rel: str) -> ReviewState:
        (state,) = api.review_state(self.paths, pages=[rel])
        return state


class TestApprove(ApprovalCase):
    def test_approve_writes_one_record_and_reports_it(self) -> None:
        rel = self.create("retry-backoff")
        result = api.approve([rel], self.paths, by="alice")
        self.assertEqual(len(result.published), 1)
        self.assertEqual((result.existing, result.warnings), ([], []))
        record = self.record(result.published[0])
        self.assertEqual(record["approver"], {"name": "alice", "source": "flag"})
        self.assertEqual(record["proposal"]["name"], "create-1")  # type: ignore[index]
        self.assertEqual(record["promoter"], {"name": None, "source": "none"})
        self.assertEqual(self.state(rel).state, "approved")

    def test_a_rerun_is_idempotent_and_reports_the_existing_record(self) -> None:
        rel = self.create("retry-backoff")
        first = api.approve([rel], self.paths)
        before = self.records()
        again = api.approve([rel, f"./{rel}"], self.paths)
        self.assertEqual((again.published, again.existing), ([], first.published))
        self.assertEqual(self.records(), before)

    def test_the_cli_approves_and_prints_the_records(self) -> None:
        rel = self.create("retry-backoff")
        result = self.cli("approve", rel, "--by", "alice")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("approved: knowledge/wiki/.audit/approvals/path/", result.stdout)
        again = self.cli("approve", rel)
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("already approved: ", again.stdout)

    def test_the_actor_comes_from_the_environment_when_no_flag_is_given(self) -> None:
        rel = self.create("retry-backoff")
        with patch.dict("os.environ", {"WIKI_STUDIO_ACTOR": "erin"}):
            result = api.approve([rel], self.paths)
        self.assertEqual(self.record(result.published[0])["approver"], {"name": "erin", "source": "env"})

    def test_a_proposal_archived_elsewhere_is_not_found(self) -> None:
        rel = f"decisions/{'x'}.md"
        self.hand_edit("index.md", (self.wiki / "index.md").read_text(encoding="utf-8") + f"\n- [x]({rel})\n")
        (self.wiki / "decisions").mkdir()
        self.hand_edit(rel, page_text("x"))
        result = api.approve([rel], self.paths)
        record = self.record(result.published[0])
        self.assertEqual((record["proposal"], record["proposer"], record["promoter"]), (None, None, None))

    def test_no_page_is_a_contract_violation(self) -> None:
        with self.assertRaises(ContractViolationError):
            api.approve([], self.paths)

    def test_a_missing_page_exits_5_and_an_outside_one_7(self) -> None:
        self.assertEqual(self.cli("approve", "decisions/nope.md").returncode, 5)
        self.assertEqual(self.cli("approve", "../notes.md").returncode, 7)
        self.assertEqual(self.cli("approve", "/etc/hosts").returncode, 7)
        self.assertEqual(self.records(), [])

    def test_a_symlinked_page_exits_7_and_a_non_utf8_page_exits_4(self) -> None:
        rel = self.create("retry-backoff")
        (self.wiki / "decisions" / "link.md").symlink_to(self.wiki / rel)
        self.assertEqual(self.cli("approve", "decisions/link.md").returncode, 7)
        (self.wiki / rel).write_bytes(b"---\nslug: \xff\n---\n")
        self.assertEqual(self.cli("approve", rel).returncode, 4)
        self.assertEqual(self.records(), [])


class TestBatchPreflight(ApprovalCase):
    def test_one_bad_page_refuses_the_batch_and_writes_nothing(self) -> None:
        good = self.create("good")
        draft = self.create("draft-page", status="draft")
        superseded = self.create("old", extra=f"superseded_by: {good}\n")
        result = self.cli("approve", good, draft, superseded)
        self.assertEqual(result.returncode, 9, result.stderr)
        self.assertIn(f"{draft}: status is draft", result.stderr)
        self.assertIn(f"{superseded}: carries superseded_by", result.stderr)
        self.assertNotIn(f"{good}:", result.stderr)
        self.assertFalse((self.wiki / APPROVALS_REL).exists(), "nothing was written")

    def test_a_structural_lint_violation_for_the_page_refuses_it(self) -> None:
        rel = self.create("retry-backoff")
        self.hand_edit(rel, page_text("wrong-slug"))
        with self.assertRaises(PromoteValidationError) as ctx:
            api.approve([rel], self.paths)
        self.assertIn(f"{rel}: structural lint: {rel}: slug 'wrong-slug'", str(ctx.exception))

    def test_a_file_the_linter_does_not_list_is_refused(self) -> None:
        (self.wiki / "schema").mkdir()
        self.hand_edit("schema/notes.md", page_text("notes"))
        with self.assertRaises(PromoteValidationError) as ctx:
            api.approve(["schema/notes.md"], self.paths)
        self.assertIn("not a page the structural linter lists", str(ctx.exception))

    def test_an_approver_is_required_when_the_policy_says_so(self) -> None:
        rel = self.create("retry-backoff")
        self.set_policy(approver_required=True)
        unnamed = self.cli("approve", rel)
        self.assertEqual(unnamed.returncode, 9)
        self.assertIn("requires an approver", unnamed.stderr)
        self.assertEqual(self.cli("approve", rel, "--by", "alice").returncode, 0)


class TestRevision(ApprovalCase):
    def test_a_matching_revision_approves(self) -> None:
        rel = self.create("retry-backoff")
        sha = api.read_page(rel, self.paths).sha256
        self.assertEqual(self.cli("approve", rel, "--revision", sha).returncode, 0)
        self.assertEqual(self.state(rel).approved_sha256, sha)

    def test_a_revision_mismatch_exits_9_and_writes_nothing(self) -> None:
        rel = self.create("retry-backoff")
        reviewed = api.read_page(rel, self.paths).sha256
        self.hand_edit(rel, page_text("retry-backoff", body="Start at 500 ms."))
        result = self.cli("approve", rel, "--revision", reviewed)
        self.assertEqual(result.returncode, 9)
        self.assertIn("not the revision that was reviewed", result.stderr)
        with self.assertRaises(PromoteValidationError):
            api.approve([rel], self.paths, expected={f"./{rel}": reviewed})
        self.assertEqual(self.records(), [])

    def test_revision_with_more_than_one_page_exits_4(self) -> None:
        a, b = self.create("a"), self.create("b")
        result = self.cli("approve", a, b, "--revision", api.read_page(a, self.paths).sha256)
        self.assertEqual(result.returncode, 4)
        self.assertIn("exactly one page", result.stderr)
        self.assertEqual(self.records(), [])

    def test_a_malformed_or_unrelated_expected_revision_is_a_contract_violation(self) -> None:
        a, b = self.create("a"), self.create("b")
        self.assertEqual(self.cli("approve", a, "--revision", "abc").returncode, 4)
        with self.assertRaises(ContractViolationError):
            api.approve([a], self.paths, expected={b: api.read_page(b, self.paths).sha256})
        with self.assertRaises(ContractViolationError):
            api.approve([a], self.paths, expected={"../x.md": "0" * 64})


class TestPartialPublication(ApprovalCase):
    def test_an_io_failure_part_way_exits_6_naming_both_sides_then_a_rerun_finishes(self) -> None:
        a, b = self.create("a"), self.create("b")
        real = promoter._publish_record
        calls = {"n": 0}

        def second_fails(paths, rel, data):  # noqa: ANN001, ANN202
            calls["n"] += 1
            if calls["n"] == 2:
                raise OSError(28, "No space left on device")
            return real(paths, rel, data)

        with patch.object(promoter, "_publish_record", second_fails), self.assertRaises(OutputWriteError) as ctx:
            api.approve([a, b], self.paths)
        message = str(ctx.exception)
        self.assertIn(f"published or already approved: {a}", message)
        self.assertIn(f"not published: {b}", message)
        self.assertEqual(len(self.records()), 1, "the published record stays")
        self.assertEqual(self.state(a).state, "approved")
        self.assertEqual(self.state(b).state, "unapproved")
        rerun = api.approve([a, b], self.paths)
        self.assertEqual((len(rerun.existing), len(rerun.published)), (1, 1))
        self.assertEqual(self.state(b).state, "approved")

    def test_the_cli_maps_a_partial_publication_to_exit_6(self) -> None:
        rel = self.create("a")
        with patch.object(promoter, "_publish_record", side_effect=OSError(5, "I/O error")):
            result = self.cli("approve", rel)
        self.assertEqual(result.returncode, 6)
        self.assertIn("not published: decisions/a.md", result.stderr)


class TestApproveNeedsTheContract(ApprovalCase):
    def test_a_legacy_wiki_exits_4_naming_init(self) -> None:
        rel = self.create("retry-backoff")
        self.manifest.unlink()
        result = self.cli("approve", rel)
        self.assertEqual(result.returncode, 4)
        self.assertIn("wiki-studio init", result.stderr)
        with self.assertRaises(ContractViolationError):
            api.approve([rel], self.paths)
        state = self.state(rel)
        self.assertEqual((state.state, state.reason), ("unapproved", "manifest_missing"))
        self.assertEqual(self.records(), [])

    def test_managed_drift_is_a_warning_in_the_result_and_on_stderr(self) -> None:
        rel = self.create("retry-backoff")
        (self.wiki / "schema").mkdir()
        (self.wiki / "schema" / "page-types.md").write_text("# local\n", encoding="utf-8")
        result = api.approve([rel], self.paths)
        self.assertTrue(any("schema drift" in w for w in result.warnings))
        self.assertEqual(len(result.published), 1)
        cli = self.cli("approve", rel)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        self.assertIn("warning: schema drift", cli.stderr)

    def test_governed_drift_exits_4(self) -> None:
        rel = self.create("retry-backoff")
        self.set_policy(approval_required=True)
        (self.wiki / "schema").mkdir()
        (self.wiki / "schema" / "page-types.md").write_text("# local\n", encoding="utf-8")
        cli = self.cli("approve", rel)
        self.assertEqual(cli.returncode, 4)
        self.assertIn("schema drift", cli.stderr)
        with self.assertRaises(ContractViolationError):
            api.approve([rel], self.paths)
        self.assertEqual(self.records(), [])

    def test_a_newer_manifest_exits_4(self) -> None:
        rel = self.create("retry-backoff")
        self.edit_manifest(manifest_version=99)
        cli = self.cli("approve", rel)
        self.assertEqual(cli.returncode, 4)
        self.assertIn("manifest_version 99", cli.stderr)
        with self.assertRaises(ContractViolationError):
            api.approve([rel], self.paths)
        self.assertEqual(self.records(), [])


class TestApiApproveWrapsOSError(ApprovalCase):
    def test_an_unexpected_os_error_becomes_exit_6(self) -> None:
        rel = self.create("a")
        with (
            patch.object(promoter, "_lint_for_approval", side_effect=OSError(13, "Permission denied")),
            self.assertRaises(OutputWriteError),
        ):
            api.approve([rel], self.paths)
