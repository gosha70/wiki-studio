# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wiki_studio.revisions — the read-only git layer of the revision check (FR-017 to FR-023).

A page cites its evidence as ``path:`` + ``sha:``. This module answers, for each
such source, whether the cited commit can be found and whether the path was
there at that commit, using git as untrusted input:

* :class:`GitRunner` is the only place a git process starts. It refuses, before
  any process, a request outside a fixed set of read-only plumbing shapes
  (FR-017), runs each allowed one with a fixed prefix of ``-c`` overrides, an
  argument list, an environment stripped of inherited ``GIT_`` variables
  (FR-018) and a timeout, and counts every call against a per-run cap (FR-022).
* :func:`check_sources` builds the repository list (the root's repository, then
  each source root in configured order), classifies each repository once
  (FR-019), validates every ``sha:`` and ``path:`` before it reaches git
  (FR-020), matches each distinct ``sha:`` by commit in list order, stopping at
  an ambiguous prefix (FR-021), and asks one ``diff-tree`` per matched
  (repository, commit) for the cited paths' statuses (FR-023).

Nothing here writes, reads the index or the working tree, or uses the network;
a repository git cannot read safely is skipped with its reason, never forced.
"""

from __future__ import annotations

import os
import posixpath
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .errors import ContractViolationError
from .review import superseded_by
from .yaml_lite import parse_frontmatter

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from subprocess import CompletedProcess

    from .paths import WikiPaths

# FR-020: a ``sha:`` reaches git only as 7-40 lowercase hex characters (fixed, not configurable).
SHA_MIN_LENGTH = 7
SHA_MAX_LENGTH = 40
_SHA_RE = re.compile(f"[0-9a-f]{{{SHA_MIN_LENGTH},{SHA_MAX_LENGTH}}}")
_SHORT_SHA_RE = re.compile(f"[0-9a-f]{{1,{SHA_MIN_LENGTH - 1}}}")
_FULL_COMMIT_RE = re.compile(f"[0-9a-f]{{{SHA_MAX_LENGTH}}}")

# FR-022: the slowest call the study recorded (0.012195 s, a p4 on the study run) times the headroom 10, rounded
# up to whole seconds (1), and at least 10.
GIT_CALL_TIMEOUT_SECONDS = 10

# FR-017: the program and the prefix every call carries before ``-C <dir>``.
GIT_PROGRAM = "git"
GIT_PREFIX: tuple[str, ...] = (
    "--no-pager",
    "-c",
    "core.fsmonitor=false",
    "-c",
    f"core.hooksPath={os.devnull}",
    "-c",
    "protocol.allow=never",
)
GIT_DIRECTORY_FLAG = "-C"
GIT_DIR_NAME = ".git"

# FR-018: every inherited ``GIT_`` variable is dropped except these three, then the settings below are set.
GIT_ENV_PREFIX = "GIT_"
KEPT_GIT_ENV = ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM")
ENV_CEILING_DIRECTORIES = "GIT_CEILING_DIRECTORIES"
SET_GIT_ENV: tuple[tuple[str, str], ...] = (("GIT_TERMINAL_PROMPT", "0"), ("LC_ALL", "C"))

# FR-017 / FR-008: the read-only call plan, p1-p7, as argument shapes.
P1_ARGS: tuple[str, ...] = ("rev-parse", "--show-toplevel", "--is-shallow-repository", "HEAD")
P2_ARGS: tuple[str, ...] = ("config", "--get", "extensions.partialclone")
P3_HEAD: tuple[str, ...] = ("rev-parse", "--verify")
COMMIT_PEEL = "^{commit}"
P4_HEAD: tuple[str, ...] = (
    "diff-tree",
    "-r",
    "--name-status",
    "--no-renames",
    "--relative",
    "--no-ext-diff",
    "--no-textconv",
)
DIFF_HEAD: tuple[str, ...] = ("diff", "--no-ext-diff", "--no-textconv")
P5_FLAGS: tuple[str, ...] = ("--quiet", "-w", "--ignore-blank-lines")
P6_FLAGS: tuple[str, ...] = ("-U0",)
P7_HEAD: tuple[str, ...] = ("cat-file", "blob")
BLOB_PATH_SEPARATOR = ":./"
PATH_SEPARATOR = "--"
# ``<commit> <commit> -- <path>``: the shortest tail of p4-p6 after their flags.
DIFF_TAIL_MIN = 4

ROLE_ROOT = "root"
ROLE_SOURCE_ROOT = "source-root"
STATUS_USED = "used"
STATUS_SKIPPED = "skipped"
STATE_ON = "on"
STATE_OFF = "off"
# FR-027: the text output's line starts with this; the nightly header names it itself.
SUMMARY_PREFIX = "revision check: "

# FR-019: why a repository is skipped, and FR-026: why the check is off.
REASON_NOT_A_WORK_TREE = "not a git work tree"
REASON_NOT_TOP = "not the top of a git work tree"
REASON_SHALLOW = "shallow clone"
REASON_PARTIAL = "partial clone"
REASON_OWNERSHIP = "refused by git: repository ownership"
REASON_NO_HEAD = "no HEAD commit"
REASON_TIMED_OUT = "git call timed out"
REASON_CALL_LIMIT = "git call limit ({limit}) reached"
REASON_GIT_NOT_FOUND = "git not found"
REASON_NO_USABLE_REPOSITORY = "no usable repository"
# FR-020 and FR-021: why a source is not checked.
REASON_NO_SHA = "no sha"
REASON_TOO_SHORT = "too short"
REASON_PATH_OUTSIDE = "path outside {directory}"
REASON_AMBIGUOUS = "ambiguous in {repository}"
REASON_NOT_FOUND_SKIPPED = "commit not found in the usable repositories"
# FR-025: the three causes of ``source-not-at-revision``.
CAUSE_NOT_AT_COMMIT = "path not at the commit"
CAUSE_COMMIT_NOT_FOUND = "commit not found in any repository"
CAUSE_MALFORMED = "malformed sha"

# One cited source's outcome.
OUTCOME_NOT_AT_REVISION = "not-at-revision"
OUTCOME_CHANGED = "changed"
OUTCOME_UNCHANGED = "unchanged"
OUTCOME_ABSENT_AT_HEAD = "absent-at-head"
OUTCOME_NOT_CHECKED = "not-checked"

# What git prints under ``LC_ALL=C``.
STDERR_AMBIGUOUS = "is ambiguous"
STDERR_NOT_FOUND = "Needed a single revision"
STDERR_NOT_A_REPOSITORY = "not a git repository"
STDERR_NOT_A_WORK_TREE = "must be run in a work tree"
STDERR_CANNOT_CHANGE_DIRECTORY = "cannot change to"
STDERR_OWNERSHIP = "dubious ownership"
SHALLOW_TRUE = "true"
# p1 prints the toplevel, the shallow flag and HEAD's full commit, one per line.
P1_OUTPUT_LINES = 3
P2_KEY_NOT_SET = 1

# p4's statuses (``--name-status --no-renames``).
STATUS_LETTER_ADDED = "A"
STATUS_LETTER_DELETED = "D"
STATUS_LETTERS_CHANGED = frozenset({"M", "T"})

SOURCES_KEY = "sources"
SOURCE_PATH_KEY = "path"
SOURCE_SHA_KEY = "sha"


class GitRefusedError(ValueError):
    """A git request outside the read-only set of FR-017; raised before any process starts."""


class GitCallLimitError(RuntimeError):
    """The per-run cap of FR-022 is reached; no further git call runs."""

    def __init__(self, limit: int) -> None:
        super().__init__(REASON_CALL_LIMIT.format(limit=limit))
        self.limit = limit


class GitTimeoutError(RuntimeError):
    """A git call ran past ``GIT_CALL_TIMEOUT_SECONDS``."""


def contained_path(path: str) -> str | None:
    """The normalised ``path`` when it is relative and stays inside its directory, else None (FR-020).

    Lexical only: no absolute path, no NUL, no leading ``..`` component after
    ``posixpath.normpath``, and not the directory itself.
    """
    if not path or "\x00" in path or posixpath.isabs(path):
        return None
    normal = posixpath.normpath(path)
    if normal in (posixpath.curdir, posixpath.pardir) or normal.startswith(posixpath.pardir + posixpath.sep):
        return None
    return normal


def _is_full_commit(value: str) -> bool:
    return bool(_FULL_COMMIT_RE.fullmatch(value))


def _is_clean_path(value: str) -> bool:
    return contained_path(value) == value


def _two_commits_then_paths(rest: Sequence[str], *, single_path: bool) -> bool:
    """``<commit> <commit> -- <path>...`` with full commits and contained paths (one path when ``single_path``)."""
    if len(rest) < DIFF_TAIL_MIN or (single_path and len(rest) != DIFF_TAIL_MIN):
        return False
    old, new, separator, *cited = rest
    return (
        _is_full_commit(old)
        and _is_full_commit(new)
        and separator == PATH_SEPARATOR
        and all(map(_is_clean_path, cited))
    )


def is_allowed(args: Sequence[str]) -> bool:
    """Whether ``args`` (after the prefix and ``-C <dir>``) is one of FR-017's read-only shapes, p1-p7."""
    argv = tuple(args)
    if argv in (P1_ARGS, P2_ARGS):
        return True
    if argv[: len(P3_HEAD)] == P3_HEAD and len(argv) == len(P3_HEAD) + 1:
        target = argv[-1]
        return target.endswith(COMMIT_PEEL) and bool(_SHA_RE.fullmatch(target.removesuffix(COMMIT_PEEL)))
    if argv[: len(P4_HEAD)] == P4_HEAD:
        return _two_commits_then_paths(argv[len(P4_HEAD) :], single_path=False)
    if argv[: len(DIFF_HEAD)] == DIFF_HEAD:
        rest = argv[len(DIFF_HEAD) :]
        return any(
            rest[: len(flags)] == flags and _two_commits_then_paths(rest[len(flags) :], single_path=True)
            for flags in (P5_FLAGS, P6_FLAGS)
        )
    if argv[: len(P7_HEAD)] == P7_HEAD and len(argv) == len(P7_HEAD) + 1:
        commit, separator, path = argv[-1].partition(BLOB_PATH_SEPARATOR)
        return bool(separator) and _is_full_commit(commit) and _is_clean_path(path)
    return False


