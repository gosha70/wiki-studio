# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""``api.propose``: a library caller's patch-set goes through the same gate as ``ingest`` output (0.2.0 FR-001..004)."""

from __future__ import annotations

import json
import unittest

from tests.test_api import _LayoutCase
from wiki_studio import api, proposal
from wiki_studio.api import PageEdit
from wiki_studio.errors import ContractViolationError, OutputWriteError

NAME = "2026-10-15-memkernel-export"
PAGE_REL = "concepts/retry-budget.md"
INDEX_LINE = "- [Retry budget](concepts/retry-budget.md) — draft compiled from memkernel (fact)."
LOG_LINE = "- 2026-10-15 — created `retry-budget` (concept): compiled from memkernel mem-1"

# The shape memkernel's WikiExporter writes: draft status, memkernel:// source, two extra keys.
PAGE = (
    "---\n"
    "page_type: concept\n"
    "slug: retry-budget\n"
    "title: Retry budget\n"
    "status: draft\n"
    "last_reviewed: 2026-10-15\n"
    "sources:\n"
    "  - url: memkernel://wiki-studio/mem-1\n"
    "    retrieved: 2026-10-15\n"
    "memkernel_ref: mem-1\n"
    "memory_type: fact\n"
    "---\n"
    "\n"
    "# Retry budget\n"
    "\n"
    "## Summary\n"
    "\n"
    "Retries are a budget, not a reflex.\n"
    "\n"
    "## Key ideas\n"
    "\n"
    "_Not recorded in memory — curate before marking this page stable._\n"
    "\n"
    "## Where this shows up\n"
    "\n"
    "_Not recorded in memory — curate before marking this page stable._\n"
    "\n"
    "## Related\n"
    "\n"
    "_Not recorded in memory — curate before marking this page stable._\n"
)


def _edits(page_rel: str = PAGE_REL) -> list[PageEdit]:
    return [
        PageEdit(page_rel, "create", PAGE, "New draft page compiled from memory mem-1."),
        PageEdit("index.md", "append-index", INDEX_LINE, "Link the draft from the index."),
        PageEdit("log.md", "append-log", LOG_LINE, "Record the export."),
    ]


class TestProposeThenPromote(_LayoutCase):
    def test_round_trip_equals_a_direct_write(self) -> None:
        wiki = self.paths.wiki_dir
        index_before = (wiki / "index.md").read_text(encoding="utf-8")
        log_before = (wiki / "log.md").read_text(encoding="utf-8")

        written = api.propose(_edits(), self.paths, name=NAME, source="memkernel", rationale="Nightly export.")
        self.assertEqual(written, (self.paths.proposals_dir / NAME).resolve())
        self.assertFalse((wiki / PAGE_REL).exists(), "propose must not touch the wiki")
        self.assertFalse(self.paths.audit_log.exists(), "propose does not write the ingest log")

        result = api.promote(written, self.paths)
        self.assertEqual((wiki / PAGE_REL).read_text(encoding="utf-8"), PAGE)
        self.assertEqual((wiki / "index.md").read_text(encoding="utf-8"), index_before + INDEX_LINE + "\n")
        self.assertEqual((wiki / "log.md").read_text(encoding="utf-8"), log_before + LOG_LINE + "\n")
        for rel in (PAGE_REL, "index.md", "log.md"):
            self.assertIn(rel, result.applied_paths)
        self.assertEqual(result.archived_dir, self.paths.applied_dir / NAME)
        archive = wiki / ".audit" / "proposals" / NAME
        self.assertTrue((archive / "plan.json").is_file())
        self.assertIn("Nightly export.", (archive / "proposal.md").read_text(encoding="utf-8"))
        self.assertTrue(api.lint(self.paths).passed)

    def test_promote_dry_run_leaves_wiki_and_proposal_in_place(self) -> None:
        written = api.propose(_edits(), self.paths, name=NAME)
        result = api.promote(written, self.paths, dry_run=True)
        self.assertTrue(result.dry_run)
        self.assertFalse((self.paths.wiki_dir / "concepts").exists())
        self.assertTrue((written / "plan.json").is_file())


