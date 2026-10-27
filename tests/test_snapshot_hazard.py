# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Reproduction of memkernel's snapshot hazard (0.7.0 US1, FR-003).

memkernel's ``WikiExporter._export_gated`` (gosha70/memkernel
``src/memkernel/wiki/sync.py`` lines 198-236 at main 641a508) takes a
whole-wiki snapshot before a gated export and restores it on failure, outside
the wiki lock. ``tests/helpers/memkernel_snapshot.py`` is a cited copy of that
snapshot. The test wraps a failing bridge-shaped export in it while a second
wiki-studio writer commits a proposal between ``take`` and ``restore``, and
shows the second writer's page rewritten to its pre-export bytes and its
wiki-side archive (``.audit/proposals/<name>/plan.json``) deleted, while its
receipt still says ``committed``; the same failing export without the wrapper
leaves that work intact. Evidence for the Release B closure, not a test of
memkernel.
"""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.helpers.memkernel_snapshot import _WikiSnapshot
from tests.test_bridge_contract import GateError, bridge_paths, export_name, memkernel_page, propose_and_promote
from tests.test_promote_recovery import _receipt
from wiki_studio import api, promoter
from wiki_studio.api import PageEdit
from wiki_studio.errors import PromoteApplyError
from wiki_studio.paths import WikiPaths

CURATOR_PROPOSAL = "curator-update"
CURATOR_LOG_LINE = "- 2026-10-26 — updated `x` (concept): curated by hand."


def _concept(body: str) -> str:
    return (
        "---\npage_type: concept\nslug: x\ntitle: X\nstatus: stable\nlast_reviewed: 2026-10-26\n"
        f"sources:\n  - path: README.md\n    sha: abc\n---\n\n# X\n\n{body}\n"
    )


V0 = _concept("Original.").encode("utf-8")
V1 = _concept("Updated by the curator.").encode("utf-8")


class TestSnapshotHazard(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-hazard-")
        self.root = Path(self._tmp.name).resolve()
        (self.root / "README.md").write_text("# Root\n", encoding="utf-8")
        self.bridge = bridge_paths(self.root)
        self.curator = WikiPaths.for_root(self.root)  # the default layout: a second, cooperating writer
        self.wiki = self.bridge.wiki_dir
        api.init(self.bridge)
        (self.wiki / "concepts").mkdir()
        (self.wiki / "concepts" / "x.md").write_bytes(V0)
        index = self.wiki / "index.md"
        index.write_text(
            index.read_text(encoding="utf-8") + "- [X](concepts/x.md) — a curated page.\n", encoding="utf-8"
        )
        self.curator_proposal = api.propose(
            [
                PageEdit(
                    "concepts/x.md", "update", V1.decode("utf-8"), "curate", base_sha256=hashlib.sha256(V0).hexdigest()
                ),
                PageEdit("log.md", "append-log", CURATOR_LOG_LINE, "log it"),
            ],
            self.curator,
            name=CURATOR_PROPOSAL,
        )
        self.archived_plan = self.wiki / ".audit" / "proposals" / CURATOR_PROPOSAL / "plan.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _failing_export(self, *, with_snapshot: bool) -> list[str]:
        """``_export_gated`` lines 219-234 around a bridge export whose commit fails; returns restore's problems."""
        pages = [memkernel_page("from-memory", "From memory", "mem-0009")]
        name = export_name()
        snapshot = _WikiSnapshot.take(self.wiki) if with_snapshot else None
        real_apply = promoter._apply_planned

        def fail_the_exports_commit(planned: list[promoter._PlannedWrite], paths: WikiPaths) -> list[str]:
            # Only the export's own commit fails; the curator's promote runs the real commit.
            if any(write.rel.startswith(f".audit/proposals/{name}") for write in planned):
                raise PromoteApplyError("simulated failure during the export's commit")
            return real_apply(planned, paths)

        landed: list[Path | None] = []

        def second_writer_lands(_proposal: Path) -> None:
            # Between take and restore: the curator's promote takes the lock and commits.
            landed.append(api.promote(self.curator_proposal, self.curator).archived_dir)

        try:
            with patch("wiki_studio.promoter._apply_planned", side_effect=fail_the_exports_commit):
                propose_and_promote(pages, self.bridge, name, before_promote=second_writer_lands)
        except GateError:
            self.assertEqual(landed, [self.curator.applied_dir / CURATOR_PROPOSAL], "the curator's promote landed")
            return snapshot.restore() if snapshot is not None else []
        self.fail("the export did not fail")

    def _assert_curator_receipt_attests_v1(self) -> None:
        receipt = _receipt(self.curator.applied_dir / CURATOR_PROPOSAL)
        self.assertEqual(receipt["state"], "committed")
        planned = {w["path"]: w for w in receipt["planned_writes"]}
        self.assertEqual(planned["concepts/x.md"]["post_sha256"], hashlib.sha256(V1).hexdigest())
        self.assertIn(f".audit/proposals/{CURATOR_PROPOSAL}/plan.json", receipt["written_paths"])

    def test_with_the_snapshot_the_second_writers_page_is_rewritten_and_its_archive_deleted(self) -> None:
        problems = self._failing_export(with_snapshot=True)
        self.assertEqual(problems, [], "the restore reports success")
        # The hazard: the curator's committed update is undone and its wiki-side archive removed,
        # while the receipt in .applied/ still attests the commit.
        self.assertEqual((self.wiki / "concepts" / "x.md").read_bytes(), V0, "the curator's page was rewritten")
        self.assertFalse(self.archived_plan.exists(), "the curator's archived plan.json was deleted")
        self.assertFalse(self.archived_plan.parent.exists(), "its archive directory went with it")
        self.assertNotIn(CURATOR_LOG_LINE, (self.wiki / "log.md").read_text(encoding="utf-8"))
        self._assert_curator_receipt_attests_v1()
        self.assertFalse((self.wiki / "concepts" / "from-memory.md").exists())

    def test_without_the_snapshot_the_second_writers_work_is_intact(self) -> None:
        problems = self._failing_export(with_snapshot=False)
        self.assertEqual(problems, [])
        self.assertEqual((self.wiki / "concepts" / "x.md").read_bytes(), V1, "the curator's page stays")
        self.assertTrue(self.archived_plan.is_file(), "the curator's archived plan.json stays")
        self.assertIn(CURATOR_LOG_LINE, (self.wiki / "log.md").read_text(encoding="utf-8"))
        self._assert_curator_receipt_attests_v1()
        # The promoter's own rollback is what covers the failed export: nothing of it landed.
        self.assertFalse((self.wiki / "concepts" / "from-memory.md").exists())
        lint = api.lint(self.bridge)
        self.assertEqual((lint.violations, lint.audit_errors), ((), ()))


if __name__ == "__main__":
    unittest.main()
