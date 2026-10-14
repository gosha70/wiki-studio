# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for the test suite.

The suite is unittest-style, so these are plain functions rather than
pytest fixtures. Every test that needs a wiki builds one in a temporary
directory through :func:`make_repo_layout`; nothing reads this
repository's own tree.
"""

from __future__ import annotations

import contextlib
import io
import os
import shutil
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SAMPLE_INCIDENT = FIXTURES_DIR / "sample-incident.md"
PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src" / "wiki_studio"

_INDEX_MD = (
    "---\npage_type: index\nslug: index\ntitle: Test Wiki\nstatus: stable\nlast_reviewed: 2026-05-06\n---\n"
    "\n# Test Wiki\n\n## Incidents\n\n"
)
_LOG_MD = "---\npage_type: log\nslug: log\ntitle: Wiki Log\nstatus: stable\nlast_reviewed: 2026-05-06\n---\n\n# Log\n\n"


def packaged_schema_dir() -> Path:
    """Return the on-disk path of the schema documents shipped with wiki_studio."""
    return Path(str(resources.files("wiki_studio").joinpath("schema")))


def make_repo_layout(
    tmp: Path,
    *,
    with_schema: bool = False,
    with_sample: bool = True,
) -> Path:
    """Build the default project layout under ``tmp`` and return the root.

    Creates ``knowledge/wiki/{index.md,log.md}`` and ``doc_internal/proposals/``.
    ``with_schema`` copies the packaged schema documents to ``knowledge/wiki/schema/``;
    ``with_sample`` copies ``sample-incident.md`` to the root so an unflagged
    ingest stays inside the repository tree.
    """
    root = tmp.resolve()
    wiki = root / "knowledge" / "wiki"
    wiki.mkdir(parents=True, exist_ok=True)
    (wiki / "index.md").write_text(_INDEX_MD, encoding="utf-8")
    (wiki / "log.md").write_text(_LOG_MD, encoding="utf-8")
    (root / "doc_internal" / "proposals").mkdir(parents=True, exist_ok=True)
    if with_schema:
        shutil.copytree(packaged_schema_dir(), wiki / "schema", dirs_exist_ok=True)
    if with_sample:
        shutil.copy(SAMPLE_INCIDENT, root / SAMPLE_INCIDENT.name)
    return root


@contextlib.contextmanager
def chdir(path: Path) -> Iterator[None]:
    """Temporarily change the working directory (the CLI resolves its root from it)."""
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


@dataclass
class CliResult:
    """What an in-process CLI invocation produced; mirrors ``subprocess.CompletedProcess``."""

    returncode: int
    stdout: str
    stderr: str


def run_cli(*argv: str, cwd: Path | None = None) -> CliResult:
    """Run ``wiki_studio.cli.main(argv)`` in-process, capturing stdout and stderr.

    ``SystemExit`` raised by argparse (``--help``, usage errors) is mapped to
    its code so callers can assert on it like a subprocess exit status.
    """
    from wiki_studio.cli import main

    out, err = io.StringIO(), io.StringIO()
    ctx = chdir(cwd) if cwd is not None else contextlib.nullcontext()
    with ctx, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(list(argv))
        except SystemExit as exc:  # argparse exits
            code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    return CliResult(returncode=code, stdout=out.getvalue(), stderr=err.getvalue())
