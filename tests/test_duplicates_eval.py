# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""US5: the near-duplicate scorer on synthetic inputs (issue 121, FR-022).

Each test writes a small corpus, labels and a protocol to a temporary directory; the protocol is the frozen
``protocol.json`` with its two input hashes replaced by the synthetic files' hashes, so the rules under test are the
frozen rules. Covered: each B1 rule alone against B0; the threshold at exactly one quarter, just below it and on two
empty token sets; every edge of the bar; selection by fewest false candidates and the tie to B0; the counts by scope
and by repository; the refusal on a changed input, writing nothing; ``eval/duplicates/`` unchanged by a run with
``--out-dir`` elsewhere; and ``--help``. The committed results are checked in US6, not here.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from eval.duplicates import candidates
from eval.duplicates.extract import CORPUS_DIR_NAME, CORPUS_JSON_NAME
from eval.duplicates.sample import LABELS_NAME

REPO_ROOT = Path(__file__).resolve().parents[1]
DUPLICATES_DIR = REPO_ROOT / "eval" / "duplicates"
CACHE_DIR_NAME = "__pycache__"

CCT = "code-copilot-team"
MK = "memkernel"
ROUTING_A = "code-copilot-team/routing/a.md"
ROUTING_B = "code-copilot-team/routing/b.md"
PI_C = "code-copilot-team/pi/c.md"
MEMKERNEL_D = "memkernel/memkernel/d.md"
WITHIN = "within-family"
CROSS_FAMILY = "cross-family"
CROSS_REPOSITORY = "cross-repository"

PageSpec = tuple[str, str, str, str]


def load_protocol() -> dict[str, Any]:
    document: dict[str, Any] = json.loads((DUPLICATES_DIR / candidates.PROTOCOL_NAME).read_text(encoding="utf-8"))
    return document


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, document: Any) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def page_text(title: str, paragraph: str) -> str:
    return (
        f"---\npage_type: decision\nslug: page\ntitle: '{title}'\nstatus: stable\n---\n\n## Decision\n\n{paragraph}\n"
    )


def write_study(
    root: Path,
    pages: dict[str, PageSpec],
    pairs: list[dict[str, Any]],
    cross_pairs: list[dict[str, Any]],
) -> Path:
    """A synthetic study directory: ``pages`` maps a path under ``corpus/`` to repository, family, title, paragraph."""
    directory = root / "duplicates"
    entries = []
    for page, (repository, family, title, paragraph) in sorted(pages.items()):
        path = directory / CORPUS_DIR_NAME / page
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page_text(title, paragraph), encoding="utf-8")
        entries.append({"page": page, "repository": repository, "family": family})
    write_json(directory / CORPUS_JSON_NAME, {"pages": entries})
    write_json(directory / LABELS_NAME, {"pairs": pairs, "cross_pairs": cross_pairs})
    protocol = load_protocol()
    protocol[candidates.CORPUS_SHA256_KEY] = sha256_of(directory / CORPUS_JSON_NAME)
    protocol[candidates.LABELS_SHA256_KEY] = sha256_of(directory / LABELS_NAME)
    write_json(directory / candidates.PROTOCOL_NAME, protocol)
    return directory


def run(directory: Path | None, out_dir: Path) -> tuple[int, str]:
    """``candidates.main`` with ``--out-dir``; the exit code and what it wrote to stderr."""
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = candidates.main(["--out-dir", str(out_dir)], duplicates_dir=directory)
    return code, stderr.getvalue()


def read_result(out_dir: Path, name: str = candidates.CANDIDATES_NAME) -> dict[str, Any]:
    document: dict[str, Any] = json.loads((out_dir / name).read_text(encoding="utf-8"))
    return document


def snapshot(directory: Path) -> dict[str, str]:
    """Path and sha256 of every file under ``directory``, bytecode caches left out (they are never committed)."""
    return {
        path.relative_to(directory).as_posix(): sha256_of(path)
        for path in sorted(directory.rglob("*"))
        if path.is_file() and CACHE_DIR_NAME not in path.parts
    }


