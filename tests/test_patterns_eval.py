# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The pattern-corpus fixture and its scripts (FR-011, FR-021).

The fixture is exercised through the real API on a temporary copy: structural lint, the
pattern-page convention, prose lint, supersession, the expected findings, and every pinned
byte the manifest records. The US4, US5 and US6 scripts run in-process against temporary
copies and must reproduce their committed results without writing under ``eval/patterns/``;
every command the README shows is parsed with full flag spelling. US7 adds the
report's structure, its one recommendation line and ``docs/patterns.md``, whose
commands run against a temporary copy of the fixture.
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
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

from eval.patterns import duplicates, retrieval, staleness, trace
from tests.conftest import run_cli
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
REPORT = PATTERNS_DIR / "report.md"
RESULTS_DIR = PATTERNS_DIR / "results"
DOCS_PATTERNS = REPO_ROOT / "docs" / "patterns.md"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
HAS_FTS5 = discovery.fts5_available().available
GIT = shutil.which("git")
MISMATCH = "PATTERNS-RESULT-MISMATCH"

REQUIRED_KEYS = ("page_type", "slug", "title", "status", "last_reviewed")
ALLOWED_KEYS = frozenset((*REQUIRED_KEYS, "sources", "superseded_by", "corrects"))
SECTIONS = ("Decision", "Context", "Alternatives considered", "Consequences")
_FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):")

# FR-030/FR-033: the report answers issue 54's six questions in this order and
# ends in exactly one of the three outcome lines.
QUESTION_HEADINGS = (
    "## Question 1: Can current pages hold a pattern?",
    "## Question 2: How does an agent propose one, and what evidence must promotion see?",
    "## Question 3: How does an agent find and cite approved patterns without treating them as binding?",
    "## Question 4: Can existing lint, query or findings expose near-duplicates without merging anything?",
    "## Question 5: How does a source or spec change mark a pattern for review?",
    "## Question 6: What should memkernel keep to point at one?",
)
RECOMMENDATION_LINES = (
    "Recommendation: docs and a template.",
    "Recommendation: a separately specified enhancement.",
    "Recommendation: no change.",
)

# FR-032: the values the docs page's placeholders take when its commands run
# against a temporary copy of the fixture.
DOCS_ARGUMENTS = {
    "<the task, in plain words>": "how should archived traces be redacted",
    "<page>": "decisions/trace-archive-reuses-the-ingest-redaction-path.md",
}


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
            "eval.patterns.staleness": (staleness, option_strings(staleness._build_arg_parser())),
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


