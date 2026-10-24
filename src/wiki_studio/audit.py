# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# wiki-studio.audit — the ONLY module that writes ingest-log.md.
#
# Contains the helpers for computing source_sha, proposal_hash, and
# truncate_reason, plus build_log_record (derives a patch-set-oriented
# IngestLogRecord from a WikiPatchSet or IngestProposal) and
# append_ingest_log (the fail-closed, marker-prefixed writer).
#
# append_ingest_log is called from cli.py ingest handlers AFTER the
# proposal dir is materialized + dry-run stripped (Design Decision 8), NOT
# from ingestor.py / ingestor_multi.py.
#
# See schema/audit-rules.md for the normative format spec.

from __future__ import annotations

import datetime
import hashlib
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

from .audit_lint import INGEST_LOG_MARKER
from .errors import OutputWriteError, PromoteValidationError
from .proposal import IngestLogRecord, IngestProposal, WikiPatchSet
from .schema import PAGE_TYPE_DIRS, PROMOTABLE_PAGE_TYPES
from .wikilock import WikiLock

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .paths import WikiPaths

# ── Helpers ────────────────────────────────────────────────────────────────

# The digest recipes documented in schema/audit-rules.md. Recipe 1 (``proposal_hash``)
# skips dot-prefixed components; recipe 2 (``payload_digest``) enumerates ``preview/``
# without exclusions. New ingest-log records and every receipt use recipe 2; recipe 1
# stays implemented to verify records written before 0.6.0.
HASH_RECIPE_PROPOSAL_HASH = 1
HASH_RECIPE_PAYLOAD_DIGEST = 2

PLAN_FILE_NAME = "plan.json"
PREVIEW_DIR_NAME = "preview"


def source_sha(source_file: Path) -> str:
    """Return the SHA-256 lowercase-hex digest of source_file's raw bytes."""
    return hashlib.sha256(source_file.read_bytes()).hexdigest()


def _canonical_digest(files: Mapping[str, bytes]) -> str:
    """The shared framing of both recipes over proposal-relative POSIX paths and their bytes.

    Sort by the UTF-8 bytes of the path (``LC_ALL=C`` order); for each file append
    ``<path>\\n<bytes>\\n--\\n``; SHA-256 the buffer; lowercase hex.
    """
    buf = bytearray()
    for rel_posix in sorted(files, key=lambda rel: rel.encode("utf-8")):
        buf += rel_posix.encode("utf-8")
        buf += b"\n"
        buf += files[rel_posix]
        buf += b"\n--\n"
    return hashlib.sha256(bytes(buf)).hexdigest()


def _identity_files(proposal_dir: Path) -> dict[str, Path]:
    """``plan.json`` plus every file under ``preview/`` (symlinks refused), keyed by proposal-relative path."""
    found: dict[str, Path] = {}
    plan = proposal_dir / PLAN_FILE_NAME
    if plan.is_symlink():
        raise PromoteValidationError(f"{PLAN_FILE_NAME} in {proposal_dir} is a symlink; refusing to read through it")
    if plan.is_file():
        found[PLAN_FILE_NAME] = plan
    preview = proposal_dir / PREVIEW_DIR_NAME
    if preview.is_symlink():
        raise PromoteValidationError(f"{PREVIEW_DIR_NAME}/ in {proposal_dir} is a symlink; refusing to read through it")
    if preview.is_dir():
        for p in sorted(preview.rglob("*")):
            if p.is_symlink():
                raise PromoteValidationError(
                    f"{p.relative_to(proposal_dir).as_posix()} in {proposal_dir} is a symlink; "
                    "refusing to read through it"
                )
            if p.is_file():
                found[p.relative_to(proposal_dir).as_posix()] = p
    return found


def payload_digest_from_files(files: Mapping[str, bytes]) -> str:
    """Recipe 2 over an in-memory capture: ``plan.json`` and every ``preview/`` file, nothing excluded.

    ``files`` maps proposal-relative POSIX paths to bytes; entries outside the
    identity set (``.ingest-snapshot/``, notes) are ignored, so the same call
    serves a full submission manifest and a bare payload.
    """
    identity = {
        rel: data for rel, data in files.items() if rel == PLAN_FILE_NAME or rel.startswith(PREVIEW_DIR_NAME + "/")
    }
    return _canonical_digest(identity)


