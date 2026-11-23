# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""US3: the revision-check study's record, scoring and report (FR-012 to FR-015).

The scorer reruns here from the committed record and must equal
``results/candidates.json``; the report carries exactly one winner line, equal
to the results' winner, and the figures as recorded; the record covers every
case present at the freeze and keeps the keyword-quoting cases' hunks inside
their fence; the scorer writes nothing; and ``record.py``'s recording function
is checked on a temporary three-commit repository (only where git is on PATH).
"""

from __future__ import annotations

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
from unittest import mock

from eval.revisions import candidates, record
from tests.test_revisions_frozen import CASE_FILE_SHA256

REPO_ROOT = Path(__file__).resolve().parents[1]
REVISIONS_DIR = REPO_ROOT / "eval" / "revisions"
RESULTS_DIR = REVISIONS_DIR / "results"
HUNKS = RESULTS_DIR / "hunks.json"
CANDIDATES = RESULTS_DIR / "candidates.json"
REPORT = REVISIONS_DIR / "report.md"
README = REVISIONS_DIR / "README.md"
FENCED_DIR = REVISIONS_DIR / "cases" / "keyword-quoting"
REVISION_TESTS = sorted((REPO_ROOT / "tests").glob("test_revisions_*.py"))
GIT = shutil.which("git")

WINNER_PREFIX = "Winner: "
COMMAND_RE = re.compile(r"python -m (eval\.revisions\.\w+)([^`\n]*)")
SCRIPTS = {"eval.revisions.record": record, "eval.revisions.candidates": candidates}
# A recorded keyword-quoting line counts as distinctive (worth searching for elsewhere) from this many characters;
# shorter lines such as a lone `fi` or `}` occur in any file and would say nothing about a leak.
MIN_DISTINCTIVE_CHARS = 20
SECONDS_FORMAT = "{:.3f}"
NOT_YET_RECORDED = (
    "is not recorded yet: run `python -m eval.revisions.record --checkout <code-copilot-team checkout>` "
    "and `python -m eval.revisions.candidates --out eval/revisions/results/candidates.json` (FR-012, FR-013)"
)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AssertionError(f"{path.relative_to(REPO_ROOT).as_posix()} {NOT_YET_RECORDED}")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def snapshot_tree(root: Path) -> dict[str, str]:
    """Every file under ``root`` with its sha256, keyed by POSIX relative path (bytecode excluded)."""
    return {
        path.relative_to(root).as_posix(): sha256_of(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def report_row(cid: str, result: dict[str, Any]) -> str:
    """The report's table row for one candidate, from ``results/candidates.json`` as recorded."""
    study, supplementary, bar = result["study"], result["supplementary"], result["bar"]
    recall = (
        f"{supplementary['kept']} of {supplementary['of']}"
        if supplementary["required"] is not None
        else f"{supplementary['kept']} of {supplementary['of']} ({bar['recall']})"
    )
    return (
        f"| {cid} | {study['false_pages_flagged_count']} of {study['false_pages_of']} "
        f"| {study['false_entries_flagged_count']} of {study['false_entries_of']} "
        f"| {result['true_entry']} | {recall} "
        f"| {supplementary['kept_without_built']} of {supplementary['of_without_built']} "
        f"| {result['negatives']['flagged']} of {result['negatives']['of']} "
        f"| {result['cost']['study_processes']} | {SECONDS_FORMAT.format(result['cost']['study_seconds'])} "
        f"| {bar['overall']} |"
    )


