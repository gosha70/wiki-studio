# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.7.0 (US5): ``superseded_by`` through lint, ``approve`` and ``review_state``, and ``corrects`` kept byte for byte.

FR-033..FR-036. The linter's own cases (missing, non-page, self, chain,
cycle, absolute, escaping) are in ``tests/test_lint.py``; this module covers
the verbs and the review state over a managed wiki.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from tests.test_approve import ApprovalCase, page_text
from wiki_studio import api
from wiki_studio.errors import PromoteValidationError
from wiki_studio.proposal import PageEdit
from wiki_studio.schema import SCHEMA_VERSION
from wiki_studio.yaml_lite import parse_frontmatter

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "tests" / "fixtures" / "corrects" / "multi-corrections.md"
ADR = REPO / "docs" / "adr" / "0002-page-identity-and-review-keys.md"
CORRECTS_VALUE = "mem-3f9c2a1b, mem-77d0e4c2, mem-a1b2c3d4"


class TestSupersededState(ApprovalCase):
    def replaced_pair(self) -> tuple[str, str]:
        """A replacement page and the page it replaces (``superseded_by`` pointing at it); (old, new)."""
        new = self.create("retry-backoff-v2")
        old = self.create("retry-backoff", extra=f"superseded_by: {new}\n")
        return old, new

    def test_a_superseded_page_with_a_valid_approved_record_reads_superseded(self) -> None:
        old, _new = self.replaced_pair()
        # approve refuses a superseded page, so the record for its live bytes is written with that check bypassed.
        with patch("wiki_studio.promoter.superseded_by", return_value=None):
            published = api.approve([old], self.paths, by="alice").published
        live = api.read_page(old, self.paths).sha256
        self.assertEqual(len(published), 1)
        self.assertIn(f"/{live}/", published[0], "the record is for the live bytes")
        state = self.state(old)
        self.assertEqual((state.state, state.reason), ("superseded", "superseded_by"))
        self.assertEqual(state.live_sha256, live)

    def test_approve_refuses_a_superseded_page(self) -> None:
        old, new = self.replaced_pair()
        result = self.cli("approve", old)
        self.assertEqual(result.returncode, 9, result.stderr)
        self.assertIn(f"{old}: carries superseded_by ({new})", result.stderr)
        with self.assertRaises(PromoteValidationError):
            api.approve([old], self.paths)
        self.assertEqual(self.records(), [])

    def test_the_replacement_itself_is_approvable(self) -> None:
        _old, new = self.replaced_pair()
        api.approve([new], self.paths)
        self.assertEqual(self.state(new).state, "approved")

    def test_a_legacy_wiki_reads_manifest_missing_before_superseded(self) -> None:
        old, _new = self.replaced_pair()
        self.manifest.unlink()
        state = self.state(old)
        self.assertEqual((state.state, state.reason), ("unapproved", "manifest_missing"))

    def test_promote_refuses_a_create_whose_target_does_not_exist(self) -> None:
        rel = "decisions/orphaned.md"
        edits = [
            PageEdit(rel, "create", page_text("orphaned", extra="superseded_by: decisions/nope.md\n"), "why"),
            PageEdit("index.md", "append-index", f"- [orphaned]({rel})", "why"),
        ]
        proposal = api.propose(edits, self.paths, name="orphaned")
        with self.assertRaises(PromoteValidationError) as ctx:
            api.promote(proposal, self.paths)
        self.assertIn(f"{rel}: superseded_by target does not exist → decisions/nope.md", str(ctx.exception))
        self.assertFalse((self.wiki / rel).exists())

    def test_a_hand_rename_of_the_target_is_a_lint_violation(self) -> None:
        old, new = self.replaced_pair()
        (self.wiki / new).rename(self.wiki / "decisions" / "renamed.md")
        violations = api.lint(self.paths).violations
        self.assertIn(f"{old}: superseded_by target does not exist → {new}", violations)


class TestCorrects(ApprovalCase):
    """``corrects`` is memkernel's: one scalar line, kept byte for byte, never interpreted (FR-036)."""

    def test_yaml_lite_parses_several_corrections_as_one_scalar_line(self) -> None:
        text = FIXTURE.read_text(encoding="utf-8")
        self.assertEqual(parse_frontmatter(text)["corrects"], CORRECTS_VALUE)
        self.assertEqual(
            [line for line in text.splitlines() if line.startswith("corrects:")], [f"corrects: {CORRECTS_VALUE}"]
        )

    def test_propose_and_promote_preserve_the_page_byte_for_byte(self) -> None:
        rel = "decisions/multi-corrections.md"
        data = FIXTURE.read_bytes()
        edits = [
            PageEdit(rel, "create", data.decode("utf-8"), "why"),
            PageEdit("index.md", "append-index", f"- [Deploy window]({rel})", "why"),
        ]
        proposal = api.propose(edits, self.paths, name="corrects")
        self.assertEqual((proposal / "preview" / rel).read_bytes(), data)
        api.promote(proposal, self.paths)
        self.assertEqual((self.wiki / rel).read_bytes(), data)
        self.assertEqual(api.lint(self.paths).violations, ())
        api.approve([rel], self.paths)
        self.assertEqual(self.state(rel).state, "approved", "corrects means nothing for review")

    def test_an_update_keeps_the_line_as_written(self) -> None:
        rel = self.create("deploy-window")
        text = api.read_page(rel, self.paths).text.replace(
            "status: stable\n", f"status: stable\ncorrects: {CORRECTS_VALUE}\n"
        )
        self.update(rel, text)
        self.assertEqual((self.wiki / rel).read_text(encoding="utf-8"), text)


class TestAdrMatchesTheBuild(ApprovalCase):
    def test_adr_0002_records_superseded_by_and_corrects_as_built(self) -> None:
        adr = " ".join(ADR.read_text(encoding="utf-8").split())
        for needle in (
            "superseded_by: decisions/retry-backoff-v2.md",
            "does not exist, is not a page, is the page itself or is itself superseded (no chains, so no cycles)",
            "An absolute or escaping target is a violation.",
            "`review_state` reports such a page `superseded` whatever its approval records say, "
            "and `approve` refuses it.",
            "corrects: mem-ref-1, mem-ref-2",
            "**memkernel-interpreted**",
            "wiki-studio preserves it byte for byte through `propose` and `promote` and does not interpret it.",
            "**The value syntax is not final.**",
            f"from `schema.version` 1 to {SCHEMA_VERSION}",
        ):
            with self.subTest(needle):
                self.assertIn(needle, adr)
