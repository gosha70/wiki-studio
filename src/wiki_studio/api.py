# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wiki_studio.api — the library surface: ``ingest``, ``propose``, ``promote``, ``query``, ``lint``, ``audit_flush``.

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

import datetime
import os
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
from .ingestor_multi import DefaultMultiIngestor, write_patch_set_dir
from .lint import lint_wiki, list_pages
from .promoter import DEFAULT_WIKI_TITLE, INDEX_NAME, LOG_NAME, InitResult, PromoteResult, init_wiki
from .promoter import promote as _promote
from .proposal import (
    IngestLogRecord,
    IngestProposal,
    IngestRequest,
    PageAction,
    PageEdit,
    QueryAnswer,
    WikiPatchSet,
    render_proposal_file,
    validate_page_edit_semantics,
    validate_patch_set,
)
from .querier import DEFAULT_MAX_QUERY_PAGES, DefaultQuerier, _select_query_candidates

if TYPE_CHECKING:
    from .health_lint import HealthLintResult
    from .ingestor import Backend
    from .paths import WikiPaths

__all__ = [
    "ALLOW_OUT_OF_REPO_HINT",
    "ALLOW_OUT_OF_REPO_PROMOTE_HINT",
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
]

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
    """Structural violations, audit-format errors and (optionally) knowledge-health findings."""

    violations: tuple[str, ...]
    pages_checked: int
    audit_errors: tuple[str, ...]
    health: HealthLintResult | None
    strict: bool

    @property
    def passed(self) -> bool:
        """Structural violations always fail; audit and health findings fail only under ``strict``."""
        if self.violations:
            return False
        if not self.strict:
            return True
        if self.audit_errors:
            return False
        return not (self.health is not None and self.health.findings)


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
        written = write_patch_set_dir(patch, output_dir)
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
        # Creating the directory is the collision check: it must not exist, and
        # from here on it is ours to remove if a later write fails.
        output_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise OutputWriteError(f"proposal dir already exists: {output_dir}") from exc
    except OSError as exc:
        raise OutputWriteError(f"could not create patch-set dir at {output_dir}: {exc}") from exc
    try:
        written = write_patch_set_dir(patch, output_dir)
        _write_ingest_snapshot(written)
    except Exception as exc:
        # Any failure, not only OSError: leave no half-written directory behind.
        shutil.rmtree(output_dir, ignore_errors=True)
        if not proposals_dir_existed:
            shutil.rmtree(paths.proposals_dir, ignore_errors=True)
        if isinstance(exc, OSError):
            raise OutputWriteError(f"could not write patch-set dir at {output_dir}: {exc}") from exc
        raise
    return written


# ── promote ───────────────────────────────────────────────────


def promote(
    proposal_dir: Path,
    paths: WikiPaths,
    *,
    dry_run: bool = False,
    allow_out_of_repo: bool = False,
) -> PromoteResult:
    """Apply a patch-set directory to the wiki atomically (the only write into the wiki).

    Raises ``SourceMissingError`` when the directory does not exist,
    ``PathOutsideRootError`` when it lies outside the root without
    ``allow_out_of_repo``, and the promoter's validation/apply errors.
    """
    proposal_path = Path(proposal_dir)
    if not proposal_path.exists():
        raise SourceMissingError(f"proposals dir not found: {proposal_path}")
    _require_within_root("proposal dir", proposal_path, paths, allow_out_of_repo, ALLOW_OUT_OF_REPO_PROMOTE_HINT)
    return _promote(proposals_dir=proposal_path, paths=paths, dry_run=dry_run)


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

    Files under hidden directories are skipped. Raises ``SourceMissingError``
    when ``source_dir`` is not a directory and ``ContractViolationError`` for
    an index or log file that is a page or a ``source_dir`` that overlaps the wiki.
    """
    root = Path(source_dir)
    if not root.is_dir():
        raise SourceMissingError(f"--from directory not found: {root}")
    src, wiki = root.resolve(), paths.wiki_dir.resolve()
    if src == wiki or src.is_relative_to(wiki) or wiki.is_relative_to(src):
        raise ContractViolationError(
            f"--from {root} overlaps the wiki directory {paths.wiki_dir}; write drafts somewhere else"
        )
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
        edits.append(PageEdit(rel, "update" if exists else "create", text, why))
    return edits


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
    An empty ``pages`` means no index-linked page shares a word with it.
    """
    _index_md, selected, contents = _select_query_candidates(paths, question, max_pages)
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
        written = write_patch_set_dir(patch, out)
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
) -> LintResult:
    """Structural lint plus the audit-format pass; ``health`` adds the knowledge-health checks.

    ``backend`` is only consulted with ``health`` (for the contradiction
    check); when it is None, contradictions are skipped.
    """
    violations = tuple(lint_wiki(paths.wiki_dir))
    pages_checked = len(list_pages(paths.wiki_dir))
    audit_errors = tuple(validate_audit_tree(paths))
    health_result: HealthLintResult | None = None
    if health:
        resolved = prepare_backend(backend, paths, redact_output=redact_output) if backend is not None else None
        health_result = lint_health(paths, only=only, backend=resolved)
    return LintResult(violations, pages_checked, audit_errors, health_result, strict)


# ── audit-flush ───────────────────────────────────────────────


def audit_flush(paths: WikiPaths, *, dry_run: bool = False) -> AuditFlushResult:
    """Commit pending ingest-log lines (or report them with ``dry_run``); raises ``AuditFlushError``."""
    return flush_state(paths, dry_run)