@unittest.skipUnless(GIT is not None, "git is not on PATH")
class PatternsStalenessTest(unittest.TestCase):
    """US6: staleness.py against a temporary repository (FR-026, FR-027, FR-029)."""

    def run_git(self, repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
        assert GIT is not None
        command = [
            GIT,
            "-C",
            str(repo),
            "-c",
            "user.name=patterns-test",
            "-c",
            "user.email=patterns@example.invalid",
            *args,
        ]
        return subprocess.run(command, check=True, capture_output=True, text=True)

    def two_commit_repo(self, tmp: Path) -> tuple[Path, str, str]:
        """A repository whose pin keeps a file unchanged, changes one and deletes one."""
        repo = tmp / "checkout"
        repo.mkdir()
        self.run_git(repo, "init")
        (repo / "unchanged.txt").write_text("same at both commits\n", encoding="utf-8")
        (repo / "changed.txt").write_text("before\n", encoding="utf-8")
        (repo / "deleted.txt").write_text("removed at the pin\n", encoding="utf-8")
        self.run_git(repo, "add", ".")
        self.run_git(repo, "commit", "-m", "first")
        first = self.run_git(repo, "rev-parse", "HEAD").stdout.strip()
        (repo / "changed.txt").write_text("after\n", encoding="utf-8")
        (repo / "deleted.txt").unlink()
        self.run_git(repo, "add", "-A")
        self.run_git(repo, "commit", "-m", "second")
        pin = self.run_git(repo, "rev-parse", "HEAD").stdout.strip()
        return repo, first, pin

    def test_check_sources_reports_unchanged_changed_and_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, first, pin = self.two_commit_repo(Path(tmp))
            results = staleness.check_sources(
                repo,
                pin,
                [
                    {"path": "unchanged.txt", "sha": first},
                    {"path": "changed.txt", "sha": first},
                    {"path": "deleted.txt", "sha": first},
                    {"path": "changed.txt", "sha": "0000000"},
                ],
            )
        self.assertEqual([entry["revision_check"] for entry in results[:3]], ["unchanged", "changed", "changed"])
        self.assertEqual([entry["stale_claim"] for entry in results[:3]], ["not flagged", "not flagged", "flagged"])
        self.assertIsNone(results[3]["revision_check"])
        self.assertTrue(results[3]["revision_reason"])

    def test_help_exits_zero(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(staleness.main(["--help"]), 0)

    def test_results_list_exactly_the_pattern_pages_path_sources(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        expected: list[tuple[str, str, str]] = []
        for entry in manifest["pages"]:
            parsed = parse_frontmatter((WIKI_DIR / entry["path"]).read_text(encoding="utf-8"))
            for source in parsed["sources"]:
                if "path" in source:
                    expected.append((entry["path"], str(source["path"]), str(source["sha"])))
        committed = json.loads((RESULTS_DIR / "staleness.json").read_text(encoding="utf-8"))
        actual = [
            (page["page"], source["path"], source["sha"]) for page in committed["pages"] for source in page["sources"]
        ]
        self.assertEqual(actual, expected)
        self.assertEqual(committed["pin"], manifest["pins"]["code_copilot_team"]["commit"])


def substitute_docs_arguments(argv: list[str]) -> list[str]:
    """Replace the docs page's placeholders with values the fixture answers (FR-032)."""
    return [DOCS_ARGUMENTS.get(token, token) for token in argv]


class PatternsReportTest(unittest.TestCase):
    """US7: the report and its one recommendation (FR-030, FR-033)."""

    report: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = REPORT.read_text(encoding="utf-8")

    def recommendation_lines(self) -> list[str]:
        return [line.strip() for line in self.report.splitlines() if line.strip().startswith("Recommendation:")]

    def test_the_six_question_sections_appear_in_order(self) -> None:
        positions = []
        for heading in QUESTION_HEADINGS:
            self.assertIn(heading, self.report)
            positions.append(self.report.index(heading))
        self.assertEqual(positions, sorted(positions))

    def test_exactly_one_recommendation_line_of_the_three_forms(self) -> None:
        lines = self.recommendation_lines()
        self.assertEqual(len(lines), 1, lines)
        self.assertIn(lines[0], RECOMMENDATION_LINES)

    def test_docs_patterns_exists_exactly_with_the_template_outcome(self) -> None:
        lines = self.recommendation_lines()
        self.assertEqual(len(lines), 1, lines)
        self.assertEqual(DOCS_PATTERNS.is_file(), lines[0] == RECOMMENDATION_LINES[0])

    def test_every_results_file_it_cites_exists(self) -> None:
        cited = sorted(set(re.findall(r"results/[A-Za-z0-9_.-]+\.json", self.report)))
        self.assertTrue(cited)
        for rel in cited:
            self.assertTrue((PATTERNS_DIR / rel).is_file(), rel)

    def test_every_wiki_studio_line_it_shows_parses(self) -> None:
        wiki_flags = option_strings(_build_arg_parser())
        for line in self.report.splitlines():
            text = line.strip()
            if not text.startswith("wiki-studio "):
                continue
            argv = shlex.split(text)[1:]
            for token in argv:
                if token.startswith("-"):
                    self.assertIn(token.split("=", 1)[0], wiki_flags, f"spell every flag in full: {text}")
            with contextlib.redirect_stderr(io.StringIO()):
                _build_arg_parser().parse_args(argv)


class PatternsDocsTest(unittest.TestCase):
    """US7: docs/patterns.md, its commands and its changelog line (FR-032, FR-033)."""

    docs: str

    @classmethod
    def setUpClass(cls) -> None:
        if not DOCS_PATTERNS.is_file():
            raise unittest.SkipTest("docs/patterns.md is not written (no template outcome)")
        cls.docs = DOCS_PATTERNS.read_text(encoding="utf-8")

    def command_lines(self) -> list[str]:
        return [line.strip() for line in self.docs.splitlines() if line.strip().startswith("wiki-studio ")]

    def test_the_page_shows_no_install_command(self) -> None:
        self.assertNotIn("pip install", self.docs)

    def test_the_page_links_the_readme_install_section(self) -> None:
        self.assertIn("(../README.md#install)", self.docs)

    def test_every_command_parses_with_full_flag_spelling(self) -> None:
        wiki_flags = option_strings(_build_arg_parser())
        lines = self.command_lines()
        self.assertTrue(lines)
        for text in lines:
            argv = substitute_docs_arguments(shlex.split(text)[1:])
            for token in argv:
                if token.startswith("-"):
                    self.assertIn(token.split("=", 1)[0], wiki_flags, f"spell every flag in full: {text}")
            with contextlib.redirect_stderr(io.StringIO()):
                _build_arg_parser().parse_args(argv)

    def test_every_command_runs_zero_against_the_fixture(self) -> None:
        lines = self.command_lines()
        self.assertTrue(lines)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            (root / "knowledge").mkdir(parents=True)
            shutil.copytree(WIKI_DIR, root / "knowledge" / "wiki")
            for text in lines:
                with self.subTest(command=text):
                    argv = substitute_docs_arguments(shlex.split(text)[1:])
                    result = run_cli(*argv, cwd=root)
                    self.assertEqual(result.returncode, 0, f"{text}\n{result.stderr}")

    def test_the_changelog_unreleased_holds_the_docs_line(self) -> None:
        changelog = CHANGELOG.read_text(encoding="utf-8")
        self.assertIn("## [Unreleased]", changelog)
        unreleased = changelog.split("## [Unreleased]", 1)[1].split("\n## [", 1)[0]
        self.assertIn("### Docs", unreleased)
        self.assertIn("docs/patterns.md", unreleased)


if __name__ == "__main__":
    unittest.main()
