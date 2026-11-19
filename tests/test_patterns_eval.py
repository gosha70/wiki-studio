# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The pattern-corpus fixture and its scripts (FR-011, FR-021).

The fixture is exercised through the real API on a temporary copy: structural lint, the
pattern-page convention, prose lint, supersession, the expected findings, and every pinned
byte the manifest records. The US4 and US5 scripts run in-process against temporary copies
and must reproduce their committed results without writing under ``eval/patterns/``; every
command the README shows is parsed with full flag spelling.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import re
import shlex
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any

from eval.patterns import duplicates, retrieval, trace
from wiki_studio import api, discovery
from wiki_studio.cli import _build_arg_parser
from wiki_studio.paths import WikiPaths
from wiki_studio.prose_lint import SEGMENT_PARAGRAPH, scan_page, split_sentences
from wiki_studio.yaml_lite import parse_frontmatter

REPO_ROOT = Path(__file__).resolve().parents[1]
PATTERNS_DIR = REPO_ROOT / "eval" / "patterns"
WIKI_DIR = PATTERNS_DIR / "wiki"
CORPUS = PATTERNS_DIR / "corpus" / "decisions-57.md"
LABELS = PATTERNS_DIR / "labels.json"
MANIFEST = PATTERNS_DIR / "manifest.json"
PROTOCOL = PATTERNS_DIR / "protocol.json"
README = PATTERNS_DIR / "README.md"
QUESTIONS = PATTERNS_DIR / "questions.json"
RESULTS_DIR = PATTERNS_DIR / "results"
HAS_FTS5 = discovery.fts5_available().available
MISMATCH = "PATTERNS-RESULT-MISMATCH"

REQUIRED_KEYS = ("page_type", "slug", "title", "status", "last_reviewed")
ALLOWED_KEYS = frozenset((*REQUIRED_KEYS, "sources", "superseded_by", "corrects"))
SECTIONS = ("Decision", "Context", "Alternatives considered", "Consequences")
_FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):")


