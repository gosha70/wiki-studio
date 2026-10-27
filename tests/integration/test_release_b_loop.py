# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# mypy: disable-error-code="import-not-found"
"""The four Release B loop cases end to end against the installed memkernel (0.7.0 FR-032).

retain, export, review (``api.approve``), import, correct, next-session recall,
plus the retry property: a promote interrupted after its commit resolves from
its receipt, and an export or import run twice creates no duplicate pages,
records or memories.

These run only in the ``memkernel-loop`` clean-install job, never skipped or
marked as expected failures there. That job is labelled expected to fail and
stays non-blocking until memkernel's counterpart (memkernel #48: snapshot
removal and an importer that reads ``review_state``) is merged; locally the
suite is skipped when memkernel is not installed. memkernel's
``MemoryService`` is the real one, never mocked.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from tests.integration.test_memkernel_clean_install import CONVENTION, DECISION, HAS_MEMKERNEL, SKIP_REASON, _service

WRONG = "Deploys happen on Fridays after 17:00."
RIGHT = "Deploys happen on Tuesdays before noon; never on Fridays."


@unittest.skipUnless(HAS_MEMKERNEL, SKIP_REASON)
class ReleaseBLoopCase(unittest.TestCase):
    def setUp(self) -> None:
        from wiki_studio import api
        from wiki_studio.paths import WikiPaths

        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-release-b-")
        self.root = Path(self._tmp.name).resolve()
        self.wiki = self.root / "knowledge" / "wiki"
        self.proposals = self.root / ".memkernel" / "wiki-proposals"
        self.paths = WikiPaths.for_root(self.root, wiki_dir=self.wiki, proposals_dir=self.proposals)
        api.init(self.paths)
        self.service = _service(self.root)
        self._count = 0

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # memkernel, driven as its MCP tools drive it.
    def retain(self, text: str, memory_type: str = "DECISION") -> Any:
        from memkernel.core.models import MemoryType

        return self.service.retain(text, getattr(MemoryType, memory_type))

    def export(self) -> Any:
        from memkernel.wiki.sync import WikiExporter

        return WikiExporter(self.service, self.wiki, project_root=self.root, proposals_dir=self.proposals).export()

    def import_pages(self) -> Any:
        from memkernel.wiki.sync import WikiImporter

        return WikiImporter(self.service, self.wiki).import_pages()

    def wiki_memories(self) -> list[Any]:
        from memkernel.core.models import MemoryTier

        return [m for m in self.service.list_memories(tier=MemoryTier.LONG_TERM) if "wiki" in m.tags]

    # wiki-studio: the curator's side of the loop.
    def make_stable(self, rel: str) -> None:
        """Review a bridge draft: a guarded update to ``status: stable`` through the gate."""
        from wiki_studio import api
        from wiki_studio.proposal import PageEdit

        page = api.read_page(rel, self.paths)
        self._count += 1
        edit = PageEdit(rel, "update", page.text.replace("status: draft", "status: stable", 1), "reviewed", page.sha256)
        api.promote(api.propose([edit], self.paths, name=f"review-{self._count}"), self.paths, by="curator")

    def state(self, rel: str) -> str:
        from wiki_studio import api

        return api.review_state(self.paths, pages=[rel])[0].state

    def records(self) -> list[Path]:
        root = self.wiki / ".audit" / "approvals"
        return sorted(p for p in root.rglob("*") if p.is_file()) if root.is_dir() else []

    def tree(self) -> dict[str, bytes]:
        return {p.relative_to(self.wiki).as_posix(): p.read_bytes() for p in self.wiki.rglob("*") if p.is_file()}


class TestReleaseBLoop(ReleaseBLoopCase):
    def test_1_a_draft_page_is_never_imported(self) -> None:
        self.retain(DECISION)
        exported = self.export()
        self.assertTrue(exported.gated)
        (rel,) = exported.written
        self.assertEqual(self.state(rel), "unapproved")
        report = self.import_pages()
        self.assertNotIn(rel, report.imported)
        self.assertEqual(self.wiki_memories(), [])

    def test_2_a_page_that_declares_itself_approved_is_refused(self) -> None:
        from wiki_studio import api
        from wiki_studio.errors import ContractViolationError
        from wiki_studio.proposal import PageEdit

        self.retain(DECISION)
        (rel,) = self.export().written
        page = api.read_page(rel, self.paths)
        claim = page.text.replace("status: draft", "status: stable\napproved_by: someone", 1)
        with self.assertRaises(ContractViolationError):
            api.propose([PageEdit(rel, "update", claim, "claim", page.sha256)], self.paths, name="claim")
        # The same claim written by hand never makes the page approved, so it is not imported.
        (self.wiki / rel).write_text(claim, encoding="utf-8")
        self.assertEqual(self.state(rel), "unapproved")
        self.assertNotIn(rel, self.import_pages().imported)
        self.assertEqual(self.wiki_memories(), [])

    def test_3_an_approved_page_edited_after_approval_is_re_reviewed_before_import(self) -> None:
        from wiki_studio import api

        self.retain(DECISION)
        (rel,) = self.export().written
        self.make_stable(rel)
        api.approve([rel], self.paths, by="curator")
        self.assertEqual(self.state(rel), "approved")
        self.assertIn(rel, self.import_pages().imported)
        approved_text = (self.wiki / rel).read_text(encoding="utf-8")
        (self.wiki / rel).write_text(
            approved_text.replace("concurrent writes", "an unreviewed claim"), encoding="utf-8"
        )
        self.assertEqual(self.state(rel), "stale")
        self.import_pages()
        (memory,) = [m for m in self.wiki_memories() if m.source == rel]
        self.assertNotIn("an unreviewed claim", memory.content, "the unreviewed revision is not imported")
        api.approve([rel], self.paths, by="curator")
        self.assertIn(rel, self.import_pages().imported)
        (memory,) = [m for m in self.wiki_memories() if m.source == rel]
        self.assertIn("an unreviewed claim", memory.content)

    def test_4_a_superseded_wrong_memory_is_not_a_current_answer_next_session(self) -> None:
        from wiki_studio import api
        from wiki_studio.proposal import PageEdit

        wrong = self.retain(WRONG, "CONVENTION")
        (rel,) = self.export().written
        page = api.read_page(rel, self.paths)
        ref_line = next(line for line in page.text.splitlines() if line.startswith("memkernel_ref:"))
        wrong_ref = ref_line.split(":", 1)[1].strip()
        corrected = page.text.replace("status: draft", f"status: stable\ncorrects: {wrong_ref}", 1).replace(
            WRONG, RIGHT
        )
        api.promote(
            api.propose([PageEdit(rel, "update", corrected, "correct", page.sha256)], self.paths, name="correct"),
            self.paths,
            by="curator",
        )
        self.assertIn(f"corrects: {wrong_ref}", (self.wiki / rel).read_text(encoding="utf-8"), "kept byte for byte")
        api.approve([rel], self.paths, by="curator")
        self.import_pages()
        # Recall after the import (the next session's view): the correction is current, the wrong memory is not.
        current = [m for m in self.service.list_memories() if getattr(m, "superseded_by", None) is None]
        self.assertFalse(any(WRONG in m.content for m in current), "the wrong memory is not a current answer")
        self.assertTrue(any(RIGHT in m.content for m in current))
        kept = [m for m in self.service.list_memories() if m.id == wrong.id]
        self.assertEqual(len(kept), 1, "its provenance is retained")


class TestRetryProperty(ReleaseBLoopCase):
    def test_a_promote_interrupted_after_its_commit_resolves_from_its_receipt(self) -> None:
        from wiki_studio import api, promoter

        self.retain(DECISION)
        with patch.object(promoter, "_archive_submission", side_effect=OSError(5, "I/O error")):
            exported = self.export()
        (rel,) = exported.written
        leftovers = [d for d in self.proposals.iterdir() if d.is_dir() and not d.name.startswith(".")]
        self.assertEqual(len(leftovers), 1)
        receipt = json.loads((leftovers[0] / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["state"], "committed")
        before = self.tree()
        result = api.promote(leftovers[0], self.paths)
        self.assertIsNotNone(result.archived_dir)
        self.assertEqual(self.tree(), before, "nothing is re-applied")
        self.assertEqual(sorted(p.name for p in (self.proposals / ".applied").iterdir()), [leftovers[0].name])
        self.assertTrue((self.wiki / rel).is_file())

    def test_export_and_import_twice_create_no_duplicate_pages_records_or_memories(self) -> None:
        from wiki_studio import api

        self.retain(DECISION)
        self.retain(CONVENTION, "CONVENTION")
        written = self.export().written
        for rel in written:
            self.make_stable(rel)
        api.approve(list(written), self.paths, by="curator")
        self.import_pages()
        pages, records = self.tree(), self.records()
        memories = sorted(m.source for m in self.wiki_memories())
        again = self.export()
        self.assertEqual(again.written, [])
        self.assertEqual(api.approve(list(written), self.paths, by="curator").published, [])
        self.import_pages()
        self.assertEqual(self.tree(), pages)
        self.assertEqual(self.records(), records)
        self.assertEqual(sorted(m.source for m in self.wiki_memories()), memories)
        self.assertEqual(memories, sorted(written))


if __name__ == "__main__":
    unittest.main()
