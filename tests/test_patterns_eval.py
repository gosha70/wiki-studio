# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""US2 tests: the pattern corpus fixture under ``eval/patterns/wiki`` (FR-011).

The fixture is exercised through the real API on a temporary copy: structural lint, the
pattern-page convention, prose lint, supersession, the expected findings, and every pinned
byte the manifest records.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any

from wiki_studio import api
from wiki_studio.paths import WikiPaths
from wiki_studio.prose_lint import SEGMENT_PARAGRAPH, scan_page, split_sentences
from wiki_studio.yaml_lite import parse_frontmatter

REPO_ROOT = Path(__file__).resolve().parents[1]
PATTERNS_DIR = REPO_ROOT / "eval" / "patterns"
WIKI_DIR = PATTERNS_DIR / "wiki"
CORPUS = PATTERNS_DIR / "corpus" / "decisions-57.md"
MANIFEST = PATTERNS_DIR / "manifest.json"
README = PATTERNS_DIR / "README.md"

REQUIRED_KEYS = ("page_type", "slug", "title", "status", "last_reviewed")
ALLOWED_KEYS = frozenset((*REQUIRED_KEYS, "sources", "superseded_by", "corrects"))
SECTIONS = ("Decision", "Context", "Alternatives considered", "Consequences")
_FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):")


