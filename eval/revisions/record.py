# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The revision-check study's record: git's answers for every cited source, once (FR-012).

``python -m eval.revisions.record --checkout PATH [--out PATH]`` reads a local
code-copilot-team checkout and records what the frozen call plan of
``protocol.json`` sees, so that ``candidates.py`` can score C0-C4 without git.

Setup, local only: inside a ``tempfile.TemporaryDirectory()`` (removed at the
end) it runs ``git clone --no-hardlinks --no-checkout <checkout> <tmp>/<name>``
and ``git -C <tmp>/<name> checkout --quiet --detach <commit>``, one clone at the
study's pin and one per case at its read commit. The checkout itself is only
read. Before recording it checks each case's ``sha256.source_at_sha`` and
``sha256.source_at_read`` against the cited file's bytes in the checkout and
stops, naming the case, on a mismatch.

The study run takes this wiki-studio checkout as the root (the wiki being
``eval/patterns/wiki/``) and the pin clone as the one source root; the
pre-successor copy and each case page are recorded the same way, each against
its own clone. Every call follows the call plan p1-p7 in repository order,
with the command prefix ``git --no-pager -c core.fsmonitor=false -c
core.hooksPath=<devnull> -c protocol.allow=never -C <dir>``, an environment
with every inherited ``GIT_`` variable dropped except the three config-location
ones, an argument list, no shell and no network.

Output: ``results/hunks.json``. Everything recorded for a keyword-quoting case
goes to that case's own ``cases/keyword-quoting/<id>/hunks.json`` instead, and
``results/hunks.json`` names such a case by id only (FR-009). Nothing else is
written. A checkout that lacks a commit exits 2; a pin mismatch exits 3; a git
call that fails outside the classification steps exits 4. In each case nothing
is written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from wiki_studio.yaml_lite import parse_frontmatter

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

REVISIONS_DIR = Path(__file__).resolve().parent
REPO_ROOT = REVISIONS_DIR.parents[1]
PROTOCOL = REVISIONS_DIR / "protocol.json"
LABELS = REVISIONS_DIR / "labels.json"
CASES_DIR = REVISIONS_DIR / "cases"
KEYWORD_QUOTING_DIR = CASES_DIR / "keyword-quoting"
DEFAULT_OUT = REVISIONS_DIR / "results" / "hunks.json"
HUNKS_NAME = "hunks.json"
STUDY = "issue 120 revision check: the record"

ROOT_NAME = "wiki-studio"
SOURCE_NAME = "code-copilot-team"
ROLE_ROOT = "root"
ROLE_SOURCE_ROOT = "source-root"
RUN_STUDY = "study"
RUN_PRE_SUCCESSOR = "pre-successor"
PRE_SUCCESSOR_PAGE = "pre-successor/merge-require-green-ci-was-never-read.md"

# FR-018: the inherited GIT_ variables that are kept; every other GIT_ variable is dropped.
GIT_ENV_PREFIX = "GIT_"
GIT_ENV_KEPT = frozenset({"GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM"})
GIT_ENV_SET = {"GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"}
GIT_CEILING = "GIT_CEILING_DIRECTORIES"
# FR-017's prefix, after the program name and before ``-C <dir>``.
GIT_PREFIX = (
    "--no-pager",
    "-c",
    "core.fsmonitor=false",
    "-c",
    f"core.hooksPath={os.devnull}",
    "-c",
    "protocol.allow=never",
)
# The record's own per-call limit; the shipped timeout is derived from what this run records (FR-022).
RECORD_CALL_TIMEOUT_SECONDS = 120
SECONDS_DIGITS = 6

