# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""US1 freeze: the similar-pages study's README and protocol pinned before any ranking code exists (FR-009).

The constants below are the sha256 of the committed files, computed in a shell, not in Python. Every ``inputs``
entry of ``protocol.json`` must still hash to its recorded value (the corpus pages stay pinned through
``corpus.json`` by ``tests/test_duplicates_frozen.py``), and the 13 tries must be the true pairs of the frozen
labels: the 5 ``redundant`` pairs both ways and the 3 ``supersedes`` pairs once. This module is edited only by a
protocol change the owner asks for at the pause after US1, in the same commit as that change.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SIMILAR_DIR = REPO_ROOT / "eval" / "similar"
README = SIMILAR_DIR / "README.md"
PROTOCOL = SIMILAR_DIR / "protocol.json"
DUPLICATES_LABELS = REPO_ROOT / "eval" / "duplicates" / "labels.json"

README_SHA256 = "9efe65f1ed2f5e89d261e8d2f185b9c576ffa7af8c59ba1b530667b788a19701"
PROTOCOL_SHA256 = "6807822a5d66a6f03254ee557ad47089ba6690b5b0839aba39422608e7c7ac89"

REDUNDANT = "redundant"
SUPERSEDES = "supersedes"
TRUE_DISPOSITIONS = frozenset({REDUNDANT, "conflicting", SUPERSEDES})
TRY_COUNT = 13
REDUNDANT_TRIES = 10
SUPERSEDES_TRIES = 3


def sha256_of(path: Path) -> str:
    """The file's sha256, lowercase hex."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    """The file's JSON object; anything else is a failure of the freeze."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"{path.name} is not a JSON object")
    return data


def true_pairs(labels: dict[str, Any]) -> dict[frozenset[str], str]:
    """Every true pair of the labels (``pairs`` and ``cross_pairs``) mapped to its disposition."""
    pairs: dict[frozenset[str], str] = {}
    for entry in labels["pairs"] + labels["cross_pairs"]:
        if entry["disposition"] in TRUE_DISPOSITIONS:
            pairs[frozenset(entry["pair"])] = entry["disposition"]
    return pairs


class FrozenSimilarProtocolTest(unittest.TestCase):
    """The README and protocol still hash to their pins, the inputs to theirs, and the tries are the true pairs."""

    protocol: dict[str, Any]
    labels: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = load_json(PROTOCOL)
        cls.labels = load_json(DUPLICATES_LABELS)

    def test_readme_and_protocol_still_hash_to_their_pinned_values(self) -> None:
        actual = {"README.md": sha256_of(README), "protocol.json": sha256_of(PROTOCOL)}
        self.assertEqual(actual, {"README.md": README_SHA256, "protocol.json": PROTOCOL_SHA256})

    def test_every_input_hashes_to_its_recorded_value(self) -> None:
        inputs = self.protocol["inputs"]
        self.assertTrue(inputs)
        paths = [entry["path"] for entry in inputs]
        self.assertEqual(len(paths), len(set(paths)))
        for entry in inputs:
            with self.subTest(path=entry["path"]):
                self.assertEqual(sha256_of(REPO_ROOT / entry["path"]), entry["sha256"])

    def test_tries_hold_the_redundant_pairs_both_ways_and_the_supersedes_pairs_once(self) -> None:
        tries = self.protocol["tries"]
        self.assertEqual(len(tries), TRY_COUNT)
        counts = Counter(entry["disposition"] for entry in tries)
        self.assertEqual(counts, Counter({REDUNDANT: REDUNDANT_TRIES, SUPERSEDES: SUPERSEDES_TRIES}))
        ordered = [(entry["query"], entry["partner"]) for entry in tries]
        self.assertEqual(len(ordered), len(set(ordered)))
        redundant = [(entry["query"], entry["partner"]) for entry in tries if entry["disposition"] == REDUNDANT]
        for query, partner in redundant:
            with self.subTest(query=query):
                self.assertIn((partner, query), redundant)

    def test_every_try_is_a_true_pair_of_the_frozen_labels(self) -> None:
        pairs = true_pairs(self.labels)
        for entry in self.protocol["tries"]:
            with self.subTest(query=entry["query"]):
                self.assertNotEqual(entry["query"], entry["partner"])
                self.assertEqual(pairs.get(frozenset((entry["query"], entry["partner"]))), entry["disposition"])

    def test_tries_cover_every_true_pair_of_the_frozen_labels(self) -> None:
        tried = {frozenset((entry["query"], entry["partner"])) for entry in self.protocol["tries"]}
        self.assertEqual(tried, set(true_pairs(self.labels)))


if __name__ == "__main__":
    unittest.main()
