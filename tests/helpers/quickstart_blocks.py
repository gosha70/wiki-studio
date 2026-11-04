# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Run the fenced blocks a quickstart page marks as executable (0.8.1 US1, FR-002).

A page is the only source of its commands (D8): the test reads the markdown
and runs the blocks in page order, so there is no script to keep in step.

The info-string grammar is one word for the renderer and the rest for this
module. ``bash run`` and ``python run`` are executable, optionally followed
by ``exit=<N>`` (the expected exit code, default 0) and ``contains=<token>``
(a token without spaces that stdout must contain). A block without ``run`` is
never executed. ``bash server-cmd`` is not executed here: it names the server
launch line a host or a conformance run uses.

Every block runs in one fresh, resolved temporary project directory, each in
its own process: a ``bash run`` block as ``bash -euo pipefail -c`` over the
block's text, a ``python run`` block as a script file run by this
interpreter. The interpreter's directory comes first on ``PATH``, so
``wiki-studio`` and ``wiki-studio-mcp`` are the installed ones, and every
``WIKI_STUDIO_*`` and ``MEMKERNEL_*`` variable is removed except
``MEMKERNEL_EMBEDDING_MODEL`` (the composition quickstart's pinned model).

A page with no run block, a malformed run info string, or a run block that
could reach a model backend (``wiki-studio ingest``, ``wiki-studio query``,
``--backend``, ``api.ingest``, ``api.query``) is refused before anything
runs. A failed block is reported with its index, first line, exit code,
stdout and stderr.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TIMEOUT_SECONDS = 120.0

_RUN_LANGUAGES = ("bash", "python")
_SERVER_COMMAND_INFO = ("bash", "server-cmd")
_FORBIDDEN_IN_RUN_BLOCKS = ("wiki-studio ingest", "wiki-studio query", "--backend", "api.ingest", "api.query")
_OPEN_FENCE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
_CLOSE_FENCE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})\s*$")


class QuickstartPageError(ValueError):
    """A page that cannot be run: no run block, a malformed one or a forbidden one."""


@dataclass(frozen=True)
class FencedBlock:
    """One fenced code block: its info string, its text and the line its opening fence sits on."""

    info: str
    text: str
    line: int


@dataclass(frozen=True)
class RunBlock:
    """A block the page marks for execution, with the expectations it declares."""

    index: int
    language: str
    text: str
    line: int
    expected_exit: int = 0
    contains: str | None = None

    @property
    def first_line(self) -> str:
        """The first line of the block's text, for a failure report."""
        lines = self.text.splitlines()
        return lines[0].strip() if lines else ""

    @property
    def label(self) -> str:
        """How a failure names this block."""
        return f"block {self.index} (line {self.line}, {self.language} run)"


@dataclass(frozen=True)
class BlockResult:
    """What one block's process produced."""

    block: RunBlock
    exit_code: int
    stdout: str
    stderr: str


class QuickstartBlockError(AssertionError):
    """A block whose exit code or expected output differs; the message names the block."""

    def __init__(self, result: BlockResult, problem: str) -> None:
        self.result = result
        self.problem = problem
        super().__init__(
            f"{result.block.label} {problem}\n"
            f"first line: {result.block.first_line}\n"
            f"--- stdout ---\n{result.stdout}"
            f"--- stderr ---\n{result.stderr}"
        )


def parse_fenced_blocks(markdown: str) -> list[FencedBlock]:
    """Every fenced code block, in page order, with its info string (CommonMark fences)."""
    lines = markdown.splitlines()
    blocks: list[FencedBlock] = []
    line_index = 0
    while line_index < len(lines):
        opened = _OPEN_FENCE.match(lines[line_index])
        if opened is None:
            line_index += 1
            continue
        fence = opened.group("fence")
        info = opened.group("info").strip()
        start = line_index
        body: list[str] = []
        line_index += 1
        while line_index < len(lines):
            closed = _CLOSE_FENCE.match(lines[line_index])
            if closed is not None and closed.group("fence")[0] == fence[0] and len(closed.group("fence")) >= len(fence):
                line_index += 1
                break
            body.append(lines[line_index])
            line_index += 1
        text = "\n".join(body) + ("\n" if body else "")
        blocks.append(FencedBlock(info=info, text=text, line=start + 1))
    return blocks