def git_environment(ceiling: Path | None, *, base: Mapping[str, str] | None = None) -> dict[str, str]:
    """FR-018's environment: ``base`` (default ``os.environ``) without inherited ``GIT_`` variables but three.

    Then ``GIT_TERMINAL_PROMPT=0`` and ``LC_ALL=C`` are set, and
    ``GIT_CEILING_DIRECTORIES`` when a ``ceiling`` is given. System and global
    config stay in effect.
    """
    source = os.environ if base is None else base
    env = {name: value for name, value in source.items() if not name.startswith(GIT_ENV_PREFIX) or name in KEPT_GIT_ENV}
    env.update(SET_GIT_ENV)
    if ceiling is not None:
        env[ENV_CEILING_DIRECTORIES] = str(ceiling)
    return env


class GitRunner:
    """The one place the revision check starts git (FR-017, FR-018, FR-022).

    ``run`` refuses a request outside :func:`is_allowed` with
    :class:`GitRefusedError` and a request past ``limit`` with
    :class:`GitCallLimitError`, both before any process starts; every started
    call counts. A call past ``timeout`` raises :class:`GitTimeoutError`; git
    missing from PATH surfaces as an ``OSError``.
    """

    def __init__(self, limit: int, *, timeout: float = GIT_CALL_TIMEOUT_SECONDS) -> None:
        self.limit = limit
        self.timeout = timeout
        self.calls = 0

    def run(self, directory: Path, args: Sequence[str], *, ceiling: Path | None) -> CompletedProcess[str]:
        argv = tuple(args)
        if not is_allowed(argv):
            raise GitRefusedError(f"git request outside the read-only set: {list(argv)!r}")
        if self.calls >= self.limit:
            raise GitCallLimitError(self.limit)
        self.calls += 1
        try:
            return subprocess.run(
                [GIT_PROGRAM, *GIT_PREFIX, GIT_DIRECTORY_FLAG, str(directory), *argv],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                env=git_environment(ceiling),
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitTimeoutError(f"git {argv[0]} in {directory} ran past {self.timeout} s") from exc


@dataclass(frozen=True)
class Repository:
    """One repository of the list, as classified (FR-019, FR-026)."""

    path: Path
    role: str
    status: str
    reason: str | None
    head: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "role": self.role,
            "status": self.status,
            "reason": self.reason,
            "head": self.head,
        }


