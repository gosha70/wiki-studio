# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# mypy: disable-error-code="import-not-found"
"""Export, re-export and import through the real ``WikiExporter`` and ``WikiImporter`` (0.7.0 FR-004).

memkernel is optional here (never in the package or the dev group), so its
imports are untyped for mypy; the file is type-checked for everything else.

The service is built by memkernel's own factory (``memkernel.factory.build_service``)
with an in-process Chroma client and a deterministic embedding port, so the
job needs no model download and no network; the ``MemoryService`` itself is
the real one. The bridge is driven exactly as memkernel's MCP tool drives it:
an explicit proposals directory under ``<root>/.memkernel/`` asks for the gate.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from memkernel.core.services import MemoryService

HAS_MEMKERNEL = importlib.util.find_spec("memkernel") is not None
SKIP_REASON = "memkernel is not installed; the memkernel-compat CI job runs this suite against the wheel"

DECISION = "Use Postgres for the user DB\n\nBecause of concurrent writes."
CONVENTION = "All services log JSON to stdout; never write log files."
PROCEDURE = "Run `make verify` before every PR."


class _HashEmbedding:
    """A deterministic ``EmbeddingPort`` (content-hash vectors): the test double memkernel's own suite uses."""

    def __init__(self, dimension: int = 8) -> None:
        self._dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            raw = [b / 255.0 for b in hashlib.sha256(text.encode("utf-8")).digest()[: self._dimension]]
            norm = sum(x * x for x in raw) ** 0.5
            vectors.append([x / norm if norm > 0 else 0.0 for x in raw])
        return vectors

    @property
    def dimension(self) -> int:
        return self._dimension


def _service(root: Path) -> MemoryService:
    import chromadb
    from memkernel.config import MemKernelSettings
    from memkernel.factory import build_service

    settings = MemKernelSettings(
        project_id=f"wiki-studio-compat-{uuid.uuid4().hex[:8]}",
        project_root=str(root),
        chroma_persist_path=str(root / ".memkernel" / "chroma"),
    )
    return build_service(
        settings, embedding=_HashEmbedding(), chroma_client=chromadb.EphemeralClient(), rebuild_sparse_index=False
    )