def sha256_of(path: Path) -> str:
    """The file's sha256, lowercase hex."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_frontmatter(text: str) -> tuple[list[str], str]:
    """The frontmatter lines and the body text (everything after the closing ``---``)."""
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise AssertionError("page does not open with ---")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[1:index], "\n".join(lines[index + 1 :])
    raise AssertionError("page has no closing ---")


def frontmatter_keys(frontmatter: list[str]) -> list[str]:
    """The top-level keys of the frontmatter block, in order."""
    return [match.group(1) for line in frontmatter if (match := _FRONTMATTER_KEY_RE.match(line))]


def section(body: str, heading: str) -> str:
    """The body text of one H2 section, up to the next H2."""
    lines = body.splitlines()
    out: list[str] = []
    inside = False
    for line in lines:
        if line.startswith("## "):
            if inside:
                break
            inside = line[3:].strip() == heading
            continue
        if inside:
            out.append(line)
    return "\n".join(out)


class PatternsFixtureTest(unittest.TestCase):
    """The US2 fixture: every pinned byte and convention, through the public API."""

    _tmp: tempfile.TemporaryDirectory[str]
    paths: WikiPaths
    manifest: dict[str, Any]
    pages: list[dict[str, Any]]
    pattern_paths: set[str]
    corpus_text: str

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls._tmp.name)
        shutil.copytree(WIKI_DIR, tmp / "wiki")
        cls.paths = WikiPaths.for_root(tmp, wiki_dir=tmp / "wiki")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.pages = cls.manifest["pages"]
        cls.pattern_paths = {entry["path"] for entry in cls.pages}
        cls.corpus_text = CORPUS.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def read_page(self, rel: str) -> str:
        return (WIKI_DIR / rel).read_text(encoding="utf-8")

    def test_structural_lint_is_clean(self) -> None:
        result = api.lint(self.paths)
        self.assertEqual(result.violations, ())

    def test_pattern_pages_follow_the_convention(self) -> None:
        for entry in self.pages:
            with self.subTest(page=entry["path"]):
                text = self.read_page(entry["path"])
                frontmatter, body = split_frontmatter(text)
                parsed = parse_frontmatter(text)
                headings = [line[3:].strip() for line in body.splitlines() if line.startswith("## ")]
                self.assertEqual(headings, list(SECTIONS))
                self.assertEqual(parsed["page_type"], "decision")
                self.assertTrue(parsed.get("sources"))
                self.assertTrue(set(frontmatter_keys(frontmatter)) <= ALLOWED_KEYS)
                for source in parsed["sources"]:
                    if "path" in source:
                        self.assertIn("sha", source)
                    for ticket in ("issue", "pr"):
                        if ticket in source:
                            self.assertRegex(source[ticket], r"^gosha70/code-copilot-team#\d+$")
                paragraphs = [
                    segment
                    for segment in scan_page(entry["path"], text)
                    if segment.kind == SEGMENT_PARAGRAPH and segment.section == "Decision"
                ]
                self.assertTrue(paragraphs[0].text.startswith("In the context of"))
                self.assertEqual(len(split_sentences(paragraphs[0])), entry["y_statement_sentences"])
                self.assertTrue(paragraphs[1].text.startswith("Chosen:"))
                self.assertIn("Applies when:", section(body, "Context"))
                self.assertIn("Does not apply when:", section(body, "Context"))
                self.assertIn("Revisit when:", section(body, "Consequences"))

    def test_prose_lint_reports_nothing_on_a_pattern_page(self) -> None:
        result = api.lint(self.paths, prose=True)
        self.assertIsNotNone(result.prose)
        assert result.prose is not None
        found = [finding for finding in result.prose.findings if finding.path in self.pattern_paths]
        self.assertEqual(found, [])

    def test_exactly_the_two_stale_pages_are_superseded_and_indexed(self) -> None:
        index_text = (WIKI_DIR / "index.md").read_text(encoding="utf-8")
        stale = [entry for entry in self.pages if entry["kind"] == "stale"]
        self.assertEqual(len(stale), 2)
        superseded_in_fixture: list[str] = []
        for page in WIKI_DIR.rglob("*.md"):
            rel = page.relative_to(WIKI_DIR).as_posix()
            parsed = parse_frontmatter(page.read_text(encoding="utf-8"))
            if "superseded_by" in parsed:
                superseded_in_fixture.append(rel)
        self.assertEqual(sorted(superseded_in_fixture), sorted(entry["path"] for entry in stale))
        for entry in stale:
            with self.subTest(page=entry["path"]):
                parsed = parse_frontmatter(self.read_page(entry["path"]))
                self.assertEqual(parsed["status"], "deprecated")
                self.assertTrue((WIKI_DIR / parsed["superseded_by"]).is_file())
                self.assertNotEqual(parsed["superseded_by"], entry["path"])
                self.assertIn(f"]({entry['path']})", index_text)

    def test_findings_report_superseded_still_indexed_for_the_two(self) -> None:
        result = api.findings(self.paths)
        reported = [finding for finding in result.findings if finding.kind == "superseded-still-indexed"]
        stale = sorted(entry["path"] for entry in self.pages if entry["kind"] == "stale")
        self.assertEqual(sorted(finding.pages[0] for finding in reported), stale)
        for finding in reported:
            self.assertEqual(finding.pages[1], "index.md")

    def test_corpus_copy_matches_the_pin(self) -> None:
        self.assertEqual(sha256_of(CORPUS), self.manifest["pins"]["memkernel"]["sha256"])

    def test_every_record_heading_occurs_in_the_corpus_copy(self) -> None:
        headings = self.corpus_text.splitlines()
        for entry in self.pages:
            if entry["record"] is not None:
                with self.subTest(record=entry["record"]):
                    self.assertIn(entry["record"], headings)

    def test_background_copies_and_exclusions(self) -> None:
        for entry in self.manifest["background"]:
            with self.subTest(page=entry["path"]):
                copy = WIKI_DIR / entry["path"]
                self.assertTrue(copy.is_file())
                self.assertEqual(sha256_of(copy), entry["sha256"])
                self.assertNotIn(entry["path"], self.pattern_paths)
        self.assertFalse((WIKI_DIR / "playbooks" / "pre-pr-close-keyword-audit.md").exists())
        self.assertFalse((WIKI_DIR / "schema").exists())
        self.assertFalse((WIKI_DIR / "scripts").exists())
        self.assertFalse((WIKI_DIR / "open-questions").exists())
        self.assertEqual(list(WIKI_DIR.rglob(".gitkeep")), [])

    def test_word_counts_recompute(self) -> None:
        corpus_lines = self.corpus_text.splitlines()
        for entry in self.pages:
            with self.subTest(page=entry["path"]):
                _, body = split_frontmatter(self.read_page(entry["path"]))
                self.assertEqual(len(body.split()), entry["words_page"])
                if entry["record"] is not None:
                    start = corpus_lines.index(entry["record"])
                    end = start + 1
                    while end < len(corpus_lines) and not re.match(r"^(### |## )", corpus_lines[end]):
                        end += 1
                    self.assertEqual(len("\n".join(corpus_lines[start:end]).split()), entry["words_record"])
                else:
                    self.assertIsNone(entry["words_record"])

    def test_readme_contains_each_pin_value(self) -> None:
        readme = README.read_text(encoding="utf-8")
        pins = self.manifest["pins"]
        for value in (
            pins["memkernel"]["tag"],
            pins["memkernel"]["commit"],
            pins["memkernel"]["path"],
            pins["memkernel"]["sha256"],
            pins["code_copilot_team"]["commit"],
        ):
            self.assertIn(value, readme)


if __name__ == "__main__":
    unittest.main()