class NormalisationTest(unittest.TestCase):
    """Each B1 rule alone: B0 keeps the token, B1 drops it (or both keep it)."""

    def setUp(self) -> None:
        built = {candidate.name: candidate for candidate in candidates.candidates_from_protocol(load_protocol())}
        self.b0 = built["B0"]
        self.b1 = built["B1"]

    def assert_dropped(self, text: str, *tokens: str) -> None:
        b0, b1 = self.b0.tokens(text, ""), self.b1.tokens(text, "")
        for token in tokens:
            with self.subTest(token=token):
                self.assertIn(token, b0)
                self.assertNotIn(token, b1)

    def assert_kept(self, text: str, *tokens: str) -> None:
        b1 = self.b1.tokens(text, "")
        for token in tokens:
            with self.subTest(token=token):
                self.assertIn(token, b1)

    def test_a_link_keeps_its_text_and_loses_its_target(self) -> None:
        text = "[keeper words](https://example.com/target-page)"
        self.assert_dropped(text, "https", "example", "com", "target-page")
        self.assertEqual(self.b1.tokens(text, ""), {"keeper", "words"})

    def test_an_image_link_keeps_its_text_and_loses_its_target(self) -> None:
        text = "![diagram label](images/flow-chart.png)"
        self.assert_dropped(text, "images", "flow-chart", "png")
        self.assertEqual(self.b1.tokens(text, ""), {"diagram", "label"})

    def test_a_bare_url_is_removed(self) -> None:
        text = "see https://example.org/some-path then"
        self.assert_dropped(text, "https", "example", "org", "some-path")
        self.assertEqual(self.b1.tokens(text, ""), {"see", "then"})

    def test_a_digits_only_token_is_dropped(self) -> None:
        self.assert_dropped("released 2026 build 12", "2026", "12")
        self.assert_kept("released 2026 build 12", "released", "build")

    def test_a_hex_token_with_a_digit_is_dropped_and_one_without_is_kept(self) -> None:
        self.assert_dropped("commit abc1234", "abc1234")
        self.assert_kept("word deadbee", "deadbee")

    def test_each_template_word_is_dropped(self) -> None:
        self.assert_dropped("context we chose over reason", "context", "we", "chose", "over", "reason")
        self.assertEqual(self.b1.tokens("context we chose over reason", "kept"), {"kept"})

    def test_item_labels_are_dropped(self) -> None:
        self.assert_dropped(
            "d6 e3 t12 g5 fr-012 adr-1 us2 nfr-3", "d6", "e3", "t12", "g5", "fr-012", "adr-1", "us2", "nfr-3"
        )

    def test_identifier_shaped_content_words_are_kept(self) -> None:
        self.assert_kept(
            "d-upsert-key s3x sha256 bm25 utf-8 t123", "d-upsert-key", "s3x", "sha256", "bm25", "utf-8", "t123"
        )

    def test_b0_is_the_issue_54_token_set(self) -> None:
        self.assertEqual(self.b0.tokens("A title", "the first paragraph"), {"title", "first", "paragraph"})


class ThresholdTest(unittest.TestCase):
    """Jaccard at least one quarter, in integers, and never on an empty union."""

    threshold = candidates.threshold_of(load_protocol())

    def test_exactly_one_quarter_is_a_candidate(self) -> None:
        self.assertTrue(candidates.is_candidate(1, 4, self.threshold))
        self.assertTrue(candidates.is_candidate(5, 20, self.threshold))

    def test_just_below_one_quarter_is_not(self) -> None:
        self.assertFalse(candidates.is_candidate(1, 5, self.threshold))
        self.assertFalse(candidates.is_candidate(4, 17, self.threshold))

    def test_two_empty_token_sets_are_not(self) -> None:
        self.assertFalse(candidates.is_candidate(0, 0, self.threshold))

    def test_end_to_end_the_quarter_pair_alone_is_a_candidate(self) -> None:
        pages = {
            "code-copilot-team/routing/x.md": (CCT, "routing", "alpha", "beta"),
            "code-copilot-team/routing/y.md": (CCT, "routing", "alpha", "gamma delta"),
            "code-copilot-team/routing/z.md": (CCT, "routing", "alpha", "epsilon zeta eta"),
            "code-copilot-team/routing/e1.md": (CCT, "routing", "", ""),
            "code-copilot-team/routing/e2.md": (CCT, "routing", "", ""),
        }
        with tempfile.TemporaryDirectory() as tmp:
            directory = write_study(Path(tmp), pages, [], [])
            code, _ = run(directory, Path(tmp) / "out")
            self.assertEqual(code, 0)
            result = read_result(Path(tmp) / "out")
        expected = ["code-copilot-team/routing/x.md code-copilot-team/routing/y.md 1/4 unrelated within-family"]
        for name in ("B0", "B1"):
            with self.subTest(candidate=name):
                self.assertEqual(result["candidates"][name]["candidate_pairs"], expected)