def _run_block(block: FencedBlock, index: int) -> RunBlock | None:
    """The block's run expectations, or None when the info string does not mark it executable."""
    tokens = block.info.split()
    if "run" not in tokens:
        if "server-cmd" in tokens and tuple(tokens) != _SERVER_COMMAND_INFO:
            raise QuickstartPageError(
                f"line {block.line}: a server command block must be 'bash server-cmd', not {block.info!r}"
            )
        return None
    if len(tokens) < 2 or tokens[0] not in _RUN_LANGUAGES or tokens[1] != "run":
        raise QuickstartPageError(
            f"line {block.line}: a run block must start with 'bash run' or 'python run', not {block.info!r}"
        )
    expected_exit = 0
    contains: str | None = None
    seen_exit = seen_contains = False
    for token in tokens[2:]:
        if token.startswith("exit="):
            if seen_exit:
                raise QuickstartPageError(f"line {block.line}: duplicate exit= in {block.info!r}")
            value = token.removeprefix("exit=")
            if not value.isdigit():
                raise QuickstartPageError(f"line {block.line}: exit= takes a non-negative integer, not {value!r}")
            expected_exit = int(value)
            seen_exit = True
        elif token.startswith("contains="):
            if seen_contains:
                raise QuickstartPageError(f"line {block.line}: duplicate contains= in {block.info!r}")
            value = token.removeprefix("contains=")
            if not value:
                raise QuickstartPageError(f"line {block.line}: contains= takes a non-empty token")
            contains = value
            seen_contains = True
        else:
            raise QuickstartPageError(f"line {block.line}: unknown info-string token {token!r} in {block.info!r}")
    for forbidden in _FORBIDDEN_IN_RUN_BLOCKS:
        if forbidden in block.text:
            raise QuickstartPageError(
                f"line {block.line}: a run block may not reach a model backend (contains {forbidden!r}, FR-002)"
            )
    return RunBlock(
        index=index,
        language=tokens[0],
        text=block.text,
        line=block.line,
        expected_exit=expected_exit,
        contains=contains,
    )


def parse_run_blocks(markdown: str) -> list[RunBlock]:
    """The executable blocks in page order; refuse a page that has none or a forbidden one."""
    run_blocks: list[RunBlock] = []
    for block in parse_fenced_blocks(markdown):
        run = _run_block(block, len(run_blocks) + 1)
        if run is not None:
            run_blocks.append(run)
    if not run_blocks:
        raise QuickstartPageError("the page has no 'bash run' or 'python run' block")
    return run_blocks


def server_command(markdown: str) -> str:
    """The text of the page's one ``bash server-cmd`` block: the launch line a host or suite uses."""
    commands = [
        block.text.strip()
        for block in parse_fenced_blocks(markdown)
        if tuple(block.info.split()) == _SERVER_COMMAND_INFO
    ]
    if len(commands) != 1:
        raise QuickstartPageError(f"the page must have exactly one 'bash server-cmd' block, found {len(commands)}")
    return commands[0]


def child_environment() -> dict[str, str]:
    """The block's environment: this interpreter first, no ``WIKI_STUDIO_*`` or ``MEMKERNEL_*`` leakage.

    ``MEMKERNEL_EMBEDDING_MODEL`` survives because the composition quickstart
    pins memkernel's embedding model through it.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("WIKI_STUDIO_")
        and (not key.startswith("MEMKERNEL_") or key == "MEMKERNEL_EMBEDDING_MODEL")
    }
    scripts = str(Path(sys.executable).parent)
    existing = env.get("PATH", "")
    env["PATH"] = os.pathsep.join(part for part in (scripts, existing) if part)
    return env


def _execute(block: RunBlock, *, workdir: Path, scripts_dir: Path, timeout: float) -> BlockResult:
    """Run one block in its own process, with ``workdir`` as the current directory."""
    env = child_environment()
    if block.language == "bash":
        argv = ["bash", "-euo", "pipefail", "-c", block.text]
    else:
        script = scripts_dir / f"block-{block.index}.py"
        script.write_text(block.text, encoding="utf-8")
        argv = [sys.executable, str(script)]
    try:
        completed = subprocess.run(
            argv,
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", "replace")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", "replace")
        raise QuickstartBlockError(
            BlockResult(block, -1, stdout, stderr), f"did not finish within {timeout:g}s"
        ) from exc
    return BlockResult(block=block, exit_code=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)


def run_quickstart(page: Path, *, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> list[BlockResult]:
    """Run every executable block of ``page`` in one fresh project directory; raise on the first failure."""
    blocks = parse_run_blocks(page.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="wiki-studio-quickstart-") as temporary:
        base = Path(temporary).resolve()
        workdir = base / "project"
        workdir.mkdir()
        results: list[BlockResult] = []
        for block in blocks:
            result = _execute(block, workdir=workdir, scripts_dir=base, timeout=timeout)
            results.append(result)
            if result.exit_code != block.expected_exit:
                raise QuickstartBlockError(result, f"exited {result.exit_code}, expected exit={block.expected_exit}")
            if block.contains is not None and block.contains not in result.stdout:
                raise QuickstartBlockError(result, f"stdout does not contain {block.contains!r}")
        return results
