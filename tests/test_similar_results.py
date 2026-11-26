# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""US3: the similar-pages study's committed results and report (issue 121, FR-015, FR-016).

The ranking script, rerun into a temporary directory, writes a ``ranks.json`` equal to the committed one byte for byte
and leaves ``eval/`` unchanged; ``timing.json`` has its keys (its values are never compared with a rerun).
``report.md`` holds exactly one verdict line, equal to ``ranks.json``'s verdict, and states the recorded figures;
``ranks.json``'s ``paths`` and ``collisions`` recompute from ``corpus.json``; every ``python -m eval.similar.…`` line
in the report parses with the script's parser. The rerun skips, with the reason, when this Python's SQLite has no
FTS5; the checks on the committed files do not rank and always run.
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

from eval.similar import rank
from wiki_studio import discovery

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = REPO_ROOT / "eval"
SIMILAR_DIR = EVAL_DIR / "similar"
RESULTS_DIR = SIMILAR_DIR / "results"
REPORT = SIMILAR_DIR / "report.md"
CACHE_DIR_NAME = "__pycache__"

FTS5 = discovery.fts5_available()
NO_FTS5 = f"this Python's SQLite has no FTS5, so rank.py cannot be rerun: {FTS5.reason}"

VERDICT_PREFIX = "Verdict: "
POST_HOC_HEADING = "Post hoc (not binding)"
POST_HOC_KEY = "post_hoc"
COMMAND_RE = re.compile(r"python -m (eval\.similar\.\w+)([^`\n]*)")
SCRIPTS = {"eval.similar.rank": rank}
TIMING_KEYS = {"clock", "fixture_pages", "fixture_tries", "pages", "seconds", "study", "tries"}
SECONDS_KEYS = {rank.BINDING, rank.WHOLE_PAGE, rank.BODY_ONLY, rank.FIXTURE}
SECONDS_FORMAT = "{:.3f} s"
YES, NO = "yes", "no"
FOUND, MISSED = "found", "missed"
NO_RANK = "none"
BINDING_READING = "the query rule (binding)"
READING_NAMES = {rank.WHOLE_PAGE: "whole page (not binding)", rank.BODY_ONLY: "body only (not binding)"}
FIXTURE_READING = "the fixture (not binding)"


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


def code(text: str) -> str:
    return f"`{text}`"


def rank_cell(record: dict[str, Any]) -> str:
    rank_value = record["partner_rank"]
    return NO_RANK if rank_value is None else str(rank_value)


def reading_cell(record: dict[str, Any]) -> str:
    return f"{rank_cell(record)} {FOUND if record['found'] else MISSED}"


def try_row(number: int, record: dict[str, Any]) -> str:
    return row(
        number,
        code(record["query"]),
        code(record["partner"]),
        record["disposition"],
        rank_cell(record),
        YES if record["found"] else NO,
    )


def summary_row(name: str, summary: dict[str, Any]) -> str:
    return row(
        name,
        f"{summary['found']} of {summary['tries']}",
        f"{summary['supersedes_found']} of {summary['supersedes_tries']}",
        f"{summary['pairs_with_a_found_try']} of {summary['pairs']}",
    )


def assert_timing_keys(case: unittest.TestCase, timing: dict[str, Any], ranks: dict[str, Any]) -> None:
    """``timing.json``'s keys and counts; its wall seconds are never compared."""
    case.assertEqual(set(timing), TIMING_KEYS)
    case.assertEqual(set(timing["seconds"]), SECONDS_KEYS)
    case.assertEqual(timing["pages"], len(ranks["paths"]))
    case.assertEqual(timing["tries"], ranks["summary"]["tries"])
    case.assertEqual(timing["fixture_tries"], ranks["fixture"]["summary"]["tries"])