# FR-019's skip reasons, as the shipped layer will word them.
REASON_NOT_A_WORK_TREE = "not a git work tree"
REASON_NOT_TOP = "not the top of a git work tree"
REASON_SHALLOW = "shallow clone"
REASON_PARTIAL = "partial clone"
REASON_OWNERSHIP = "refused by git: repository ownership"
REASON_NO_HEAD = "no HEAD commit"
REASON_TIMED_OUT = "git call timed out"
# FR-020 and FR-021's reasons for a source that is not checked.
REASON_NO_SHA = "no sha"
REASON_TOO_SHORT = "too short"
REASON_PATH_OUTSIDE = "path outside {name}"
REASON_AMBIGUOUS = "ambiguous in {name}"
REASON_NOT_FOUND_SKIPPED = "commit not found in the usable repositories"
REASON_NOT_FOUND = "commit not found in any repository"
REASON_MALFORMED = "malformed sha"

STATE_CHECKED = "checked"
STATE_NOT_CHECKED = "not checked"
STATE_EXACT = "exact kind"
STATUS_USED = "used"
STATUS_SKIPPED = "skipped"

SHA_RE = re.compile(r"[0-9a-f]{7,40}")
SHORT_SHA_RE = re.compile(r"[0-9a-f]{1,6}")
FULL_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
STDERR_AMBIGUOUS = "is ambiguous"
STDERR_NOT_FOUND = "Needed a single revision"
STDERR_NOT_A_REPO = "not a git repository"
STDERR_NOT_A_WORK_TREE = "must be run in a work tree"
STDERR_OWNERSHIP = "dubious ownership"
HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
ATX_HEADING_RE = re.compile(r"^ {0,3}#{1,6}(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
MAX_FENCE_INDENT = 3
MARKDOWN_SUFFIX = ".md"
STATUS_ADDED = "A"
STATUS_DELETED = "D"
CHANGED_STATUSES = frozenset({"M", "T"})

STEPS = ("p1", "p2", "p3", "p4", "p5", "p6", "p7")

CHECKOUT_UNREADABLE = 2
PIN_MISMATCH = 3
GIT_FAILED = 4


class CheckoutError(RuntimeError):
    """The checkout lacks a commit the record needs."""


class PinMismatchError(RuntimeError):
    """A case's recorded source hash differs from the checkout's bytes."""


class RecordError(RuntimeError):
    """A git call outside the classification steps failed, so the record is incomplete."""


@dataclass
class Repository:
    """One repository of a run's list, in order: the root's first, then the source roots."""

    name: str
    role: str
    path: Path
    status: str = STATUS_USED
    reason: str | None = None
    head: str | None = None
    ceiling: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "role": self.role, "status": self.status, "reason": self.reason, "head": self.head}


@dataclass
class Page:
    """A page the run examines: its id in the record and its text."""

    page: str
    text: str


@dataclass
class _Run:
    """The calls and their timings for one run."""

    calls: list[dict[str, Any]] = field(default_factory=list)


def clean_env(ceiling: str | None) -> dict[str, str]:
    """``os.environ`` without inherited ``GIT_`` variables (three kept), plus FR-018's settings."""
    env = {
        name: value for name, value in os.environ.items() if not name.startswith(GIT_ENV_PREFIX) or name in GIT_ENV_KEPT
    }
    env.update(GIT_ENV_SET)
    if ceiling is not None:
        env[GIT_CEILING] = ceiling
    return env


def _git(directory: Path, args: Sequence[str], *, ceiling: str | None) -> subprocess.CompletedProcess[bytes]:
    """One hardened, read-only git call: argument list, no shell, clean environment, timeout."""
    return subprocess.run(
        ["git", *GIT_PREFIX, "-C", str(directory), *args],
        capture_output=True,
        env=clean_env(ceiling),
        timeout=RECORD_CALL_TIMEOUT_SECONDS,
        check=False,
    )


