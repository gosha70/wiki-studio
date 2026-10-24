# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wiki_studio.api — the library surface: ``ingest``, ``propose``, ``promote``, ``read_page``, ``query``, ``lint``.

Each function takes a :class:`~wiki_studio.paths.WikiPaths`, returns a typed result
and raises the exceptions in :mod:`wiki_studio.errors`. Nothing here prints; the
CLI in :mod:`wiki_studio.cli` is a thin parser over these functions that renders
results and maps exceptions to exit codes.

Example::

    from pathlib import Path
    from wiki_studio import api
    from wiki_studio.paths import WikiPaths

    paths = WikiPaths.for_root(Path("."))
    result = api.ingest(Path("notes/incident.md"), paths, backend="test")
    api.promote(result.written, paths)
    print(api.query("what caused the outage?", paths, backend="test").answer.answer)

Stability
---------
The functions in this module, their keyword names, the result dataclasses,
the edit model (:class:`PageEdit`, :data:`PageAction`, :class:`WikiPatchSet`)
and the patch-set directory format that :func:`propose` writes and
:func:`promote` reads (``docs/patch-set-format.md``) are public and follow
semantic versioning: fields and keywords are only removed or renamed in a
major version; a minor version may add fields with defaults. ``__all__``
names that surface; the set of names a star-import brings in is not part of
the contract.
"""

from __future__ import annotations

import contextlib
import datetime
import json
import os
import posixpath
import re
import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from .audit import append_ingest_log, build_log_record
from .audit_flush import FlushResult, flush_state
from .audit_lint import validate_audit_tree
from .backends import resolve_backend
from .backends.copilot_cli import CopilotCliBackend
from .errors import ContractViolationError, OutputWriteError, PathOutsideRootError, SourceMissingError
from .health_lint import lint_health
from .ingestor import DefaultIngestor
from .ingestor_multi import COLLISION_ERROR, COLLISION_SUFFIX, DefaultMultiIngestor, write_patch_set_dir
from .lint import lint_wiki, list_pages
from .promoter import (
    DEFAULT_WIKI_TITLE,
    INDEX_NAME,
    LOG_NAME,
    PROMOTE_ENTRY_POINT_API,
    PROMOTE_ENTRY_POINT_CLI,
    InitResult,
    PromoteResult,
    init_wiki,
)
from .promoter import promote as _promote
from .proposal import (
    IngestLogRecord,
    IngestProposal,
    IngestRequest,
    PageAction,
    PageEdit,
    QueryAnswer,
    WikiPatchSet,
    is_sha256_hex,
    render_proposal_file,
    validate_page_edit_semantics,
    validate_patch_set,
)
from .prose_lint import run_prose_lint
from .querier import DEFAULT_MAX_QUERY_PAGES, DefaultQuerier, _select_query_candidates
from .wiki_state import read_page_content

if TYPE_CHECKING:
    from .health_lint import HealthLintResult
    from .ingestor import Backend
    from .paths import WikiPaths
    from .prose_lint import ProseLintResult

__all__ = [
    "ALLOW_OUT_OF_REPO_HINT",
    "ALLOW_OUT_OF_REPO_PROMOTE_HINT",
    "PROMOTE_ENTRY_POINT_API",
    "PROMOTE_ENTRY_POINT_CLI",
    "PROPOSE_BACKEND",
    "AuditFlushResult",
    "FlushResult",
    "IngestLogRecord",
    "IngestProposal",
    "IngestRequest",
    "IngestResult",
    "LintResult",
    "PageAction",
    "PageEdit",
    "FindResult",
    "FoundPage",
    "InitResult",
    "PromoteResult",
    "QueryAnswer",
    "QueryResult",
    "ReadResult",
    "WikiPatchSet",
    "audit_flush",
    "edits_from_dir",
    "find",
    "backend_display_name",
    "ingest",
    "init",
    "lint",
    "prepare_backend",
    "promote",
    "propose",
    "query",
    "read_page",
]

# ``propose --from``: the optional manifest an agent writes beside its draft, mapping each wiki
# path it replaces to the sha256 ``read`` reported for the page it drafted from (FR-007).
BASE_MANIFEST_NAME = ".base.json"

# The env var the legacy single-source ingestor reads its task hint from.
_TASK_ENV = "WIKI_INGEST_TASK"
_GATE_ONLY_TASK = "gate-only"
_SNAPSHOT_DIR_NAME = ".ingest-snapshot"
_FILE_BACK_SLUG = "query-fileback"

# Recorded as ``backend`` in plan.json when a library caller proposes edits directly.
PROPOSE_BACKEND = "api"

# A proposal name: one path component of ASCII letters, digits, '.', '_' and
# '-', not starting with '.' (hidden names such as ``.applied`` are the
# archive's). Matched with fullmatch: '$' alone would accept a trailing newline.
_PROPOSAL_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

ALLOW_OUT_OF_REPO_HINT = "Pass --allow-out-of-repo to override (only when ingesting external artifacts deliberately)."
ALLOW_OUT_OF_REPO_PROMOTE_HINT = (
    "Pass --allow-out-of-repo to override (only when the proposal dir comes from a trusted source you've audited)."
)


# ── Results ───────────────────────────────────────────────────


@dataclass(frozen=True)
class IngestResult:
    """What ``ingest`` produced.

    ``written`` is the proposal file (legacy single-source) or the patch-set
    directory (multi-page); None in check mode. ``edits`` lists the
    wiki-relative pages the proposal touches.
    """

    disposition: str
    written: Path | None
    edits: tuple[str, ...]
    rationale: str
    dry_run: bool
    check: bool
    patch: WikiPatchSet | None
    proposal: IngestProposal | None
    record: IngestLogRecord | None


@dataclass(frozen=True)
class QueryResult:
    """An answer with citations; with ``file_back`` also the patch-set and where it was written."""

    answer: QueryAnswer
    patch: WikiPatchSet | None
    file_back_dir: Path | None


@dataclass(frozen=True)
class LintResult:
    """Structural violations, audit-format errors and (optionally) knowledge-health and prose findings."""

    violations: tuple[str, ...]
    pages_checked: int
    audit_errors: tuple[str, ...]
    health: HealthLintResult | None
    strict: bool
    prose: ProseLintResult | None = None

    @property
    def passed(self) -> bool:
        """Structural violations always fail; audit, health and prose findings fail only under ``strict``."""
        if self.violations:
            return False
        if not self.strict:
            return True
        if self.audit_errors:
            return False
        if self.health is not None and self.health.findings:
            return False
        return not (self.prose is not None and self.prose.findings)


AuditFlushResult = FlushResult


# ── Backends ──────────────────────────────────────────────────


def prepare_backend(
    backend: str | Backend | None,
    paths: WikiPaths,
    *,
    redact_output: bool = True,
) -> Backend:
    """Resolve a backend by name (or env/auto-detect when None) and apply per-run settings.

    A :class:`Backend` instance is used as given; a copilot-CLI backend gets a
    copy carrying the stderr redaction setting and the wiki label used in
    rendered prompts.
    """
    resolved: Backend = backend if backend is not None and not isinstance(backend, str) else resolve_backend(backend)
    if isinstance(resolved, CopilotCliBackend):
        return resolved.with_options(redact_output=redact_output, wiki_label=paths.wiki_label)
    return resolved


def backend_display_name(backend: object, requested: str | None) -> str:
    """Best-effort name for the resolved backend, recorded in proposal frontmatter."""
    if requested:
        return requested
    cli_name = getattr(backend, "_cli_name", None)
    if cli_name:
        return str(cli_name)
    cls_name = backend.__class__.__name__
    return cls_name.removesuffix("Backend").lower() or "unknown"


# ── ingest ────────────────────────────────────────────────────


def _proposal_filename(proposal: IngestProposal) -> str:
    """``<YYYY-MM-DD>-<slug>.md``."""
    today = datetime.date.today().isoformat()
    base = proposal.slug or f"unslugged-{proposal.disposition}"
    return f"{today}-{base}.md"


def _write_proposal_file(proposal: IngestProposal, request: IngestRequest, backend_name: str, output_dir: Path) -> Path:
    proposal_path = output_dir / _proposal_filename(proposal)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        proposal_path.write_text(render_proposal_file(proposal, request, backend_name), encoding="utf-8")
    except OSError as exc:
        raise OutputWriteError(f"Could not write proposal file at {proposal_path}: {exc}") from exc
    return proposal_path.resolve()


def _write_ingest_snapshot(proposal_dir: Path) -> None:
    """Immutable copy of plan.json + preview/ so promote can diff the curator's edits (never on dry-run or check)."""
    snapshot_dir = proposal_dir / _SNAPSHOT_DIR_NAME
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    plan = proposal_dir / "plan.json"
    if plan.is_file():
        shutil.copy2(str(plan), str(snapshot_dir / "plan.json"))
    preview = proposal_dir / "preview"
    if preview.is_dir():
        preview_snapshot = snapshot_dir / "preview"
        if preview_snapshot.exists():
            shutil.rmtree(str(preview_snapshot))
        shutil.copytree(str(preview), str(preview_snapshot))


