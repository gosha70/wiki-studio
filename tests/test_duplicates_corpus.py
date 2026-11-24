# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The near-duplicate study's extracted corpus, checked against ``corpus.json`` and the rule (issue 121, FR-012).

The pages and ``corpus.json`` were written once by ``python -m eval.duplicates.extract`` and committed as written.
These tests read them and run no script: every page is pinned to its ``corpus.json`` entry by sha256, the per-page
input counts are recomputed, the README's corpus section equals what ``corpus.json`` gives, the six fixed items'
pages are byte-equal to what extract.py builds from the raw texts of ``tests.test_duplicates_extract`` and read the
first paragraph of each item's text after its label, no excluded spec is present, no body keeps its label, no file
holds closing-keyword text, and every page passes the structural lint on a temporary wiki with only the README's
listed violations.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import statistics
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from typing import Any

from eval.duplicates.extract import (
    BOLD_SPAN_RE,
    CLOSING_KEYWORD_RE,
    FORM_H3,
    FORM_H3_ADR,
    H3_PREFIX,
    fenced_lines,
    is_excluded,
    title_from_label,
)
from eval.patterns.duplicates import _first_paragraph, _title
from tests.test_duplicates_extract import FIXED_ITEMS, fixed_page
from wiki_studio.lint import lint_wiki
from wiki_studio.wiki_state import _tokenise

REPO_ROOT = Path(__file__).resolve().parents[1]
DUPLICATES_DIR = REPO_ROOT / "eval" / "duplicates"
CORPUS_DIR = DUPLICATES_DIR / "corpus"
CORPUS_JSON = DUPLICATES_DIR / "corpus.json"
README = DUPLICATES_DIR / "README.md"

FRONTMATTER_END = "\n---\n"
DECISION_HEADING = "## Decision"
INDEX_MD = "---\npage_type: index\nslug: index\ntitle: Corpus\nstatus: stable\nlast_reviewed: 2026-11-23\n---\n\n"
LOG_MD = "---\npage_type: log\nslug: log\ntitle: Log\nstatus: stable\nlast_reviewed: 2026-11-23\n---\n\n# Log\n"

# The README's corpus section and its subsections (FR-011).
SECTION_PAGES = "### Pages per repository, family and form"
SECTION_PITCH = "### Against the pitch's counts"
SECTION_LEFT_OUT = "### Items left out"
SECTION_EMPTY = "### Pages with an empty first paragraph"
SECTION_COUNTS = "### Input counts per repository and form"
SECTION_FIXED = "### The six fixed items in the corpus"
SECTION_LINT = "### Structural-lint violations from an item's own text"


def load_corpus() -> dict[str, Any]:
    document: dict[str, Any] = json.loads(CORPUS_JSON.read_text(encoding="utf-8"))
    return document


def page_text(entry: dict[str, Any]) -> str:
    return (CORPUS_DIR / entry["page"]).read_text(encoding="utf-8")


def page_body(page: str) -> str:
    """The text after the frontmatter, without the blank line that follows it."""
    return page.split(FRONTMATTER_END, 1)[1].lstrip("\n")


def section(readme: str, heading: str) -> list[str]:
    """The README's lines under ``heading`` up to the next heading of any level."""
    lines = readme.splitlines()
    start = lines.index(heading) + 1
    end = next((index for index in range(start, len(lines)) if lines[index].startswith("#")), len(lines))
    return lines[start:end]


def tables(lines: list[str]) -> list[list[list[str]]]:
    """Each Markdown table in ``lines`` as its body rows (header and separator dropped), cells unquoted."""
    found: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in [*lines, ""]:
        if line.startswith("|"):
            current.append([cell.strip().strip("`") for cell in line.strip().strip("|").split("|")])
        elif current:
            found.append(current[2:])
            current = []
    return found


def bullets(lines: list[str]) -> list[str]:
    """The text of each ``- `` bullet in ``lines``, its backticks removed."""
    return [line[2:].strip().strip("`") for line in lines if line.startswith("- ")]


def median_text(values: list[int]) -> str:
    value = statistics.median(values)
    return str(int(value)) if float(value).is_integer() else str(value)