def sha256_of(path: Path) -> str:
    """The file's sha256, lowercase hex."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_frontmatter(text: str) -> tuple[list[str], str]:
    """The frontmatter lines and the body text (everything after the closing ``---``)."""
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise AssertionError("page does not open with ---")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[1:index], "\n".join(lines[index + 1 :])
    raise AssertionError("page has no closing ---")


def frontmatter_keys(frontmatter: list[str]) -> list[str]:
    """The top-level keys of the frontmatter block, in order."""
    return [match.group(1) for line in frontmatter if (match := _FRONTMATTER_KEY_RE.match(line))]


def section(body: str, heading: str) -> str:
    """The body text of one H2 section, up to the next H2."""
    lines = body.splitlines()
    out: list[str] = []
    inside = False
    for line in lines:
        if line.startswith("## "):
            if inside:
                break
            inside = line[3:].strip() == heading
            continue
        if inside:
            out.append(line)
    return "\n".join(out)


class PatternsFixtureTest(unittest.TestCase):
    """The US2 fixture: every pinned byte and convention, through the public API."""

    _tmp: tempfile.TemporaryDirectory[str]
    paths: WikiPaths
    manifest: dict[str, Any]
    pages: list[dict[str, Any]]
    pattern_paths: set[str]
    corpus_text: str

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls._tmp.name)
        shutil.copytree(WIKI_DIR, tmp / "wiki")
        cls.paths = WikiPaths.for_root(tmp, wiki_dir=tmp / "wiki")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.pages = cls.manifest["pages"]
        cls.pattern_paths = {entry["path"] for entry in cls.pages}
        cls.corpus_text = CORPUS.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def read_page(self, rel: str) -> str:
        return (WIKI_DIR / rel).read_text(encoding="utf-8")

    def test_structural_lint_is_clean(self) -> None:
        result = api.lint(self.paths)
        self.assertEqual(result.violations, ())

    def test_pattern_pages_follow_the_convention(self) -> None:
        for entry in self.pages:
            with self.subTest(page=entry["path"]):
                text = self.read_page(entry["path"])
                frontmatter, body = split_frontmatter(text)
                parsed = parse_frontmatter(text)
                headings = [line[3:].strip() for line in body.splitlines() if line.startswith("## ")]
                self.assertEqual(headings, list(SECTIONS))
                self.assertEqual(parsed["page_type"], "decision")
                self.assertTrue(parsed.get("sources"))
                self.assertTrue(set(frontmatter_keys(frontmatter)) <= ALLOWED_KEYS)
                for source in parsed["sources"]:
                    if "path" in source:
                        self.assertIn("sha", source)
                    for ticket in ("issue", "pr"):
                        if ticket in source:
                            self.assertRegex(source[ticket], r"^gosha70/code-copilot-team#\d+$")
                paragraphs = [
                    segment
                    for segment in scan_page(entry["path"], text)
                    if segment.kind == SEGMENT_PARAGRAPH and segment.section == "Decision"
                ]
                self.assertTrue(paragraphs[0].text.startswith("In the context of"))
                self.assertEqual(len(split_sentences(paragraphs[0])), entry["y_statement_sentences"])
                self.assertTrue(paragraphs[1].text.startswith("Chosen:"))
                self.assertIn("Applies when:", section(body, "Context"))
                self.assertIn("Does not apply when:", section(body, "Context"))
                self.assertIn("Revisit when:", section(body, "Consequences"))

    def test_prose_lint_reports_nothing_on_a_pattern_page(self) -> None:
        result = api.lint(self.paths, prose=True)
        self.assertIsNotNone(result.prose)
        assert result.prose is not None
        found = [finding for finding in result.prose.findings if finding.path in self.pattern_paths]
        self.assertEqual(found, [])

    def test_exactly_the_two_stale_pages_are_superseded_and_indexed(self) -> None:
        index_text = (WIKI_DIR / "index.md").read_text(encoding="utf-8")
        stale = [entry for entry in self.pages if entry["kind"] == "stale"]
        self.assertEqual(len(stale), 2)
        superseded_in_fixture: list[str] = []
        for page in WIKI_DIR.rglob("*.md"):
            rel = page.relative_to(WIKI_DIR).as_posix()
            parsed = parse_frontmatter(page.read_text(encoding="utf-8"))
            if "superseded_by" in parsed:
                superseded_in_fixture.append(rel)
        self.assertEqual(sorted(superseded_in_fixture), sorted(entry["path"] for entry in stale))
        for entry in stale:
            with self.subTest(page=entry["path"]):
                parsed = parse_frontmatter(self.read_page(entry["path"]))
                self.assertEqual(parsed["status"], "deprecated")
                self.assertTrue((WIKI_DIR / parsed["superseded_by"]).is_file())
                self.assertNotEqual(parsed["superseded_by"], entry["path"])
                self.assertIn(f"]({entry['path']})", index_text)

    def test_findings_report_superseded_still_indexed_for_the_two(self) -> None:
        result = api.findings(self.paths)
        reported = [finding for finding in result.findings if finding.kind == "superseded-still-indexed"]
        stale = sorted(entry["path"] for entry in self.pages if entry["kind"] == "stale")
        self.assertEqual(sorted(finding.pages[0] for finding in reported), stale)
        for finding in reported:
            self.assertEqual(finding.pages[1], "index.md")

    def test_corpus_copy_matches_the_pin(self) -> None:
        self.assertEqual(sha256_of(CORPUS), self.manifest["pins"]["memkernel"]["sha256"])

    def test_every_record_heading_occurs_in_the_corpus_copy(self) -> None:
        headings = self.corpus_text.splitlines()
        for entry in self.pages:
            if entry["record"] is not None:
                with self.subTest(record=entry["record"]):
                    self.assertIn(entry["record"], headings)

    def test_background_copies_and_exclusions(self) -> None:
        for entry in self.manifest["background"]:
            with self.subTest(page=entry["path"]):
                copy = WIKI_DIR / entry["path"]
                self.assertTrue(copy.is_file())
                self.assertEqual(sha256_of(copy), entry["sha256"])
                self.assertNotIn(entry["path"], self.pattern_paths)
        self.assertFalse((WIKI_DIR / "playbooks" / "pre-pr-close-keyword-audit.md").exists())
        self.assertFalse((WIKI_DIR / "schema").exists())
        self.assertFalse((WIKI_DIR / "scripts").exists())
        self.assertFalse((WIKI_DIR / "open-questions").exists())
        self.assertEqual(list(WIKI_DIR.rglob(".gitkeep")), [])

    def test_word_counts_recompute(self) -> None:
        corpus_lines = self.corpus_text.splitlines()
        for entry in self.pages:
            with self.subTest(page=entry["path"]):
                _, body = split_frontmatter(self.read_page(entry["path"]))
                self.assertEqual(len(body.split()), entry["words_page"])
                if entry["record"] is not None:
                    start = corpus_lines.index(entry["record"])
                    end = start + 1
                    while end < len(corpus_lines) and not re.match(r"^(### |## )", corpus_lines[end]):
                        end += 1
                    self.assertEqual(len("\n".join(corpus_lines[start:end]).split()), entry["words_record"])
                else:
                    self.assertIsNone(entry["words_record"])

    def test_readme_contains_each_pin_value(self) -> None:
        readme = README.read_text(encoding="utf-8")
        pins = self.manifest["pins"]
        for value in (
            pins["memkernel"]["tag"],
            pins["memkernel"]["commit"],
            pins["memkernel"]["path"],
            pins["memkernel"]["sha256"],
            pins["code_copilot_team"]["commit"],
        ):
            self.assertIn(value, readme)


def snapshot_tree(root: Path) -> dict[str, str]:
    """Every file under ``root`` with its sha256, keyed by POSIX relative path (bytecode excluded)."""
    return {
        path.relative_to(root).as_posix(): sha256_of(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def record_result(actual: object, name: str) -> None:
    """Fail with the whole generated result, so a stale committed file can be regenerated from it."""
    raise AssertionError(
        f"{MISMATCH} results/{name} differs from the generated output; record this JSON as the result: "
        f"{json.dumps(actual, sort_keys=True)}"
    )


def option_strings(parser: argparse.ArgumentParser) -> set[str]:
    """Every long and short option spelling a parser (and its subparsers) accepts."""
    found: set[str] = set()
    for action in parser._actions:
        found.update(action.option_strings)
        if isinstance(action, argparse._SubParsersAction):
            for sub in action.choices.values():
                found |= option_strings(sub)
    return found


class PatternsScriptsTest(unittest.TestCase):
    """US4: the trace and retrieval scripts reproduce their committed results (FR-021)."""

    def run_trace(self) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "trace.json"
            self.assertEqual(trace.main(["--out", str(out)]), 0)
            return json.loads(out.read_text(encoding="utf-8"))

    def run_retrieval(self) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "retrieval.json"
            self.assertEqual(retrieval.main(["--out", str(out)]), 0)
            return json.loads(out.read_text(encoding="utf-8"))

    def committed(self, name: str) -> dict[str, Any] | None:
        path = RESULTS_DIR / name
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def test_trace_matches_the_recorded_result(self) -> None:
        actual = self.run_trace()
        if actual != self.committed("trace.json"):
            record_result(actual, "trace.json")

    def test_retrieval_matches_the_recorded_result_for_index_first(self) -> None:
        actual = self.run_retrieval()
        committed = self.committed("retrieval.json")
        if committed is None or actual["rankers"]["index-first"] != committed["rankers"]["index-first"]:
            record_result(actual, "retrieval.json")

    @unittest.skipUnless(HAS_FTS5, "this Python's SQLite has no FTS5")
    def test_retrieval_matches_the_recorded_result_for_fts5(self) -> None:
        actual = self.run_retrieval()
        committed = self.committed("retrieval.json")
        if committed is None or actual["rankers"]["fts5"] != committed["rankers"]["fts5"]:
            record_result(actual, "retrieval.json")

    def test_retrieval_records_the_questions_hash(self) -> None:
        committed = self.committed("retrieval.json")
        if committed is None:
            record_result(self.run_retrieval(), "retrieval.json")
        assert committed is not None
        self.assertEqual(committed["questions_sha256"], sha256_of(QUESTIONS))

    def test_the_readme_records_the_committed_runs_versions(self) -> None:
        committed = self.committed("retrieval.json")
        if committed is None:
            record_result(self.run_retrieval(), "retrieval.json")
        assert committed is not None
        readme = README.read_text(encoding="utf-8")
        self.assertIn(committed["environment"]["python"], readme)
        self.assertIn(committed["environment"]["sqlite"], readme)

    def test_the_scripts_write_nothing_under_eval_patterns(self) -> None:
        before = snapshot_tree(PATTERNS_DIR)
        self.run_trace()
        self.run_retrieval()
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(duplicates.main(["--out", str(Path(tmp) / "duplicates.json")]), 0)
        self.assertEqual(snapshot_tree(PATTERNS_DIR), before)

    def test_help_exits_zero(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            for script in (trace, retrieval, duplicates):
                self.assertEqual(script.main(["--help"]), 0, script.__name__)

    def test_every_readme_command_parses_with_full_flag_spelling(self) -> None:
        wiki_flags = option_strings(_build_arg_parser())
        script_flags = {
            "eval.patterns.trace": (trace, option_strings(trace._build_arg_parser())),
            "eval.patterns.retrieval": (retrieval, option_strings(retrieval._build_arg_parser())),
            "eval.patterns.duplicates": (duplicates, option_strings(duplicates._build_arg_parser())),
        }
        seen = 0
        for line in README.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if text.startswith("wiki-studio "):
                argv = shlex.split(text)[1:]
                for token in argv:
                    if token.startswith("-"):
                        self.assertIn(token.split("=", 1)[0], wiki_flags, f"spell every flag in full: {text}")
                with contextlib.redirect_stderr(io.StringIO()):
                    _build_arg_parser().parse_args(argv)
                seen += 1
            elif text.startswith("python -m eval.patterns."):
                argv = shlex.split(text)
                self.assertIn(argv[2], script_flags, f"unknown study script: {text}")
                script, flags = script_flags[argv[2]]
                for token in argv[3:]:
                    if token.startswith("-"):
                        self.assertIn(token.split("=", 1)[0], flags, f"spell every flag in full: {text}")
                script._build_arg_parser().parse_args(argv[3:])
                seen += 1
        self.assertGreater(seen, 0)


class PatternsDuplicatesTest(unittest.TestCase):
    """US5: duplicates.py on the frozen labels (FR-022..FR-025)."""

    def run_duplicates(self, patterns_dir: Path | None = None) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "duplicates.json"
            kwargs = {} if patterns_dir is None else {"patterns_dir": patterns_dir}
            self.assertEqual(duplicates.main(["--out", str(out)], **kwargs), 0)
            return json.loads(out.read_text(encoding="utf-8"))

    def committed(self) -> dict[str, Any] | None:
        path = RESULTS_DIR / "duplicates.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def test_output_matches_the_recorded_result(self) -> None:
        actual = self.run_duplicates()
        if actual != self.committed():
            record_result(actual, "duplicates.json")

    def test_recorded_hashes_equal_the_frozen_files(self) -> None:
        committed = self.committed()
        if committed is None:
            record_result(self.run_duplicates(), "duplicates.json")
        assert committed is not None
        self.assertEqual(committed["labels_sha256"], sha256_of(LABELS))
        self.assertEqual(committed["protocol_sha256"], sha256_of(PROTOCOL))

    def test_every_true_pair_carries_the_annotation_link_mark(self) -> None:
        committed = self.committed()
        if committed is None:
            record_result(self.run_duplicates(), "duplicates.json")
        assert committed is not None
        self.assertEqual(sorted(committed["signals"]), ["a", "a-path", "b", "c", "combined"])
        for name, signal in committed["signals"].items():
            for candidate in signal["candidates"]:
                if candidate["true"]:
                    self.assertIsInstance(candidate["annotation_linked"], bool, f"{name}: {candidate['pair']}")

    def test_the_readme_states_the_frozen_input_and_the_recorded_verdicts(self) -> None:
        readme = README.read_text(encoding="utf-8")
        self.assertIn("python -m eval.patterns.duplicates --out <PATH>", readme)
        protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        self.assertIn(protocol["labels_sha256"], readme)
        committed = self.committed()
        if committed is None:
            record_result(self.run_duplicates(), "duplicates.json")
        assert committed is not None
        rows = []
        for name, signal in committed["signals"].items():
            counts = signal["counts"]
            label = name if name == "combined" else f"({name})"
            rows.append(
                f"| {label} | {counts['found_labelled_pairs']} of {counts['eligible_labelled_pairs']} | "
                f"{counts['found_labelled_annotation_linked']} | {counts['true_candidates']} | "
                f"{counts['false_candidates']} | {signal['verdict']} |"
            )
        missing = [row for row in rows if row not in readme]
        self.assertEqual(missing, [], "the README's duplicate-candidates table must state the recorded counts")

    def test_a_changed_disposition_exits_one_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "patterns"
            shutil.copytree(PATTERNS_DIR, copy)
            labels_path = copy / "labels.json"
            text = labels_path.read_text(encoding="utf-8")
            changed = text.replace('"disposition": "conflicting"', '"disposition": "unrelated"', 1)
            self.assertNotEqual(changed, text)
            labels_path.write_text(changed, encoding="utf-8")
            expected = json.loads((copy / "protocol.json").read_text(encoding="utf-8"))["labels_sha256"]
            actual = sha256_of(labels_path)
            out = Path(tmp) / "duplicates.json"
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = duplicates.main(["--out", str(out)], patterns_dir=copy)
            self.assertEqual(code, 1)
            self.assertFalse(out.exists())
            self.assertIn(actual, stderr.getvalue())
            self.assertIn(expected, stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
