# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""US6: the near-duplicate study's committed results and report (issue 121, FR-024, FR-025).

The scorer, rerun into a temporary directory, writes ``candidates.json`` and ``secondary.json`` equal to the committed
files byte for byte and leaves ``eval/duplicates/`` unchanged; ``timing.json`` has its keys (its values are never
compared with a rerun). ``report.md`` holds exactly one winner line, equal to the results' winner, and states the
recorded figures; the secondary B0 reading as recorded equals the frozen issue 54 signal (b) counts; every
``python -m eval.duplicates.…`` line in the README and the report parses with its script's parser.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import re
import shlex
import tempfile
import unittest
from pathlib import Path
from typing import Any, ClassVar

from eval.duplicates import candidates, extract, sample

REPO_ROOT = Path(__file__).resolve().parents[1]
DUPLICATES_DIR = REPO_ROOT / "eval" / "duplicates"
RESULTS_DIR = DUPLICATES_DIR / candidates.RESULTS_DIR_NAME
REPORT = DUPLICATES_DIR / "report.md"
README = DUPLICATES_DIR / "README.md"
ISSUE_54_RESULTS = REPO_ROOT / "eval" / "patterns" / "results" / "duplicates.json"
CACHE_DIR_NAME = "__pycache__"

WINNER_PREFIX = "Winner: "
VERDICT_LINE = "**Verdict:** {verdict}."
COMMAND_RE = re.compile(r"python -m (eval\.duplicates\.\w+)([^`\n]*)")
SCRIPTS = {
    "eval.duplicates.extract": extract,
    "eval.duplicates.sample": sample,
    "eval.duplicates.candidates": candidates,
}
TIMING_KEYS = {"clock", "pages", "pairs", "seconds", "study"}
SECONDS_FORMAT = "{:.3f} s"
RECORDED_READING = "as recorded"
YES, NO = "yes", "no"
NOT_A_CANDIDATE = "not a candidate"
BAR_KEYS = ("enough_true_pairs", "recall", "false_not_above_true")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_tree(root: Path) -> dict[str, str]:
    """Every file under ``root`` with its sha256, keyed by POSIX relative path (bytecode excluded)."""
    return {
        path.relative_to(root).as_posix(): sha256_of(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and CACHE_DIR_NAME not in path.parts
    }


def row(*cells: object) -> str:
    return "| " + " | ".join(str(cell) for cell in cells) + " |"


def yes_no(value: bool) -> str:
    return YES if value else NO


def pair_cell(left: str, right: str) -> str:
    return f"`{left}` and `{right}`"


class RecordedResultsTest(unittest.TestCase):
    """The committed results, a rerun of the scorer and the report agree (FR-025)."""

    committed: ClassVar[dict[str, Any]]
    protocol: ClassVar[dict[str, Any]]
    report: ClassVar[str]
    rerun_dir: ClassVar[Path]
    before: ClassVar[dict[str, str]]
    after: ClassVar[dict[str, str]]
    exit_code: ClassVar[int]
    _tmp: ClassVar[tempfile.TemporaryDirectory[str]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.committed = load_json(RESULTS_DIR / candidates.CANDIDATES_NAME)
        cls.protocol = load_json(DUPLICATES_DIR / candidates.PROTOCOL_NAME)
        cls.report = REPORT.read_text(encoding="utf-8")
        cls._tmp = tempfile.TemporaryDirectory()
        cls.rerun_dir = Path(cls._tmp.name) / candidates.RESULTS_DIR_NAME
        cls.before = snapshot_tree(DUPLICATES_DIR)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            cls.exit_code = candidates.main(["--out-dir", str(cls.rerun_dir)])
        cls.after = snapshot_tree(DUPLICATES_DIR)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_the_scorer_equals_the_committed_results_byte_for_byte(self) -> None:
        self.assertEqual(self.exit_code, 0)
        for name in (candidates.CANDIDATES_NAME, candidates.SECONDARY_NAME):
            with self.subTest(file=name):
                self.assertEqual((self.rerun_dir / name).read_bytes(), (RESULTS_DIR / name).read_bytes())

    def test_the_rerun_leaves_the_study_directory_unchanged(self) -> None:
        self.assertEqual(self.after, self.before)

    def test_timing_has_its_keys(self) -> None:
        for directory in (RESULTS_DIR, self.rerun_dir):
            with self.subTest(directory=directory.name):
                timing = load_json(directory / candidates.TIMING_NAME)
                self.assertEqual(set(timing), TIMING_KEYS)
                self.assertEqual(set(timing["seconds"]), set(self.protocol["candidates"]["order"]))
                self.assertEqual(timing["pages"], self.committed["pages"])
                self.assertEqual(timing["pairs"], self.committed["pairs"]["total"])

    def test_the_report_has_exactly_one_winner_line_equal_to_the_results(self) -> None:
        lines = [line for line in self.report.splitlines() if line.startswith(WINNER_PREFIX)]
        self.assertEqual(lines, [self.committed["winner_line"]])
        self.assertEqual(lines, [f"{WINNER_PREFIX}{self.committed['winner']}"])
        self.assertEqual(lines, [self.protocol["winner_lines"][self.committed["winner"]]])

    def test_the_report_states_the_verdict(self) -> None:
        self.assertIn(VERDICT_LINE.format(verdict=self.committed["verdict"]), self.report.splitlines())

    def test_the_report_states_each_candidates_figures_as_recorded(self) -> None:
        splits = self.protocol["reporting_splits"]
        expected: list[str] = []
        for name, result in self.committed["candidates"].items():
            bar = result["bar"]
            expected.append(
                row(
                    name,
                    result["found_out_of_n"],
                    result["true_candidates"],
                    result["false_candidates"],
                    result["false_per_100_pages"],
                    bar["overall"],
                )
            )
            expected.append(row(name, *(yes_no(bar[key]) for key in BAR_KEYS), bar["overall"]))
            expected.append(row(name, *(result["false_by_disposition"][label] for label in splits["by_disposition"])))
            for split in ("by_scope", "by_repository"):
                cells = [result[split][key][side] for key in splits[split] for side in ("true", "false")]
                expected.append(row(name, *cells))
        missing = [line for line in expected if line not in self.report.splitlines()]
        self.assertEqual(missing, [], "the report's tables must state the recorded figures")

    def test_the_report_lists_every_candidate_pair_as_recorded(self) -> None:
        order = list(self.protocol["candidates"]["order"])
        scored: dict[tuple[str, str], dict[str, str]] = {}
        details: dict[tuple[str, str], tuple[str, str]] = {}
        for name in order:
            for line in self.committed["candidates"][name]["candidate_pairs"]:
                left, right, score, label, scope = line.split(" ")
                scored.setdefault((left, right), {})[name] = score
                details[(left, right)] = (label, scope)
        self.assertTrue(scored)
        for (left, right), scores in sorted(scored.items()):
            label, scope = details[(left, right)]
            line = row(pair_cell(left, right), label, scope, *(scores.get(name, NOT_A_CANDIDATE) for name in order))
            with self.subTest(pair=(left, right)):
                self.assertIn(line, self.report.splitlines())

    def test_the_report_states_the_true_pairs_scores_as_recorded(self) -> None:
        order = list(self.protocol["candidates"]["order"])
        for line in self.committed["true_pair_scores"]:
            left, right, label, scope, *rest = line.split(" ")
            cells = {rest[i]: f"{rest[i + 1]} {rest[i + 2]}" for i in range(0, len(rest), 3)}
            expected = row(pair_cell(left, right), label, scope, *(cells[name] for name in order))
            with self.subTest(pair=(left, right)):
                self.assertIn(expected, self.report.splitlines())

    def test_the_report_states_the_secondary_counts_as_recorded(self) -> None:
        secondary = load_json(RESULTS_DIR / candidates.SECONDARY_NAME)
        self.assertIs(secondary["binding"], False)
        order = list(self.protocol["candidates"]["order"])
        for reading, view in secondary["readings"].items():
            cells = [view[name][key] for name in order for key in ("found", "false_candidates")]
            with self.subTest(reading=reading):
                self.assertIn(row(reading, view["true_pairs"], *cells), self.report.splitlines())

    def test_the_report_states_the_recorded_wall_times(self) -> None:
        timing = load_json(RESULTS_DIR / candidates.TIMING_NAME)
        for name, seconds in timing["seconds"].items():
            with self.subTest(candidate=name):
                self.assertIn(SECONDS_FORMAT.format(seconds), self.report)

    def test_secondary_b0_as_recorded_equals_the_frozen_issue_54_signal_b(self) -> None:
        recorded = load_json(RESULTS_DIR / candidates.SECONDARY_NAME)["readings"][RECORDED_READING]
        frozen = load_json(ISSUE_54_RESULTS)["signals"]["b"]["counts"]
        self.assertEqual(recorded["true_pairs"], frozen["eligible_labelled_pairs"])
        self.assertEqual(recorded["B0"]["found"], frozen["found_labelled_pairs"])
        self.assertEqual(recorded["B0"]["false_candidates"], frozen["false_candidates"])


class ShownCommandsTest(unittest.TestCase):
    """Every ``python -m eval.duplicates.…`` line in the README and the report parses (FR-025)."""

    def test_every_shown_command_parses(self) -> None:
        seen: dict[str, int] = {}
        for page in (README, REPORT):
            for match in COMMAND_RE.finditer(page.read_text(encoding="utf-8")):
                module, rest = match.group(1), match.group(2)
                with self.subTest(page=page.name, command=match.group(0)):
                    self.assertIn(module, SCRIPTS)
                    with contextlib.redirect_stderr(io.StringIO()):
                        SCRIPTS[module]._build_arg_parser().parse_args(shlex.split(rest))
                    seen[page.name] = seen.get(page.name, 0) + 1
        self.assertEqual(sorted(seen), sorted([README.name, REPORT.name]), "both pages show their commands")


if __name__ == "__main__":
    unittest.main()