@dataclass(frozen=True)
class SourceCheck:
    """One cited source's outcome: ``OUTCOME_*``, with its reason or cause, matched repository and full commit."""

    page: str
    path: str
    sha: str | None
    outcome: str
    reason: str | None
    repository: Repository | None
    commit: str | None


@dataclass(frozen=True)
class RevisionCheck:
    """The run's state, its repositories in list order and every examined source (FR-026)."""

    state: str
    reason: str | None
    repositories: tuple[Repository, ...]
    sources: tuple[SourceCheck, ...]

    @property
    def sources_checked(self) -> int:
        return sum(1 for source in self.sources if source.outcome != OUTCOME_NOT_CHECKED)

    @property
    def sources_not_checked(self) -> int:
        return len(self.sources) - self.sources_checked

    def not_checked(self) -> dict[str, int]:
        """Sources not checked, counted by reason in first-seen order (O9)."""
        counts: dict[str, int] = {}
        for source in self.sources:
            if source.outcome == OUTCOME_NOT_CHECKED:
                key = source.reason or ""
                counts[key] = counts.get(key, 0) + 1
        return counts

    def as_dict(self) -> dict[str, Any]:
        """FR-026's ``revision_check`` object."""
        return {
            "state": self.state,
            "reason": self.reason,
            "repositories": [repository.as_dict() for repository in self.repositories],
            "sources_checked": self.sources_checked,
            "sources_not_checked": self.sources_not_checked,
            "not_checked": self.not_checked(),
        }

    def summary(self) -> str:
        """FR-027's one line."""
        if self.state == STATE_OFF:
            return f"{SUMMARY_PREFIX}{STATE_OFF} ({self.reason})"
        used = sum(1 for repository in self.repositories if repository.status == STATUS_USED)
        return (
            f"{SUMMARY_PREFIX}{STATE_ON} ({used} of {len(self.repositories)} repositories used); "
            f"{self.sources_checked} sources checked, {self.sources_not_checked} not checked"
        )