def payload_digest(proposal_dir: Path) -> str:
    """Recipe 2: the SHA-256 identity of the applied payload, read from ``proposal_dir``.

    Like :func:`proposal_hash` but with no dot-component exclusion: hidden
    preview files such as ``preview/.line.md`` count, so a preview the loader
    would accept cannot change under an unchanged digest. ``.ingest-snapshot/``
    is outside ``preview/`` and therefore outside the identity. Symlinks under
    the proposal are refused (``PromoteValidationError``).
    """
    return _canonical_digest({rel: p.read_bytes() for rel, p in _identity_files(proposal_dir).items()})


def proposal_hash(proposal_dir: Path) -> str:
    """Recipe 1: the SHA-256 canonical hash every ingest-log record before 0.6.0 carries.

    Canonicalization recipe (from audit-rules.md):
      1. Collect plan.json + every file under preview/ recursively.
         Exclude .ingest-snapshot/ and any path component beginning with '.'.
      2. Sort by repo-relative POSIX path under LC_ALL=C (byte order).
      3. For each file, append:
           <rel_path UTF-8> + b'\\n' + raw bytes + b'\\n--\\n'
      4. SHA-256 the concatenated buffer; return lowercase hex.

    Kept to verify those records; new records and receipts use :func:`payload_digest`.
    """
    files: list[Path] = []

    plan = proposal_dir / PLAN_FILE_NAME
    if plan.is_file():
        files.append(plan)

    preview = proposal_dir / PREVIEW_DIR_NAME
    if preview.is_dir():
        for p in preview.rglob("*"):
            if p.is_file():
                files.append(p)

    def _is_excluded(p: Path) -> bool:
        """True if any path component begins with '.' (dotfile/dotdir)."""
        # Check each component relative to proposal_dir.
        try:
            rel = p.relative_to(proposal_dir)
        except ValueError:
            return True
        return any(part.startswith(".") for part in rel.parts)

    included = {f.relative_to(proposal_dir).as_posix(): f.read_bytes() for f in files if not _is_excluded(f)}
    return _canonical_digest(included)


def truncate_reason(s: str) -> str:
    """Collapse whitespace/newlines to single spaces; truncate to 240 codepoints.

    If the result exceeds 240 codepoints, it is truncated to 239 codepoints
    followed by U+2026 (HORIZONTAL ELLIPSIS) — total exactly 240.
    """
    # Collapse runs of whitespace (including newlines) to a single space.
    collapsed = re.sub(r"\s+", " ", s).strip()
    if len(collapsed) <= 240:
        return collapsed
    return collapsed[:239] + "…"


# ── Record builder ─────────────────────────────────────────────────────────


def _page_type_from_path(path: str) -> str:
    """Derive a page type from a wiki-relative path (best-effort)."""
    # Most wiki paths are <page_type_dir>/<slug>.md; the directory name
    # is the canonical page type string. E.g. "concepts/foo.md" → "concept"
    # but the directory is "concepts" not "concept".  We want the
    # *directory name* as the type label for audit purposes.
    parts = Path(path).parts
    if len(parts) >= 2:
        return parts[0]
    return "unknown"