class CorpusPinnedTest(unittest.TestCase):
    """Every file is an entry and every entry a file; sha256, paths and the input counts recompute."""

    document: dict[str, Any]
    entries: list[dict[str, Any]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.document = load_corpus()
        cls.entries = cls.document["pages"]

    def test_files_equal_entries(self) -> None:
        files = sorted(path.relative_to(CORPUS_DIR).as_posix() for path in CORPUS_DIR.rglob("*") if path.is_file())
        pages = [entry["page"] for entry in self.entries]
        self.assertEqual(pages, sorted(pages))
        self.assertEqual(len(set(pages)), len(pages))
        self.assertEqual(files, pages)

    def test_each_page_hashes_to_its_entry(self) -> None:
        for entry in self.entries:
            with self.subTest(page=entry["page"]):
                data = (CORPUS_DIR / entry["page"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"])

    def test_each_path_names_its_repository_family_and_slug(self) -> None:
        pins = {row["name"]: row["pin"] for row in self.document["repositories"]}
        for entry in self.entries:
            with self.subTest(page=entry["page"]):
                repository, family, name = entry["page"].split("/")
                self.assertEqual((repository, family), (entry["repository"], entry["family"]))
                page = page_text(entry)
                self.assertIn(f"\nslug: {name.removesuffix('.md')}\n", page)
                self.assertIn(f"\n  - path: {entry['spec_path']}\n    sha: {pins[repository]}\n", page)
                self.assertEqual(_title(page), entry["title"])

    def test_the_input_counts_recompute_from_each_page(self) -> None:
        for entry in self.entries:
            with self.subTest(page=entry["page"]):
                page = page_text(entry)
                paragraph = _first_paragraph(page)
                self.assertEqual(entry["title_tokens"], len(_tokenise(_title(page))))
                self.assertEqual(entry["paragraph_tokens"], len(_tokenise(paragraph)))
                self.assertEqual(entry["paragraph_empty"], paragraph == "")


class ReadmeCorpusSectionTest(unittest.TestCase):
    """FR-011: the README's counts and lists equal what ``corpus.json`` gives."""

    document: dict[str, Any]
    entries: list[dict[str, Any]]
    readme: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.document = load_corpus()
        cls.entries = cls.document["pages"]
        cls.readme = README.read_text(encoding="utf-8")

    def by(self, *keys: str) -> Counter[tuple[str, ...]]:
        return Counter(tuple(entry[key] for key in keys) for entry in self.entries)

    def test_pages_per_repository_family_and_form(self) -> None:
        lines = section(self.readme, SECTION_PAGES)
        repositories = self.by("repository")
        total = (
            f"**{len(self.entries)} pages**: {repositories[('code-copilot-team',)]} from code-copilot-team and "
            f"{repositories[('memkernel',)]} from"
        )
        self.assertIn(total, " ".join(lines))
        (rows,) = tables(lines)
        self.assertEqual(
            {(repository, family, form): int(pages) for repository, family, form, pages in rows},
            dict(self.by("repository", "family", "form")),
        )
        self.assertEqual(len(rows), len(self.by("repository", "family", "form")))

    def test_the_counts_against_the_pitch(self) -> None:
        families, forms = tables(section(self.readme, SECTION_PITCH))
        self.assertEqual(
            {(row[0], row[1]): int(row[2]) for row in families}, dict(self.by("repository", "family").items())
        )
        self.assertEqual({(row[0], row[1]): int(row[2]) for row in forms}, dict(self.by("repository", "form").items()))
        self.assertEqual(len(families), len(self.by("repository", "family")))
        self.assertEqual(len(forms), len(self.by("repository", "form")))

    def test_the_left_out_items(self) -> None:
        (rows,) = tables(section(self.readme, SECTION_LEFT_OUT))
        expected = [
            [
                item["repository"],
                item["spec_path"],
                f"{item['line_start']}-{item['line_end']}",
                item["slug"],
                item["reason"],
            ]
            for item in self.document["left_out"]
        ]
        self.assertEqual(rows, expected)

    def test_the_pages_with_an_empty_first_paragraph(self) -> None:
        lines = section(self.readme, SECTION_EMPTY)
        (rows,) = tables(lines)
        empty = [entry for entry in self.entries if entry["paragraph_empty"]]
        expected: Counter[tuple[str, ...]] = Counter((entry["repository"], entry["form"]) for entry in empty)
        self.assertEqual(
            {(repository, form): int(count) for repository, form, count in rows},
            {key: expected[key] for key in self.by("repository", "form")},
        )
        self.assertEqual(len(rows), len(self.by("repository", "form")))
        self.assertEqual(bullets(lines), [entry["page"] for entry in empty])

    def test_the_input_counts_per_repository_and_form(self) -> None:
        (rows,) = tables(section(self.readme, SECTION_COUNTS))
        expected = []
        for repository, form in sorted(self.by("repository", "form")):
            group = [entry for entry in self.entries if (entry["repository"], entry["form"]) == (repository, form)]
            row = [repository, form, str(len(group))]
            for key in ("title_tokens", "paragraph_tokens"):
                values = [entry[key] for entry in group]
                row += [str(min(values)), median_text(values), str(max(values))]
            expected.append(row)
        self.assertEqual(rows, expected)

    def test_the_six_fixed_items_by_id(self) -> None:
        pages = {Path(entry["page"]).stem: entry["page"] for entry in self.entries}
        self.assertEqual(bullets(section(self.readme, SECTION_FIXED)), sorted(pages[slug] for slug in FIXED_ITEMS))


class FixedPagesTest(unittest.TestCase):
    """The six fixed items' pages: byte-equal to the builder, and the paragraph the scorer reads is the first
    paragraph of each item's text after its label."""

    def test_each_fixed_page_is_the_builders_page(self) -> None:
        entries = {Path(entry["page"]).stem: entry for entry in load_corpus()["pages"]}
        for slug, spec in FIXED_ITEMS.items():
            with self.subTest(slug=slug):
                entry = entries[slug]
                self.assertEqual(
                    (entry["repository"], entry["spec_path"], entry["line_start"], entry["line_end"], entry["form"]),
                    (spec["repository"], spec["spec_path"], spec["line_start"], spec["line_end"], spec["form"]),
                )
                data = (CORPUS_DIR / entry["page"]).read_bytes()
                title, page = fixed_page(slug)
                self.assertEqual(data, page.encode("utf-8"))
                self.assertEqual(entry["title"], title)
                self.assertEqual(_first_paragraph(data.decode("utf-8")), spec["paragraph"])


class CorpusRuleTest(unittest.TestCase):
    """No excluded spec, no label left in a body, no closing-keyword text."""

    document: dict[str, Any]
    entries: list[dict[str, Any]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.document = load_corpus()
        cls.entries = cls.document["pages"]

    def test_no_excluded_spec_is_present(self) -> None:
        for row in [*self.entries, *self.document["left_out"]]:
            with self.subTest(spec=row["spec_path"]):
                self.assertFalse(is_excluded(row["repository"], row["spec_path"].split("/")[1]))
        for family in self.document["families"]:
            for name in family["directories"]:
                with self.subTest(directory=name):
                    self.assertFalse(is_excluded(family["repository"], name))

    def test_no_body_keeps_its_label_line(self) -> None:
        for entry in self.entries:
            with self.subTest(page=entry["page"]):
                body = page_body(page_text(entry))
                self.assertNotIn("**", entry["title"])
                if entry["form"] in (FORM_H3, FORM_H3_ADR):
                    lines = body.split("\n")
                    fenced = fenced_lines(lines)
                    self.assertFalse(
                        [line for index, line in enumerate(lines) if not fenced[index] and line.startswith(H3_PREFIX)]
                    )
                    continue
                self.assertTrue(body.startswith(DECISION_HEADING), body)
                rest = body[len(DECISION_HEADING) :].lstrip("\n")
                opening = BOLD_SPAN_RE.match(rest)
                if opening is not None:
                    self.assertNotEqual(title_from_label(" ".join(opening.group(1).split())), entry["title"])

    def test_no_page_or_file_holds_closing_keyword_text(self) -> None:
        files = [path for path in DUPLICATES_DIR.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
        self.assertTrue(any(path.is_relative_to(CORPUS_DIR) for path in files))
        for path in files:
            with self.subTest(path=path.relative_to(REPO_ROOT).as_posix()):
                text = path.read_bytes().decode("utf-8", errors="replace")
                self.assertIsNone(CLOSING_KEYWORD_RE.search(text))


class StructuralLintTest(unittest.TestCase):
    """Every page passes ``wiki_studio.lint``'s structural checks on a temporary wiki, but for the README's list."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_only_the_listed_violations(self) -> None:
        wiki = self.tmp / "wiki"
        decisions = wiki / "decisions"
        decisions.mkdir(parents=True)
        slugs = []
        for entry in load_corpus()["pages"]:
            slug = Path(entry["page"]).stem
            shutil.copyfile(CORPUS_DIR / entry["page"], decisions / f"{slug}.md")
            slugs.append(slug)
        links = "".join(f"- [{slug}](decisions/{slug}.md)\n" for slug in slugs)
        (wiki / "index.md").write_text(INDEX_MD + links, encoding="utf-8")
        (wiki / "log.md").write_text(LOG_MD, encoding="utf-8")
        violations = lint_wiki(wiki, root=self.tmp)
        listed = bullets(section(README.read_text(encoding="utf-8"), SECTION_LINT))
        self.assertEqual(sorted(violations), sorted(listed))


if __name__ == "__main__":
    unittest.main()