class _Repo:
    """A repository while the run classifies and probes it; ``status`` None until classified."""

    def __init__(self, path: Path, role: str) -> None:
        self.path = path
        self.role = role
        self.status: str | None = None
        self.reason: str | None = None
        self.head: str | None = None
        self.ceiling: Path | None = None

    def skip(self, reason: str) -> None:
        self.status, self.reason = STATUS_SKIPPED, reason

    @property
    def usable(self) -> bool:
        return self.status == STATUS_USED

    def frozen(self) -> Repository:
        return Repository(self.path, self.role, self.status or STATUS_SKIPPED, self.reason, self.head)


class _Source:
    """A cited source while the run decides it; ``outcome`` None until decided."""

    def __init__(self, page: str, path: str, sha: str | None) -> None:
        self.page = page
        self.path = path
        self.sha = sha
        self.outcome: str | None = None
        self.reason: str | None = None
        self.repo: _Repo | None = None
        self.commit: str | None = None

    def decide(self, outcome: str, reason: str | None = None) -> None:
        self.outcome, self.reason = outcome, reason

    def not_checked(self, reason: str) -> None:
        self.decide(OUTCOME_NOT_CHECKED, reason)


def _call(runner: GitRunner, repo: _Repo, args: Sequence[str], ceiling: Path | None) -> CompletedProcess[str] | None:
    """One call for ``repo``; a timeout skips the repository for the rest of the run and returns None."""
    try:
        return runner.run(repo.path, args, ceiling=ceiling)
    except GitTimeoutError:
        repo.skip(REASON_TIMED_OUT)
        return None


def _message(result: CompletedProcess[str]) -> str:
    """Git's last non-empty stderr line, or the exit status when it printed nothing."""
    lines = [line.strip() for line in result.stderr.splitlines() if line.strip()]
    return lines[-1] if lines else f"git exited {result.returncode}"


def _classify(runner: GitRunner, repo: _Repo) -> None:
    """p1 and p2, once per run: status, reason, HEAD and the ceiling for later calls (FR-019)."""
    resolved = repo.path.resolve()
    p1 = _call(runner, repo, P1_ARGS, None if repo.role == ROLE_ROOT else resolved.parent)
    if p1 is None:
        return
    if p1.returncode != 0:
        stderr = p1.stderr
        if STDERR_OWNERSHIP in stderr:
            repo.skip(REASON_OWNERSHIP)
        elif any(
            marker in stderr
            for marker in (STDERR_NOT_A_REPOSITORY, STDERR_NOT_A_WORK_TREE, STDERR_CANNOT_CHANGE_DIRECTORY)
        ):
            # Under its ceiling git cannot see a repository above a source root; a ``.git`` there means the
            # configured directory is a subdirectory of a work tree, which is never used (no git call decides it).
            above = repo.role == ROLE_SOURCE_ROOT and any(
                (parent / GIT_DIR_NAME).exists() for parent in resolved.parents
            )
            repo.skip(REASON_NOT_TOP if above else REASON_NOT_A_WORK_TREE)
        else:
            repo.skip(REASON_NO_HEAD)
        return
    lines = [line.strip() for line in p1.stdout.splitlines()]
    if len(lines) < P1_OUTPUT_LINES or not lines[0]:
        repo.skip(REASON_NO_HEAD)
        return
    toplevel, shallow, head = Path(lines[0]).resolve(), lines[1], lines[2]
    if repo.role == ROLE_SOURCE_ROOT and toplevel != resolved:
        repo.skip(REASON_NOT_TOP)
        return
    if shallow == SHALLOW_TRUE:
        repo.skip(REASON_SHALLOW)
        return
    if not _is_full_commit(head):
        repo.skip(REASON_NO_HEAD)
        return
    repo.ceiling = toplevel.parent
    p2 = _call(runner, repo, P2_ARGS, repo.ceiling)
    if p2 is None:
        return
    if p2.returncode == 0:
        repo.skip(REASON_PARTIAL)
        return
    if p2.returncode != P2_KEY_NOT_SET:
        repo.skip(_message(p2))
        return
    repo.status, repo.head = STATUS_USED, head