def _require_within_root(kind: str, path: Path, paths: WikiPaths, allow: bool, hint: str) -> None:
    if allow or paths.within_root(path):
        return
    raise PathOutsideRootError(f"{kind} is outside the repository tree: {path}\n  Repo root: {paths.root}\n  {hint}")


def ingest(
    source: Path,
    paths: WikiPaths,
    *,
    backend: str | Backend | None = None,
    legacy_single_source: bool = False,
    dry_run: bool = False,
    check: bool = False,
    output_dir: Path | None = None,
    allow_out_of_repo: bool = False,
    redact_output: bool = True,
) -> IngestResult:
    """Run the ingest gate over ``source`` and write the proposal.

    Multi-page by default (a patch-set directory under the proposals dir);
    ``legacy_single_source`` runs the v1 single-page generator. ``check``
    runs the gate with zero filesystem side effects; ``dry_run`` skips the
    draft body (legacy) or marks the audit record (multi).

    Raises ``ValueError`` when ``check`` and ``dry_run`` are combined, and the
    :mod:`wiki_studio.errors` exceptions for everything else.
    """
    if check and dry_run:
        raise ValueError("--check and --dry-run are mutually exclusive")
    source_path = Path(source)
    if not source_path.exists():
        raise SourceMissingError(f"source file not found: {source_path}")
    _require_within_root("source path", source_path, paths, allow_out_of_repo, ALLOW_OUT_OF_REPO_HINT)

    requested = backend if isinstance(backend, str) else None
    resolved = prepare_backend(backend, paths, redact_output=redact_output)
    backend_name = backend_display_name(resolved, requested)
    request = IngestRequest(source_path=source_path, source_kind="file", backend_name=backend_name)
    proposals_root = output_dir if output_dir is not None else paths.proposals_dir

    if legacy_single_source:
        return _ingest_legacy(request, paths, resolved, backend_name, proposals_root, dry_run, check, allow_out_of_repo)
    return _ingest_multi(request, paths, resolved, backend_name, proposals_root, dry_run, check, allow_out_of_repo)