class RecordedResultsTest(unittest.TestCase):
    """The committed record, scores and report agree with each other (FR-013 to FR-015)."""

    def committed(self) -> dict[str, Any]:
        return load_json(CANDIDATES)

    def test_the_scorer_equals_the_committed_results(self) -> None:
        load_json(HUNKS)
        actual = candidates.score()
        committed = self.committed()
        if actual != committed:
            raise AssertionError(
                "results/candidates.json differs from the scorer's output; record this JSON as the result: "
                + json.dumps(actual, sort_keys=True)
            )

    def test_the_report_has_exactly_one_winner_line_equal_to_the_results(self) -> None:
        lines = [line for line in REPORT.read_text(encoding="utf-8").splitlines() if line.startswith(WINNER_PREFIX)]
        self.assertEqual(lines, [f"{WINNER_PREFIX}{self.committed()['winner']}"])

    def test_the_report_states_each_candidates_figures_as_recorded(self) -> None:
        report = REPORT.read_text(encoding="utf-8")
        committed = self.committed()
        rows = [report_row(cid, result) for cid, result in committed["candidates"].items()]
        missing = [row for row in rows if row not in report]
        self.assertEqual(missing, [], "the report's table must state the recorded figures")
        counts = committed["process_counts"]
        self.assertIn(str(counts["exact_kind_plan"]["processes"]), report)
        self.assertIn(SECONDS_FORMAT.format(counts["slowest_call"]["seconds"]), report)

    def test_the_report_states_the_post_hoc_figures_as_recorded(self) -> None:
        report = REPORT.read_text(encoding="utf-8")
        post_hoc = self.committed()["post_hoc"]
        self.assertIs(post_hoc["binding"], False)
        self.assertIn(post_hoc["rule"], " ".join(report.split()))
        for cid, result in post_hoc["candidates"].items():
            flagged = "yes" if result["reported_only"]["run-wiki-ingest-rules"] else "no"
            row = (
                f"| {cid} | {result['false_pages_flagged_count']} of {result['false_pages_of']} "
                f"| {result['false_entries_flagged_count']} of {result['false_entries_of']} "
                f"| {result['true_entry']} | {result['supplementary_kept']} of {result['supplementary_of']} "
                f"| {flagged} |"
            )
            self.assertIn(row, report, "the report's post-hoc table must state the recorded figures")

    def test_c0_keeps_every_supplementary_positive(self) -> None:
        supplementary = self.committed()["candidates"]["C0"]["supplementary"]
        self.assertGreater(supplementary["of"], 0)
        self.assertEqual(supplementary["kept"], supplementary["of"])

    def test_the_record_covers_every_case_present_at_the_freeze(self) -> None:
        hunks = load_json(HUNKS)
        frozen_dirs = sorted({Path(name).parent for name in CASE_FILE_SHA256})
        self.assertEqual(len(frozen_dirs), 7)
        for rel in frozen_dirs:
            directory = REVISIONS_DIR / rel
            case = json.loads((directory / "case.json").read_text(encoding="utf-8"))
            with self.subTest(case=case["id"]):
                entry = hunks["cases"][case["id"]]
                if directory.parent == FENCED_DIR:
                    own = directory / record.HUNKS_NAME
                    self.assertEqual(entry, {"recorded_in": own.relative_to(REPO_ROOT).as_posix()})
                    case_record = load_json(own)
                    self.assertEqual(case_record["case"], case["id"])
                    run = case_record["run"]
                else:
                    run = entry
                self.assertEqual(run["read_commit"], case["read_commit"])
                cited = [(s["path"], s["sha"]) for page in run["pages"] for s in page["sources"]]
                self.assertIn((case["path"], case["sha"]), cited)
        self.assertEqual(set(hunks["cases"]), {rel.name for rel in frozen_dirs})

    def test_no_keyword_quoting_hunk_line_appears_outside_the_fence(self) -> None:
        recorded = sorted(FENCED_DIR.glob(f"*/{record.HUNKS_NAME}"))
        self.assertEqual(len(recorded), 3, f"each keyword-quoting case has its own record; {NOT_YET_RECORDED}")
        distinctive: set[str] = set()
        for path in recorded:
            run = load_json(path)["run"]
            for entry in run["paths"]:
                for hunk in entry["hunks"]:
                    distinctive |= {line[1:].strip() for line in hunk["lines"]}
        distinctive = {line for line in distinctive if len(line) >= MIN_DISTINCTIVE_CHARS}
        outside = [
            path
            for path in sorted(REVISIONS_DIR.rglob("*"))
            if path.is_file() and FENCED_DIR not in path.parents and "__pycache__" not in path.parts
        ]
        for path in [*outside, *REVISION_TESTS]:
            text = path.read_text(encoding="utf-8")
            with self.subTest(file=path.relative_to(REPO_ROOT).as_posix()):
                self.assertEqual([line for line in distinctive if line in text], [])

    def test_the_scorer_writes_nothing_and_prints_the_committed_results(self) -> None:
        load_json(HUNKS)
        before = snapshot_tree(REVISIONS_DIR)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(candidates.main([]), 0)
        self.assertEqual(snapshot_tree(REVISIONS_DIR), before)
        self.assertEqual(json.loads(out.getvalue()), self.committed())


