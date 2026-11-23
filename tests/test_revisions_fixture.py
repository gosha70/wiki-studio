# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""US1 structure of the revision-check study's labels and cases (FR-010).

Checks what the committed files allow: the 13-to-10 derivation recomputed from
the issue 54 study's results, the 24 labels, every case directory's shape and
page hash, the pre-successor copy's edits, and the fence (FR-009). The cited
sources' own hashes cannot be rechecked here, because CI has no
code-copilot-team checkout; this test only compares the two recorded values.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PATTERNS_DIR = REPO_ROOT / "eval" / "patterns"
PATTERNS_WIKI = PATTERNS_DIR / "wiki"
PATTERNS_README = PATTERNS_DIR / "README.md"
STALENESS = PATTERNS_DIR / "results" / "staleness.json"

REVISIONS_DIR = REPO_ROOT / "eval" / "revisions"
README = REVISIONS_DIR / "README.md"
LABELS = REVISIONS_DIR / "labels.json"
PROTOCOL = REVISIONS_DIR / "protocol.json"
CASES_DIR = REVISIONS_DIR / "cases"
FENCED_DIR = CASES_DIR / "keyword-quoting"
MERGE_PAGE = "decisions/merge-require-green-ci-was-never-read.md"
PRE_SUCCESSOR = REVISIONS_DIR / "pre-successor" / "merge-require-green-ci-was-never-read.md"

CHANGED = "changed"
SUPERSEDED_KEY = "superseded_by:"
NEEDS_REVIEW_ENTRY = (MERGE_PAGE, "specs/auto-build-loop-merge-profile/spec.md", "a24a00e")
CITATION_ERROR_ENTRY = (
    "decisions/judge-statistics-and-charts-stay-in-the-stdlib.md",
    "scripts/benchmark_runner/calibration/spearman.py",
    "dafbc5b",
)

# FR-003: entries, page-and-file citations, pages.
DERIVATION_ROWS = [(15, 14, 13), (-3, -2, -2), (12, 12, 11), (-1, -1, -1), (11, 11, 10)]

OPEN_CASE_IDS = frozenset(
    {"vllm-backend-doc", "run-wiki-ingest-rules", "provider-config-guarantee", "benchmark-provider-id"}
)
FENCED_CASE_IDS = frozenset({"pre-pr-strict-mode", "pre-pr-keyword-set", "pre-pr-doc-audit"})
FENCED_PREFIX = "pre-pr-"
NEGATIVE_SUFFIX = "-negative"

# FR-005: every key of case.json; sha_derivation is present only with a derived sha.
CASE_KEYS = frozenset(
    {
        "id",
        "repository",
        "page_origin",
        "page_from",
        "path",
        "sha",
        "sha_derived",
        "source_change_commits",
        "read_commit",
        "read_rule",
        "correcting_commit",
        "sha256",
        "evidence",
        "negative",
        "should_flag",
        "reason",
    }
)
SHA_DERIVATION_KEY = "sha_derivation"
SHA256_KEYS = frozenset({"page_md", "source_at_sha", "source_at_read"})
PAGE_ORIGINS = frozenset({"verbatim", "built"})
READ_RULE_PARENT = "parent"
READ_RULE_CORRECTING = "correcting"
CASE_REPOSITORY = "code-copilot-team"

FULL_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
CITED_SHA_RE = re.compile(r"[0-9a-f]{7,40}")
# A closing verb followed by an issue reference, as GitHub reads it.
CLOSING_KEYWORD_RE = re.compile(r"(close[sd]?|fix(e[sd])?|resolve[sd]?)\s+#[0-9]", re.IGNORECASE)

# FR-007: the lines the pre-successor copy drops from the fixture page, and the lines it gains.
PRE_SUCCESSOR_REMOVED = [
    "status: deprecated",
    "superseded_by: decisions/merge-require-green-ci-was-never-read-and-was-removed.md",
    "  - path: specs/auto-build-loop-merge-profile/spec.md",
    "    sha: e39969f",
    "Confidence: high: the correction says the key was never read and was removed, with the commit to prove it.",
    "",
    "Correction: [merge.require_green_ci was never read and was removed]"
    "(merge-require-green-ci-was-never-read-and-was-removed.md).",
]
PRE_SUCCESSOR_ADDED = ["status: stable", "Confidence: high."]

Entry = tuple[str, str, str]


def sha256_of(path: Path) -> str:
    """The file's sha256, lowercase hex."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    """The file's JSON object."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"{path.name} is not a JSON object")
    return data


