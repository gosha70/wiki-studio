# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""US3 freeze: labels, gold and protocol pinned by sha256 (FR-016).

These files were written before any signal code existed and are never edited
after the US3 phase. The constants below are the sha256 of the committed
files; a change to any of the three breaks this test.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PATTERNS_DIR = REPO_ROOT / "eval" / "patterns"
WIKI_DIR = PATTERNS_DIR / "wiki"
CORPUS = PATTERNS_DIR / "corpus" / "decisions-57.md"
MANIFEST = PATTERNS_DIR / "manifest.json"
LABELS = PATTERNS_DIR / "labels.json"
QUESTIONS = PATTERNS_DIR / "questions.json"
PROTOCOL = PATTERNS_DIR / "protocol.json"

LABELS_SHA256 = "96da1b5a7553096ca38e7f0491692b61018c6735cc70d1dcf5c1afc478f39a7e"
QUESTIONS_SHA256 = "3701e8a2fcaa3ca7bde8ee0c0ac41ff1d7968c589821830944ad335373a7e1bf"
PROTOCOL_SHA256 = "01ed306a0854e19d5e52898224eecb9543859917f193ae3d28adcadfc17bc467"

DISPOSITIONS = frozenset({"redundant", "distinct-by-precondition", "conflicting", "unrelated"})

# The four pairs the corpus annotates (FR-012): the conflict pair, the
# config-redaction trap against the trace-archive page, and each stale page
# against its successor.
ANNOTATED_PAIRS: frozenset[frozenset[str]] = frozenset(
    frozenset(pair)
    for pair in (
        (
            "decisions/balanced-profile-denies-destructive-git-commands.md",
            "decisions/destructive-git-commands-require-confirmation.md",
        ),
        (
            "decisions/config-redaction-is-not-free-text-redaction.md",
            "decisions/trace-archive-reuses-the-ingest-redaction-path.md",
        ),
        (
            "decisions/benchmark-explains-itself-linking-runs-is-a-pipeline-step.md",
            "decisions/benchmark-ui-was-backend-free-one-shot-and-studio-only.md",
        ),
        (
            "decisions/merge-require-green-ci-was-never-read-and-was-removed.md",
            "decisions/merge-require-green-ci-was-never-read.md",
        ),
    )
)


def sha256_of(path: Path) -> str:
    """The file's sha256, lowercase hex."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    """The file's JSON object; anything else is a failure of the freeze."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"{path.name} is not a JSON object")
    return data


class FrozenPatternFilesTest(unittest.TestCase):
    """The three frozen files still hash to their pins and keep their structure."""

    labels: dict[str, Any]
    questions: dict[str, Any]
    protocol: dict[str, Any]
    manifest: dict[str, Any]
    corpus_text: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.labels = load_json(LABELS)
        cls.questions = load_json(QUESTIONS)
        cls.protocol = load_json(PROTOCOL)
        cls.manifest = load_json(MANIFEST)
        cls.corpus_text = CORPUS.read_text(encoding="utf-8")

    def test_files_still_hash_to_their_pinned_values(self) -> None:
        actual = {
            "labels.json": sha256_of(LABELS),
            "questions.json": sha256_of(QUESTIONS),
            "protocol.json": sha256_of(PROTOCOL),
        }
        expected = {
            "labels.json": LABELS_SHA256,
            "questions.json": QUESTIONS_SHA256,
            "protocol.json": PROTOCOL_SHA256,
        }
        self.assertEqual(actual, expected)

    def test_protocol_records_the_frozen_file_hashes(self) -> None:
        self.assertEqual(self.protocol["labels_sha256"], sha256_of(LABELS))
        self.assertEqual(self.protocol["questions_sha256"], sha256_of(QUESTIONS))

    def test_labels_hold_every_pattern_pair_once(self) -> None:
        pages = sorted(entry["path"] for entry in self.manifest["pages"])
        self.assertEqual(len(pages), 14)
        expected = {frozenset(pair) for pair in itertools.combinations(pages, 2)}
        pairs = [frozenset(entry["pair"]) for entry in self.labels["pattern_pairs"]]
        self.assertEqual(len(pairs), 91)
        self.assertEqual(len(set(pairs)), 91)
        self.assertEqual(set(pairs), expected)

    def test_every_pair_uses_one_of_the_four_dispositions(self) -> None:
        for entry in self.labels["pattern_pairs"]:
            with self.subTest(pair=entry["pair"]):
                self.assertEqual(entry["pair"], sorted(entry["pair"]))
                self.assertIn(entry["disposition"], DISPOSITIONS)

    def test_the_annotated_pairs_carry_an_annotation(self) -> None:
        annotated = {
            frozenset(entry["pair"]) for entry in self.labels["pattern_pairs"] if entry["annotation"] is not None
        }
        self.assertEqual(annotated, ANNOTATED_PAIRS)

    def test_questions_quote_the_corpus_copy(self) -> None:
        questions = self.questions["questions"]
        self.assertEqual(len(questions), 12)
        for entry in questions:
            with self.subTest(question=entry["id"]):
                self.assertIn(entry["question"], self.corpus_text)
                self.assertIn(entry["record"], self.corpus_text)

    def test_question_pages_exist_in_the_fixture(self) -> None:
        for entry in self.questions["questions"]:
            with self.subTest(question=entry["id"]):
                for page in entry["gold"]:
                    self.assertTrue((WIKI_DIR / page).is_file(), page)
                for key in ("reuse_target", "trap", "superseded"):
                    value = entry[key]
                    if value is not None:
                        self.assertTrue((WIKI_DIR / value).is_file(), value)


if __name__ == "__main__":
    unittest.main()
