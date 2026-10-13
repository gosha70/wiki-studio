# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# aiwiki.audit_flush — the ONLY git-committing module in the wiki pipeline.
#
# Implements `detect_pending(paths) -> PendingState` and
# `flush(paths, dry_run) -> int` for the `ai-wiki audit-flush` verb.
#
# `ai-wiki audit-flush` is the sole pipeline command that runs `git commit`,
# by design and in one place. `ingest`/`promote`/`lint` remain git-free.
# Never auto-invoked, hooked, or scheduled — only user-driven.
#

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .audit_lint import _validate_ingest_log
from .errors import AuditFlushError

if TYPE_CHECKING:
    from .paths import WikiPaths

# Number of fixed preamble lines: "<!-- ingest-log schema v1 -->" + blank.
_PREAMBLE_LINES = 2


@dataclass(frozen=True)
class PendingState:
    """Summary of the uncommitted tail of ingest-log.md."""

    path: Path  # repo-relative POSIX path to ingest-log.md (as a Path)
    pending: int  # N >= 0: data lines in working but not in committed blob
    blob_sha: str | None  # git hash-object of the working file (None if absent)
    diverged: bool  # True when committed bytes are NOT a prefix of working bytes
    malformed: bool  # True when working log is torn or fails audit_lint v1


def _run(argv: list[str], **kw: object) -> subprocess.CompletedProcess[bytes]:
    """Run a subprocess, capturing stdout/stderr as bytes."""
    return subprocess.run(argv, capture_output=True, **kw)  # type: ignore[call-overload]


def _count_data_lines(raw: bytes) -> int:
    """Count NDJSON data lines after the 2-line preamble in raw bytes.

    Lines are split on b'\\n'. The preamble is the first two logical lines
    (the marker line + the empty line). Data lines are non-empty lines
    after the preamble.
    """
    lines = raw.split(b"\n")
    # Drop the preamble lines.
    data_lines = lines[_PREAMBLE_LINES:]
    return sum(1 for ln in data_lines if ln.strip())


def detect_pending(paths: WikiPaths) -> PendingState:
    """Return the pending-state for the ingest log (``paths.audit_log``).

    Reads the committed blob from HEAD via `git show` and the working file
    from disk. Never mutates git or the filesystem.

    Parameters
    ----------
    paths : WikiPaths
        The resolved layout; ``paths.root`` is the git work tree.

    Returns
    -------
    PendingState
        (path, pending, blob_sha, diverged, malformed)

    Raises
    ------
    AuditFlushError
        When the directory is not a git work tree (``git show`` fails with
        a "not a git repository" error) — re-raised at the CLI layer.
        This function propagates the subprocess result; callers must decide
        whether a non-zero `git show` exit means "absent" or "not a repo".
    """
    log_path = paths.audit_log
    log_rel = paths.relative_to_root(log_path)

    # ── Committed blob ────────────────────────────────────────────────────
    result = _run(
        # ``HEAD:./p`` is relative to the -C directory; ``HEAD:p`` would be relative to the toplevel.
        [
            "git",
            "-C",
            str(paths.root),
            "show",
            f"HEAD:{log_rel}" if Path(log_rel).is_absolute() else f"HEAD:./{log_rel}",
        ],
    )
    if result.returncode != 0:
        stderr_text = result.stderr.decode("utf-8", errors="replace")
        # Distinguish "not a git repo" from "file absent at HEAD".
        if "not a git repository" in stderr_text or "not a git repo" in stderr_text:
            raise AuditFlushError(f"not a git work tree: {paths.root}\n  {stderr_text.strip()}")
        # File absent at HEAD (untracked or brand-new): treat as empty committed.
        committed_bytes = b""
    else:
        committed_bytes = result.stdout

    # ── Working file ──────────────────────────────────────────────────────
    if not log_path.exists():
        # Nothing on disk either → trivially clean, nothing pending.
        return PendingState(
            path=Path(log_rel),
            pending=0,
            blob_sha=None,
            diverged=False,
            malformed=False,
        )

    working_bytes = log_path.read_bytes()

    # ── blob_sha via git hash-object ──────────────────────────────────────
    sha_result = _run(
        ["git", "-C", str(paths.root), "hash-object", str(log_path)],
    )
    blob_sha: str | None = sha_result.stdout.decode("ascii").strip() if sha_result.returncode == 0 else None

    # ── Divergence check ──────────────────────────────────────────────────
    # The append-only contract: committed bytes must be a byte-exact prefix
    # of working bytes.
    diverged = not working_bytes.startswith(committed_bytes)

    # ── Malformed check ───────────────────────────────────────────────────
    # (1) Working file must be non-empty and newline-terminated.
    # (2) audit_lint v1 validation must report zero errors.
    malformed = False
    if working_bytes:
        if working_bytes[-1:] != b"\n":
            malformed = True
        else:
            lint_errors = _validate_ingest_log(log_path)
            if lint_errors:
                malformed = True

    # ── Pending count ─────────────────────────────────────────────────────
    working_data = _count_data_lines(working_bytes)
    committed_data = _count_data_lines(committed_bytes) if committed_bytes else 0
    pending = max(0, working_data - committed_data)

    return PendingState(
        path=Path(log_rel),
        pending=pending,
        blob_sha=blob_sha,
        diverged=diverged,
        malformed=malformed,
    )


