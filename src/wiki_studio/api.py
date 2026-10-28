# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wiki_studio.api — the library surface: ``ingest``, ``propose``, ``promote``, ``approve``, ``read_page``, ``lint``...

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
import stat
import warnings
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .audit import append_ingest_log, build_log_record
from .audit_flush import FlushResult, flush_state
from .audit_lint import validate_audit_tree
from .backends import resolve_backend
from .backends.copilot_cli import CopilotCliBackend
from .contract import InfoResult, check_write_contract, describe
from .discovery import (
    DEFAULT_MAX_CONTEXT_BYTES,
    DEFAULT_RANKER,
    IneligiblePage,
    OmittedPage,
    RankerConfig,
    describe_discovery,
    resolve_ranker,
    select,
    validate_max_pages,
)
from .errors import ContractViolationError, DriftWarning, OutputWriteError, PathOutsideRootError, SourceMissingError
from .findings import Finding, FindingsResult
from .findings import findings as _findings
from .health_lint import lint_health
from .ingestor import DefaultIngestor
from .ingestor_multi import COLLISION_ERROR, COLLISION_SUFFIX, DefaultMultiIngestor, write_patch_set_dir
from .lint import lint_wiki, list_pages
from .paths import CONTAIN_SYMLINK, ContainmentError, contain, is_absolute_path, resolve_actor
from .promoter import (
    DEFAULT_WIKI_TITLE,
    INDEX_NAME,
    LOG_NAME,
    PROMOTE_ENTRY_POINT_API,
    PROMOTE_ENTRY_POINT_CLI,
    PROMOTE_ENTRY_POINT_MCP,
    ApproveResult,
    InitResult,
    PromoteResult,
    init_wiki,
)
from .promoter import approve as _approve
from .promoter import promote as _promote
from .proposal import (
    IngestLogRecord,
    IngestProposal,
    IngestRequest,
    PageAction,
    PageEdit,
    QueryAnswer,
    WikiPatchSet,
    check_reserved_edits,
    is_sha256_hex,
    render_proposal_file,
    validate_page_edit_semantics,
    validate_patch_set,
)
from .proposal import assign_page_ids as _assign_page_ids
from .prose_lint import run_prose_lint
from .querier import DEFAULT_MAX_QUERY_PAGES, DefaultQuerier
from .review import ReviewState, review_states
from .wiki_state import read_page_content
from .wikilock import WikiLock

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
    "PROMOTE_ENTRY_POINT_MCP",
    "PROPOSE_BACKEND",
    "ApproveResult",
    "AuditFlushResult",
    "Finding",
    "FindingsResult",
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
    "IneligiblePage",
    "OmittedPage",
    "RankerConfig",
    "InfoResult",
    "InitResult",
    "PromoteResult",
    "QueryAnswer",
    "QueryResult",
    "ReadResult",
    "ReviewState",
    "WikiPatchSet",
    "approve",
    "audit_flush",
    "edits_from_dir",
    "find",
    "findings",
    "backend_display_name",
    "check_proposal_name",
    "info",
    "ingest",
    "init",
    "lint",
    "prepare_backend",
    "promote",
    "propose",
    "query",
    "read_page",
    "review_state",
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


_LEGACY_BACKUP_ATTEMPTS = 100


def _legacy_slot(output_dir: Path, name: str) -> Path | None:
    """Make the deterministic legacy path ``output_dir/name`` free to create, moving a previous file aside.

    The path must pass the proposal boundary (no symlink, inside
    ``output_dir``); a previous proposal is renamed to a backup sibling
    atomically, never read and never followed, so its bytes survive until
    publication succeeds. Returns the backup path, or None when nothing was
    there.
    """
    target = output_dir / name
    try:
        contain(name, output_dir)
    except ContainmentError as exc:
        raise OutputWriteError(f"legacy proposal path {target} is outside the proposal boundary ({exc})") from exc
    try:
        st = os.lstat(target)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(st.st_mode):
        # Only a regular file is a previous proposal; a directory or any other
        # entry at this name is refused before anything is moved or published.
        raise OutputWriteError(f"{target} exists and is not a regular file; refusing to replace it")
    # A unique backup, reserved exclusively: an existing backup is a surviving
    # copy of an earlier proposal that a failed restoration left behind, and
    # is never overwritten. The backup is a visible sibling so it is found.
    for attempt in range(1, _LEGACY_BACKUP_ATTEMPTS + 1):
        backup = target.with_name(f"{name}.bak-{os.getpid()}-{attempt}")
        try:
            os.link(target, backup)
        except FileExistsError:
            continue
        except OSError:
            # No hard links here (or a different filesystem rule): fall back
            # to an exclusive create followed by a copy, still never over an
            # existing backup.
            fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o644)
            os.close(fd)
            shutil.copy2(target, backup)
        os.unlink(target)
        return backup
    raise OutputWriteError(
        f"could not reserve a backup for {target}: {_LEGACY_BACKUP_ATTEMPTS} backups already exist beside it; "
        "a .bak-* file beside a proposal is an earlier proposal a failed restoration left behind, "
        "review and remove them first"
    )


