# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""US3: the duplicate-audit study's development stage, committed and reported (issue 121, FR-019, FR-020).

The audit script, rerun on the development set into a temporary directory, writes a ``development.json`` equal to
the committed one byte for byte and leaves ``eval/`` unchanged; that is a reproduction of the committed bytes, not a
reading (plan, O7). ``development-timing.json`` has its keys (its values are never compared). ``report.md`` holds
exactly one development stage line, equal to ``development.json``'s outcome, and its two tables state the committed
numbers; every ``python -m eval.duplicate_audit.…`` line in the report parses with the script's parser. The rerun
skips, with the reason, when this Python's SQLite has no FTS5; the checks on the committed files do not rank and
always run.
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

from eval.duplicate_audit import audit
from wiki_studio import discovery

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = REPO_ROOT / "eval"
AUDIT_DIR = EVAL_DIR / "duplicate_audit"
RESULTS_DIR = AUDIT_DIR / "results"
REPORT = AUDIT_DIR / "report.md"
CACHE_DIR_NAME = "__pycache__"
RESULTS_NAME = f"{audit.DEVELOPMENT}{audit.RESULTS_SUFFIX}"
TIMING_NAME = f"{audit.DEVELOPMENT}{audit.TIMING_SUFFIX}"

FTS5 = discovery.fts5_available()
NO_FTS5 = f"this Python's SQLite has no FTS5, so audit.py cannot be rerun: {FTS5.reason}"

STAGE_PREFIX = "Development stage: "
COMMAND_RE = re.compile(r"python -m (eval\.duplicate_audit\.\w+)([^`\n]*)")
SCRIPTS = {"eval.duplicate_audit.audit": audit}
TIMING_KEYS = {"clock", "pages", "seconds", "set", "study"}
PER_100_FORMAT = "{:.2f}"
YES, NO = "yes", "no"


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


def candidate_row(name: str, counts: dict[str, Any], n: int, false_dispositions: list[str]) -> str:
    """The development table's row for one candidate, from ``development.json``'s counts."""
    readings = counts["not_binding"]
    per_100 = readings["per_100_pages"]
    restatements = sum(readings["flagged_by_restatement"][rule] for rule in audit.RESTATEMENT_RULES)
    found_restatements = sum(readings["found_by_restatement"][rule] for rule in audit.RESTATEMENT_RULES)
    return row(
        code(name),
        counts["k"],
        counts["flagged"],
        f"{counts['found']} of {n}",
        counts["false"],
        *(readings["false_by_disposition"][label] for label in false_dispositions),
        *(PER_100_FORMAT.format(per_100[key]) for key in ("flagged", "true", "false")),
        restatements,
        found_restatements,
        counts["non_restatement_found"],
    )


def stop_rule_row(name: str, counts: dict[str, Any], holds: bool) -> str:
    return row(code(name), counts["false"], counts["true"], YES if holds else NO)


def assert_timing_keys(case: unittest.TestCase, timing: dict[str, Any], results: dict[str, Any]) -> None:
    """``development-timing.json``'s keys and page count; its wall seconds are never compared."""
    case.assertEqual(set(timing), TIMING_KEYS)
    case.assertEqual(timing["set"], audit.DEVELOPMENT)
    case.assertEqual(timing["pages"], results["pages"])
    case.assertIsInstance(timing["seconds"], float)


class CommittedDevelopmentAndReportTest(unittest.TestCase):
    """The committed development files and the report agree; nothing here ranks (FR-019, FR-020)."""

    committed: ClassVar[dict[str, Any]]
    timing: ClassVar[dict[str, Any]]
    protocol: ClassVar[dict[str, Any]]
    lines: ClassVar[list[str]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.committed = load_json(RESULTS_DIR / RESULTS_NAME)
        cls.timing = load_json(RESULTS_DIR / TIMING_NAME)
        cls.protocol = load_json(REPO_ROOT / audit.PROTOCOL_PATH)
        cls.lines = REPORT.read_text(encoding="utf-8").splitlines()

    def test_the_report_has_exactly_one_stage_line_equal_to_the_outcome(self) -> None:
        stage_lines = [line for line in self.lines if line.startswith(STAGE_PREFIX)]
        stop_rule = self.committed["stop_rule"]
        expected = self.protocol[audit.DEVELOPMENT]["stage_lines"][stop_rule["outcome"]]
        self.assertEqual(stage_lines, [expected])
        self.assertEqual(stop_rule["line"], expected)

    def test_the_results_were_written_from_the_frozen_protocol(self) -> None:
        self.assertEqual(self.committed["set"], audit.DEVELOPMENT)
        self.assertEqual(self.committed["inputs"][audit.PROTOCOL_PATH], sha256_of(REPO_ROOT / audit.PROTOCOL_PATH))
        names = [candidate["name"] for candidate in self.protocol["candidates"]]
        self.assertEqual(sorted(self.committed["candidates"]), sorted(names))

    def test_timing_has_its_keys(self) -> None:
        assert_timing_keys(self, self.timing, self.committed)

    def test_the_report_states_each_candidate_as_recorded(self) -> None:
        n = self.committed["true_pairs"]["n"]
        false_dispositions = list(self.protocol["false_dispositions"])
        for name, counts in self.committed["candidates"].items():
            with self.subTest(candidate=name):
                self.assertIn(candidate_row(name, counts, n, false_dispositions), self.lines)

    def test_the_report_states_the_stop_rule_as_recorded(self) -> None:
        holds = self.committed["stop_rule"]["false_not_above_true"]
        for name, counts in self.committed["candidates"].items():
            with self.subTest(candidate=name):
                self.assertIn(stop_rule_row(name, counts, holds[name]), self.lines)


class ShownCommandsTest(unittest.TestCase):
    """Every ``python -m eval.duplicate_audit.…`` line in the report parses with the script's parser (FR-020)."""

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
    """``audit.py --set development`` rerun into a temporary directory reproduces the committed bytes (FR-020)."""

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
            cls.exit_code = audit.main(["--set", audit.DEVELOPMENT, "--out-dir", str(cls.rerun_dir)])
        cls.after = snapshot_tree(EVAL_DIR)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_the_rerun_equals_the_committed_development_results_byte_for_byte(self) -> None:
        self.assertEqual(self.exit_code, 0)
        self.assertEqual((self.rerun_dir / RESULTS_NAME).read_bytes(), (RESULTS_DIR / RESULTS_NAME).read_bytes())

    def test_the_rerun_writes_timing_with_its_keys(self) -> None:
        self.assertEqual(self.exit_code, 0)
        results = load_json(self.rerun_dir / RESULTS_NAME)
        assert_timing_keys(self, load_json(self.rerun_dir / TIMING_NAME), results)

    def test_the_rerun_leaves_eval_unchanged(self) -> None:
        self.assertEqual(self.after, self.before)


if __name__ == "__main__":
    unittest.main()