@dataclass(frozen=True)
class _Probe:
    """Where a ``sha:`` matched (``repo`` and ``commit``), or why it did not (``reason``, ``finding``)."""

    repo: _Repo | None = None
    commit: str | None = None
    reason: str | None = None
    finding: bool = False


def _probe(runner: GitRunner, repos: Sequence[_Repo], sha: str) -> _Probe:
    """p3 in list order until the first match or ambiguity (FR-021)."""
    skipped_any = False
    for repo in repos:
        if not repo.usable:
            skipped_any = True
            continue
        p3 = _call(runner, repo, (*P3_HEAD, f"{sha}{COMMIT_PEEL}"), repo.ceiling)
        if p3 is None:
            skipped_any = True
            continue
        out = p3.stdout.strip()
        if p3.returncode == 0 and _is_full_commit(out):
            return _Probe(repo=repo, commit=out)
        if p3.returncode != 0 and STDERR_AMBIGUOUS in p3.stderr:
            return _Probe(reason=REASON_AMBIGUOUS.format(repository=repo.path))
        if p3.returncode != 0 and STDERR_NOT_FOUND in p3.stderr:
            continue
        repo.skip(_message(p3))
        skipped_any = True
    if skipped_any:
        return _Probe(reason=REASON_NOT_FOUND_SKIPPED)
    return _Probe(reason=CAUSE_COMMIT_NOT_FOUND, finding=True)


def _validate(source: _Source) -> None:
    """FR-020 for the ``sha:``: a value that may not reach git decides the source here, with no call."""
    sha = source.sha
    if not sha:
        source.not_checked(REASON_NO_SHA)
    elif _SHORT_SHA_RE.fullmatch(sha):
        source.not_checked(REASON_TOO_SHORT)
    elif not _SHA_RE.fullmatch(sha):
        source.decide(OUTCOME_NOT_AT_REVISION, CAUSE_MALFORMED)


def _statuses(runner: GitRunner, repo: _Repo, commit: str, sources: Sequence[_Source]) -> None:
    """One p4 for (repository, commit): each cited path's status decides its source (FR-023)."""
    if not repo.usable or repo.head is None:
        for source in sources:
            source.not_checked(repo.reason or REASON_NOT_FOUND_SKIPPED)
        return
    cited = list(dict.fromkeys(str(contained_path(source.path)) for source in sources))
    p4 = _call(runner, repo, (*P4_HEAD, commit, repo.head, PATH_SEPARATOR, *cited), repo.ceiling)
    if p4 is not None and p4.returncode != 0:
        repo.skip(_message(p4))
    if p4 is None or p4.returncode != 0:
        for source in sources:
            source.not_checked(repo.reason or REASON_TIMED_OUT)
        return
    letters: dict[str, str] = {}
    for line in p4.stdout.splitlines():
        letter, _, listed = line.partition("\t")
        letters[listed] = letter[:1]
    for source in sources:
        letter = letters.get(str(contained_path(source.path)), "")
        if letter == STATUS_LETTER_ADDED:
            source.decide(OUTCOME_NOT_AT_REVISION, CAUSE_NOT_AT_COMMIT)
        elif letter == STATUS_LETTER_DELETED:
            source.decide(OUTCOME_ABSENT_AT_HEAD)
        elif letter in STATUS_LETTERS_CHANGED:
            source.decide(OUTCOME_CHANGED)
        else:
            source.decide(OUTCOME_UNCHANGED)


