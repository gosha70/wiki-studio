# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# tests/test_ingestor_with_test_backend.py — end-to-end ingestor test using the test backend.

import tempfile
import unittest
from pathlib import Path

from tests.conftest import make_repo_layout
from wiki_studio.backends.test import TestBackend
from wiki_studio.ingestor import DefaultIngestor
from wiki_studio.paths import WikiPaths
from wiki_studio.proposal import IngestProposal, IngestRequest

_FIXTURE = Path(__file__).parent / "fixtures" / "sample-incident.md"

# A project root built in setUpModule; the ingestor reads the packaged
# schema through it (there is no schema/ override in the layout).
_TMP: tempfile.TemporaryDirectory[str] | None = None
_REPO_ROOT = Path()
_PATHS = WikiPaths.for_root(_REPO_ROOT)


def setUpModule() -> None:
    global _TMP, _REPO_ROOT, _PATHS
    _TMP = tempfile.TemporaryDirectory(prefix="wiki_studio-ingestor-")
    _REPO_ROOT = make_repo_layout(Path(_TMP.name), with_sample=False)
    _PATHS = WikiPaths.for_root(_REPO_ROOT)


def tearDownModule() -> None:
    if _TMP is not None:
        _TMP.cleanup()


class TestIngestorWithTestBackend(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = TestBackend()
        self.ingestor = DefaultIngestor(backend=self.backend, paths=_PATHS)
        self.request = IngestRequest(
            source_path=_FIXTURE,
            source_kind="file",
            backend_name="test",
        )

    def test_returns_ingest_proposal(self) -> None:
        proposal = self.ingestor.ingest(self.request)
        self.assertIsInstance(proposal, IngestProposal)

    def test_disposition_is_accept(self) -> None:
        proposal = self.ingestor.ingest(self.request)
        self.assertEqual(proposal.disposition, "accept")

    def test_page_type_is_incident(self) -> None:
        proposal = self.ingestor.ingest(self.request)
        self.assertEqual(proposal.page_type, "incident")

    def test_slug_is_kebab_case(self) -> None:
        proposal = self.ingestor.ingest(self.request)
        self.assertIsNotNone(proposal.slug)
        self.assertRegex(proposal.slug, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    def test_slug_derived_from_h1(self) -> None:
        """The fixture H1 is 'Empty Index Commit After Git Lock Bypass'."""
        proposal = self.ingestor.ingest(self.request)
        self.assertEqual(proposal.slug, "empty-index-commit-after-git-lock-bypass")

    def test_title_matches_h1(self) -> None:
        proposal = self.ingestor.ingest(self.request)
        self.assertEqual(proposal.title, "Empty Index Commit After Git Lock Bypass")

    def test_sources_non_empty(self) -> None:
        proposal = self.ingestor.ingest(self.request)
        self.assertGreater(len(proposal.sources), 0)

    def test_draft_markdown_present(self) -> None:
        proposal = self.ingestor.ingest(self.request)
        self.assertIsNotNone(proposal.draft_markdown)
        self.assertIn("---", proposal.draft_markdown)

    def test_draft_markdown_has_required_sections(self) -> None:
        proposal = self.ingestor.ingest(self.request)
        assert proposal.draft_markdown is not None
        for section in ("What happened", "Why it happened", "What we changed", "How to recognize a recurrence"):
            self.assertIn(section, proposal.draft_markdown)

    def test_reason_is_string(self) -> None:
        proposal = self.ingestor.ingest(self.request)
        self.assertIsInstance(proposal.reason, str)
        self.assertGreater(len(proposal.reason), 0)

    def test_determinism(self) -> None:
        """Same input → same output across two calls."""
        p1 = self.ingestor.ingest(self.request)
        p2 = self.ingestor.ingest(self.request)
        self.assertEqual(p1.slug, p2.slug)
        self.assertEqual(p1.title, p2.title)
        self.assertEqual(p1.page_type, p2.page_type)

    def test_source_missing_raises(self) -> None:
        from wiki_studio.errors import SourceMissingError

        bad_request = IngestRequest(
            source_path=Path("/nonexistent/path/does-not-exist.md"),
            source_kind="file",
            backend_name="test",
        )
        with self.assertRaises(SourceMissingError):
            self.ingestor.ingest(bad_request)


if __name__ == "__main__":
    unittest.main()
