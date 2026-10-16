# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The navigation evaluation is deterministic and its fixture is the preregistered one (0.3.0 FR-002, FR-007).

No backend runs here. The script's output must equal the committed
``results.json``; a change to the querier's selection that moves any number
has to update that file in the same commit, which makes the change visible.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from eval.navigation import run
from wiki_studio.lint import lint_wiki

FIXTURE = Path(__file__).resolve().parents[1] / "eval" / "navigation"
RUN2 = FIXTURE / "run2"
# Run 2 (spec US5) shares run 1's corpus, questions and stop list and is asserted once it exists.
RUNS: list[tuple[str, Path, Path]] = [("run1", FIXTURE, FIXTURE)]
if (RUN2 / "results.json").is_file():
    RUNS.append(("run2", RUN2, FIXTURE))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestFixtureIsThePreregisteredOne(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))

    def test_questions_and_stop_list_match_the_manifest(self) -> None:
        self.assertEqual(_sha256(FIXTURE / "questions.json"), self.manifest["questions_sha256"])
        self.assertEqual(_sha256(FIXTURE / "stopwords.txt"), self.manifest["stopwords_sha256"])
        self.assertIsNotNone(self.manifest["questions_commit"])

    def test_corpus_matches_the_manifest(self) -> None:
        for entry in self.manifest["corpus_files"]:
            with self.subTest(path=entry["path"]):
                self.assertEqual(_sha256(FIXTURE / "corpus" / entry["path"]), entry["sha256"])

    def test_stop_list_is_the_queriers(self) -> None:
        from wiki_studio.wiki_state import _STOPWORDS

        self.assertEqual(
            run.load_stopwords(FIXTURE / "stopwords.txt"),
            _STOPWORDS,
            "the querier's stop list changed after the fixture was frozen: keep stopwords.txt as it is "
            "(FR-006) and record the divergence in eval/navigation/manifest.json instead",
        )

    def test_missing_gold_entry_is_a_clear_error(self) -> None:
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "fixture"
            shutil.copytree(FIXTURE, copy, ignore=shutil.ignore_patterns("proposals", "ingest-logs", "__pycache__"))
            gold = [g for g in json.loads((copy / "gold.json").read_text(encoding="utf-8")) if g["id"] != "q01"]
            (copy / "gold.json").write_text(json.dumps(gold), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                run.compute(copy)
        self.assertIn("q01", str(ctx.exception))

    def test_every_question_has_a_gold_entry_with_a_reason(self) -> None:
        questions = json.loads((FIXTURE / "questions.json").read_text(encoding="utf-8"))
        gold = {g["id"]: g for g in json.loads((FIXTURE / "gold.json").read_text(encoding="utf-8"))}
        self.assertEqual({q["id"] for q in questions}, set(gold))
        for q in questions:
            with self.subTest(id=q["id"]):
                self.assertTrue(gold[q["id"]]["reason"].strip())
                if q["kind"] == run.KIND_ABSENT:
                    self.assertIsNone(gold[q["id"]]["gold"])

    def test_frozen_wiki_lints_clean(self) -> None:
        self.assertEqual(lint_wiki(FIXTURE / "wiki"), [])


class TestResultsAreReproduced(unittest.TestCase):
    def test_script_output_equals_committed_results(self) -> None:
        for name, fixture, shared in RUNS:
            with self.subTest(run=name):
                committed = json.loads((fixture / "results.json").read_text(encoding="utf-8"))
                self.assertEqual(run.compute(fixture, shared_dir=shared), committed)

    def test_compute_is_stable_across_runs(self) -> None:
        for name, fixture, shared in RUNS:
            with self.subTest(run=name):
                self.assertEqual(run.compute(fixture, shared_dir=shared), run.compute(fixture, shared_dir=shared))

    def test_run2_shares_run1_inputs_unchanged(self) -> None:
        # FR-013: run 2 records the shared files' checksums and they equal run 1's manifest values.
        if not (RUN2 / "manifest.json").is_file():
            self.skipTest("run 2 has not been recorded yet (spec US5)")
        run1 = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
        run2 = json.loads((RUN2 / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(run2["questions_sha256"], run1["questions_sha256"])
        self.assertEqual(run2["stopwords_sha256"], run1["stopwords_sha256"])
        self.assertEqual(run2["corpus_files"], run1["corpus_files"])
        self.assertTrue(run2["isolation_probe"]["passed"])
        self.assertEqual(run2["ingest"]["summary"]["documents_attempted"], len(run1["corpus_files"]))
        self.assertTrue(all(d["attempts"] == 1 or d["transport_error"] for d in run2["ingest"]["documents"]))
        for shared in ("corpus", "questions.json", "stopwords.txt"):
            self.assertFalse((RUN2 / shared).exists(), f"run 2 must use run 1's {shared} in place, not a copy")


class TestIndexOnlyAnswers(unittest.TestCase):
    def test_index_only_gold_counts_for_words_but_not_for_hits(self) -> None:
        # FR-004: excluded from the hit rates (the index is always loaded); FR-006: words still counted.
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "fixture"
            shutil.copytree(FIXTURE, copy, ignore=shutil.ignore_patterns("proposals", "ingest-logs", "__pycache__"))
            gold = json.loads((copy / "gold.json").read_text(encoding="utf-8"))
            for g in gold:
                if g["id"] == "q11":
                    g["gold"] = run.INDEX_NAME
            (copy / "gold.json").write_text(json.dumps(gold), encoding="utf-8")
            result = run.compute(copy)
        q11 = next(e for e in result["per_question"] if e["id"] == "q11")
        self.assertEqual(q11["excluded_reason"], "answered_by_index")
        self.assertIsNone(q11["hit_at_1"])
        self.assertGreater(q11["wiki_words"], 0)
        self.assertGreater(q11["grep_words"], 0)
        self.assertEqual(result["navigation"]["answered_by_index"], ["q11"])
        self.assertEqual(result["navigation"]["evaluated"], 2)
        self.assertEqual(result["words"]["evaluated"], 3)
        self.assertEqual(result["counts"]["with_gold"], 3)


class TestGrepRule(unittest.TestCase):
    def test_question_words_use_the_queriers_pattern_and_stop_list(self) -> None:
        words = run.question_words("What does `get` return for a page_type export?", frozenset({"what", "for"}))
        self.assertEqual(words, ["does", "get", "return", "page", "type", "export"])

    def test_context_windows_merge(self) -> None:
        self.assertEqual(run._merge_ranges([3, 4, 10], last_line=20), [(1, 6), (8, 12)])
        self.assertEqual(run._merge_ranges([0], last_line=0), [(0, 0)])

    def test_count_words_is_whitespace_split(self) -> None:
        self.assertEqual(run.count_words("a  b\nc\t d "), 4)

    def test_shared_inputs_resolve_to_run1_when_the_fixture_lacks_them(self) -> None:
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            run2 = Path(tmp) / "run2"
            shutil.copytree(FIXTURE / "wiki", run2 / "wiki")
            shutil.copy(FIXTURE / "gold.json", run2 / "gold.json")
            self.assertEqual(run.compute(run2, shared_dir=FIXTURE), run.compute(FIXTURE))
            with self.assertRaises(FileNotFoundError):
                run.compute(run2)

    def test_main_rejects_extra_arguments(self) -> None:
        import contextlib
        import io

        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(run.main(["one", "two"]), 2)
        self.assertIn("usage", err.getvalue())


if __name__ == "__main__":
    unittest.main()