def _run_plan(runner: GitRunner, repos: Sequence[_Repo], sources: Sequence[_Source]) -> None:
    """Classify, match and batch (FR-019, FR-021, FR-023); exceptions of the runner propagate."""
    for repo in repos:
        _classify(runner, repo)
    pending = [source for source in sources if source.outcome is None]
    if not any(repo.usable for repo in repos):
        return
    probes: dict[str, _Probe] = {}
    groups: dict[tuple[int, str], list[_Source]] = {}
    for source in pending:
        sha = str(source.sha)
        if sha not in probes:
            probes[sha] = _probe(runner, repos, sha)
        probe = probes[sha]
        if probe.repo is None or probe.commit is None:
            if probe.finding:
                source.decide(OUTCOME_NOT_AT_REVISION, probe.reason)
            else:
                source.not_checked(probe.reason or REASON_NOT_FOUND_SKIPPED)
            continue
        source.repo, source.commit = probe.repo, probe.commit
        if contained_path(source.path) is None:
            source.not_checked(REASON_PATH_OUTSIDE.format(directory=probe.repo.path))
            continue
        groups.setdefault((repos.index(probe.repo), probe.commit), []).append(source)
    for (index, commit), grouped in groups.items():
        _statuses(runner, repos[index], commit, grouped)


def _repositories(paths: WikiPaths) -> list[_Repo]:
    """The root's repository first, then each source root in configured order (FR-019)."""
    return [_Repo(paths.root, ROLE_ROOT), *(_Repo(root, ROLE_SOURCE_ROOT) for root in paths.source_roots)]


def _cited_sources(paths: WikiPaths, pages: Sequence[str]) -> list[_Source]:
    """Every ``sources:`` entry with a ``path:`` of each readable page that does not carry ``superseded_by``."""
    found: list[_Source] = []
    for page in pages:
        try:
            text = (paths.wiki_dir / page).read_text(encoding="utf-8")
            frontmatter = parse_frontmatter(text)
        except (OSError, UnicodeDecodeError, ContractViolationError):
            continue
        if superseded_by(text) is not None:
            continue
        entries = frontmatter.get(SOURCES_KEY)
        for entry in entries if isinstance(entries, list) else ():
            if isinstance(entry, dict) and entry.get(SOURCE_PATH_KEY):
                found.append(_Source(page, str(entry[SOURCE_PATH_KEY]), entry.get(SOURCE_SHA_KEY) or None))
    return found


def check_sources(paths: WikiPaths, pages: Sequence[str], *, runner: GitRunner | None = None) -> RevisionCheck:
    """Check every cited ``path:`` + ``sha:`` of ``pages`` (wiki-relative) against the repository list.

    Read-only: a skipped repository, an ambiguous or unknown commit, a path
    outside its directory, git missing and the call cap each leave sources
    *not checked* with their reason, never a finding. With no usable
    repository the state is ``off`` and no source is decided by git.
    """
    runner = GitRunner(paths.git_call_limit) if runner is None else runner
    repos = _repositories(paths)
    sources = _cited_sources(paths, pages)
    for source in sources:
        _validate(source)
    leftover: str | None = None
    try:
        _run_plan(runner, repos, sources)
    except OSError:
        leftover = REASON_GIT_NOT_FOUND
    except GitCallLimitError as exc:
        leftover = str(exc)
    if leftover is not None:
        for repo in repos:
            if repo.status is None:
                repo.skip(leftover)
    usable = any(repo.head is not None for repo in repos)
    reason = (
        None if usable else (REASON_GIT_NOT_FOUND if leftover == REASON_GIT_NOT_FOUND else REASON_NO_USABLE_REPOSITORY)
    )
    frozen = {id(repo): repo.frozen() for repo in repos}
    checks: list[SourceCheck] = []
    for source in sources:
        if source.outcome is None:
            source.not_checked(leftover or REASON_NOT_FOUND_SKIPPED)
        if reason is not None and source.outcome != OUTCOME_NOT_CHECKED:
            source.not_checked(reason)
        checks.append(
            SourceCheck(
                page=source.page,
                path=source.path,
                sha=source.sha,
                outcome=str(source.outcome),
                reason=source.reason,
                repository=frozen[id(source.repo)] if source.repo is not None else None,
                commit=source.commit,
            )
        )
    return RevisionCheck(
        state=STATE_OFF if reason is not None else STATE_ON,
        reason=reason,
        repositories=tuple(frozen[id(repo)] for repo in repos),
        sources=tuple(checks),
    )
