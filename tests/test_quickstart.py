# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The standalone quickstart page, executed (0.8.1 US1, FR-002..FR-005).

``docs/quickstart.md`` is the only source of its commands (D8): the run
blocks are extracted from the markdown and executed in page order in a fresh
temporary project directory by ``tests/helpers/quickstart_blocks.py``. The
page's ``bash server-cmd`` line is also the line the MCP conformance suite
runs. The parser's refusals (no run block, an ``ingest``/``query``/backend
block) are tested on small pages here.

The conformance check needs the ``mcp`` extra; it is skipped, with the
reason, when the SDK is not importable (the standalone ``quickstart`` CI job
installs it, so the check is not skipped there).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers.quickstart_blocks import (
    QuickstartBlockError,
    QuickstartPageError,
    child_environment,
    parse_fenced_blocks,
    parse_run_blocks,
    run_quickstart,
    server_command,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
QUICKSTART = REPO_ROOT / "docs" / "quickstart.md"
HAS_MCP = importlib.util.find_spec("mcp") is not None


class _PageCase(unittest.TestCase):
    """A scratch directory for pages the parser tests write."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="quickstart-page-")
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()

    def write_page(self, text: str) -> Path:
        path = self.tmp / "page.md"
        path.write_text(text, encoding="utf-8")
        return path


class QuickstartPageTest(unittest.TestCase):
    """FR-002, FR-004: the page's blocks and its launch line."""

    def test_every_run_block_passes_in_page_order(self) -> None:
        results = run_quickstart(QUICKSTART)
        expected = parse_run_blocks(QUICKSTART.read_text(encoding="utf-8"))
        self.assertEqual([result.block.index for result in results], [block.index for block in expected])
        self.assertEqual([result.block.language for result in results].count("python"), 2)
        self.assertGreaterEqual(len(results), 12)

    def test_the_claude_add_command_equals_the_server_command(self) -> None:
        markdown = QUICKSTART.read_text(encoding="utf-8")
        launch = server_command(markdown)
        added = [
            line.strip()
            for block in parse_fenced_blocks(markdown)
            for line in block.text.splitlines()
            if line.strip().startswith("claude mcp add ")
        ]
        self.assertEqual(len(added), 1, added)
        prefix, separator, command = added[0].partition(" -- ")
        self.assertEqual(separator, " -- ", added[0])
        self.assertIn("--env WIKI_STUDIO_ACTOR=you", prefix)
        self.assertEqual(command, launch)

    @unittest.skipUnless(HAS_MCP, "the mcp extra is not installed; the quickstart CI job installs it")
    def test_the_conformance_suite_passes_against_the_page_launch_line(self) -> None:
        launch = server_command(QUICKSTART.read_text(encoding="utf-8")).replace("$PWD", "{root}")
        completed = subprocess.run(
            [sys.executable, "-m", "conformance.mcp.run", "--server-cmd", launch],
            cwd=REPO_ROOT,
            env=child_environment(),
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, f"{completed.stdout}\n{completed.stderr}")


class RunBlockGrammarTest(_PageCase):
    """FR-002: the info-string grammar and the per-block assertions."""

    def test_bash_run_defaults_to_exit_zero(self) -> None:
        blocks = parse_run_blocks(self.write_page("```bash run\nprintf 'ok\\n'\n```\n").read_text(encoding="utf-8"))
        self.assertEqual(len(blocks), 1)
        self.assertEqual((blocks[0].language, blocks[0].expected_exit, blocks[0].contains), ("bash", 0, None))
        self.assertEqual(blocks[0].first_line, "printf 'ok\\n'")

    def test_exit_and_contains_are_read_from_the_info_string(self) -> None:
        page = self.write_page(
            "```bash run exit=3 contains=done\nprintf 'done\\n'\nexit 3\n```\n"
            "```python run exit=0\nprint('next')\n```\n"
        )
        blocks = parse_run_blocks(page.read_text(encoding="utf-8"))
        self.assertEqual(
            [(b.index, b.language, b.expected_exit, b.contains) for b in blocks],
            [
                (1, "bash", 3, "done"),
                (2, "python", 0, None),
            ],
        )
        run_quickstart(page)

    def test_each_block_is_its_own_process_in_one_shared_directory(self) -> None:
        page = self.write_page(
            '```bash run\nLEAK=1\necho one > order.txt\ntest -z "$(ls -A | grep -v order.txt)"\n```\n'
            '```bash run\ntest -z "${LEAK:-}"\necho two >> order.txt\n```\n'
            '```bash run\ntest "$(cat order.txt)" = "$(printf \'one\\ntwo\')"\n```\n'
        )
        self.assertEqual(len(run_quickstart(page)), 3)

    def test_a_block_without_run_is_never_executed(self) -> None:
        page = self.write_page("```bash\ntouch marker.txt\n```\n```bash run\ntest ! -e marker.txt\n```\n")
        self.assertEqual(len(run_quickstart(page)), 1)

    def test_blocks_run_in_a_fresh_project_directory(self) -> None:
        page = self.write_page('```bash run\ntest -z "$(ls -A)"\n```\n')
        run_quickstart(page)

    def test_an_exit_mismatch_names_the_block(self) -> None:
        page = self.write_page("```bash run exit=0\nexit 7\n```\n")
        with self.assertRaises(QuickstartBlockError) as caught:
            run_quickstart(page)
        message = str(caught.exception)
        self.assertIn("block 1", message)
        self.assertIn("exited 7, expected exit=0", message)
        self.assertIn("first line: exit 7", message)

    def test_a_missing_contains_token_names_the_block(self) -> None:
        page = self.write_page("```bash run contains=absent\nprintf 'present\\n'\n```\n")
        with self.assertRaises(QuickstartBlockError) as caught:
            run_quickstart(page)
        message = str(caught.exception)
        self.assertIn("block 1", message)
        self.assertIn("stdout does not contain 'absent'", message)
        self.assertIn("present", message)

    def test_a_malformed_run_info_string_is_refused(self) -> None:
        for info in ("bash exit=1 run", "run bash", "bash run verbose", "bash run exit=one", "bash run exit=1 exit=2"):
            with self.subTest(info=info):
                page = self.write_page(f"```{info}\nexit 0\n```\n")
                with self.assertRaises(QuickstartPageError):
                    parse_run_blocks(page.read_text(encoding="utf-8"))

    def test_a_page_with_no_run_block_is_refused(self) -> None:
        page = self.write_page("# Nothing to run\n\n```bash\nwiki-studio --help\n```\n")
        with self.assertRaises(QuickstartPageError):
            parse_run_blocks(page.read_text(encoding="utf-8"))

    def test_a_run_block_that_reaches_a_model_backend_is_refused(self) -> None:
        for line in (
            "wiki-studio ingest note.md --backend test",
            "wiki-studio query 'question?'",
            "wiki-studio ingest note.md --backend claude",
            "wiki-studio lint --backend claude",
            "python -c 'from wiki_studio import api; api.ingest'",
            "python -c 'from wiki_studio import api; api.query'",
        ):
            with self.subTest(line=line):
                page = self.write_page(f"```bash run\n{line}\n```\n")
                with self.assertRaises(QuickstartPageError):
                    parse_run_blocks(page.read_text(encoding="utf-8"))


class ServerCommandTest(_PageCase):
    """FR-004: the page's launch line is one ``bash server-cmd`` block."""

    def test_server_command_returns_the_block_text(self) -> None:
        page = self.write_page(
            '```bash run\nwiki-studio init\n```\n\n```bash server-cmd\nwiki-studio-mcp --root "$PWD"\n```\n'
        )
        self.assertEqual(server_command(page.read_text(encoding="utf-8")), 'wiki-studio-mcp --root "$PWD"')

    def test_a_page_without_a_server_command_is_refused(self) -> None:
        page = self.write_page("```bash run\ntrue\n```\n")
        with self.assertRaises(QuickstartPageError):
            server_command(page.read_text(encoding="utf-8"))

    def test_two_server_command_blocks_are_refused(self) -> None:
        page = self.write_page(
            "```bash run\ntrue\n```\n```bash server-cmd\nwiki-studio-mcp --root a\n```\n"
            "```bash server-cmd\nwiki-studio-mcp --root b\n```\n"
        )
        with self.assertRaises(QuickstartPageError):
            server_command(page.read_text(encoding="utf-8"))