def _ingest_legacy(
    request: IngestRequest,
    paths: WikiPaths,
    backend: Backend,
    backend_name: str,
    output_dir: Path,
    dry_run: bool,
    check: bool,
    allow_out_of_repo: bool,
) -> IngestResult:
    ingestor = DefaultIngestor(backend=backend, paths=paths)
    # The legacy prompt reads the dry-run intent from the environment; the
    # render side still strips the body as a safety net for stubs that
    # ignore the task hint.
    env_backup = os.environ.get(_TASK_ENV)
    if dry_run:
        os.environ[_TASK_ENV] = _GATE_ONLY_TASK
    try:
        proposal = ingestor.ingest(request)
    finally:
        if env_backup is None:
            os.environ.pop(_TASK_ENV, None)
        else:
            os.environ[_TASK_ENV] = env_backup

    edits = (proposal.slug,) if proposal.slug else ()
    if check:
        return IngestResult(proposal.disposition, None, edits, proposal.reason, False, True, None, proposal, None)
    if dry_run:
        proposal = replace(proposal, draft_markdown=None)

    proposal_path = _write_proposal_file(proposal, request, backend_name, output_dir)
    if not dry_run:
        _write_ingest_snapshot(proposal_path.parent)
    record = build_log_record(
        source_file=request.source_path,
        paths=paths,
        backend_name=backend_name,
        proposal_dir_path=proposal_path.parent,
        allow_out_of_repo=allow_out_of_repo,
        legacy_proposal=proposal,
        dry_run=dry_run,
    )
    append_ingest_log(paths, record)
    return IngestResult(
        proposal.disposition, proposal_path, edits, proposal.reason, dry_run, False, None, proposal, record
    )


