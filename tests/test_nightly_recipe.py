# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.10.0 (US5): the cron and CI recipe, checked as a reader copies it (FR-028, FR-029).

``docs/nightly.md`` is the only source of its commands. Every line that
holds ``wiki-studio nightly`` in a ``bash`` block or as a ``run:`` value is
split like a shell line, parsed with the CLI's own parser with every flag
spelled in full, and then run in-process against a temporary wiki with one
draftable finding (the ``--backend`` value is replaced by ``test``). The
wrapper script is run once by ``bash``; the crontab line and the workflow
are checked line by line, with no YAML dependency. The page's install line
is resolved as written by the ``quickstart-memkernel`` job's ``PAGES``
list.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import io
import re
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.conftest import make_repo_layout, run_cli
from tests.helpers.quickstart_blocks import child_environment, parse_fenced_blocks, pip_install_commands
from wiki_studio import api
from wiki_studio.cli import _build_arg_parser
from wiki_studio.paths import WikiPaths

REPO_ROOT = Path(__file__).resolve().parents[1]
PAGE_PATH = REPO_ROOT / "docs" / "nightly.md"
PAGE = PAGE_PATH.read_text(encoding="utf-8")
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

# The wrapper's file name, as the page saves it and the crontab line names it.
WRAPPER_NAME = "nightly-report.sh"
PLACEHOLDER_RE = re.compile(r"<[^<>\n]+>")
_RUN_LINE = re.compile(r"^\s*(?:-\s*)?run:\s*(?P<value>.+?)\s*$")

_INDEX = (
    "---\npage_type: index\nslug: index\ntitle: Test Wiki\nstatus: stable\nlast_reviewed: 2026-11-17\n---\n"
    "\n# Test Wiki\n\n{links}\n"
)

_DECISION = (
    "---\n"
    "page_type: decision\n"
    "slug: {slug}\n"
    "title: {title}\n"
    "status: stable\n"
    "last_reviewed: 2026-11-17\n"
    "sources:\n"
    "  - path: notes.md\n"
    "---\n"
    "\n"
    "# {title}\n"
    "\n"
    "## Decision\n"
    "\n"
    "{body}\n"
    "\n"
    "## Context\n"
    "\n"
    "Agreed with the platform team.\n"
    "\n"
    "## Alternatives considered\n"
    "\n"
    "A fixed delay was rejected.\n"
    "\n"
    "## Consequences\n"
    "\n"
    "Retries are bounded.\n"
)


def _decision(slug: str, body: str) -> str:
    return _DECISION.format(slug=slug, title=slug.replace("-", " ").title(), body=body)


def _bash_blocks(page: str) -> list:
    """Every fenced block whose info string starts with ``bash``."""
    return [block for block in parse_fenced_blocks(page) if block.info.split()[:1] == ["bash"]]


def _yaml_blocks(page: str) -> list:
    """Every fenced block whose info string starts with ``yaml``."""
    return [block for block in parse_fenced_blocks(page) if block.info.split()[:1] == ["yaml"]]


def _nightly_lines(page: str) -> list[str]:
    """Every line holding ``wiki-studio nightly`` in a bash block or as a yaml ``run:`` value."""
    lines: list[str] = []
    for block in _bash_blocks(page):
        lines.extend(line.strip() for line in block.text.splitlines() if "wiki-studio nightly" in line)
    for block in _yaml_blocks(page):
        for line in block.text.splitlines():
            match = _RUN_LINE.match(line)
            if match is not None and "wiki-studio nightly" in match.group("value"):
                lines.append(match.group("value").strip())
    return lines


def _argv(line: str) -> list[str]:
    """``line`` as argv: placeholders become one token, and a given ``--backend`` value becomes ``test``."""
    tokens = shlex.split(PLACEHOLDER_RE.sub("PLACEHOLDER", line))
    for index, token in enumerate(tokens):
        if token == "--backend" and index + 1 < len(tokens):
            tokens[index + 1] = "test"
        elif token.startswith("--backend="):
            tokens[index] = "--backend=test"
    return tokens


