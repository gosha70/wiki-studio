# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The fixture wiki (FR-010): one page of every type plus memkernel-exported drafts; lint clean; queryable."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.conftest import FIXTURES_DIR, run_cli
from wiki_studio import api, yaml_lite
from wiki_studio.lint import VALID_PAGE_TYPES, lint_wiki, list_pages
from wiki_studio.paths import WikiPaths

FIXTURE_WIKI = FIXTURES_DIR / "wiki"

# The three drafts in the shape memkernel 0.3's WikiExporter writes.
MEMKERNEL_PAGES = {
    "decisions/adopt-wiki-as-semantic-layer.md": ("decision", "decision"),
    "concepts/prefer-small-commits.md": ("concept", "convention"),
    "workflows/release-a-package.md": ("workflow", "procedure"),
}


def _frontmatter(rel: str) -> dict:
    return yaml_lite.parse_frontmatter((FIXTURE_WIKI / rel).read_text(encoding="utf-8"))


class TestFixtureWikiStructure(unittest.TestCase):
    def test_lints_clean(self) -> None:
        self.assertEqual(lint_wiki(FIXTURE_WIKI), [])

    def test_has_one_page_of_every_type(self) -> None:
        types = {_frontmatter(p.relative_to(FIXTURE_WIKI).as_posix())["page_type"] for p in list_pages(FIXTURE_WIKI)}
        self.assertEqual(types, set(VALID_PAGE_TYPES))
        self.assertEqual(len(list_pages(FIXTURE_WIKI)), 13)

    def test_cli_lint_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli("lint", "--wiki-dir", str(FIXTURE_WIKI), "--root", tmp, cwd=Path(tmp))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("linted 13 pages, 0 violations", result.stdout)


class TestMemkernelContract(unittest.TestCase):
    """Pins the schema shared with memkernel's WikiExporter / WikiImporter."""

    def test_exported_pages_carry_the_extra_keys_and_source(self) -> None:
        for rel, (page_type, memory_type) in MEMKERNEL_PAGES.items():
            with self.subTest(page=rel):
                fm = _frontmatter(rel)
                self.assertEqual(fm["page_type"], page_type)
                self.assertEqual(fm["status"], "draft")
                self.assertEqual(fm["memory_type"], memory_type)
                self.assertTrue(str(fm["memkernel_ref"]).startswith("mem-"))
                sources = fm["sources"]
                self.assertIsInstance(sources, list)
                self.assertTrue(str(sources[0]["url"]).startswith("memkernel://"))
                self.assertIn("retrieved", sources[0])

    def test_exported_pages_are_linked_from_index_and_logged(self) -> None:
        index = (FIXTURE_WIKI / "index.md").read_text(encoding="utf-8")
        log = (FIXTURE_WIKI / "log.md").read_text(encoding="utf-8")
        for rel, (page_type, memory_type) in MEMKERNEL_PAGES.items():
            self.assertIn(f"]({rel}) — draft compiled from memkernel ({memory_type}).", index)
            slug = Path(rel).stem
            self.assertIn(f"create `{slug}` ({page_type}): compiled from memkernel", log)


class TestFixtureWikiQuery(unittest.TestCase):
    def test_query_with_test_backend_answers_over_the_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = WikiPaths.for_root(Path(tmp), wiki_dir=FIXTURE_WIKI)
            result = api.query("what is spec-driven development?", paths, backend="test")
            self.assertTrue(result.answer.answer)
            self.assertIn("concepts/spec-driven-development.md", result.answer.pages_loaded)
            self.assertTrue(any(c.page == "concepts/spec-driven-development.md" for c in result.answer.citations))
            # The query log lands under the root, not inside the fixture.
            self.assertTrue((Path(tmp) / "doc_internal" / "wiki-query-log.jsonl").is_file())
            self.assertFalse((FIXTURE_WIKI / ".audit").exists())

    def test_cli_query_over_the_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli(
                "query",
                "promote a lesson to the wiki",
                "--backend",
                "test",
                "--wiki-dir",
                str(FIXTURE_WIKI),
                cwd=Path(tmp),
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Consulted", result.stdout)
        self.assertIn("workflows/promote-lesson-to-wiki.md", result.stderr)


if __name__ == "__main__":
    unittest.main()