def build_log_record(
    *,
    source_file: Path,
    paths: WikiPaths,
    backend_name: str,
    proposal_dir_path: Path | None,
    allow_out_of_repo: bool = False,
    patch: WikiPatchSet | None = None,
    legacy_proposal: IngestProposal | None = None,
    dry_run: bool = False,
) -> IngestLogRecord:
    """Derive an IngestLogRecord from a WikiPatchSet or IngestProposal.

    Exactly one of ``patch`` or ``legacy_proposal`` must be supplied.

    Parameters
    ----------
    source_file : Path
        The source file on disk (used to compute source_sha and derive
        source_path).
    paths : WikiPaths
        The resolved layout; ``paths.root`` anchors the repo-relative POSIX source_path.
    backend_name : str
        Backend display name (``"test"``, ``"claude"``, etc.).
    proposal_dir_path : Path | None
        Path to the materialized proposal directory (used as the basename
        for ``proposal_dir`` and to compute ``proposal_hash``). None only
        when the dir was not materialized (impossible for a normal or
        --dry-run run; --check never calls this).
    allow_out_of_repo : bool
        When True, source_path is recorded verbatim and
        source_repo_relative is False.
    patch : WikiPatchSet | None
        Multi-page ingest result.  Disposition is "accept" iff edits
        non-empty; reason is patch.rationale.
    legacy_proposal : IngestProposal | None
        Legacy single-source result.  Disposition and reason taken directly.
    dry_run : bool
        When True, proposal_hash is forced to None (body was stripped).
    """
    if patch is None and legacy_proposal is None:
        raise ValueError("build_log_record: must supply patch or legacy_proposal")
    if patch is not None and legacy_proposal is not None:
        raise ValueError("build_log_record: supply exactly one of patch/legacy_proposal")

    # source_path and source_repo_relative.
    try:
        rel = source_file.resolve().relative_to(paths.root.resolve())
        src_path = rel.as_posix()
        src_repo_relative = True
    except ValueError:
        src_path = str(source_file)
        src_repo_relative = False

    sha = source_sha(source_file)

    now_ts = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    if patch is not None:
        # Multi-page (WikiPatchSet).
        disp = "accept" if patch.edits else "reject"
        raw_reason = patch.rationale or ""
        if patch.edits:
            tgt_paths = sorted({e.path for e in patch.edits})
            pg_types = sorted({_page_type_from_path(e.path) for e in patch.edits})
        else:
            tgt_paths = []
            pg_types = []
    else:
        # Legacy (IngestProposal).
        assert legacy_proposal is not None
        disp = legacy_proposal.disposition
        raw_reason = legacy_proposal.reason or ""
        if legacy_proposal.slug:
            page_type = legacy_proposal.page_type or "unknown"
            page_dir = _LEGACY_PAGE_TYPE_DIR.get(page_type, page_type + "s")
            tgt_paths = [f"{page_dir}/{legacy_proposal.slug}.md"]
            pg_types = [page_type]
        else:
            tgt_paths = []
            pg_types = []

    reason = truncate_reason(raw_reason)

    prop_dir_name: str | None = proposal_dir_path.name if proposal_dir_path is not None else None

    # proposal_hash: None on reject (empty edits), --dry-run, or no proposal dir.
    # Since 0.6.0 the value is recipe 2 (payload_digest) and the record says so.
    p_hash: str | None = None
    recipe: int | None = None
    if not dry_run and disp == "accept" and proposal_dir_path is not None and proposal_dir_path.is_dir():
        p_hash = payload_digest(proposal_dir_path)
        recipe = HASH_RECIPE_PAYLOAD_DIGEST

    return IngestLogRecord(
        v=1,
        ts=now_ts,
        source_path=src_path,
        source_repo_relative=src_repo_relative,
        source_sha=sha,
        backend=backend_name,
        disposition=disp,
        reason=reason,
        proposal_dir=prop_dir_name,
        target_paths=tgt_paths,
        page_types=pg_types,
        proposal_hash=p_hash,
        hash_recipe=recipe,
    )


# Map legacy page_type values (always a promotable type) to their wiki directory names.
_LEGACY_PAGE_TYPE_DIR: dict[str, str] = {name: PAGE_TYPE_DIRS[name] for name in PROMOTABLE_PAGE_TYPES}


# ── Append writer (the only writer of ingest-log.md) ──────────────────────


def record_to_json_line(record: IngestLogRecord) -> str:
    """One NDJSON line for ``record``: the fields in definition order; ``hash_recipe`` only when set."""
    import dataclasses

    obj = dataclasses.asdict(record)
    if obj.get("hash_recipe") is None:
        # A record without the key was produced by recipe 1 (or carries no hash).
        obj.pop("hash_recipe", None)
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def append_ingest_log(paths: WikiPaths, record: IngestLogRecord) -> None:
    """Append one NDJSON line to the ingest log (``paths.audit_log``).

    Creates the file with the marker preamble if it does not exist. The read
    of the current tail and the append happen under the wiki lock
    (:class:`~wiki_studio.wikilock.WikiLock`), so two cooperating writers
    never interleave lines and ``audit-flush`` never commits a torn tail.
    Fail-closed: any OSError is re-raised so the caller can exit via
    OutputWriteError (exit code 6); a lock timeout is ``PromoteApplyError``
    (exit 10, ``reason="lock_timeout"``).
    """
    log_path = paths.audit_log
    line = record_to_json_line(record)
    try:
        with WikiLock(paths.wiki_dir, paths.lock_timeout):
            log_path.parent.mkdir(parents=True, exist_ok=True)

            if not log_path.exists():
                # First write: create with marker + blank line.
                content = INGEST_LOG_MARKER + "\n\n" + line + "\n"
                log_path.write_text(content, encoding="utf-8")
                return

            # Ensure the file ends with a newline before we append.
            existing = log_path.read_bytes()
            prefix = b"" if not existing or existing.endswith(b"\n") else b"\n"
            # Binary append: no re-encoding of the existing content, and the
            # existing bytes are never rewritten (the append-only invariant
            # ``audit-flush`` checks).
            with log_path.open("ab") as handle:
                handle.write(prefix + (line + "\n").encode("utf-8"))
    except OSError as exc:
        raise OutputWriteError(f"audit log append failed for {log_path}: {exc}") from exc