@dataclass(frozen=True)
class FlushResult:
    """Outcome of an audit-flush run: the pending state and whether a commit was made."""

    state: PendingState
    committed: bool
    dry_run: bool


def flush_state(paths: WikiPaths, dry_run: bool) -> FlushResult:
    """Commit any pending ingest-log lines, or report them in dry-run mode, without printing.

    Parameters
    ----------
    paths : WikiPaths
        The resolved layout; ``paths.root`` is the git work tree.
    dry_run : bool
        When True, never commit; the pending count and blob SHA are in the result.

    Raises
    ------
    AuditFlushError
        For non-git-repo, divergence, malformed log, or a failed git commit.
        A wiki outside the git work tree (``paths.root``) ends here too: git
        rejects the pathspec, which is reported as a failed git add.
    """
    state = detect_pending(paths)
    log_rel = state.path.as_posix()

    # ── Fail-closed gates (apply before dry-run report) ───────────────────
    if state.diverged:
        raise AuditFlushError(
            "audit-flush: append-only invariant violated — committed "
            "ingest-log.md is not a byte prefix of the working copy.\n"
            "  Repair the file before flushing (do not truncate; let the "
            "next correct `wiki ingest` append fix the tail)."
        )
    if state.malformed:
        raise AuditFlushError(
            "audit-flush: working ingest-log.md is malformed (torn final "
            "line, not newline-terminated, or contains a record that fails "
            "audit_lint v1 validation).\n"
            "  Run `ai-wiki lint --strict` for details. The file is "
            "left untouched; the next correct `wiki ingest` append will "
            "repair the tail."
        )

    # ── No-op / dry-run ───────────────────────────────────────────────────
    if state.pending == 0 or state.blob_sha is None or dry_run:
        return FlushResult(state=state, committed=False, dry_run=dry_run)

    # ── Real commit ───────────────────────────────────────────────────────
    # Message BEFORE `--`; pathspec AFTER. `-m` after `--` is parsed as a
    # pathspec by git and fails with "pathspec '-m' did not match".
    if state.pending == 1:
        msg = "audit: flush 1 pending ingest-log line"
    else:
        msg = f"audit: flush {state.pending} pending ingest-log lines"

    # Stage exactly this one file. `git add -- <path>` (not `git add -A`)
    # is required for the initial flush when the file is untracked; for
    # subsequent flushes the file is already tracked so this is a no-op.
    # The pathspec on `git commit` then restricts the commit to only this
    # file even if other paths are staged.
    add_result = _run(["git", "-C", str(paths.root), "add", "--", log_rel])
    if add_result.returncode != 0:
        stderr_text = add_result.stderr.decode("utf-8", errors="replace")
        raise AuditFlushError(f"audit-flush: git add failed (exit {add_result.returncode}):\n  {stderr_text.strip()}")

    commit_result = _run(["git", "-C", str(paths.root), "commit", "-m", msg, "--", log_rel])
    if commit_result.returncode != 0:
        stderr_text = commit_result.stderr.decode("utf-8", errors="replace")
        raise AuditFlushError(
            f"audit-flush: git commit failed (exit {commit_result.returncode}):\n  {stderr_text.strip()}"
        )

    return FlushResult(state=state, committed=True, dry_run=False)


def flush(paths: WikiPaths, dry_run: bool) -> int:
    """``flush_state`` plus the human-readable report on stdout; returns the exit code (0)."""
    report = describe_flush(flush_state(paths, dry_run))
    if report:
        print(report)
    return 0


def describe_flush(result: FlushResult) -> str | None:
    """The one-line report ``ai-wiki audit-flush`` prints; None after a real commit (git already reported)."""
    state = result.state
    if state.pending == 0 or state.blob_sha is None:
        return "nothing to flush"
    if result.dry_run:
        return f"{state.pending} pending ingest-log line(s); blob {state.blob_sha}"
    return None