def _write_proposal_file(proposal: IngestProposal, request: IngestRequest, backend_name: str, output_dir: Path) -> Path:
    """Create the legacy proposal file exclusively (``O_EXCL``, never following a symlink)."""
    proposal_path = output_dir / _proposal_filename(proposal)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(proposal_path, flags, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(render_proposal_file(proposal, request, backend_name))
    except OSError as exc:
        raise OutputWriteError(f"Could not write proposal file at {proposal_path}: {exc}") from exc
    return proposal_path.resolve()


def _roll_back_legacy(proposal_path: Path, backup: Path | None, cause: BaseException) -> None:
    """Undo a failed legacy publication: remove the file this call created and put the previous one back.

    Every rollback failure is reported with the cause (the promoter's rollback
    pattern); a failed restoration is never silent, because the previous
    proposal's bytes are what the backup protects.
    """
    problems: list[str] = []
    if backup is None:
        try:
            os.unlink(proposal_path)
        except FileNotFoundError:
            pass
        except OSError as exc:
            problems.append(f"removing {proposal_path} failed: {exc}")
    else:
        # The file at proposal_path is the one this call created exclusively; it
        # is removed, then the backup takes its place by an atomic rename.
        try:
            os.unlink(proposal_path)
        except FileNotFoundError:
            pass
        except OSError as exc:
            problems.append(f"removing {proposal_path} failed: {exc}")
        try:
            os.replace(backup, proposal_path)
        except OSError as exc:
            problems.append(
                f"restoring the previous proposal from {backup} over {proposal_path} failed: {exc}; "
                f"the previous proposal's bytes are in {backup}"
            )
    if problems:
        raise OutputWriteError(
            f"legacy ingest failed ({cause}); rollback also raised: " + "; ".join(problems)
        ) from cause


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

    with WikiLock(paths.wiki_dir, paths.lock_timeout) as lock:
        # The legacy name is deterministic: a previous proposal is moved aside
        # atomically (never read, never followed) and restored if publication
        # fails, so no caller ever loses it.
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            backup = _legacy_slot(output_dir, _proposal_filename(proposal))
        except OSError as exc:
            raise OutputWriteError(f"could not prepare the proposal path in {output_dir}: {exc}") from exc
        try:
            proposal_path = _write_proposal_file(proposal, request, backend_name, output_dir)
        except BaseException as exc:
            _roll_back_legacy(output_dir / _proposal_filename(proposal), backup, exc)
            raise
        try:
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
            append_ingest_log(paths, record, lock=lock)
        except BaseException as exc:
            # Same policy as the multi-page path, before the lock is released:
            # the file this call created goes, the previous one comes back.
            _roll_back_legacy(proposal_path, backup, exc)
            raise
        if backup is not None:
            try:
                os.unlink(backup)
            except OSError as exc:
                raise OutputWriteError(f"published, but the backup {backup} could not be removed: {exc}") from exc
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
    # One lock from the proposal files through the snapshot and the audit
    # record: a concurrent promote never sees (and archives) a proposal that
    # is still being published.
    with WikiLock(paths.wiki_dir, paths.lock_timeout) as lock:
        try:
            # A generated name: a second ingest of the same source on the same day
            # lands in ``<name>-2`` rather than in a directory that may be mid-promotion.
            written = write_patch_set_dir(
                patch, output_dir, wiki_dir=paths.wiki_dir, on_collision=COLLISION_SUFFIX, lock=lock
            )
        except OSError as exc:
            raise OutputWriteError(f"could not write patch-set dir at {output_dir}: {exc}") from exc
        try:
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
            append_ingest_log(paths, record, lock=lock)
        except BaseException as exc:
            # The directory is ours (created exclusively above): a proposal whose
            # snapshot or audit record failed is removed before the lock is
            # released, so no concurrent promote can apply a half-published one.
            shutil.rmtree(written, ignore_errors=True)
            if isinstance(exc, OSError):
                raise OutputWriteError(f"could not write patch-set dir at {output_dir}: {exc}") from exc
            raise
    return IngestResult(disposition, written, edits, patch.rationale, dry_run, False, patch, None, record)


# ── propose ───────────────────────────────────────────────────


def check_proposal_name(name: str) -> None:
    """Raise ``ValueError`` unless ``name`` is one path component :func:`propose` accepts (0.8.0).

    ASCII letters, digits, ``.``, ``_`` and ``-``, not starting with ``.``: so
    ``<proposals_dir>/<name>`` never leaves the proposals directory.
    """
    if not isinstance(name, str) or not _PROPOSAL_NAME_RE.fullmatch(name):
        raise ValueError(
            "name must be one path component of ASCII letters, digits, '.', '_' and '-' "
            f"not starting with '.', got {name!r}"
        )


def propose(
    edits: list[PageEdit],
    paths: WikiPaths,
    *,
    name: str,
    source: str = "",
    rationale: str = "",
    backend: str = PROPOSE_BACKEND,
    by: str | None = None,
    assign_page_ids: bool = False,
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

    The wiki's knowledge contract is checked first: a malformed manifest, one
    newer than this package, and schema drift on a governed wiki raise
    ``ContractViolationError`` (exit 4); drift on a managed wiki is emitted at
    once as a :class:`~wiki_studio.errors.DriftWarning` and the proposal is
    still written.

    ``by`` names who proposes; ``plan.json`` records it as ``proposer``
    ``{name, source}``: ``flag`` for a non-empty ``by``, else ``env`` from
    ``WIKI_STUDIO_ACTOR``, else ``none`` (attribution, not authentication;
    the OS user name is never recorded). With ``assign_page_ids`` every
    ``create`` whose content has no ``page_id`` gets a fresh
    ``page_id: pg-<32 hex>`` as its last frontmatter line before the preview
    is written; by default the caller's bytes are written unchanged, and a
    caller-supplied ``page_id`` is never rewritten.

    Every wiki, legacy included, refuses (``ContractViolationError``, exit 4)
    an edit whose normalised path has a dot-prefixed component or lies under
    ``schema/`` (the manifest, the audit trail and approval records, schema
    overrides) and a ``create`` or ``update`` whose frontmatter carries a key
    reserved for the approval record (``approved``, ``approved_by``,
    ``approval``, ``review_state``).
    """
    check_proposal_name(name)
    # The knowledge contract (FR-009, FR-011): refused on a newer or malformed
    # manifest and on governed drift; managed drift is a DriftWarning, now.
    for message in check_write_contract(paths):
        warnings.warn(message, DriftWarning, stacklevel=2)
    # FR-014: before validation and the preview, so the preview, the commit and any approval cover these bytes.
    page_edits = _assign_page_ids(list(edits)) if assign_page_ids else list(edits)
    patch = WikiPatchSet(
        edits=page_edits, source_path=source, backend=backend, rationale=rationale, proposer=resolve_actor(by)
    )
    set_errors = validate_patch_set(patch)
    if set_errors:
        raise ContractViolationError("patch-set failed set-level validation:\n  - " + "\n  - ".join(set_errors))
    # FR-028 / FR-029: after the escape checks; every wiki, legacy included.
    check_reserved_edits(patch.edits)
    per_edit_errors = [error for edit in patch.edits for error in validate_page_edit_semantics(edit, paths)]
    if per_edit_errors:
        raise ContractViolationError(
            "patch-set failed per-edit semantic validation:\n  - " + "\n  - ".join(per_edit_errors)
        )
    output_dir = paths.proposals_dir / name
    proposals_dir_existed = paths.proposals_dir.is_dir()
    # Creating the directory (exclusively, under the wiki lock) is the
    # collision check: a caller-selected name that exists is an error, and
    # from here on the directory is ours to remove if a later write fails.
    # The removal happens under the same lock: once the lock is released a
    # concurrent promote may apply and archive whatever it finds.
    with WikiLock(paths.wiki_dir, paths.lock_timeout) as lock:
        try:
            written = write_patch_set_dir(
                patch, output_dir, wiki_dir=paths.wiki_dir, on_collision=COLLISION_ERROR, lock=lock
            )
        except FileExistsError as exc:
            raise OutputWriteError(f"proposal dir already exists: {output_dir}") from exc
        except OSError as exc:
            _discard_partial_proposal(output_dir, paths, proposals_dir_existed)
            raise OutputWriteError(f"could not write patch-set dir at {output_dir}: {exc}") from exc
        except BaseException:
            _discard_partial_proposal(output_dir, paths, proposals_dir_existed)
            raise
        try:
            # Under the same lock as the proposal files: a concurrent promote
            # never sees the directory without its snapshot.
            _write_ingest_snapshot(written)
        except BaseException as exc:
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
    by: str | None = None,
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
    software identity. ``by`` names who promotes; the receipt records it as
    ``actor`` ``{name, source}`` by the rule :func:`propose` uses for
    ``proposer`` (attribution, not authentication). When the manifest's
    policy sets ``auto_approve_on_promote``, each created or updated content
    page whose live bytes still match the committed ones is then approved
    under that actor (drafts never); ``PromoteResult.approved_paths`` lists
    them and a skipped page is a warning, never a failed promotion.

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
        by=by,
    )


# ── approve and review_state: approval bound to the revision and the policy ──


def approve(
    pages: list[str],
    paths: WikiPaths,
    *,
    by: str | None = None,
    expected: dict[str, str] | None = None,
) -> ApproveResult:
    """Record that each page's live revision is approved under the wiki's current policy (FR-021).

    ``pages`` are wiki-relative paths; ``expected`` maps a page path to the
    sha256 the caller reviewed (``read_page``), and a page whose live bytes
    differ is refused. ``by`` names the approver (``flag``; else
    ``WIKI_STUDIO_ACTOR``, ``env``; else none), attribution, not
    authentication. Each decision is one immutable record under
    ``<wiki>/.audit/approvals/``, written by ``promoter.py`` under the wiki
    lock; a page whose live bytes already carry a record that satisfies the
    policy is reported in ``ApproveResult.existing`` and nothing is written.

    Raises ``PathOutsideRootError`` (7) and ``SourceMissingError`` (5) as
    ``read_page``; ``PromoteValidationError`` (9, nothing written) naming
    each page and reason: expected revision differs, a structural-lint
    violation for the page, ``status: draft``, ``superseded_by``, an approver
    required and none named; ``ContractViolationError`` (4) for a legacy wiki
    (run ``init``), a newer or malformed manifest, drift on a governed wiki
    and a symlink in the approval tree; ``OutputWriteError`` (6) when
    publication fails part way, naming the pages published and not (running
    ``approve`` again is idempotent). Drift on a managed wiki is in
    ``ApproveResult.warnings``.
    """
    try:
        return _approve(list(pages), paths, by=by, expected=expected)
    except OSError as exc:
        raise OutputWriteError(f"could not write an approval record under {paths.wiki_dir}: {exc}") from exc


def review_state(paths: WikiPaths, *, pages: list[str] | None = None) -> list[ReviewState]:
    """Each page's review state from its verified approval records; reads only, takes no lock (FR-026).

    Advisory and point-in-time, like ``promote --dry-run``. ``pages=None``
    covers every page the structural linter lists except the root
    ``index.md`` and ``log.md``; an explicit list covers exactly those pages
    (exit 7 / 5 as ``read_page``). States, decided in order: a legacy wiki
    reads ``unapproved`` with reason ``manifest_missing``; a page carrying
    ``superseded_by`` reads ``superseded``; a live ``status: draft`` reads
    ``unapproved`` with reason ``draft``; then ``approved`` when a verified
    record for the live bytes satisfies the current policy,
    ``policy-changed`` when such records exist but none satisfies it,
    ``stale`` when only records for other bytes exist, else ``unapproved``.
    Frontmatter never makes a page approved. Each state names the live and
    the approved sha256 and the record it rests on.
    """
    return review_states(paths, pages)


def findings(paths: WikiPaths, *, pages: list[str] | None = None) -> FindingsResult:
    """What needs a curator's attention, from code that takes no backend and calls no model (FR-037, FR-038).

    Counts by kind first, then the findings: the deterministic health kinds
    (``stale-claim``, ``weak-orphan``, ``missing-cross-link``,
    ``avoid-format``), the review kinds from :func:`review_state`
    (``unapproved``, ``approval-stale``, ``approval-policy-changed``),
    ``superseded-still-indexed`` and ``no-page-id``. Reads only, takes no
    lock. ``pages=None`` covers the whole wiki; an explicit list scopes every
    kind to those pages (``PathOutsideRootError`` / ``SourceMissingError`` as
    ``read_page``). A completed run is a result whatever it finds;
    ``lint --health --strict`` stays the CI gate.
    """
    return _findings(paths, pages=pages)


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

    The wiki boundary (FR-012), checked by :func:`wiki_studio.paths.contain`
    before anything is read: the candidate must be relative, resolve inside
    the resolved wiki directory, and no component of it may be a symlink.
    """
    raw = Path(path)
    text = raw.as_posix()
    rel = posixpath.normpath(text)
    if is_absolute_path(text) or rel == "." or rel.startswith("../") or rel == "..":
        raise PathOutsideRootError(f"page path must be wiki-relative and stay inside the wiki: {path}")
    try:
        contain(rel, paths.wiki_dir)
    except ContainmentError as exc:
        if exc.reason == CONTAIN_SYMLINK:
            raise PathOutsideRootError(
                f"page path passes through a symlink, which is outside the wiki boundary: {rel}"
            ) from exc
        raise PathOutsideRootError(f"page path escapes the wiki directory {paths.wiki_dir}: {rel}") from exc
    return rel, paths.wiki_dir / rel


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


def init(paths: WikiPaths, *, title: str = DEFAULT_WIKI_TITLE, update_schema: bool = False) -> InitResult:
    """Create the wiki directory with a minimal ``index.md`` and ``log.md`` when absent, and the root manifest.

    Never overwrites: a wiki without a manifest gains one and nothing else
    changes. ``update_schema`` acknowledges changed project schema overrides
    by rewriting only the manifest's ``schema_fingerprint``.
    ``InitResult.manifest`` says what happened (``created``, ``existing``,
    ``updated``).

    Raises ``ContractViolationError`` (exit 4) for a symlinked wiki directory,
    manifest or schema override, and for a malformed or newer manifest;
    ``OutputWriteError`` when the directory or a file cannot be written.
    """
    try:
        return init_wiki(paths, title=title, update_schema=update_schema)
    except OSError as exc:
        raise OutputWriteError(f"could not initialise the wiki at {paths.wiki_dir}: {exc}") from exc


# ── info: the contract this build and this wiki follow ────────


def info(paths: WikiPaths) -> InfoResult:
    """Describe the shipped build and the wiki's knowledge contract (FR-010); reads only, takes no lock.

    ``package_version``; ``schema_contract`` (schema id and version, whether
    the rules come from project overrides, the current and the declared
    fingerprint, drift); ``formats`` and ``capabilities`` of this build; and
    ``manifest`` (``present`` with its version, ``wiki_id``, policy and mode,
    or ``missing`` for a legacy wiki with the instruction to run ``init``).
    ``warnings`` carries the drift message ``propose`` and ``promote`` give.
    A host checks this before it writes. ``discovery`` (0.8.0) says whether
    this Python's SQLite has FTS5, the default ranker and where it came from,
    and the live ranker configuration hash. Raises ``ContractViolationError``
    (exit 4) for a malformed or newer manifest and a symlinked override, and
    ``ValueError`` when ``WIKI_STUDIO_RANKER`` names no ranker.
    """
    return replace(describe(paths), discovery=describe_discovery(paths))


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
    """One page the querier would load for a question: wiki-relative path, file, title, sha256 and byte count.

    ``sha256`` and ``bytes`` describe the bytes read in this call (0.8.0).
    """

    path: str
    file: Path
    title: str
    sha256: str = ""
    bytes: int = 0


@dataclass(frozen=True)
class FindResult:
    """The pages ``query`` would put in front of a model, in order, without calling one.

    0.8.0 adds how they were chosen: the ``ranker`` that ran (``index-first``
    when ``fts5`` fell back, with ``fallback_reason``), ``bytes_loaded``
    (``index.md`` plus the pages) against ``max_bytes``, the ranked pages
    ``omitted`` for the budget, the index-linked pages that are
    ``ineligible`` and why, the ``ranker_config_hash`` of the ``fts5``
    configuration (None for ``index-first``) and ``warnings``.
    """

    question: str
    index: Path
    pages: tuple[FoundPage, ...]
    ranker: str = DEFAULT_RANKER
    fallback_reason: str | None = None
    bytes_loaded: int = 0
    max_bytes: int = DEFAULT_MAX_CONTEXT_BYTES
    omitted: tuple[OmittedPage, ...] = ()
    ineligible: tuple[IneligiblePage, ...] = ()
    ranker_config_hash: str | None = None
    warnings: tuple[str, ...] = ()

    def as_dict(self, paths: WikiPaths) -> dict[str, Any]:
        """The ``find --json`` object (FR-009), files relative to ``paths.root``; the MCP ``find`` tool returns it."""
        return {
            "question": self.question,
            "index": paths.relative_to_root(self.index),
            "pages": [
                {
                    "path": p.path,
                    "file": paths.relative_to_root(p.file),
                    "title": p.title,
                    "sha256": p.sha256,
                    "bytes": p.bytes,
                }
                for p in self.pages
            ],
            "ranker": self.ranker,
            "fallback_reason": self.fallback_reason,
            "bytes_loaded": self.bytes_loaded,
            "max_bytes": self.max_bytes,
            "ranker_config_hash": self.ranker_config_hash,
            "omitted": [{"path": o.path, "bytes": o.bytes} for o in self.omitted],
            "ineligible": [{"path": i.path, "reason": i.reason} for i in self.ineligible],
            "warnings": list(self.warnings),
        }


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


def find(
    question: str,
    paths: WikiPaths,
    *,
    max_pages: int = DEFAULT_MAX_QUERY_PAGES,
    max_bytes: int = DEFAULT_MAX_CONTEXT_BYTES,
    ranker: str | None = None,
    ranker_config: RankerConfig | None = None,
) -> FindResult:
    """Run only the page selection of :func:`query`: no backend, no query log, nothing written.

    The result is what a model would be given to read: ``index.md`` plus up to
    ``max_pages`` eligible index-linked pages within ``max_bytes``, ranked by
    ``ranker`` (``fts5`` or ``index-first``; None means ``WIKI_STUDIO_RANKER``,
    then the default). ``ranker_config`` (None: the live default) configures
    ``fts5``. An empty ``pages`` means no eligible page matched. Raises
    ``SourceMissingError`` (exit 5) when the wiki has no ``index.md`` and
    ``ValueError`` for an unknown ranker, a ``max_pages`` outside 1..5 or a
    ``max_bytes`` that is not a positive integer.
    """
    validate_max_pages(max_pages)
    resolved, _source = resolve_ranker(ranker)
    selection = select(paths, question, max_pages=max_pages, max_bytes=max_bytes, ranker=resolved, config=ranker_config)
    if not selection.index_md:
        raise SourceMissingError(
            f"{paths.wiki_label}/index.md not found; nothing to find. Run `wiki-studio init` to create the wiki."
        )
    pages = tuple(
        FoundPage(
            path=page.path,
            file=paths.wiki_dir / page.path,
            title=_page_title(page.text, Path(page.path).stem),
            sha256=page.sha256,
            bytes=page.bytes,
        )
        for page in selection.pages
    )
    return FindResult(
        question=question,
        index=paths.wiki_dir / INDEX_NAME,
        pages=pages,
        ranker=selection.ranker,
        fallback_reason=selection.fallback_reason,
        bytes_loaded=selection.bytes_loaded,
        max_bytes=selection.max_bytes,
        omitted=selection.omitted,
        ineligible=selection.ineligible,
        ranker_config_hash=selection.ranker_config_hash,
        warnings=selection.warnings,
    )


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
    max_bytes: int = DEFAULT_MAX_CONTEXT_BYTES,
    ranker: str | None = None,
    ranker_config: RankerConfig | None = None,
) -> QueryResult:
    """Answer ``question`` index-first over the wiki; with ``file_back`` also write a patch-set for the answer.

    Pages are selected as :func:`find` selects them (``max_pages`` in 1..5,
    ``max_bytes``, ``ranker``, ``ranker_config``); a rejected value is a
    ``ValueError`` before any backend is resolved.
    """
    max_pages = DEFAULT_MAX_QUERY_PAGES if max_pages is None else max_pages
    validate_max_pages(max_pages)
    resolve_ranker(ranker)
    resolved = prepare_backend(backend, paths, redact_output=redact_output)
    querier = DefaultQuerier(
        backend=resolved,
        paths=paths,
        max_pages=max_pages,
        max_bytes=max_bytes,
        ranker=ranker,
        ranker_config=ranker_config,
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
    violations = tuple(lint_wiki(paths.wiki_dir, root=paths.root, source_roots=paths.source_roots))
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