class TestProposeOutput(_LayoutCase):
    def test_plan_json_has_the_documented_shape(self) -> None:
        written = api.propose(_edits(), self.paths, name=NAME, source="memkernel", rationale="why", backend="mk")
        plan = json.loads((written / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(set(plan), {"version", "source_path", "backend", "rationale", "edits"})
        self.assertEqual(plan["version"], 1)
        self.assertEqual((plan["source_path"], plan["backend"], plan["rationale"]), ("memkernel", "mk", "why"))
        self.assertEqual(len(plan["edits"]), 3)
        for entry, edit in zip(plan["edits"], _edits(), strict=True):
            self.assertEqual(set(entry), {"path", "action", "rationale", "preview"})
            self.assertEqual(entry["path"], edit.path)
            self.assertEqual(entry["action"], edit.action)
            self.assertEqual(entry["rationale"], edit.rationale)
            self.assertEqual(entry["preview"], f"preview/{edit.path}")
            self.assertEqual((written / entry["preview"]).read_text(encoding="utf-8"), edit.new_content)
        self.assertTrue((written / ".ingest-snapshot" / "plan.json").is_file())
        self.assertTrue((written / ".ingest-snapshot" / "preview" / PAGE_REL).is_file())

    def test_defaults_record_the_api_as_backend(self) -> None:
        written = api.propose(_edits(), self.paths, name=NAME)
        plan = json.loads((written / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual((plan["source_path"], plan["backend"], plan["rationale"]), ("", api.PROPOSE_BACKEND, ""))

    def test_edit_types_are_re_exported(self) -> None:
        self.assertIs(api.PageEdit, proposal.PageEdit)
        self.assertIs(api.WikiPatchSet, proposal.WikiPatchSet)
        self.assertIs(api.PageAction, proposal.PageAction)
        for name in ("propose", "PageEdit", "PageAction", "WikiPatchSet"):
            self.assertIn(name, api.__all__)


class TestProposeRejects(_LayoutCase):
    def _assert_nothing_written(self) -> None:
        self.assertEqual(list(self.paths.proposals_dir.iterdir()), [])

    def test_wrong_directory_for_page_type(self) -> None:
        with self.assertRaises(ContractViolationError) as ctx:
            api.propose(_edits("workflows/retry-budget.md"), self.paths, name=NAME)
        self.assertEqual(ctx.exception.exit_code, 4)
        self.assertIn("should live under concepts/", str(ctx.exception))
        self._assert_nothing_written()

    def test_create_of_an_existing_page(self) -> None:
        api.promote(api.propose(_edits(), self.paths, name=NAME), self.paths)
        with self.assertRaises(ContractViolationError) as ctx:
            api.propose(_edits(), self.paths, name=NAME + "-again")
        self.assertIn("already exists", str(ctx.exception))

    def test_empty_edits(self) -> None:
        with self.assertRaises(ContractViolationError) as ctx:
            api.propose([], self.paths, name=NAME)
        self.assertIn("at least one edit", str(ctx.exception))
        self._assert_nothing_written()

    def test_path_escaping_the_wiki(self) -> None:
        with self.assertRaises(ContractViolationError):
            api.propose([PageEdit("../outside.md", "create", PAGE, "r")], self.paths, name=NAME)
        self._assert_nothing_written()

    def test_name_must_be_one_visible_path_component(self) -> None:
        for bad in ("", ".", "..", "a/b", "sub/", ".applied", ".hidden"):
            with self.subTest(name=bad), self.assertRaises(ValueError):
                api.propose(_edits(), self.paths, name=bad)
        self._assert_nothing_written()

    def test_existing_directory_is_not_overwritten(self) -> None:
        existing = self.paths.proposals_dir / NAME
        existing.mkdir(parents=True)
        (existing / "keep.txt").write_text("curated\n", encoding="utf-8")
        with self.assertRaises(OutputWriteError) as ctx:
            api.propose(_edits(), self.paths, name=NAME)
        self.assertEqual(ctx.exception.exit_code, 6)
        self.assertEqual(sorted(p.name for p in existing.iterdir()), ["keep.txt"])


if __name__ == "__main__":
    unittest.main()
