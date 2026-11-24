# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The near-duplicate study's labels, checked by structure (issue 121, FR-017).

``labels.json`` was written by hand in the labelling session, with no candidate code in the tree. These tests read it
beside ``corpus.json`` and run no script: its keys and families; every group within one family and naming pages of
the corpus; every pair inside a group labelled exactly once, and no labelled pair without a common group; one of the
six dispositions and a one-line reason on every label; the cross pairs' scopes; one summary line per group (its
question) and per page in no group (its title); the true-pair count, in the file and in the README; and
``corpus_sha256``. From the pause on, the review sample is checked too: 20 distinct within-family pairs of the base
families, split by FR-008's largest-remainder rule. No file under ``eval/duplicates/`` holds closing-keyword text.
"""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

from eval.duplicates.extract import CLOSING_KEYWORD_RE, CORPUS_JSON_NAME
from eval.duplicates.sample import (
    DEFAULT_LABEL,
    LABELS_NAME,
    SAMPLE_NAME,
    SAMPLE_SIZE,
    SAMPLED_FAMILIES,
    TRUE_DISPOSITIONS,
    largest_remainder,
    within_family_pairs,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DUPLICATES_DIR = REPO_ROOT / "eval" / "duplicates"
CORPUS_JSON = DUPLICATES_DIR / CORPUS_JSON_NAME
LABELS_JSON = DUPLICATES_DIR / LABELS_NAME
SAMPLE_JSON = DUPLICATES_DIR / SAMPLE_NAME
README = DUPLICATES_DIR / "README.md"

LABEL_KEYS = frozenset(
    {"corpus_sha256", "families", "groups", "pairs", "summary", "cross_pairs", "defaults", "true_pairs"}
)
FALSE_DISPOSITIONS = frozenset({"companion", "distinct-by-precondition", DEFAULT_LABEL})
DISPOSITIONS = TRUE_DISPOSITIONS | FALSE_DISPOSITIONS
DEFAULTS = {"within_family": DEFAULT_LABEL, "cross": DEFAULT_LABEL}
SCOPE_CROSS_FAMILY = "cross-family"
SCOPE_CROSS_REPOSITORY = "cross-repository"
SUMMARY_GROUP = "group"
SUMMARY_PAGE = "page"
MINIMUM_TRUE_PAIRS = 8
TRUE_PAIRS_RE = re.compile(r"\*\*True pairs: (\d+)\*\*")
PAIR_SIZE = 2


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def pair_key(pair: list[str]) -> tuple[str, ...]:
    return tuple(pair)


class LabelsTestCase(unittest.TestCase):
    labels: dict[str, Any]
    corpus: dict[str, Any]
    entries: dict[str, dict[str, Any]]
    groups: dict[str, dict[str, Any]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.labels = load(LABELS_JSON)
        cls.corpus = load(CORPUS_JSON)
        cls.entries = {str(entry["page"]): entry for entry in cls.corpus["pages"]}
        cls.groups = {str(group["id"]): group for group in cls.labels["groups"]}

    def assert_pair(self, pair: list[str]) -> None:
        """Two distinct pages of the corpus, in sorted order."""
        self.assertEqual(len(pair), PAIR_SIZE, pair)
        self.assertEqual(pair, sorted(pair), pair)
        self.assertNotEqual(pair[0], pair[1])
        for page in pair:
            self.assertIn(page, self.entries)

    def assert_label(self, row: dict[str, Any]) -> None:
        """One of the six dispositions and a non-empty one-line reason."""
        self.assertIn(row["disposition"], DISPOSITIONS, row["pair"])
        reason = row["reason"]
        self.assertIsInstance(reason, str)
        self.assertTrue(reason.strip(), row["pair"])
        self.assertNotIn("\n", reason, row["pair"])


class LabelsFileTest(LabelsTestCase):
    """FR-015: the keys, the families, the defaults and the corpus hash."""

    def test_keys(self) -> None:
        self.assertEqual(set(self.labels), LABEL_KEYS)

    def test_families_equal_the_corpus(self) -> None:
        counts = Counter((str(entry["family"]), str(entry["repository"])) for entry in self.corpus["pages"])
        expected = sorted((family, repository, pages) for (family, repository), pages in counts.items())
        stated = sorted((row["name"], row["repository"], row["pages"]) for row in self.labels["families"])
        self.assertEqual(stated, expected)

    def test_defaults(self) -> None:
        self.assertEqual(self.labels["defaults"], DEFAULTS)

    def test_corpus_sha256(self) -> None:
        self.assertEqual(self.labels["corpus_sha256"], hashlib.sha256(CORPUS_JSON.read_bytes()).hexdigest())


class GroupsAndPairsTest(LabelsTestCase):
    """FR-013: groups by question within one family; every in-group pair labelled exactly once."""

    def test_group_ids_are_unique(self) -> None:
        self.assertEqual(len(self.groups), len(self.labels["groups"]))

    def test_each_group_names_its_question_and_pages_of_its_family(self) -> None:
        for group in self.labels["groups"]:
            with self.subTest(group=group["id"]):
                self.assertTrue(str(group["question"]).strip())
                pages = group["pages"]
                self.assertGreaterEqual(len(pages), PAIR_SIZE)
                self.assertEqual(len(set(pages)), len(pages))
                for page in pages:
                    self.assertIn(page, self.entries)
                    self.assertEqual(self.entries[page]["family"], group["family"])

    def test_every_in_group_pair_is_labelled_exactly_once(self) -> None:
        expected = {
            tuple(sorted(pair)) for group in self.labels["groups"] for pair in combinations(group["pages"], PAIR_SIZE)
        }
        labelled = [pair_key(row["pair"]) for row in self.labels["pairs"]]
        self.assertEqual(len(labelled), len(set(labelled)))
        self.assertEqual(set(labelled), expected)

    def test_each_pair_names_a_group_holding_both_pages(self) -> None:
        for row in self.labels["pairs"]:
            with self.subTest(pair=row["pair"]):
                self.assert_pair(row["pair"])
                self.assertIn(row["group"], self.groups)
                self.assertTrue(set(row["pair"]) <= set(self.groups[row["group"]]["pages"]))

    def test_dispositions_and_reasons(self) -> None:
        for row in [*self.labels["pairs"], *self.labels["cross_pairs"]]:
            with self.subTest(pair=row["pair"]):
                self.assert_label(row)


class CrossPairsTest(LabelsTestCase):
    """FR-014: cross pairs join pages of different families, and their scope matches the repositories."""

    def test_cross_pairs_and_scopes(self) -> None:
        seen: set[tuple[str, ...]] = set()
        for row in self.labels["cross_pairs"]:
            with self.subTest(pair=row["pair"]):
                self.assert_pair(row["pair"])
                first, second = (self.entries[page] for page in row["pair"])
                self.assertNotEqual(first["family"], second["family"])
                scope = SCOPE_CROSS_FAMILY if first["repository"] == second["repository"] else SCOPE_CROSS_REPOSITORY
                self.assertEqual(row["scope"], scope)
                self.assertNotIn(pair_key(row["pair"]), seen)
                seen.add(pair_key(row["pair"]))


class SummaryTest(LabelsTestCase):
    """FR-014: one summary line per group (its question) and one per page in no group (its title)."""

    def test_one_line_per_group_and_per_ungrouped_page(self) -> None:
        kinds = Counter(row["kind"] for row in self.labels["summary"])
        self.assertEqual(set(kinds), {SUMMARY_GROUP, SUMMARY_PAGE})
        group_refs = [row["ref"] for row in self.labels["summary"] if row["kind"] == SUMMARY_GROUP]
        page_refs = [row["ref"] for row in self.labels["summary"] if row["kind"] == SUMMARY_PAGE]
        grouped = {page for group in self.labels["groups"] for page in group["pages"]}
        self.assertEqual(sorted(group_refs), sorted(self.groups))
        self.assertEqual(sorted(page_refs), sorted(set(self.entries) - grouped))

    def test_each_line_is_the_question_or_the_title(self) -> None:
        for row in self.labels["summary"]:
            with self.subTest(ref=row["ref"]):
                if row["kind"] == SUMMARY_GROUP:
                    self.assertEqual(row["line"], self.groups[row["ref"]]["question"])
                else:
                    self.assertEqual(row["line"], self.entries[row["ref"]]["title"])


class TruePairsTest(LabelsTestCase):
    """FR-015: ``true_pairs`` counts the true labels, and the README states it beside the minimum of 8."""

    def test_true_pairs_counts_the_true_labels(self) -> None:
        rows = [*self.labels["pairs"], *self.labels["cross_pairs"]]
        self.assertEqual(self.labels["true_pairs"], sum(row["disposition"] in TRUE_DISPOSITIONS for row in rows))

    def test_the_readme_states_the_count_beside_the_minimum(self) -> None:
        readme = README.read_text(encoding="utf-8")
        self.assertEqual(TRUE_PAIRS_RE.findall(readme), [str(self.labels["true_pairs"])])
        self.assertIn(f"against the minimum of {MINIMUM_TRUE_PAIRS}", readme)


class ReviewSampleTest(LabelsTestCase):
    """FR-008: the review sample, drawn at the pause: 20 distinct false within-family pairs of the base families.

    The sample's ``labels_sha256`` is deliberately not compared with the current ``labels.json``: FR-016(c) lets the
    owner change labels by commit after the sample is drawn, so the hash only records which labels it came from.
    """

    def setUp(self) -> None:
        if not SAMPLE_JSON.exists():
            self.skipTest(f"{SAMPLE_NAME} is drawn at the pause after the labels")
        self.sample = load(SAMPLE_JSON)

    def test_twenty_distinct_pairs_each_within_one_base_family(self) -> None:
        pairs = self.sample["pairs"]
        self.assertEqual(len(pairs), SAMPLE_SIZE)
        self.assertEqual(len({pair_key(row["pair"]) for row in pairs}), SAMPLE_SIZE)
        for row in pairs:
            with self.subTest(pair=row["pair"]):
                self.assert_pair(row["pair"])
                self.assertIn(row["family"], SAMPLED_FAMILIES)
                for page in row["pair"]:
                    self.assertEqual(self.entries[page]["family"], row["family"])
                self.assertIn(row["label"], FALSE_DISPOSITIONS)

    def test_the_split_is_the_largest_remainder_rule_on_the_corpus(self) -> None:
        counts = {family: len(pairs) for family, pairs in within_family_pairs(self.corpus["pages"]).items()}
        split = largest_remainder(counts)
        self.assertEqual(self.sample["split"], split)
        self.assertEqual(
            dict(Counter(row["family"] for row in self.sample["pairs"])), {k: v for k, v in split.items() if v}
        )


class ClosingKeywordTest(unittest.TestCase):
    """FR-009's scan: no file under ``eval/duplicates/`` holds closing-keyword text, the labels included."""

    def test_no_file_holds_closing_keyword_text(self) -> None:
        files = [path for path in DUPLICATES_DIR.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
        self.assertIn(LABELS_JSON, files)
        for path in files:
            with self.subTest(path=path.relative_to(DUPLICATES_DIR).as_posix()):
                self.assertIsNone(CLOSING_KEYWORD_RE.search(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