def frontmatter_lines(path: Path) -> list[str]:
    """The lines between the page's opening and closing ``---``."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise AssertionError(f"{path} has no frontmatter")
    return lines[1 : lines.index("---", 1)]


def is_superseded(page: str) -> bool:
    """Whether the issue 54 fixture page carries ``superseded_by``."""
    return any(line.startswith(SUPERSEDED_KEY) for line in frontmatter_lines(PATTERNS_WIKI / page))


def counts(entries: list[Entry]) -> tuple[int, int, int]:
    """Source entries, page-and-file citations and pages among ``entries``."""
    return (len(entries), len({(page, path) for page, path, _ in entries}), len({page for page, _, _ in entries}))


def difference(after: tuple[int, int, int], before: tuple[int, int, int]) -> tuple[int, int, int]:
    return (after[0] - before[0], after[1] - before[1], after[2] - before[2])


def case_directories() -> list[Path]:
    """Every directory under ``cases/`` that holds a ``case.json``."""
    return sorted(path.parent for path in CASES_DIR.rglob("case.json"))


class StudyLabelsTest(unittest.TestCase):
    """The 24 labels and the 13-to-10 derivation (FR-002, FR-003)."""

    staleness: dict[str, Any]
    labels: dict[str, Any]
    protocol: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.staleness = load_json(STALENESS)
        cls.labels = load_json(LABELS)
        cls.protocol = load_json(PROTOCOL)

    def test_labels_follow_the_study_results_in_order(self) -> None:
        expected = [
            (page["page"], source["path"], source["sha"], source["revision_check"])
            for page in self.staleness["pages"]
            for source in page["sources"]
        ]
        actual = [
            (page["page"], source["path"], source["sha"], source["revision_check"])
            for page in self.labels["pages"]
            for source in page["sources"]
        ]
        self.assertEqual(len(self.labels["pages"]), 14)
        self.assertEqual(len(actual), 24)
        self.assertEqual(actual, expected)

    def test_exactly_one_needs_review_and_one_citation_error(self) -> None:
        needs_review = []
        citation_error = []
        for page in self.labels["pages"]:
            for source in page["sources"]:
                self.assertIsInstance(source["needs_review"], bool)
                self.assertIsInstance(source["citation_error"], bool)
                entry = (page["page"], source["path"], source["sha"])
                if source["needs_review"]:
                    needs_review.append(entry)
                if source["citation_error"]:
                    citation_error.append(entry)
        self.assertEqual(needs_review, [NEEDS_REVIEW_ENTRY])
        self.assertEqual(citation_error, [CITATION_ERROR_ENTRY])

    def test_superseded_matches_the_fixture_frontmatter(self) -> None:
        for page in self.labels["pages"]:
            with self.subTest(page=page["page"]):
                self.assertIs(page["superseded"], is_superseded(page["page"]))

    def test_judgments_are_the_study_readme_cells(self) -> None:
        readme = PATTERNS_README.read_text(encoding="utf-8")
        for page in self.labels["pages"]:
            for source in page["sources"]:
                with self.subTest(page=page["page"], path=source["path"], sha=source["sha"]):
                    judgment = source["judgment"]
                    if source["revision_check"] == CHANGED:
                        row_end = f"@ `{source['sha']}` | not flagged | changed | {judgment} |"
                        self.assertIn(row_end, readme)
                    else:
                        self.assertIsNone(judgment)

    def test_the_derivation_recomputes_and_equals_the_protocol(self) -> None:
        changed: list[Entry] = [
            (page["page"], source["path"], source["sha"])
            for page in self.staleness["pages"]
            for source in page["sources"]
            if source["revision_check"] == CHANGED
        ]
        live = [entry for entry in changed if not is_superseded(entry[0])]
        left = [entry for entry in live if entry != CITATION_ERROR_ENTRY]
        rows = [
            counts(changed),
            difference(counts(live), counts(changed)),
            counts(live),
            difference(counts(left), counts(live)),
            counts(left),
        ]
        self.assertEqual(rows, DERIVATION_ROWS)
        recorded = [(row["entries"], row["citations"], row["pages"]) for row in self.protocol["derivation"]]
        self.assertEqual(recorded, rows)
        self.assertEqual(self.protocol["false_pages"], list(dict.fromkeys(page for page, _, _ in left)))
        self.assertEqual(
            [(entry["page"], entry["path"], entry["sha"]) for entry in self.protocol["false_entries"]],
            left,
        )
        self.assertEqual(len(self.protocol["false_pages"]), 10)
        self.assertEqual(len(self.protocol["false_entries"]), 11)

    def test_the_readme_carries_the_derivation_table(self) -> None:
        readme = README.read_text(encoding="utf-8")
        for entries, citations, pages in DERIVATION_ROWS:
            with self.subTest(row=(entries, citations, pages)):
                self.assertIn(f"| {entries} | {citations} | {pages} |", readme)

    def test_the_protocol_names_the_two_special_entries(self) -> None:
        true_entry = self.protocol["true_entry"]
        self.assertEqual((true_entry["page"], true_entry["path"], true_entry["sha"]), NEEDS_REVIEW_ENTRY)
        self.assertEqual(REPO_ROOT / true_entry["read_on"], PRE_SUCCESSOR)
        error_entry = self.protocol["citation_error_entry"]
        self.assertEqual((error_entry["page"], error_entry["path"], error_entry["sha"]), CITATION_ERROR_ENTRY)


class CaseFixturesTest(unittest.TestCase):
    """Every supplementary case directory (FR-004, FR-005, FR-006, FR-009)."""

    directories: list[Path]
    cases: dict[Path, dict[str, Any]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.directories = case_directories()
        cls.cases = {directory: load_json(directory / "case.json") for directory in cls.directories}

    def test_the_seven_inventoried_cases_are_present_and_named(self) -> None:
        readme = README.read_text(encoding="utf-8")
        protocol = load_json(PROTOCOL)
        positives_and_false = [directory for directory in self.directories if not self.cases[directory]["negative"]]
        self.assertEqual({directory.name for directory in positives_and_false}, OPEN_CASE_IDS | FENCED_CASE_IDS)
        self.assertEqual(len(positives_and_false), 7)
        self.assertEqual(
            sorted(protocol["cases"]),
            sorted(directory.relative_to(REPO_ROOT).as_posix() for directory in positives_and_false),
        )
        for directory in positives_and_false:
            with self.subTest(case=directory.name):
                self.assertIn(f"`{directory.name}`", readme)

    def test_every_directory_under_cases_is_a_case(self) -> None:
        present = {path for path in CASES_DIR.iterdir() if path.is_dir() and path != FENCED_DIR}
        present |= {path for path in FENCED_DIR.iterdir() if path.is_dir()}
        self.assertEqual(present, set(self.directories))
        for directory in self.directories:
            with self.subTest(case=directory.name):
                self.assertTrue((directory / "page.md").is_file())
                self.assertTrue((directory / "case.json").is_file())

    def test_case_json_has_every_key(self) -> None:
        for directory, case in self.cases.items():
            with self.subTest(case=directory.name):
                self.assertEqual(set(case) - {SHA_DERIVATION_KEY}, CASE_KEYS)
                self.assertEqual(case["id"], directory.name)
                self.assertEqual(case["repository"], CASE_REPOSITORY)
                self.assertIn(case["page_origin"], PAGE_ORIGINS)
                self.assertEqual(set(case["sha256"]), SHA256_KEYS)
                self.assertIsInstance(case["negative"], bool)
                self.assertIsInstance(case["should_flag"], bool)
                self.assertIsInstance(case["reason"], str)
                self.assertTrue(case["reason"].strip())
                self.assertNotIn("\n", case["reason"])
                self.assertIsInstance(case["sha_derived"], bool)
                self.assertEqual(SHA_DERIVATION_KEY in case, case["sha_derived"])
                if case["negative"]:
                    self.assertTrue(case["id"].endswith(NEGATIVE_SUFFIX))
                    self.assertIs(case["should_flag"], False)

    def test_page_md_hashes_to_its_recorded_value(self) -> None:
        for directory, case in self.cases.items():
            with self.subTest(case=directory.name):
                self.assertEqual(case["sha256"]["page_md"], sha256_of(directory / "page.md"))

    def test_commits_are_full_hashes_and_follow_the_read_rule(self) -> None:
        for directory, case in self.cases.items():
            with self.subTest(case=directory.name):
                commits = [
                    case["read_commit"],
                    case["correcting_commit"],
                    case["page_from"]["commit"],
                    case["evidence"]["message_of"],
                    case["evidence"]["diff_of"],
                    *case["source_change_commits"],
                ]
                for commit in commits:
                    self.assertRegex(commit, FULL_COMMIT_RE)
                    self.assertEqual(len(commit), 40)
                self.assertTrue(case["source_change_commits"])
                self.assertTrue(case["page_from"]["path"])
                if case["read_rule"] == READ_RULE_CORRECTING:
                    self.assertEqual(case["read_commit"], case["correcting_commit"])
                    self.assertIn(case["correcting_commit"], case["source_change_commits"])
                else:
                    self.assertEqual(case["read_rule"], READ_RULE_PARENT)
                    self.assertNotEqual(case["read_commit"], case["correcting_commit"])

    def test_the_page_cites_the_case_source(self) -> None:
        for directory, case in self.cases.items():
            with self.subTest(case=directory.name):
                self.assertTrue(CITED_SHA_RE.fullmatch(case["sha"]))
                lines = frontmatter_lines(directory / "page.md")
                self.assertIn(f"  - path: {case['path']}", lines)
                cited = lines.index(f"  - path: {case['path']}")
                self.assertEqual(lines[cited + 1], f"    sha: {case['sha']}")

    def test_a_flagged_case_changed_between_its_sha_and_its_read_commit(self) -> None:
        # C0 flags every positive by construction (FR-004); nothing is diffed here.
        for directory, case in self.cases.items():
            with self.subTest(case=directory.name):
                at_sha = case["sha256"]["source_at_sha"]
                at_read = case["sha256"]["source_at_read"]
                for value in (at_sha, at_read):
                    if value is not None:
                        self.assertTrue(SHA256_RE.fullmatch(value))
                if case["should_flag"]:
                    self.assertIsNotNone(at_sha)
                    self.assertIsNotNone(at_read)
                    self.assertNotEqual(at_sha, at_read)

    def test_the_keyword_quoting_cases_live_only_inside_the_fence(self) -> None:
        for directory in self.directories:
            with self.subTest(case=directory.name):
                fenced = directory.name.startswith(FENCED_PREFIX)
                self.assertEqual(directory.parent, FENCED_DIR if fenced else CASES_DIR)
        self.assertEqual(
            {directory.name for directory in self.directories if directory.parent == FENCED_DIR}
            - {f"{case_id}{NEGATIVE_SUFFIX}" for case_id in FENCED_CASE_IDS},
            FENCED_CASE_IDS,
        )


class PreSuccessorCopyTest(unittest.TestCase):
    """The pre-successor copy differs from the fixture page by exactly FR-007's edits."""

    def test_the_line_diff_is_the_five_edits(self) -> None:
        original = (PATTERNS_WIKI / MERGE_PAGE).read_text(encoding="utf-8").splitlines()
        copy = PRE_SUCCESSOR.read_text(encoding="utf-8").splitlines()
        removed: list[str] = []
        added: list[str] = []
        for line in difflib.unified_diff(original, copy, lineterm="", n=0):
            if line.startswith(("---", "+++", "@@")):
                continue
            (removed if line.startswith("-") else added).append(line[1:])
        self.assertEqual(sorted(removed), sorted(PRE_SUCCESSOR_REMOVED))
        self.assertEqual(sorted(added), sorted(PRE_SUCCESSOR_ADDED))

    def test_the_copy_keeps_only_the_first_source(self) -> None:
        lines = frontmatter_lines(PRE_SUCCESSOR)
        self.assertEqual([line for line in lines if line.startswith("    sha:")], ["    sha: a24a00e"])
        self.assertFalse(any(line.startswith(SUPERSEDED_KEY) for line in lines))


class FenceTest(unittest.TestCase):
    """No closing-keyword phrase outside the fenced directory (FR-009)."""

    def test_the_pattern_matches_a_closing_phrase(self) -> None:
        verb = "clo" + "ses"
        self.assertTrue(CLOSING_KEYWORD_RE.search(f"this {verb} #12"))
        self.assertFalse(CLOSING_KEYWORD_RE.search("issue #12 stays open"))

    def test_no_closing_keyword_outside_the_fenced_directory(self) -> None:
        scanned = 0
        for path in sorted(REVISIONS_DIR.rglob("*")):
            if not path.is_file() or FENCED_DIR in path.parents or path.suffix == ".pyc":
                continue
            scanned += 1
            with self.subTest(file=path.relative_to(REPO_ROOT).as_posix()):
                text = path.read_text(encoding="utf-8")
                self.assertIsNone(CLOSING_KEYWORD_RE.search(text))
        self.assertGreater(scanned, 0)


if __name__ == "__main__":
    unittest.main()
