# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""US4 freeze: the near-duplicate study's corpus, labels, protocol, review sample and README pinned (FR-019).

These files were committed before any candidate code existed; the labels were reviewed by the owner first. The
constants below are the sha256 of the committed files, computed in a shell, not in Python. Every page under
``corpus/`` is pinned through its entry in the pinned ``corpus.json``, and the pages present must equal the entries.
``protocol.json``'s ``corpus_sha256`` and ``labels_sha256`` and ``labels.json``'s ``corpus_sha256`` must equal the
frozen files' hashes. This module is written once and never edited after the US4 phase.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DUPLICATES_DIR = REPO_ROOT / "eval" / "duplicates"
CORPUS_DIR = DUPLICATES_DIR / "corpus"
CORPUS_JSON = "corpus.json"
LABELS_JSON = "labels.json"
PROTOCOL_JSON = "protocol.json"

# Paths relative to eval/duplicates/, as committed at the freeze.
FROZEN_FILE_SHA256: dict[str, str] = {
    CORPUS_JSON: "fc0f710ab994dd4a57a9bb23e700bd61b2ffde58f66a54bb30353c6cc5bbc4de",
    LABELS_JSON: "e1c34ca9533aedb39482d628fd8704752035fba3ca34f132d730f8a555082287",
    PROTOCOL_JSON: "5daac7f4605038fc98284cd0e055aecdc33459cd4a51aa24b1cdc1e4e9ddde51",
    "review-sample.json": "c06bd5a8807c5ec4105f2f651e9b156b72ed66ea15c3f1bbe34d64c3ea35a8ea",
    "README.md": "ac194276860ffe72b290afb1a174217455d234b55e46b73509d3a572bde53e26",
}


def sha256_of(path: Path) -> str:
    """The file's sha256, lowercase hex."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict[str, Any]:
    document: dict[str, Any] = json.loads((DUPLICATES_DIR / name).read_text(encoding="utf-8"))
    return document


class FrozenDuplicateFilesTest(unittest.TestCase):
    """The frozen study files still hash to their pins, every page to its entry, and the recorded hashes agree."""

    def test_frozen_files_still_hash_to_their_pinned_values(self) -> None:
        actual = {name: sha256_of(DUPLICATES_DIR / name) for name in FROZEN_FILE_SHA256}
        self.assertEqual(actual, FROZEN_FILE_SHA256)

    def test_every_page_hashes_to_its_corpus_entry(self) -> None:
        for entry in load(CORPUS_JSON)["pages"]:
            with self.subTest(page=entry["page"]):
                self.assertEqual(sha256_of(CORPUS_DIR / entry["page"]), entry["sha256"])

    def test_the_pages_present_are_exactly_the_entries(self) -> None:
        present = {path.relative_to(CORPUS_DIR).as_posix() for path in CORPUS_DIR.rglob("*") if path.is_file()}
        entries = [entry["page"] for entry in load(CORPUS_JSON)["pages"]]
        self.assertEqual(len(entries), len(set(entries)))
        self.assertEqual(present, set(entries))

    def test_protocol_records_the_frozen_corpus_and_labels(self) -> None:
        protocol = load(PROTOCOL_JSON)
        self.assertEqual(protocol["corpus_sha256"], FROZEN_FILE_SHA256[CORPUS_JSON])
        self.assertEqual(protocol["labels_sha256"], FROZEN_FILE_SHA256[LABELS_JSON])

    def test_labels_record_the_frozen_corpus(self) -> None:
        self.assertEqual(load(LABELS_JSON)["corpus_sha256"], FROZEN_FILE_SHA256[CORPUS_JSON])


if __name__ == "__main__":
    unittest.main()