class BarTest(unittest.TestCase):
    """Every edge of the bar's three conditions."""

    bar = load_protocol()["bar"]

    def test_seven_true_pairs_are_not_testable(self) -> None:
        verdict = candidates.bar_verdict(7, 7, 7, 0, self.bar)
        self.assertFalse(verdict["enough_true_pairs"])
        self.assertEqual(verdict["overall"], candidates.NOT_TESTABLE)

    def test_eight_true_pairs_with_six_found_pass_recall(self) -> None:
        verdict = candidates.bar_verdict(6, 8, 6, 0, self.bar)
        self.assertTrue(verdict["enough_true_pairs"])
        self.assertTrue(verdict["recall"])
        self.assertEqual(verdict["overall"], candidates.PASS)

    def test_eight_true_pairs_with_five_found_fail_recall(self) -> None:
        verdict = candidates.bar_verdict(5, 8, 5, 0, self.bar)
        self.assertFalse(verdict["recall"])
        self.assertEqual(verdict["overall"], candidates.FAIL)

    def test_false_equal_to_true_passes_the_ratio(self) -> None:
        verdict = candidates.bar_verdict(6, 8, 6, 6, self.bar)
        self.assertTrue(verdict["false_not_above_true"])
        self.assertEqual(verdict["overall"], candidates.PASS)

    def test_one_false_more_than_true_fails_the_ratio(self) -> None:
        verdict = candidates.bar_verdict(6, 8, 6, 7, self.bar)
        self.assertFalse(verdict["false_not_above_true"])
        self.assertEqual(verdict["overall"], candidates.FAIL)


class SelectionTest(unittest.TestCase):
    """Fewest false candidates among the passing candidates; a tie goes to B0."""

    protocol = load_protocol()

    def results(self, b0: tuple[str, int], b1: tuple[str, int]) -> dict[str, Any]:
        return {
            "B0": {"bar": {"overall": b0[0]}, "false_candidates": b0[1]},
            "B1": {"bar": {"overall": b1[0]}, "false_candidates": b1[1]},
        }

    def test_fewest_false_candidates_wins(self) -> None:
        verdict, winner = candidates.select(self.protocol, self.results((candidates.PASS, 5), (candidates.PASS, 3)))
        self.assertEqual((verdict, winner), ("winner", "B1"))

    def test_a_tie_goes_to_b0(self) -> None:
        verdict, winner = candidates.select(self.protocol, self.results((candidates.PASS, 3), (candidates.PASS, 3)))
        self.assertEqual((verdict, winner), ("winner", "B0"))

    def test_a_failing_candidate_never_wins(self) -> None:
        verdict, winner = candidates.select(self.protocol, self.results((candidates.PASS, 9), (candidates.FAIL, 1)))
        self.assertEqual((verdict, winner), ("winner", "B0"))

    def test_no_passing_candidate(self) -> None:
        verdict, winner = candidates.select(self.protocol, self.results((candidates.FAIL, 1), (candidates.FAIL, 1)))
        self.assertEqual((verdict, winner), ("no candidate clears the bar", candidates.WINNER_NONE))

    def test_not_testable(self) -> None:
        not_testable = candidates.NOT_TESTABLE
        verdict, winner = candidates.select(self.protocol, self.results((not_testable, 0), (not_testable, 0)))
        self.assertEqual((verdict, winner), ("not testable", candidates.WINNER_NONE))