@unittest.skipUnless(HAS_MEMKERNEL, SKIP_REASON)
class TestMemkernelCleanInstall(unittest.TestCase):
    def setUp(self) -> None:
        from memkernel.core.models import MemoryType

        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-memkernel-")
        self.root = Path(self._tmp.name).resolve()
        self.wiki = self.root / "knowledge" / "wiki"
        self.proposals = self.root / ".memkernel" / "wiki-proposals"
        self.service = _service(self.root)
        self.service.retain(DECISION, MemoryType.DECISION)
        self.service.retain(CONVENTION, MemoryType.CONVENTION)
        self.service.retain(PROCEDURE, MemoryType.PROCEDURE)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _export(self) -> Any:
        from memkernel.wiki.sync import WikiExporter

        return WikiExporter(self.service, self.wiki, project_root=self.root, proposals_dir=self.proposals).export()

    def _wiki_tree(self) -> dict[str, bytes]:
        return {p.relative_to(self.wiki).as_posix(): p.read_bytes() for p in self.wiki.rglob("*") if p.is_file()}

    def _archives(self) -> list[Path]:
        applied = self.proposals / ".applied"
        return sorted(applied.iterdir()) if applied.is_dir() else []

    def test_export_goes_through_the_gate_and_lands_with_a_committed_receipt(self) -> None:
        from wiki_studio import api
        from wiki_studio.paths import WikiPaths

        report = self._export()
        self.assertIsNone(report.gate_error)
        self.assertTrue(report.gated, "the export did not go through the gate")
        self.assertEqual(
            sorted(report.written),
            [
                "concepts/all-services-log-json-to-stdout-never-write-log-files.md",
                "decisions/use-postgres-for-the-user-db.md",
                "workflows/run-make-verify-before-every-pr.md",
            ],
        )
        index = (self.wiki / "index.md").read_text(encoding="utf-8")
        log = (self.wiki / "log.md").read_text(encoding="utf-8")
        for rel in report.written:
            page = (self.wiki / rel).read_text(encoding="utf-8")
            self.assertIn("status: draft", page)
            self.assertIn("memkernel_ref: ", page)
            self.assertIn("memory_type: ", page)
            self.assertIn('url: "memkernel://', page)
            self.assertIn(f"]({rel})", index)
            self.assertIn(f"created `{Path(rel).stem}`", log)
        archives = self._archives()
        self.assertEqual(len(archives), 1)
        self.assertTrue(archives[0].name.startswith("memkernel-export-"))
        receipt = json.loads((archives[0] / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["state"], "committed")
        self.assertEqual(receipt["promoter"]["package"], "wiki-studio")
        plan = json.loads((archives[0] / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual((plan["source_path"], plan["backend"]), ("memkernel wiki_export", "memkernel"))
        self.assertTrue((self.wiki / ".audit" / "proposals" / archives[0].name / "plan.json").is_file())
        lint = api.lint(WikiPaths.for_root(self.root, wiki_dir=self.wiki, proposals_dir=self.proposals))
        self.assertEqual((lint.violations, lint.audit_errors), ((), ()))
        self.assertIsNone(report.lint_error)
        self.assertIsNotNone(report.lint)
        self.assertEqual(report.lint.violations, [])

    def test_a_re_export_writes_nothing_new(self) -> None:
        first = self._export()
        self.assertTrue(first.gated)
        before = self._wiki_tree()
        again = self._export()
        self.assertIsNone(again.gate_error)
        self.assertEqual(again.written, [])
        self.assertEqual(again.skipped, 3, "every exported memory already has its page")
        self.assertEqual(self._wiki_tree(), before)
        self.assertEqual(len(self._archives()), 1, "no second submission was proposed or archived")

    def _approve(self, rel: str) -> None:
        """The curator's review of a bridge draft: a guarded update to ``status: stable``, then ``approve``."""
        from wiki_studio import api
        from wiki_studio.paths import WikiPaths
        from wiki_studio.proposal import PageEdit

        paths = WikiPaths.for_root(self.root, wiki_dir=self.wiki, proposals_dir=self.proposals)
        page = api.read_page(rel, paths)
        edit = PageEdit(rel, "update", page.text.replace("status: draft", "status: stable", 1), "reviewed", page.sha256)
        api.promote(api.propose([edit], paths, name=f"review-{rel.replace('/', '-')}"), paths, by="curator")
        api.approve([rel], paths, by="curator")

    def test_import_indexes_the_exported_pages_once(self) -> None:
        from memkernel.core.models import MemoryTier
        from memkernel.wiki.sync import WikiImporter

        exported = self._export()
        self.assertTrue(exported.gated)

        def wiki_memories() -> list[Any]:
            return [m for m in self.service.list_memories(tier=MemoryTier.LONG_TERM) if "wiki" in m.tags]

        self.assertEqual(wiki_memories(), [])
        importer = WikiImporter(self.service, self.wiki)
        # The import is governed: the bridge's drafts are not imported until a curator approves them.
        drafts = importer.import_pages()
        self.assertTrue(drafts.governed)
        self.assertEqual(drafts.imported, [])
        self.assertEqual(sorted(d["path"] for d in drafts.not_approved), sorted(exported.written))
        self.assertEqual(wiki_memories(), [])
        for rel in exported.written:
            self._approve(rel)
        report = importer.import_pages()
        self.assertEqual(sorted(report.imported), sorted(exported.written))
        memories = wiki_memories()
        self.assertEqual(sorted(m.source for m in memories), sorted(exported.written))
        self.assertNotIn("index.md", {m.source for m in memories})
        self.assertNotIn("log.md", {m.source for m in memories})
        # A second import of the same approved revisions imports nothing again and reports them unchanged.
        again = importer.import_pages()
        self.assertEqual(again.imported, [])
        self.assertEqual(sorted(again.unchanged), sorted(exported.written))
        self.assertEqual(
            sorted(m.source for m in wiki_memories()), sorted(exported.written), "a second import adds no memory"
        )

    def test_memkernel_parses_several_corrections_as_the_line_wiki_studio_keeps(self) -> None:
        """FR-036: the ``corrects`` fixture, parsed by memkernel's page parser, keeps the one scalar line."""
        from memkernel.wiki import parse_page, render_page

        from wiki_studio.yaml_lite import parse_frontmatter

        fixture = Path(__file__).resolve().parent.parent / "fixtures" / "corrects" / "multi-corrections.md"
        text = fixture.read_text(encoding="utf-8")
        value = parse_frontmatter(text)["corrects"]
        page = parse_page(text)
        self.assertEqual(page.extra["corrects"], value)
        rendered = render_page(page)
        self.assertIn(f"corrects: {value}\n", rendered, "memkernel writes the line back as wiki-studio reads it")
        self.assertEqual(parse_frontmatter(rendered)["corrects"], value)


if __name__ == "__main__":
    unittest.main()
