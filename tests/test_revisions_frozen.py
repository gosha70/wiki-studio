# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""US2 freeze: the revision-check study's labels, cases and protocol pinned by sha256 (FR-011).

These files were committed and reviewed by the owner before any candidate code
existed, and are never edited after the US2 phase. The constants below are the
sha256 of the committed files; a change to any of them, or a case file added or
removed, breaks this test. The one exception is a file named exactly
``hunks.json`` directly inside a ``cases/keyword-quoting/<id>/`` directory,
which ``record.py`` alone writes after the freeze (FR-012) and FR-015 checks.
This module is written once and never edited after the US2 phase.
"""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REVISIONS_DIR = REPO_ROOT / "eval" / "revisions"
CASES_DIR = REVISIONS_DIR / "cases"
KEYWORD_QUOTING_DIR = CASES_DIR / "keyword-quoting"
RECORDED_HUNKS_NAME = "hunks.json"

# Paths relative to eval/revisions/, as committed at the freeze.
STUDY_FILE_SHA256: dict[str, str] = {
    "labels.json": "1160ac277ce4bf740140502dc67d038e7d62c023fb085b12578766b9173b9ad5",
    "protocol.json": "3185dc62cb71e5f4522e37e9d2a0c51a87e1e65f4eb096a2c7c959caab4ceedf",
    "README.md": "6ee726317b1a92cc4e905325d17070239839f6755c181e6daa8ef714d074ca2a",
    "pre-successor/merge-require-green-ci-was-never-read.md": (
        "1b4d6dd8acb51b89c51e22585fe6621b4bba9cd3c2bcefa5c5eccd5392ae104f"
    ),
}

# Every file under eval/revisions/cases/ at the freeze (an explicit list).
CASE_FILE_SHA256: dict[str, str] = {
    "cases/benchmark-provider-id/case.json": "c8da512c7bc6c7d61a5af2b2c6e1ff345215017229b3df095a3635fe61afdeed",
    "cases/benchmark-provider-id/page.md": "beb329451d82a5162ed210480cff08b64b5dd6f817dd4381e8f171f79290c160",
    "cases/keyword-quoting/pre-pr-doc-audit/case.json": (
        "5855960255fe82a2c3716a7906838f228597af2423062f937ded595bc4db1567"
    ),
    "cases/keyword-quoting/pre-pr-doc-audit/page.md": (
        "f7448bc62b980bc7117230644e0199e051a65ed2a56e91fd73c7b9e16625eab7"
    ),
    "cases/keyword-quoting/pre-pr-keyword-set/case.json": (
        "e9d0935808debc9b110730d69b99054cdddd1a50b324a4adeefa3149b0fb8039"
    ),
    "cases/keyword-quoting/pre-pr-keyword-set/page.md": (
        "a469f426332bac4760aa552ae7bc2089ca17463daa43df6be9457677cf7ca38b"
    ),
    "cases/keyword-quoting/pre-pr-strict-mode/case.json": (
        "c88cce9cf95316ec615c3a2a82a58e4887579e24b28d710cf830831aca63b669"
    ),
    "cases/keyword-quoting/pre-pr-strict-mode/page.md": (
        "e326f37e422df2925383d8804c4517c93b7ddee1ef5063362d81cdee26426e7d"
    ),
    "cases/provider-config-guarantee/case.json": "c81718a7f3c73ba356464e4d4bf40178bf188c6cc6a0cdc67533126dde1e6a5a",
    "cases/provider-config-guarantee/page.md": "d1fca3aadbf56e910ec0828feed397e7ab0cd39bd6ac2772e61605ba150bfaeb",
    "cases/run-wiki-ingest-rules/case.json": "93792d804c93efa9a720b2393a217042f79a22ba4e91a1d737819dd3d26250f2",
    "cases/run-wiki-ingest-rules/page.md": "0627ed574630959cab0f532db91563921308a61e49363c4843ba00f9b24780bc",
    "cases/vllm-backend-doc/case.json": "cb51f448b1475396e64eb579e82a710cc54a473ea08d6f5711c59fa8e698b3c4",
    "cases/vllm-backend-doc/page.md": "4506f78ebe993596dbe39edb03f5f1321e0216f67f73901f5f35deace3339e9e",
}


def sha256_of(path: Path) -> str:
    """The file's sha256, lowercase hex."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_recorded_hunks(path: Path) -> bool:
    """True only for ``cases/keyword-quoting/<id>/hunks.json``, which ``record.py`` writes after the freeze."""
    return path.name == RECORDED_HUNKS_NAME and path.parent.parent == KEYWORD_QUOTING_DIR


def case_files_present() -> set[str]:
    """Every file under ``cases/`` relative to eval/revisions/, the recorded keyword-quoting hunks excepted."""
    return {
        path.relative_to(REVISIONS_DIR).as_posix()
        for path in CASES_DIR.rglob("*")
        if path.is_file() and not is_recorded_hunks(path)
    }


class FrozenRevisionFilesTest(unittest.TestCase):
    """The frozen study files still hash to their pins, and no case file was added or removed."""

    def test_study_files_still_hash_to_their_pinned_values(self) -> None:
        actual = {name: sha256_of(REVISIONS_DIR / name) for name in STUDY_FILE_SHA256}
        self.assertEqual(actual, STUDY_FILE_SHA256)

    def test_case_files_still_hash_to_their_pinned_values(self) -> None:
        actual = {name: sha256_of(REVISIONS_DIR / name) for name in CASE_FILE_SHA256}
        self.assertEqual(actual, CASE_FILE_SHA256)

    def test_pinned_case_files_are_exactly_the_case_files_present(self) -> None:
        self.assertEqual(case_files_present(), set(CASE_FILE_SHA256))

    def test_only_keyword_quoting_hunks_are_excepted(self) -> None:
        case_dir = KEYWORD_QUOTING_DIR / "pre-pr-strict-mode"
        self.assertTrue(is_recorded_hunks(case_dir / RECORDED_HUNKS_NAME))
        self.assertFalse(is_recorded_hunks(case_dir / "page.md"))
        self.assertFalse(is_recorded_hunks(case_dir / "case.json"))
        self.assertFalse(is_recorded_hunks(KEYWORD_QUOTING_DIR / RECORDED_HUNKS_NAME))
        self.assertFalse(is_recorded_hunks(CASES_DIR / "vllm-backend-doc" / RECORDED_HUNKS_NAME))
        self.assertFalse(is_recorded_hunks(case_dir / "nested" / RECORDED_HUNKS_NAME))


if __name__ == "__main__":
    unittest.main()