class ScriptsTest(unittest.TestCase):
    """Both scripts' command lines (FR-015)."""

    def test_help_exits_zero(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            for script in (record, candidates):
                self.assertEqual(script.main(["--help"]), 0, script.__name__)

    def test_every_shown_command_parses(self) -> None:
        seen = 0
        for page in (README, REPORT):
            if not page.is_file():
                continue
            for match in COMMAND_RE.finditer(page.read_text(encoding="utf-8")):
                module, rest = match.group(1), match.group(2)
                with self.subTest(page=page.name, command=match.group(0)):
                    self.assertIn(module, SCRIPTS)
                    SCRIPTS[module]._build_arg_parser().parse_args(shlex.split(rest))
                    seen += 1
        self.assertGreater(seen, 0, "the report shows how the record and the scores were produced")


DOC_V1 = "# Title\n\nIntro line.\n\n## Second\n\nOld text.\n\n```bash\n# not a heading\n```\n\nTail line.\n"
DOC_HEAD = "Preface.\n" + DOC_V1.replace("Old text.", "New text.").replace("Tail line.", "Tail changed.")


@unittest.skipUnless(GIT is not None, "git is not on PATH")
class RecordFunctionTest(unittest.TestCase):
    """``record.record_run`` on a temporary repository with three commits (FR-015)."""

    def run_git(self, repo: Path, *args: str) -> str:
        assert GIT is not None
        command = [
            GIT,
            "-C",
            str(repo),
            "-c",
            "user.name=revisions-test",
            "-c",
            "user.email=revisions@example.invalid",
            "-c",
            "commit.gpgsign=false",
            *args,
        ]
        return subprocess.run(command, check=True, capture_output=True, text=True).stdout.strip()

    def three_commit_repo(self, repo: Path) -> str:
        """Commit 1 holds every file; commit 2 changes, deletes and adds; commit 3 edits the Markdown file."""
        repo.mkdir()
        self.run_git(repo, "init", "-q")
        files = {
            "keep.txt": "same at every commit\n",
            "change.py": "VALUE = 1\n",
            "gone.txt": "deleted in commit two\n",
            "spaces.txt": "a b\n",
            "doc.md": DOC_V1,
        }
        for name, text in files.items():
            (repo / name).write_text(text, encoding="utf-8")
        self.run_git(repo, "add", ".")
        self.run_git(repo, "commit", "-q", "-m", "one")
        first = self.run_git(repo, "rev-parse", "HEAD")
        (repo / "change.py").write_text("VALUE = 2\n", encoding="utf-8")
        (repo / "gone.txt").unlink()
        (repo / "spaces.txt").write_text("a   b\n", encoding="utf-8")
        (repo / "new.txt").write_text("added in commit two\n", encoding="utf-8")
        self.run_git(repo, "add", "-A")
        self.run_git(repo, "commit", "-q", "-m", "two")
        (repo / "doc.md").write_text(DOC_HEAD, encoding="utf-8")
        self.run_git(repo, "commit", "-q", "-am", "three")
        return first

    def page(self, short: str) -> str:
        cited = [
            ("keep.txt", short),
            ("change.py", short),
            ("gone.txt", short),
            ("spaces.txt", short),
            ("doc.md", short),
            ("new.txt", short),
            ("change.py", None),
            ("change.py", short[:5]),
            ("change.py", short.upper() if short.upper() != short else "ABCDEF1"),
            ("../outside.txt", short),
        ]
        lines = ["---", "page_type: decision", "sources:"]
        for path, sha in cited:
            lines.append(f"  - path: {path}")
            if sha is not None:
                lines.append(f"    sha: {sha}")
        return "\n".join([*lines, "---", "", "# A page", ""])

    def test_presence_change_hunks_and_headings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            first = self.three_commit_repo(repo)
            head = self.run_git(repo, "rev-parse", "HEAD")
            short = first[:7]
            repos = [record.Repository("repo", record.ROLE_SOURCE_ROOT, repo)]
            result = record.record_run([record.Page("page.md", self.page(short))], repos)

        self.assertEqual(
            result["repositories"],
            [{"name": "repo", "role": "source-root", "status": "used", "reason": None, "head": head}],
        )
        sources = result["pages"][0]["sources"]
        summary = [
            (s["path"], s["state"], s["reason"], s["status"], s["present_at_sha"], s["present_at_head"])
            for s in sources
        ]
        self.assertEqual(
            summary,
            [
                ("keep.txt", "checked", None, None, None, None),
                ("change.py", "checked", None, "M", True, True),
                ("gone.txt", "checked", None, "D", True, False),
                ("spaces.txt", "checked", None, "M", True, True),
                ("doc.md", "checked", None, "M", True, True),
                ("new.txt", "exact kind", None, "A", False, True),
                ("change.py", "not checked", "no sha", None, None, None),
                ("change.py", "not checked", "too short", None, None, None),
                ("change.py", "exact kind", "malformed sha", None, None, None),
                ("../outside.txt", "not checked", "path outside repo", None, None, None),
            ],
        )
        for source in sources[:6]:
            self.assertEqual((source["repository"], source["commit"]), ("repo", first))

        paths = {entry["path"]: entry for entry in result["paths"]}
        self.assertEqual(sorted(paths), ["change.py", "doc.md", "spaces.txt"])
        self.assertTrue(paths["change.py"]["p5_differs"])
        self.assertFalse(paths["spaces.txt"]["p5_differs"])
        self.assertEqual(
            [(h["old_start"], h["old_count"], h["lines"]) for h in paths["change.py"]["hunks"]],
            [(1, 1, ["-VALUE = 1", "+VALUE = 2"])],
        )
        self.assertFalse(paths["change.py"]["markdown"])
        self.assertIsNone(paths["change.py"]["hunks"][0]["heading"])
        doc = paths["doc.md"]
        self.assertTrue(doc["markdown"])
        self.assertEqual(
            [(h["old_start"], h["old_count"], h["lines"], h["heading"]) for h in doc["hunks"]],
            [
                (0, 0, ["+Preface."], None),
                (7, 1, ["-Old text.", "+New text."], "Second"),
                (13, 1, ["-Tail line.", "+Tail changed."], "Second"),
            ],
        )
        self.assertEqual(
            {step: totals["processes"] for step, totals in result["steps"].items()},
            {"p1": 1, "p2": 1, "p3": 1, "p4": 1, "p5": 3, "p6": 3, "p7": 1},
        )
        self.assertEqual(len(result["calls"]), 11)

    def test_a_directory_that_is_not_a_repository_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plain = Path(tmp) / "plain"
            plain.mkdir()
            repos = [record.Repository("plain", record.ROLE_SOURCE_ROOT, plain)]
            result = record.record_run([record.Page("page.md", self.page("abcdef1"))], repos)
        self.assertEqual(result["repositories"][0]["status"], "skipped")
        self.assertEqual(result["repositories"][0]["reason"], record.REASON_NOT_A_WORK_TREE)
        states = {(s["path"], s["state"], s["reason"]) for s in result["pages"][0]["sources"]}
        self.assertIn(("keep.txt", "not checked", record.REASON_NOT_FOUND_SKIPPED), states)
        self.assertEqual(result["steps"]["p3"]["processes"], 0)

    def test_the_environment_drops_inherited_git_variables(self) -> None:
        with mock.patch.dict("os.environ", {"GIT_DIR": "/elsewhere", "GIT_CONFIG_GLOBAL": "/dev/null"}):
            env = record.clean_env("/ceiling")
        self.assertNotIn("GIT_DIR", env)
        self.assertEqual(env["GIT_CONFIG_GLOBAL"], "/dev/null")
        self.assertEqual(env["GIT_CEILING_DIRECTORIES"], "/ceiling")
        self.assertEqual((env["GIT_TERMINAL_PROMPT"], env["LC_ALL"]), ("0", "C"))


class FragmentAnchorTest(unittest.TestCase):
    """The post-hoc anchor rule leaves out fragments and keeps whole anchors."""

    PAGE = (
        "---\ntitle: t\n---\n\n## Decision\n\n"
        'Uses `correlate.run`, `scripts/tool.py`, `merge.require_green_ci`, `"`, `0` and `gh`.\n'
    )

    def test_frozen_anchors_include_fragments(self) -> None:
        found = candidates.anchors(self.PAGE)
        self.assertTrue({"run", "py", "0", "gh", "merge.require_green_ci", "require_green_ci"} <= found)

    def test_post_hoc_anchors_leave_out_fragments(self) -> None:
        found = candidates.anchors(self.PAGE, fragments=False)
        self.assertEqual(found, {"correlate.run", "scripts/tool.py", "merge.require_green_ci", "require_green_ci"})


class HeadingRuleTest(unittest.TestCase):
    """The nearest ATX heading at or above a line, outside fenced code (FR-008's heading rule)."""

    def test_headings(self) -> None:
        lines = DOC_V1.split("\n")
        self.assertIsNone(record.heading_above(lines, 0))
        self.assertEqual(record.heading_above(lines, 1), "Title")
        self.assertEqual(record.heading_above(lines, 4), "Title")
        self.assertEqual(record.heading_above(lines, 13), "Second")
        self.assertEqual(record.heading_above(["### Closed ##", "text"], 2), "Closed")


if __name__ == "__main__":
    unittest.main()