def _ingest_multi(
    request: IngestRequest,
    paths: WikiPaths,
    backend: Backend,
    backend_name: str,
    proposals_root: Path,
    dry_run: bool,
    check: bool,
    allow_out_of_repo: bool,
) -> IngestResult:
    multi = DefaultMultiIngestor(backend=backend, paths=paths)
    patch = multi.ingest_multi(request)
    disposition = "accept" if patch.edits else "reject"
    edits = tuple(e.path for e in patch.edits)
    if check:
        return IngestResult(disposition, None, edits, patch.rationale, False, True, patch, None, None)

    today = datetime.date.today().isoformat()
    output_dir = proposals_root / f"{today}-{request.source_path.stem or 'source'}"
    try:
        # A generated name: a second ingest of the same source on the same day
        # lands in ``<name>-2`` rather than in a directory that may be mid-promotion.
        written = write_patch_set_dir(
            patch,
            output_dir,
            wiki_dir=paths.wiki_dir,
            on_collision=COLLISION_SUFFIX,
            lock_timeout=paths.lock_timeout,
        )
    except OSError as exc:
        raise OutputWriteError(f"could not write patch-set dir at {output_dir}: {exc}") from exc
    if not dry_run and patch.edits:
        _write_ingest_snapshot(written)
    record = build_log_record(
        source_file=request.source_path,
        paths=paths,
        backend_name=backend_name,
        proposal_dir_path=written,
        allow_out_of_repo=allow_out_of_repo,
        patch=patch,
        dry_run=dry_run,
    )
    append_ingest_log(paths, record)
    return IngestResult(disposition, written, edits, patch.rationale, dry_run, False, patch, None, record)


# ── propose ───────────────────────────────────────────────────


def propose(
    edits: list[PageEdit],
    paths: WikiPaths,
    *,
    name: str,
    source: str = "",
    rationale: str = "",
    backend: str = PROPOSE_BACKEND,
) -> Path:
    """Write ``edits`` as a patch-set directory ``<proposals_dir>/<name>/`` for :func:`promote`.

    The directory has the format ``ingest`` writes (``docs/patch-set-format.md``):
    ``plan.json``, one ``preview/<path>`` per edit and an ``.ingest-snapshot/``
    copy. The edits are validated first with the same two checks ``ingest`` and
    ``promote`` run (set-level invariants, then per-edit frontmatter and
    placement against the live wiki); nothing is written when they fail.
    ``source``, ``rationale`` and ``backend`` are recorded in ``plan.json`` and
    rendered into the audit archive by ``promote``. The ingest log is not
    touched: nothing was ingested.

    Raises ``ValueError`` when ``name`` is not one path component of ASCII
    letters, digits, ``.``, ``_`` and ``-`` that does not start with ``.``
    (stricter than the names ``ingest`` generates), ``ContractViolationError``
    when the edits are invalid (including an empty list), and
    ``OutputWriteError`` when the directory already exists or cannot be
    written. Whatever the failure while writing, the directory (and a
    proposals directory this call created) is removed again. Returns the
    absolute directory path.
    """
    if not _PROPOSAL_NAME_RE.fullmatch(name):
        raise ValueError(
            "name must be one path component of ASCII letters, digits, '.', '_' and '-' "
            f"not starting with '.', got {name!r}"
        )
    patch = WikiPatchSet(edits=list(edits), source_path=source, backend=backend, rationale=rationale)
    set_errors = validate_patch_set(patch)
    if set_errors:
        raise ContractViolationError("patch-set failed set-level validation:\n  - " + "\n  - ".join(set_errors))
    per_edit_errors = [error for edit in patch.edits for error in validate_page_edit_semantics(edit, paths)]
    if per_edit_errors:
        raise ContractViolationError(
            "patch-set failed per-edit semantic validation:\n  - " + "\n  - ".join(per_edit_errors)
        )
    output_dir = paths.proposals_dir / name
    proposals_dir_existed = paths.proposals_dir.is_dir()
    try:
        # Creating the directory (exclusively, under the wiki lock) is the
        # collision check: a caller-selected name that exists is an error, and
        # from here on the directory is ours to remove if a later write fails.
        written = write_patch_set_dir(
            patch, output_dir, wiki_dir=paths.wiki_dir, on_collision=COLLISION_ERROR, lock_timeout=paths.lock_timeout
        )
    except FileExistsError as exc:
        raise OutputWriteError(f"proposal dir already exists: {output_dir}") from exc
    except Exception as exc:
        _discard_partial_proposal(output_dir, paths, proposals_dir_existed)
        if isinstance(exc, OSError):
            raise OutputWriteError(f"could not write patch-set dir at {output_dir}: {exc}") from exc
        raise
    try:
        _write_ingest_snapshot(written)
    except Exception as exc:
        # Any failure, not only OSError: leave no half-written directory behind.
        _discard_partial_proposal(output_dir, paths, proposals_dir_existed)
        if isinstance(exc, OSError):
            raise OutputWriteError(f"could not write patch-set dir at {output_dir}: {exc}") from exc
        raise
    return written