class ScopeTest(unittest.TestCase):
    """Four pages with the same text, so every pair is a candidate: scopes, repositories and the files written."""

    pages: dict[str, PageSpec] = {
        ROUTING_A: (CCT, "routing", "Shared words", "alpha beta gamma"),
        ROUTING_B: (CCT, "routing", "Shared words", "alpha beta gamma"),
        PI_C: (CCT, "pi", "Shared words", "alpha beta gamma"),
        MEMKERNEL_D: (MK, MK, "Shared words", "alpha beta gamma"),
    }
    pairs = [{"pair": [ROUTING_A, ROUTING_B], "group": "g", "disposition": "redundant", "reason": "same"}]
    cross_pairs = [
        {"pair": [PI_C, ROUTING_A], "scope": CROSS_FAMILY, "disposition": "companion", "reason": "kept apart"},
        {"pair": [ROUTING_B, MEMKERNEL_D], "scope": CROSS_REPOSITORY, "disposition": "supersedes", "reason": "later"},
    ]

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.directory = write_study(self.root, self.pages, self.pairs, self.cross_pairs)
        self.out_dir = self.root / "out"

    def test_counts_by_scope_and_repository(self) -> None:
        code, _ = run(self.directory, self.out_dir)
        self.assertEqual(code, 0)
        result = read_result(self.out_dir)
        self.assertEqual(result["pages"], 4)
        self.assertEqual(result["pairs"], {"total": 6, "by_scope": {WITHIN: 1, CROSS_FAMILY: 2, CROSS_REPOSITORY: 3}})
        self.assertEqual(
            result["true_pairs"],
            {
                "total": 2,
                "by_disposition": {"redundant": 1, "conflicting": 0, "supersedes": 1},
                "by_scope": {WITHIN: 1, CROSS_FAMILY: 0, CROSS_REPOSITORY: 1},
            },
        )
        for name in ("B0", "B1"):
            with self.subTest(candidate=name):
                view = result["candidates"][name]
                self.assertEqual((view["true_candidates"], view["false_candidates"]), (2, 4))
                self.assertEqual(view["found_out_of_n"], candidates.NOT_TESTABLE)
                self.assertEqual(
                    view["false_by_disposition"], {"companion": 1, "distinct-by-precondition": 0, "unrelated": 3}
                )
                self.assertEqual(
                    view["by_scope"],
                    {
                        WITHIN: {"true": 1, "false": 0},
                        CROSS_FAMILY: {"true": 0, "false": 2},
                        CROSS_REPOSITORY: {"true": 1, "false": 2},
                    },
                )
                self.assertEqual(
                    view["by_repository"],
                    {
                        CCT: {"true": 1, "false": 2},
                        MK: {"true": 0, "false": 0},
                        CROSS_REPOSITORY: {"true": 1, "false": 2},
                    },
                )
                self.assertEqual(view["false_per_100_pages"], "100.00")
                self.assertEqual(view["bar"]["overall"], candidates.NOT_TESTABLE)
                self.assertEqual(len(view["candidate_pairs"]), 6)
                self.assertIn(f"{ROUTING_A} {ROUTING_B} 5/5 redundant {WITHIN}", view["candidate_pairs"])
                self.assertIn(f"{PI_C} {MEMKERNEL_D} 5/5 unrelated {CROSS_REPOSITORY}", view["candidate_pairs"])
        self.assertEqual(
            result["true_pair_scores"],
            [
                f"{ROUTING_A} {ROUTING_B} redundant {WITHIN} B0 5/5 found B1 5/5 found",
                f"{ROUTING_B} {MEMKERNEL_D} supersedes {CROSS_REPOSITORY} B0 5/5 found B1 5/5 found",
            ],
        )
        self.assertEqual((result["verdict"], result["winner"]), ("not testable", candidates.WINNER_NONE))
        self.assertEqual(result["winner_line"], "Winner: none")
        timing = read_result(self.out_dir, candidates.TIMING_NAME)
        self.assertEqual((timing["pages"], timing["pairs"]), (4, 6))
        self.assertEqual(set(timing["seconds"]), {"B0", "B1"})
        self.assertIn("readings", read_result(self.out_dir, candidates.SECONDARY_NAME))

    def test_two_runs_write_the_same_candidates_and_secondary(self) -> None:
        first, second = self.root / "first", self.root / "second"
        self.assertEqual(run(self.directory, first)[0], 0)
        self.assertEqual(run(self.directory, second)[0], 0)
        for name in (candidates.CANDIDATES_NAME, candidates.SECONDARY_NAME):
            with self.subTest(file=name):
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())

    def test_a_changed_labels_file_is_refused_and_nothing_is_written(self) -> None:
        labels = self.directory / LABELS_NAME
        expected = sha256_of(labels)
        labels.write_text(labels.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        before = snapshot(self.directory)
        code, stderr = run(self.directory, self.out_dir)
        self.assertEqual(code, candidates.REFUSED)
        self.assertFalse(self.out_dir.exists())
        self.assertIn(sha256_of(labels), stderr)
        self.assertIn(expected, stderr)
        self.assertEqual(snapshot(self.directory), before)

    def test_a_changed_corpus_file_is_refused_and_nothing_is_written(self) -> None:
        corpus = self.directory / CORPUS_JSON_NAME
        corpus.write_text(corpus.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        code, stderr = run(self.directory, self.out_dir)
        self.assertEqual(code, candidates.REFUSED)
        self.assertFalse(self.out_dir.exists())
        self.assertIn(sha256_of(corpus), stderr)


class StudyDirectoryTest(unittest.TestCase):
    """A run on the study's own inputs with ``--out-dir`` elsewhere leaves ``eval/duplicates/`` as it was."""

    def test_eval_duplicates_is_unchanged_by_a_run_elsewhere(self) -> None:
        before = snapshot(DUPLICATES_DIR)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "results"
            code, stderr = run(None, out_dir)
            self.assertEqual(code, 0, stderr)
            written = sorted(path.name for path in out_dir.iterdir())
        self.assertEqual(snapshot(DUPLICATES_DIR), before)
        self.assertEqual(
            written, sorted((candidates.CANDIDATES_NAME, candidates.SECONDARY_NAME, candidates.TIMING_NAME))
        )


class HelpTest(unittest.TestCase):
    def test_help_exits_zero(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(candidates.main(["--help"]), 0)


if __name__ == "__main__":
    unittest.main()