def _timed(
    run: _Run,
    step: str,
    repo: Repository,
    args: Sequence[str],
    *,
    ceiling: str | None,
    commit: str | None = None,
    path: str | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Run one call of the plan and record its step, repository, exit status and wall time."""
    started = time.perf_counter()
    result = _git(repo.path, args, ceiling=ceiling)
    seconds = round(time.perf_counter() - started, SECONDS_DIGITS)
    run.calls.append(
        {
            "step": step,
            "repository": repo.name,
            "commit": commit,
            "path": path,
            "exit": result.returncode,
            "seconds": seconds,
        }
    )
    return result


def _text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def classify(run: _Run, repo: Repository) -> None:
    """p1 and p2: set the repository's status, reason, HEAD and ceiling (FR-019)."""
    resolved = repo.path.resolve()
    first_ceiling = None if repo.role == ROLE_ROOT else str(resolved.parent)
    try:
        p1 = _timed(
            run, "p1", repo, ["rev-parse", "--show-toplevel", "--is-shallow-repository", "HEAD"], ceiling=first_ceiling
        )
    except subprocess.TimeoutExpired:
        repo.status, repo.reason = STATUS_SKIPPED, REASON_TIMED_OUT
        return
    stderr = _text(p1.stderr)
    if p1.returncode != 0:
        if STDERR_NOT_A_REPO in stderr or STDERR_NOT_A_WORK_TREE in stderr:
            reason = REASON_NOT_A_WORK_TREE
        elif STDERR_OWNERSHIP in stderr:
            reason = REASON_OWNERSHIP
        else:
            reason = REASON_NO_HEAD
        repo.status, repo.reason = STATUS_SKIPPED, reason
        return
    lines = _text(p1.stdout).splitlines()
    toplevel, shallow, head = Path(lines[0]).resolve(), lines[1].strip(), lines[2].strip()
    if repo.role == ROLE_SOURCE_ROOT and toplevel != resolved:
        repo.status, repo.reason = STATUS_SKIPPED, REASON_NOT_TOP
        return
    if shallow == "true":
        repo.status, repo.reason = STATUS_SKIPPED, REASON_SHALLOW
        return
    repo.ceiling = str(toplevel.parent)
    try:
        p2 = _timed(run, "p2", repo, ["config", "--get", "extensions.partialclone"], ceiling=repo.ceiling)
    except subprocess.TimeoutExpired:
        repo.status, repo.reason = STATUS_SKIPPED, REASON_TIMED_OUT
        return
    if p2.returncode == 0:
        repo.status, repo.reason = STATUS_SKIPPED, REASON_PARTIAL
        return
    if not FULL_COMMIT_RE.fullmatch(head):
        repo.status, repo.reason = STATUS_SKIPPED, REASON_NO_HEAD
        return
    repo.head = head


def _cited_sources(text: str) -> list[dict[str, str | None]]:
    """Every ``sources:`` entry with a ``path:``, in frontmatter order, with its ``sha:`` or None."""
    sources = parse_frontmatter(text).get("sources") or []
    return [
        {"path": str(source["path"]), "sha": str(source["sha"]) if source.get("sha") is not None else None}
        for source in sources
        if isinstance(source, dict) and source.get("path")
    ]


def _is_superseded(text: str) -> bool:
    return bool(parse_frontmatter(text).get("superseded_by"))


def _inside(path: str) -> str | None:
    """The normalised path when it stays inside the matched directory, else None (FR-020)."""
    if not path or "\x00" in path or path.startswith("/"):
        return None
    normal = posixpath.normpath(path)
    if normal == ".." or normal.startswith("../") or normal.startswith("/"):
        return None
    return normal


def _probe(run: _Run, repos: Sequence[Repository], sha: str) -> tuple[Repository | None, str | None, str | None]:
    """p3 in list order: (repository, full commit, None) on a match, else (None, None, reason) (FR-021)."""
    skipped_any = any(repo.status != STATUS_USED for repo in repos)
    for repo in repos:
        if repo.status != STATUS_USED:
            continue
        try:
            p3 = _timed(run, "p3", repo, ["rev-parse", "--verify", f"{sha}^{{commit}}"], ceiling=repo.ceiling)
        except subprocess.TimeoutExpired:
            repo.status, repo.reason, skipped_any = STATUS_SKIPPED, REASON_TIMED_OUT, True
            continue
        out = _text(p3.stdout).strip()
        stderr = _text(p3.stderr)
        if p3.returncode == 0 and FULL_COMMIT_RE.fullmatch(out):
            return repo, out, None
        if STDERR_AMBIGUOUS in stderr:
            return None, None, REASON_AMBIGUOUS.format(name=repo.name)
        if STDERR_NOT_FOUND in stderr:
            continue
        repo.status, repo.reason, skipped_any = STATUS_SKIPPED, stderr.strip() or f"exit {p3.returncode}", True
    return None, None, REASON_NOT_FOUND_SKIPPED if skipped_any else REASON_NOT_FOUND


def _checked(result: subprocess.CompletedProcess[bytes], what: str, *, allowed: Iterable[int] = (0,)) -> None:
    if result.returncode not in set(allowed):
        raise RecordError(f"{what} exited {result.returncode}: {_text(result.stderr).strip()}")


def parse_hunks(diff: str) -> list[dict[str, Any]]:
    """The hunks of one file's ``git diff -U0``: line ranges and the ``+``/``-`` lines, headers excluded."""
    hunks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in diff.split("\n"):
        header = HUNK_HEADER_RE.match(line)
        if header:
            old_start, old_count, new_start, new_count = header.groups()
            current = {
                "old_start": int(old_start),
                "old_count": 1 if old_count is None else int(old_count),
                "new_start": int(new_start),
                "new_count": 1 if new_count is None else int(new_count),
                "lines": [],
                "heading": None,
            }
            hunks.append(current)
        elif current is not None and line[:1] in ("+", "-"):
            current["lines"].append(line)
    return hunks


def heading_above(source_lines: Sequence[str], line_number: int) -> str | None:
    """The text of the nearest ATX heading at or above 1-based ``line_number``, outside fenced code.

    For a pure insertion ``git diff -U0`` gives the old-side line the insertion
    follows, which is ``line_number`` here too; 0 means "before the first line"
    and has no heading above it.
    """
    nearest: str | None = None
    fence: str | None = None
    for line in source_lines[:line_number]:
        if fence is not None:
            stripped = line.strip()
            indent = len(line) - len(line.lstrip(" "))
            if indent <= MAX_FENCE_INDENT and stripped and set(stripped) == {fence[0]} and len(stripped) >= len(fence):
                fence = None
            continue
        opened = FENCE_OPEN_RE.match(line)
        if opened:
            fence = opened.group(1)
            continue
        heading = ATX_HEADING_RE.match(line)
        if heading:
            nearest = (heading.group(1) or "").strip()
    return nearest


def record_run(pages: Sequence[Page], repos: Sequence[Repository]) -> dict[str, Any]:
    """Run the call plan for ``pages`` over ``repos`` and return what git answered.

    Superseded pages are listed and not examined. Every p5, p6 and p7 is run
    for each changed cited path, so that the scoring can charge each candidate
    only the steps it needs.
    """
    run = _Run()
    for repo in repos:
        classify(run, repo)
    page_records: list[dict[str, Any]] = []
    for page in pages:
        superseded = _is_superseded(page.text)
        sources = [] if superseded else [_validated(cited, repos) for cited in _cited_sources(page.text)]
        page_records.append({"page": page.page, "superseded": superseded, "sources": sources})
    examined = [source for entry in page_records for source in entry["sources"]]

    matches: dict[str, tuple[Repository | None, str | None, str | None]] = {}
    for source in examined:
        if source["state"] == STATE_CHECKED and source["sha"] not in matches:
            matches[source["sha"]] = _probe(run, repos, source["sha"])
    groups: dict[tuple[str, str], tuple[Repository, list[str]]] = {}
    for source in examined:
        if source["state"] != STATE_CHECKED:
            continue
        matched, commit, reason = matches[source["sha"]]
        if matched is None or commit is None:
            source["state"] = STATE_EXACT if reason == REASON_NOT_FOUND else STATE_NOT_CHECKED
            source["reason"] = reason
            continue
        source["repository"], source["commit"] = matched.name, commit
        cited_paths = groups.setdefault((matched.name, commit), (matched, []))[1]
        if source["normal_path"] not in cited_paths:
            cited_paths.append(source["normal_path"])

    statuses: dict[tuple[str, str, str], str] = {}
    for (name, commit), (matched, cited_paths) in groups.items():
        assert matched.head is not None
        p4 = _timed(
            run,
            "p4",
            matched,
            [
                "diff-tree",
                "-r",
                "--name-status",
                "--no-renames",
                "--relative",
                "--no-ext-diff",
                "--no-textconv",
                commit,
                matched.head,
                "--",
                *cited_paths,
            ],
            ceiling=matched.ceiling,
            commit=commit,
        )
        _checked(p4, f"diff-tree in {name}")
        for line in _text(p4.stdout).splitlines():
            letter, _, listed = line.partition("\t")
            statuses[(name, commit, listed)] = letter[:1]

    changed: dict[tuple[str, str, str], dict[str, Any]] = {}
    repo_by_name = {repo.name: repo for repo in repos}
    for source in examined:
        if source["state"] != STATE_CHECKED:
            continue
        key = (source["repository"], source["commit"], source["normal_path"])
        status = statuses.get(key)
        source["status"] = status
        source["present_at_sha"], source["present_at_head"] = _presence(status)
        if status == STATUS_ADDED:
            source["state"] = STATE_EXACT
        if status is not None and status in CHANGED_STATUSES and key not in changed:
            changed[key] = _changed_path(run, repo_by_name[key[0]], key[1], key[2], status)

    for source in examined:
        source.pop("normal_path", None)
    return {
        "repositories": [repo.as_dict() for repo in repos],
        "pages": page_records,
        "paths": list(changed.values()),
        "calls": run.calls,
        "steps": step_totals(run.calls),
    }


def _validated(cited: dict[str, str | None], repos: Sequence[Repository]) -> dict[str, Any]:
    """A source entry before matching: checked, not checked with a reason, or malformed (FR-020)."""
    sha, path = cited["sha"], str(cited["path"])
    source: dict[str, Any] = {
        "path": path,
        "sha": sha,
        "state": STATE_CHECKED,
        "reason": None,
        "repository": None,
        "commit": None,
        "status": None,
        "present_at_sha": None,
        "present_at_head": None,
        "normal_path": None,
    }
    if sha is None:
        source["state"], source["reason"] = STATE_NOT_CHECKED, REASON_NO_SHA
    elif SHORT_SHA_RE.fullmatch(sha):
        source["state"], source["reason"] = STATE_NOT_CHECKED, REASON_TOO_SHORT
    elif not SHA_RE.fullmatch(sha):
        source["state"], source["reason"] = STATE_EXACT, REASON_MALFORMED
    else:
        normal = _inside(path)
        if normal is None:
            first = repos[0].name if repos else ""
            source["state"], source["reason"] = STATE_NOT_CHECKED, REASON_PATH_OUTSIDE.format(name=first)
        source["normal_path"] = normal
    return source


def _presence(status: str | None) -> tuple[bool | None, bool | None]:
    """Presence at the ``sha:`` and at HEAD from p4's status; None when p4 does not list the path.

    An unlisted path is unchanged, or absent at both commits; the call plan
    does not tell the two apart and neither yields a finding (FR-023).
    """
    if status == STATUS_ADDED:
        return False, True
    if status == STATUS_DELETED:
        return True, False
    if status in CHANGED_STATUSES:
        return True, True
    return None, None


def _changed_path(run: _Run, repo: Repository, commit: str, path: str, status: str) -> dict[str, Any]:
    """p5, p6 and, for a Markdown source, p7 for one changed cited path."""
    assert repo.head is not None
    diff = ["diff", "--no-ext-diff", "--no-textconv"]
    p5 = _timed(
        run,
        "p5",
        repo,
        [*diff, "--quiet", "-w", "--ignore-blank-lines", commit, repo.head, "--", path],
        ceiling=repo.ceiling,
        commit=commit,
        path=path,
    )
    _checked(p5, f"diff --quiet in {repo.name} for {path}", allowed=(0, 1))
    p6 = _timed(
        run, "p6", repo, [*diff, "-U0", commit, repo.head, "--", path], ceiling=repo.ceiling, commit=commit, path=path
    )
    _checked(p6, f"diff -U0 in {repo.name} for {path}")
    hunks = parse_hunks(_text(p6.stdout))
    markdown = path.endswith(MARKDOWN_SUFFIX)
    if markdown:
        p7 = _timed(
            run, "p7", repo, ["cat-file", "blob", f"{commit}:./{path}"], ceiling=repo.ceiling, commit=commit, path=path
        )
        _checked(p7, f"cat-file in {repo.name} for {path}")
        source_lines = _text(p7.stdout).split("\n")
        for hunk in hunks:
            hunk["heading"] = heading_above(source_lines, hunk["old_start"])
    return {
        "repository": repo.name,
        "commit": commit,
        "head": repo.head,
        "path": path,
        "status": status,
        "markdown": markdown,
        "p5_differs": p5.returncode == 1,
        "hunks": hunks,
    }


def step_totals(calls: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per step p1-p7, the number of git processes and their summed wall time."""
    totals: dict[str, dict[str, Any]] = {}
    for step in STEPS:
        mine = [call for call in calls if call["step"] == step]
        totals[step] = {
            "processes": len(mine),
            "seconds": round(sum(call["seconds"] for call in mine), SECONDS_DIGITS),
        }
    return totals


def _setup_git(args: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
    """A setup call (clone, checkout, version): argument list, no shell, clean environment."""
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        env=clean_env(None),
        timeout=RECORD_CALL_TIMEOUT_SECONDS * 10,
        check=False,
    )


def _local_clone(checkout: Path, destination: Path, commit: str) -> None:
    """``git clone --no-hardlinks --no-checkout`` then a detached checkout of ``commit``."""
    cloned = _setup_git(["clone", "--quiet", "--no-hardlinks", "--no-checkout", str(checkout), str(destination)])
    _checked(cloned, f"git clone into {destination.name}")
    detached = _setup_git(
        ["-c", f"core.hooksPath={os.devnull}", "-C", str(destination), "checkout", "--quiet", "--detach", commit]
    )
    _checked(detached, f"git checkout {commit} in {destination.name}")


def _resolve(checkout: Path, revision: str) -> str:
    result = _git(checkout, ["rev-parse", "--verify", f"{revision}^{{commit}}"], ceiling=None)
    commit = _text(result.stdout).strip()
    if result.returncode != 0 or not FULL_COMMIT_RE.fullmatch(commit):
        raise CheckoutError(f"the checkout has no commit {revision}")
    return commit


def _blob_sha256(checkout: Path, commit: str, path: str) -> str | None:
    """The sha256 of ``path``'s bytes at ``commit`` in the checkout, or None when the path is absent there."""
    result = _git(checkout, ["cat-file", "blob", f"{commit}:{path}"], ceiling=None)
    return hashlib.sha256(result.stdout).hexdigest() if result.returncode == 0 else None


def load_cases() -> list[tuple[Path, dict[str, Any]]]:
    """Every case directory under ``cases/`` with its ``case.json``, in path order."""
    return [
        (path.parent, json.loads(path.read_text(encoding="utf-8"))) for path in sorted(CASES_DIR.rglob("case.json"))
    ]


def is_fenced(directory: Path) -> bool:
    """Whether the case lives under ``cases/keyword-quoting/`` (FR-009)."""
    return directory.parent == KEYWORD_QUOTING_DIR


def verify_pins(checkout: Path, cases: Sequence[tuple[Path, dict[str, Any]]]) -> None:
    """Each case's recorded source hashes equal the checkout's bytes at the ``sha:`` and the read commit."""
    for _, case in cases:
        for commit, key in ((case["sha"], "source_at_sha"), (case["read_commit"], "source_at_read")):
            actual = _blob_sha256(checkout, _resolve(checkout, commit), case["path"])
            expected = case["sha256"][key]
            if actual != expected:
                raise PinMismatchError(
                    f"case {case['id']}: {case['path']} at {commit} hashes to {actual}, recorded {key} {expected}"
                )


def _study_pages(protocol: dict[str, Any]) -> list[Page]:
    """The 14 fixture pages in ``labels.json``'s order, read in place."""
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    wiki = REPO_ROOT / protocol["inputs"]["wiki"]
    return [Page(entry["page"], (wiki / entry["page"]).read_text(encoding="utf-8")) for entry in labels["pages"]]


def _repositories(clone: Path) -> list[Repository]:
    return [Repository(ROOT_NAME, ROLE_ROOT, REPO_ROOT), Repository(SOURCE_NAME, ROLE_SOURCE_ROOT, clone)]


def record(checkout: Path) -> tuple[dict[str, Any], dict[Path, dict[str, Any]]]:
    """The main record and, per keyword-quoting case directory, that case's own record."""
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    pin = protocol["study_pin"]["commit"]
    _resolve(checkout, pin)
    cases = load_cases()
    for _, case in cases:
        _resolve(checkout, case["read_commit"])
    verify_pins(checkout, cases)
    version = _setup_git(["--version"])
    _checked(version, "git --version")
    fenced: dict[Path, dict[str, Any]] = {}
    with tempfile.TemporaryDirectory() as tmp:
        pin_clone = Path(tmp) / "pin"
        _local_clone(checkout, pin_clone, pin)
        study = record_run(_study_pages(protocol), _repositories(pin_clone))
        pre_successor_text = (REPO_ROOT / protocol["inputs"]["pre_successor"]).read_text(encoding="utf-8")
        pre_successor = record_run([Page(PRE_SUCCESSOR_PAGE, pre_successor_text)], _repositories(pin_clone))
        case_records: dict[str, Any] = {}
        for directory, case in cases:
            clone = Path(tmp) / case["id"]
            _local_clone(checkout, clone, case["read_commit"])
            page = Page(case["id"], (directory / "page.md").read_text(encoding="utf-8"))
            run = record_run([page], _repositories(clone))
            run["read_commit"] = case["read_commit"]
            if is_fenced(directory):
                rel = (directory / HUNKS_NAME).relative_to(REPO_ROOT).as_posix()
                fenced[directory] = {"study": STUDY, "case": case["id"], "run": run}
                case_records[case["id"]] = {"recorded_in": rel}
            else:
                case_records[case["id"]] = run
    main_record = {
        "study": STUDY,
        "git": _text(version.stdout).strip(),
        "study_pin": pin,
        "runs": {RUN_STUDY: study, RUN_PRE_SUCCESSOR: pre_successor},
        "cases": case_records,
    }
    return main_record, fenced


def _dump(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2) + "\n"


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m eval.revisions.record",
        description="Record git's answers for the revision-check study from a local code-copilot-team checkout.",
    )
    parser.add_argument(
        "--checkout",
        type=Path,
        required=True,
        metavar="PATH",
        help="The local code-copilot-team checkout (only read; the record works on temporary local clones).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        metavar="PATH",
        help=(
            f"Write the main record to PATH (default {DEFAULT_OUT.relative_to(REPO_ROOT).as_posix()}). "
            "A keyword-quoting case's record always goes to its own case directory."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Record once and return the exit code: 0 ok, 2 a missing commit, 3 a pin mismatch, 4 a failed git call."""
    parser = _build_arg_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    try:
        main_record, fenced = record(args.checkout)
    except CheckoutError as exc:
        sys.stderr.write(f"{exc}; nothing was recorded or written\n")
        return CHECKOUT_UNREADABLE
    except PinMismatchError as exc:
        sys.stderr.write(f"{exc}; nothing was recorded or written\n")
        return PIN_MISMATCH
    except (RecordError, subprocess.TimeoutExpired) as exc:
        sys.stderr.write(f"{exc}; nothing was written\n")
        return GIT_FAILED
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(_dump(main_record), encoding="utf-8")
    for directory, case_record in fenced.items():
        (directory / HUNKS_NAME).write_text(_dump(case_record), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