def _discard_partial_proposal(output_dir: Path, paths: WikiPaths, proposals_dir_existed: bool) -> None:
    """Remove a proposal directory ``propose`` could only partly write (and a proposals dir it created).

    The proposals dir is removed only while empty: another writer may have
    created it, and filled it, while this call waited for the lock.
    """
    shutil.rmtree(output_dir, ignore_errors=True)
    if not proposals_dir_existed:
        with contextlib.suppress(OSError):
            paths.proposals_dir.rmdir()


# ── promote ───────────────────────────────────────────────────


def promote(
    proposal_dir: Path,
    paths: WikiPaths,
    *,
    dry_run: bool = False,
    allow_out_of_repo: bool = False,
    lock_timeout: float | None = None,
    entry_point: str = PROMOTE_ENTRY_POINT_API,
    allow_unguarded_updates: bool = False,
) -> PromoteResult:
    """Apply a patch-set directory to the wiki (the only write into the wiki).

    The promotion is validated, serialised against other wiki-studio writers
    on the same machine by the wiki lock, and rolled back on failure; it is
    not crash-safe across files, and uncoordinated readers may observe
    intermediate state. Under the lock, before the commit, the revision
    preconditions are checked against the live wiki: a ``create`` needs its
    target absent and an ``update`` with ``base_sha256`` needs the live page
    to still carry that hash (``PromoteValidationError``, exit 9, nothing
    written, otherwise). An ``update`` without a ``base_sha256`` is refused
    the same way unless ``allow_unguarded_updates`` is set: compatibility
    mode with incomplete conflict protection, which applies it and lists the
    path in ``PromoteResult.unguarded_paths`` and the receipt; a stale draft
    can then overwrite a newer page. ``dry_run`` stages and checks the
    preconditions under the lock, then validates the staged snapshot after
    releasing it, writing nothing (point-in-time evidence). ``lock_timeout``
    overrides ``paths.lock_timeout`` (seconds to wait for the lock).
    ``entry_point`` (``"api"`` or ``"cli"``) is recorded in the receipt as
    software identity.

    Raises ``SourceMissingError`` when the directory does not exist,
    ``PathOutsideRootError`` when it lies outside the root without
    ``allow_out_of_repo``, ``OutputWriteError`` when the receipt cannot be
    written, and the promoter's validation/apply errors (``PromoteApplyError``
    carries ``reason`` for the lock and recovery refusals).
    """
    proposal_path = Path(proposal_dir)
    if not proposal_path.exists():
        raise SourceMissingError(f"proposals dir not found: {proposal_path}")
    _require_within_root("proposal dir", proposal_path, paths, allow_out_of_repo, ALLOW_OUT_OF_REPO_PROMOTE_HINT)
    if lock_timeout is not None:
        paths = replace(paths, lock_timeout=float(lock_timeout))
    return _promote(
        proposals_dir=proposal_path,
        paths=paths,
        dry_run=dry_run,
        entry_point=entry_point,
        allow_unguarded_updates=allow_unguarded_updates,
    )