def _parse(parser: argparse.ArgumentParser, argv: list[str]) -> tuple[argparse.Namespace | None, str]:
    """The parsed namespace, or None and the stderr argparse printed before its ``SystemExit``."""
    stderr = io.StringIO()
    try:
        with contextlib.redirect_stderr(stderr):
            args = parser.parse_args(argv)
    except SystemExit:
        return None, stderr.getvalue().strip() or "the parser exited without a message"
    return args, stderr.getvalue().strip()


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    """The verb choices of ``_build_arg_parser()``."""
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    raise AssertionError("wiki_studio.cli._build_arg_parser() has no subparsers action")


class RecipeCase(unittest.TestCase):
    """A managed project whose wiki carries one draftable ``missing-cross-link`` finding."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-nightly-recipe-")
        self.root = make_repo_layout(Path(self._tmp.name))
        (self.root / "notes.md").write_text("# notes\n", encoding="utf-8")
        self.paths = WikiPaths.for_root(self.root)
        api.init(self.paths)
        self.wiki = self.paths.wiki_dir
        self.proposals = self.paths.proposals_dir
        links = "\n".join(
            f"- [{Path(rel).stem}]({rel})"
            for rel in ("decisions/queue-policy.md", "decisions/alpha.md", "decisions/beta.md", "decisions/gamma.md")
        )
        (self.wiki / "index.md").write_text(_INDEX.format(links=links), encoding="utf-8")
        pages = {
            "decisions/queue-policy.md": _decision("queue-policy", "The rules live here."),
            "decisions/alpha.md": _decision("alpha", "Use the queue policy before a retry."),
            "decisions/beta.md": _decision("beta", "The queue policy bounds every retry."),
            "decisions/gamma.md": _decision("gamma", "Follow the queue policy."),
        }
        for rel, text in pages.items():
            target = self.wiki / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def proposal_dirs(self) -> list[str]:
        """The pending (non-hidden) proposal directories directly under the proposals directory."""
        return sorted(
            entry.name for entry in self.proposals.iterdir() if entry.is_dir() and not entry.name.startswith(".")
        )


class TestEveryShownNightlyLine(RecipeCase):
    def test_every_line_parses_in_full_and_runs(self) -> None:
        lines = _nightly_lines(PAGE)
        self.assertGreaterEqual(len(lines), 4, lines)
        parser = _build_arg_parser()
        drafted: set[str] = set()
        for line in lines:
            with self.subTest(line=line):
                tokens = _argv(line)
                self.assertEqual(tokens[0], "wiki-studio", line)
                parsed, message = _parse(parser, tokens[1:])
                self.assertIsNotNone(parsed, f"{line!r} does not parse with the CLI's own parser: {message}")
                assert parsed is not None
                allowed = set(_subparsers(parser).choices[parsed.verb]._option_string_actions) | set(
                    parser._option_string_actions
                )
                for token in tokens[1:]:
                    flag = token.split("=", 1)[0]
                    if flag.startswith("--"):
                        self.assertIn(flag, allowed, f"{line!r}: {flag} is not an option of {parsed.verb} in full")
                before = set(self.proposal_dirs())
                result = run_cli(*tokens[1:], cwd=self.root)
                self.assertEqual(result.returncode, 0, f"{line!r} exited {result.returncode}: {result.stderr}")
                if "--backend" in tokens:
                    after = set(self.proposal_dirs())
                    if not drafted:
                        self.assertEqual(len(after - before), 1, f"{line!r} created {sorted(after - before)}")
                        drafted = after - before
                    else:
                        self.assertEqual(after, before, f"{line!r} drafted again on an unchanged wiki")
        self.assertTrue(drafted, "no drafting line created a proposal")


class TestTheCronRecipe(RecipeCase):
    def test_the_wrapper_runs_once_and_writes_the_days_report(self) -> None:
        blocks = [block for block in _bash_blocks(PAGE) if block.text.startswith("#!/usr/bin/env bash")]
        self.assertEqual(len(blocks), 1, "the page shows one wrapper script")
        wrapper = blocks[0].text
        self.assertIn("set -euo pipefail", wrapper)
        script = Path(self._tmp.name) / WRAPPER_NAME
        script.write_text(wrapper.replace("<project-dir>", str(self.root)), encoding="utf-8")
        completed = subprocess.run(
            ["bash", str(script)],
            cwd=self.root,
            env=child_environment(),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        today = datetime.date.today().strftime("%Y-%m-%d")
        report = self.root / "reports" / f"nightly-{today}.md"
        self.assertTrue(report.is_file(), str(report))


class TestTheCrontabLine(unittest.TestCase):
    def test_five_schedule_fields_name_the_wrapper_and_hold_no_percent(self) -> None:
        blocks = [block for block in parse_fenced_blocks(PAGE) if block.info.strip() == "crontab"]
        self.assertEqual(len(blocks), 1, "the page shows one crontab line")
        line = blocks[0].text.strip()
        self.assertNotIn("%", line, "a crontab entry holding % must escape it")
        fields = line.split()
        self.assertEqual(len(fields), 6, line)
        self.assertTrue(fields[5].endswith(WRAPPER_NAME), line)


class TestTheWorkflow(unittest.TestCase):
    def test_the_schedule_install_run_and_upload_steps_are_present(self) -> None:
        workflows = _yaml_blocks(PAGE)
        self.assertEqual(len(workflows), 2, "the page shows the workflow and its drafting variant")
        lines = workflows[0].text.splitlines()
        stripped = [line.strip() for line in lines]
        self.assertIn("on:", stripped)
        self.assertIn("schedule:", stripped)
        self.assertLess(stripped.index("on:"), stripped.index("schedule:"))
        cron = next(line for line in lines if line.strip().startswith("- cron:"))
        self.assertEqual(len(cron.split("cron:", 1)[1].strip().strip('"').split()), 5, cron)
        installs = [line for line in lines if re.search(r"\brun:\s+pip install\b", line)]
        self.assertTrue(installs, "the workflow has a pip install step")
        bash_installs = pip_install_commands(PAGE)
        self.assertEqual(len(bash_installs), 1, "the page shows one bash install line")
        for line in installs:
            self.assertEqual(shlex.split(line.split("run:", 1)[1].strip())[2:], bash_installs[0], line)
        run_index = next(index for index, line in enumerate(lines) if "run:" in line and "wiki-studio nightly" in line)
        self.assertNotIn("--backend", lines[run_index], "the workflow shows the no-backend run first")
        upload_index = next(
            index for index in range(run_index + 1, len(lines)) if "actions/upload-artifact@" in lines[index]
        )
        self.assertTrue(
            any(line.strip() == "- if: always()" for line in lines[run_index:upload_index]),
            "the upload step must run after a failed pass, with if: always()",
        )
        upload = "\n".join(lines[upload_index:])
        self.assertIn("reports/", upload)
        self.assertIn("doc_internal/proposals/", upload)
        drafting = workflows[1].text.splitlines()
        drafting_run = next(line for line in drafting if "run:" in line and "wiki-studio nightly" in line)
        self.assertIn("--backend", drafting_run, "the drafting variant is shown second")


class TestThePageKeepsToItsPhase(unittest.TestCase):
    def test_the_page_names_no_readme_section_and_no_version(self) -> None:
        self.assertNotIn("README", PAGE)
        self.assertIsNone(re.search(r"\b\d+\.\d+\.\d+\b", PAGE), "the page names a release version")


class TestTheInstallLineIsResolved(unittest.TestCase):
    def test_the_page_is_in_the_quickstart_memkernel_pages_list(self) -> None:
        workflow = CI_WORKFLOW.read_text(encoding="utf-8")
        match = re.search(r"PAGES = \[(?P<pages>[^\]]*)\]", workflow)
        self.assertIsNotNone(match, "ci.yml has no PAGES list")
        assert match is not None
        self.assertIn("docs/nightly.md", re.findall(r'"([^"]+)"', match.group("pages")))


if __name__ == "__main__":
    unittest.main()
