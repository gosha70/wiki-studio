# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""US1 freeze: the duplicate-audit study's README and protocol pinned before any audit code exists (FR-013).

The constants below are the sha256 of the committed files, computed in a shell, not in Python. Every
``development.inputs`` entry of ``protocol.json`` must still hash to its recorded value (the corpus pages stay
pinned through ``corpus.json`` by ``tests/test_duplicates_frozen.py``), the candidates must be mutual rank at
k = 1, 3, 5 in that order, and the bar must hold its four values. This module is edited only by a protocol change
the owner asks for at the pause after US1, in the same commit as that change and before ``audit.py`` exists.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = REPO_ROOT / "eval" / "duplicate_audit"
README = AUDIT_DIR / "README.md"
PROTOCOL = AUDIT_DIR / "protocol.json"

README_SHA256 = "afbba9f5baa07da4186f14af7f8ae7cd6cea3ce95d7b08046baeb94c923f2e7c"
PROTOCOL_SHA256 = "8845c2ba4514037954fd3d8cd8b9156b82c1225bfe2d9cc6a49437f8d5ee3c37"

CANDIDATE_KS = [1, 3, 5]
MIN_TRUE_PAIRS = 8
RECALL_NUMERATOR = 3
RECALL_DENOMINATOR = 4
MIN_NON_RESTATEMENT_FOUND = 2


def sha256_of(path: Path) -> str:
    """The file's sha256, lowercase hex."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    """The file's JSON object; anything else is a failure of the freeze."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"{path.name} is not a JSON object")
    return data


class FrozenDuplicateAuditProtocolTest(unittest.TestCase):
    """The README and protocol still hash to their pins, the inputs to theirs, and k and the bar are as frozen."""

    protocol: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = load_json(PROTOCOL)

    def test_readme_and_protocol_still_hash_to_their_pinned_values(self) -> None:
        actual = {"README.md": sha256_of(README), "protocol.json": sha256_of(PROTOCOL)}
        self.assertEqual(actual, {"README.md": README_SHA256, "protocol.json": PROTOCOL_SHA256})

    def test_every_development_input_hashes_to_its_recorded_value(self) -> None:
        inputs = self.protocol["development"]["inputs"]
        self.assertTrue(inputs)
        paths = [entry["path"] for entry in inputs]
        self.assertEqual(len(paths), len(set(paths)))
        for entry in inputs:
            with self.subTest(path=entry["path"]):
                self.assertEqual(sha256_of(REPO_ROOT / entry["path"]), entry["sha256"])

    def test_candidates_are_mutual_rank_at_k_1_3_5_in_order(self) -> None:
        candidates = self.protocol["candidates"]
        self.assertEqual([entry["k"] for entry in candidates], CANDIDATE_KS)
        self.assertEqual([entry["name"] for entry in candidates], [f"mutual-top-{k}" for k in CANDIDATE_KS])

    def test_bar_holds_its_four_frozen_values(self) -> None:
        bar = self.protocol["bar"]
        self.assertEqual(bar["min_true_pairs"], MIN_TRUE_PAIRS)
        self.assertEqual((bar["recall_numerator"], bar["recall_denominator"]), (RECALL_NUMERATOR, RECALL_DENOMINATOR))
        self.assertIs(bar["false_not_above_true"], True)
        self.assertEqual(bar["min_non_restatement_found"], MIN_NON_RESTATEMENT_FOUND)


if __name__ == "__main__":
    unittest.main()