# ── read: one page, its text and the hash of the bytes read ───


@dataclass(frozen=True)
class ReadResult:
    """One wiki page as read once: wiki-relative ``path``, exact ``data``, decoded ``text`` and ``sha256`` of the bytes.

    ``sha256`` is what an ``update`` of this page records as ``base_sha256``;
    ``promote`` applies the update only while the live page still has it.
    """

    path: str
    data: bytes
    text: str
    sha256: str


def _wiki_relative_page(path: str | os.PathLike[str], paths: WikiPaths) -> tuple[str, Path]:
    """Normalise a wiki-relative page path and refuse one that leaves the wiki or passes through a symlink.

    The wiki boundary (FR-012): the candidate must be relative, resolve inside
    the resolved wiki directory, and no component of it may be a symlink.
    """
    raw = Path(path)
    rel = posixpath.normpath(raw.as_posix())
    if raw.is_absolute() or rel == "." or rel.startswith("../") or rel == "..":
        raise PathOutsideRootError(f"page path must be wiki-relative and stay inside the wiki: {path}")
    target = paths.wiki_dir / rel
    wiki = paths.wiki_dir.resolve()
    probe = paths.wiki_dir
    for part in Path(rel).parts:
        probe = probe / part
        if probe.is_symlink():
            raise PathOutsideRootError(f"page path passes through a symlink, which is outside the wiki boundary: {rel}")
    if not target.resolve().is_relative_to(wiki):
        raise PathOutsideRootError(f"page path escapes the wiki directory {paths.wiki_dir}: {rel}")
    return rel, target