class CommittedResultsAndReportTest(unittest.TestCase):
    """The committed ``ranks.json``, ``timing.json`` and the report agree; nothing here ranks (FR-015, FR-016)."""

    committed: ClassVar[dict[str, Any]]
    timing: ClassVar[dict[str, Any]]
    protocol: ClassVar[dict[str, Any]]
    report: ClassVar[str]
    lines: ClassVar[list[str]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.committed = load_json(RESULTS_DIR / rank.RANKS_NAME)
        cls.timing = load_json(RESULTS_DIR / rank.TIMING_NAME)
        cls.protocol = load_json(REPO_ROOT / rank.PROTOCOL_PATH)
        cls.report = REPORT.read_text(encoding="utf-8")
        cls.lines = cls.report.splitlines()

    def test_the_report_has_exactly_one_verdict_line_equal_to_the_results(self) -> None:
        verdict_lines = [line for line in self.lines if line.startswith(VERDICT_PREFIX)]
        self.assertEqual(verdict_lines, [f"{VERDICT_PREFIX}{self.committed['summary']['verdict']}"])
        self.assertIn(verdict_lines[0], self.protocol["verdict_lines"])

    def test_the_results_were_written_from_the_frozen_protocol(self) -> None:
        self.assertEqual(self.committed["inputs"][rank.PROTOCOL_PATH], sha256_of(REPO_ROOT / rank.PROTOCOL_PATH))
        self.assertEqual(self.committed["k"], self.protocol["k"])

    def test_paths_and_collisions_recompute_from_corpus_json(self) -> None:
        entries = load_json(REPO_ROOT / rank.CORPUS_JSON_PATH)[rank.PAGES_KEY]
        self.assertEqual(self.committed["paths"], rank.slug_paths(entries))
        self.assertEqual(self.committed["collisions"], rank.slug_collisions(entries))
        self.assertEqual(len(set(self.committed["paths"].values())), len(entries), "every page has its own path")

    def test_timing_has_its_keys(self) -> None:
        assert_timing_keys(self, self.timing, self.committed)

    def test_the_report_states_every_try_as_recorded(self) -> None:
        for number, record in enumerate(self.committed["tries"], start=1):
            with self.subTest(try_number=number):
                self.assertIn(try_row(number, record), self.lines)

    def test_the_report_states_the_summaries_as_recorded(self) -> None:
        self.assertIn(summary_row(BINDING_READING, self.committed["summary"]), self.lines)
        for name, label in READING_NAMES.items():
            view = self.committed["readings"][name]
            with self.subTest(reading=name):
                self.assertIs(view[rank.BINDING], False)
                self.assertIn(summary_row(label, view["summary"]), self.lines)

    def test_the_report_states_each_readings_ranks_as_recorded(self) -> None:
        readings = [self.committed["readings"][name]["tries"] for name in READING_NAMES]
        for number, record in enumerate(self.committed["tries"], start=1):
            cells = [reading_cell(record), *(reading_cell(tries[number - 1]) for tries in readings)]
            with self.subTest(try_number=number):
                self.assertIn(row(number, *cells), self.lines)

    def test_the_report_states_the_noise_as_recorded(self) -> None:
        self.assertTrue(self.committed["noise"])
        for label, count in self.committed["noise"].items():
            with self.subTest(label=label):
                self.assertIn(row(label, count), self.lines)

    def test_the_report_states_the_fixture_as_recorded(self) -> None:
        fixture = self.committed["fixture"]
        self.assertIs(fixture[rank.BINDING], False)
        for number, record in enumerate(fixture["tries"], start=1):
            with self.subTest(try_number=number):
                self.assertIn(try_row(number, record), self.lines)
        summary = fixture["summary"]
        self.assertIn(
            row(
                FIXTURE_READING,
                f"{summary['found']} of {summary['tries']}",
                f"{summary['pairs_with_a_found_try']} of {summary['pairs']}",
            ),
            self.lines,
        )
        for page in [*fixture["superseded_left_out"], *(p for entry in fixture["never_listed"] for p in entry["pair"])]:
            with self.subTest(page=page):
                self.assertIn(code(page), self.report)

    def test_the_report_states_the_collisions_as_recorded(self) -> None:
        paths = self.committed["paths"]
        for slug, pages in self.committed["collisions"].items():
            line = row(code(slug), ", ".join(code(page) for page in pages), ", ".join(code(paths[p]) for p in pages))
            with self.subTest(slug=slug):
                self.assertIn(line, self.lines)

    def test_the_report_states_the_recorded_wall_times(self) -> None:
        for name, seconds in self.timing["seconds"].items():
            with self.subTest(timing=name):
                self.assertIn(SECONDS_FORMAT.format(seconds), self.report)

    def test_a_post_hoc_section_exists_only_with_a_post_hoc_block(self) -> None:
        self.assertEqual(POST_HOC_HEADING in self.report, POST_HOC_KEY in self.committed)


class ShownCommandsTest(unittest.TestCase):
    """Every ``python -m eval.similar.…`` line in the report parses with the script's parser (FR-016)."""

    def test_every_shown_command_parses(self) -> None:
        matches = list(COMMAND_RE.finditer(REPORT.read_text(encoding="utf-8")))
        self.assertTrue(matches, "the report shows how to rerun the script")
        for match in matches:
            module, rest = match.group(1), match.group(2)
            with self.subTest(command=match.group(0)):
                self.assertIn(module, SCRIPTS)
                with contextlib.redirect_stderr(io.StringIO()):
                    SCRIPTS[module].build_parser().parse_args(shlex.split(rest))


@unittest.skipUnless(FTS5.available, NO_FTS5)
class RerunTest(unittest.TestCase):
    """``rank.py`` rerun into a temporary directory reproduces the committed ``ranks.json`` (FR-016)."""

    rerun_dir: ClassVar[Path]
    before: ClassVar[dict[str, str]]
    after: ClassVar[dict[str, str]]
    exit_code: ClassVar[int]
    _tmp: ClassVar[tempfile.TemporaryDirectory[str]]

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.rerun_dir = Path(cls._tmp.name) / "results"
        cls.before = snapshot_tree(EVAL_DIR)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            cls.exit_code = rank.main(["--out-dir", str(cls.rerun_dir)])
        cls.after = snapshot_tree(EVAL_DIR)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_the_rerun_equals_the_committed_ranks_byte_for_byte(self) -> None:
        self.assertEqual(self.exit_code, 0)
        self.assertEqual((self.rerun_dir / rank.RANKS_NAME).read_bytes(), (RESULTS_DIR / rank.RANKS_NAME).read_bytes())

    def test_the_rerun_writes_timing_with_its_keys(self) -> None:
        self.assertEqual(self.exit_code, 0)
        ranks = load_json(self.rerun_dir / rank.RANKS_NAME)
        assert_timing_keys(self, load_json(self.rerun_dir / rank.TIMING_NAME), ranks)

    def test_the_rerun_leaves_eval_unchanged(self) -> None:
        self.assertEqual(self.after, self.before)


if __name__ == "__main__":
    unittest.main()