def read_page(path: str | os.PathLike[str], paths: WikiPaths) -> ReadResult:
    """Read one wiki page once and return its bytes, UTF-8 text and the sha256 of exactly those bytes.

    ``path`` is wiki-relative (``index.md``, ``concepts/<slug>.md``) and is
    checked against the wiki boundary before anything is read:
    ``PathOutsideRootError`` (exit 7) for an absolute path, a ``..`` escape or
    a symlink. ``SourceMissingError`` (exit 5) when there is no such file;
    ``ContractViolationError`` (exit 4) when the bytes are not valid UTF-8, in
    which case no content is returned. The procedure for an agent that
    replaces a page: ``read`` it, draft from that text, record the ``sha256``
    as the edit's ``base_sha256`` (``api.propose``) or in the draft's
    ``.base.json`` (``propose --from``).
    """
    rel, target = _wiki_relative_page(path, paths)
    if not target.is_file():
        raise SourceMissingError(f"page not found: {paths.wiki_label}/{rel}")
    try:
        content = read_page_content(target)
    except OSError as exc:
        raise SourceMissingError(f"page not readable: {paths.wiki_label}/{rel}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ContractViolationError(f"page is not valid UTF-8: {paths.wiki_label}/{rel}: {exc}") from exc
    return ReadResult(path=rel, data=content.data, text=content.text, sha256=content.sha256)


# ── init ──────────────────────────────────────────────────────


def init(paths: WikiPaths, *, title: str = DEFAULT_WIKI_TITLE) -> InitResult:
    """Create the wiki directory with a minimal ``index.md`` and ``log.md`` when absent; never overwrites.

    Raises ``OutputWriteError`` when the directory or a file cannot be written.
    """
    try:
        return init_wiki(paths, title=title)
    except OSError as exc:
        raise OutputWriteError(f"could not initialise the wiki at {paths.wiki_dir}: {exc}") from exc


# ── propose from a directory of agent-written files ───────────


def edits_from_dir(source_dir: Path, paths: WikiPaths, *, rationale: str = "") -> list[PageEdit]:
    """Turn a directory laid out like the wiki into edits for :func:`propose`.

    Every ``*.md`` file under ``source_dir`` maps to the wiki path it sits at:
    ``index.md`` holds index bullets and ``log.md`` log entries, one per
    non-empty line (the root ``index.md`` and ``log.md`` only), each becoming an
    ``append-index`` / ``append-log`` edit
    (a file there that starts with frontmatter is refused: the root index and
    log are never rewritten); any other file is a content page, a ``create``
    when the wiki has no page at that path and an ``update`` when it has one
    (``glossary/index.md`` included). Validation is :func:`propose`'s.

    An ``update`` carries the base revision the agent recorded in
    ``<source_dir>/.base.json``, a JSON object mapping the wiki path to the
    ``sha256`` that ``read`` reported for the page the draft was made from.
    The hash is never taken from the live page here: a page with no manifest
    entry (or no manifest) is an unguarded update, which ``promote`` refuses
    unless its compatibility option is passed.

    Files under hidden directories are skipped. Raises ``SourceMissingError``
    when ``source_dir`` is not a directory and ``ContractViolationError`` for
    an index or log file that is a page, a ``source_dir`` that overlaps the
    wiki, or a malformed ``.base.json``.
    """
    root = Path(source_dir)
    if not root.is_dir():
        raise SourceMissingError(f"--from directory not found: {root}")
    src, wiki = root.resolve(), paths.wiki_dir.resolve()
    if src == wiki or src.is_relative_to(wiki) or wiki.is_relative_to(src):
        raise ContractViolationError(
            f"--from {root} overlaps the wiki directory {paths.wiki_dir}; write drafts somewhere else"
        )
    base_hashes = _read_base_manifest(root)
    why = rationale or f"written by the agent in {root.name}"
    edits: list[PageEdit] = []
    for file in sorted(p for p in root.rglob("*.md") if p.is_file()):
        rel_parts = file.relative_to(root).parts
        if any(part.startswith(".") for part in rel_parts):
            continue  # hidden directories (.audit/, .git/, editor state) are never wiki content
        rel = file.relative_to(root).as_posix()
        text = file.read_text(encoding="utf-8")
        if rel in (INDEX_NAME, LOG_NAME):
            if text.lstrip().startswith("---"):
                raise ContractViolationError(
                    f"{rel} in {root} must hold only the lines to append (one per line), not a page with frontmatter"
                )
            action: PageAction = "append-index" if rel == INDEX_NAME else "append-log"
            edits.extend(PageEdit(rel, action, line.strip(), why) for line in text.splitlines() if line.strip())
            continue
        exists = (paths.wiki_dir / rel).is_file()
        # Only an update takes a base revision, and only the one the agent recorded.
        base = base_hashes.get(rel) if exists else None
        edits.append(PageEdit(rel, "update" if exists else "create", text, why, base_sha256=base))
    return edits


def _read_base_manifest(root: Path) -> dict[str, str]:
    """``<root>/.base.json``: wiki path -> sha256 the agent read; ``{}`` when absent."""
    manifest = root / BASE_MANIFEST_NAME
    if not manifest.is_file():
        return {}
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ContractViolationError(f"{manifest} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or not all(isinstance(k, str) and is_sha256_hex(v) for k, v in data.items()):
        raise ContractViolationError(
            f"{manifest} must be a JSON object mapping wiki-relative page paths to sha256 hex digests "
            "(the sha256 that `wiki-studio read <path>` printed for the page the draft was made from)"
        )
    return {posixpath.normpath(k): str(v) for k, v in data.items()}


# ── find (model-free page selection) ──────────────────────────


@dataclass(frozen=True)
class FoundPage:
    """One page the querier would load for a question: wiki-relative path, file and title."""

    path: str
    file: Path
    title: str


@dataclass(frozen=True)
class FindResult:
    """The pages ``query`` would put in front of a model, in order, without calling one."""

    question: str
    index: Path
    pages: tuple[FoundPage, ...]


def _page_title(text: str, fallback: str) -> str:
    """The frontmatter ``title:``; the fallback when the page has no frontmatter or no title."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return fallback
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("title:"):
            return line[len("title:") :].strip().strip('"').strip("'") or fallback
    return fallback


def find(question: str, paths: WikiPaths, *, max_pages: int = DEFAULT_MAX_QUERY_PAGES) -> FindResult:
    """Run only the index-first page selection of :func:`query`: no backend, no query log.

    The result is what a model would be given to read: ``index.md`` plus up to
    ``max_pages`` index-linked pages ranked by word overlap with the question.
    An empty ``pages`` means no index-linked page shares a word with it. Raises
    ``SourceMissingError`` (exit 5) when the wiki has no ``index.md``.
    """
    index_md, selected, contents = _select_query_candidates(paths, question, max_pages)
    if not index_md:
        raise SourceMissingError(
            f"{paths.wiki_label}/index.md not found; nothing to find. Run `wiki-studio init` to create the wiki."
        )
    pages = tuple(
        FoundPage(path=rel, file=paths.wiki_dir / rel, title=_page_title(contents[rel], Path(rel).stem))
        for rel in selected
    )
    return FindResult(question=question, index=paths.wiki_dir / INDEX_NAME, pages=pages)


# ── query ─────────────────────────────────────────────────────


def query(
    question: str,
    paths: WikiPaths,
    *,
    backend: str | Backend | None = None,
    file_back: bool = False,
    max_pages: int | None = None,
    output_dir: Path | None = None,
    redact_output: bool = True,
) -> QueryResult:
    """Answer ``question`` index-first over the wiki; with ``file_back`` also write a patch-set for the answer."""
    resolved = prepare_backend(backend, paths, redact_output=redact_output)
    querier = (
        DefaultQuerier(backend=resolved, paths=paths)
        if max_pages is None
        else DefaultQuerier(resolved, paths, max_pages)
    )
    if not file_back:
        return QueryResult(answer=querier.query(question), patch=None, file_back_dir=None)

    answer, patch = querier.query_with_file_back(question)
    if not patch.edits:
        return QueryResult(answer=answer, patch=patch, file_back_dir=None)
    today = datetime.date.today().isoformat()
    out = (output_dir if output_dir is not None else paths.proposals_dir) / f"{today}-{_FILE_BACK_SLUG}"
    try:
        written = write_patch_set_dir(
            patch, out, wiki_dir=paths.wiki_dir, on_collision=COLLISION_SUFFIX, lock_timeout=paths.lock_timeout
        )
    except OSError as exc:
        raise OutputWriteError(f"could not write file-back dir: {exc}") from exc
    return QueryResult(answer=answer, patch=patch, file_back_dir=written)


# ── lint ──────────────────────────────────────────────────────


def lint(
    paths: WikiPaths,
    *,
    health: bool = False,
    strict: bool = False,
    only: list[str] | None = None,
    backend: str | Backend | None = None,
    redact_output: bool = True,
    prose: bool = False,
) -> LintResult:
    """Structural lint plus the audit-format pass; ``health`` adds the knowledge-health checks.

    ``prose`` adds the prose checks (``lint --prose``); ``only`` limits the
    pages they scan. ``backend`` is only consulted with ``health`` (for the
    contradiction check); when it is None, contradictions are skipped.
    Avoid-format problems are reported by the health tier when it runs and
    by the prose tier otherwise, so each appears once.
    """
    violations = tuple(lint_wiki(paths.wiki_dir))
    pages_checked = len(list_pages(paths.wiki_dir))
    audit_errors = tuple(validate_audit_tree(paths))
    health_result: HealthLintResult | None = None
    if health:
        resolved = prepare_backend(backend, paths, redact_output=redact_output) if backend is not None else None
        health_result = lint_health(paths, only=only, backend=resolved)
    prose_result: ProseLintResult | None = None
    if prose:
        prose_result = run_prose_lint(paths.wiki_dir, paths=only, avoid_format=not health)
    return LintResult(violations, pages_checked, audit_errors, health_result, strict, prose_result)


# ── audit-flush ───────────────────────────────────────────────


def audit_flush(paths: WikiPaths, *, dry_run: bool = False) -> AuditFlushResult:
    """Commit pending ingest-log lines (or report them with ``dry_run``); raises ``AuditFlushError``."""
    return flush_state(paths, dry_run)
