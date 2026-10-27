# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# wiki-studio.audit_lint — Phase-1 audit-trail format lint.
#
# The lint-side validator for <wiki_dir>/.audit/. It implements the
# machine-checkable spec in schema/audit-rules.md the same way
# wiki-studio.lint implements lint-rules.md: the schema file is the
# human contract, this module is the executable check. It is NOT loaded
# via prompt.load_schema_files and is never injected into a backend
# prompt — it is consumed directly by `wiki-studio lint`.
#
# v1 is FORMAT-ONLY: marker, NDJSON shape, required keys/types/enums,
# ts pattern, reason codepoint bound, archive directory contents. No
# referential cross-checks (source_sha resolves, proposal_hash matches
# an archive) — those are a named follow-up, not v1.

from __future__ import annotations

import json
import os
import re
import stat
from typing import TYPE_CHECKING

from .contract import parse_manifest
from .errors import ContractViolationError
from .paths import AUDIT_DIR_NAME, MANIFEST_NAME
from .proposal import is_page_id, is_sha256_hex
from .review import (
    APPROVALS_DIR_NAME,
    DECISIONS,
    NAMESPACE_ID,
    NAMESPACES,
    RECORD_SUFFIX,
    RECORD_TMP_SUFFIX,
    canonical_path,
    path_digest,
    record_problem,
)

if TYPE_CHECKING:
    from pathlib import Path

    from .paths import WikiPaths

INGEST_LOG_MARKER = "<!-- ingest-log schema v1 -->"

_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

_REASON_MAX_CODEPOINTS = 240
_DISPOSITIONS = {"accept", "reject"}

# Exact key set for schema v1. No more, no less.
_REQUIRED_KEYS: dict[str, type | tuple[type, ...]] = {
    "v": int,
    "ts": str,
    "source_path": str,
    "source_repo_relative": bool,
    "source_sha": str,
    "backend": str,
    "disposition": str,
    "reason": str,
    "proposal_dir": (str, type(None)),
    "target_paths": list,
    "page_types": list,
    "proposal_hash": (str, type(None)),
}

# The one optional key accepted in v: 1 since 0.6.0: which digest recipe produced
# ``proposal_hash`` (2 = ``audit.payload_digest``). A record without it used recipe 1.
_OPTIONAL_KEYS: frozenset[str] = frozenset({"hash_recipe"})
_HASH_RECIPES = {1, 2}

_PERMITTED_PROPOSAL_ENTRIES = {"plan.json", "proposal.md", "curator-delta.md"}


def _validate_ingest_log(path: Path) -> list[str]:
    """Return a list of violation strings for ingest-log.md (empty = clean)."""
    errors: list[str] = []
    raw = path.read_text(encoding="utf-8")
    lines = raw.split("\n")

    if not lines or lines[0] != INGEST_LOG_MARKER:
        errors.append(f"{path}: line 1 must be exactly '{INGEST_LOG_MARKER}'")
        # Without a valid marker the rest is unreliable; still try lines.
    if len(lines) < 2 or lines[1] != "":
        errors.append(f"{path}: line 2 must be empty")

    for n, line in enumerate(lines[2:], start=3):
        if line == "":
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{n}: not valid JSON ({exc.msg})")
            continue
        if not isinstance(obj, dict):
            errors.append(f"{path}:{n}: JSON value is not an object")
            continue

        keys = set(obj)
        missing = set(_REQUIRED_KEYS) - keys
        extra = keys - set(_REQUIRED_KEYS) - set(_OPTIONAL_KEYS)
        if missing:
            errors.append(f"{path}:{n}: missing keys {sorted(missing)}")
        if extra:
            errors.append(f"{path}:{n}: unexpected keys {sorted(extra)}")

        recipe = obj.get("hash_recipe")
        if "hash_recipe" in obj and (isinstance(recipe, bool) or not isinstance(recipe, int)):
            errors.append(f"{path}:{n}: 'hash_recipe' must be int (got {type(recipe).__name__})")
        elif isinstance(recipe, int) and recipe not in _HASH_RECIPES:
            errors.append(f"{path}:{n}: unknown hash_recipe {recipe} (this linter knows {sorted(_HASH_RECIPES)})")

        for key, typ in _REQUIRED_KEYS.items():
            if key in obj and not isinstance(obj[key], typ):
                # bool is an int subclass — guard v/source_repo_relative.
                if key == "v" and isinstance(obj[key], bool):
                    errors.append(f"{path}:{n}: 'v' must be int, not bool")
                elif typ is int and isinstance(obj[key], bool):
                    errors.append(f"{path}:{n}: '{key}' must be int, not bool")
                else:
                    errors.append(f"{path}:{n}: '{key}' has wrong type (got {type(obj[key]).__name__})")

        ver = obj.get("v")
        if isinstance(ver, int) and not isinstance(ver, bool) and ver != 1:
            errors.append(f"{path}:{n}: unsupported schema version v={ver} (this linter knows v=1)")

        for arr_key in ("target_paths", "page_types"):
            arr = obj.get(arr_key)
            if isinstance(arr, list):
                bad = [i for i, v in enumerate(arr) if not isinstance(v, str)]
                if bad:
                    errors.append(
                        f"{path}:{n}: '{arr_key}' must be an array of strings (non-string item at index {bad[0]})"
                    )

        disp = obj.get("disposition")
        if isinstance(disp, str) and disp not in _DISPOSITIONS:
            errors.append(f"{path}:{n}: disposition '{disp}' not in {sorted(_DISPOSITIONS)}")

        ts = obj.get("ts")
        if isinstance(ts, str) and not _TS_RE.match(ts):
            errors.append(f"{path}:{n}: ts '{ts}' is not ISO-8601 UTC (YYYY-MM-DDThh:mm:ssZ)")

        reason = obj.get("reason")
        if isinstance(reason, str) and len(reason) > _REASON_MAX_CODEPOINTS:
            errors.append(f"{path}:{n}: reason is {len(reason)} codepoints (max {_REASON_MAX_CODEPOINTS})")

        sha = obj.get("source_sha")
        if isinstance(sha, str) and not _HEX64_RE.match(sha):
            errors.append(f"{path}:{n}: source_sha is not 64 lowercase hex")

        phash = obj.get("proposal_hash")
        if isinstance(phash, str) and not _HEX64_RE.match(phash):
            errors.append(f"{path}:{n}: proposal_hash is not null or 64 lowercase hex")

    return errors


def _validate_proposal_dir(d: Path) -> list[str]:
    """Return violation strings for one .audit/proposals/<name>/ dir."""
    errors: list[str] = []
    children = list(d.iterdir())
    entries = {p.name for p in children}

    # Required entries must exist AND be regular files (a directory
    # named plan.json is a violation, not an IsADirectoryError).
    for required in ("plan.json", "proposal.md"):
        target = d / required
        if required not in entries:
            errors.append(f"{d}: missing required {required}")
        elif not target.is_file():
            errors.append(f"{d}/{required}: must be a regular file")

    plan = d / "plan.json"
    if plan.is_file():
        try:
            json.loads(plan.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{d}/plan.json: not valid JSON ({exc.msg})")
        except OSError as exc:
            errors.append(f"{d}/plan.json: unreadable ({exc})")

    unexpected = sorted(entries - _PERMITTED_PROPOSAL_ENTRIES)
    if unexpected:
        errors.append(f"{d}: unexpected entries {unexpected} (permitted: {sorted(_PERMITTED_PROPOSAL_ENTRIES)})")
    return errors


def validate_audit_tree(paths: WikiPaths) -> list[str]:
    """Validate ``<wiki_dir>/.audit/``. Empty list = clean (or absent).

    Format-only per audit-rules.md v1. A missing .audit/ tree is clean
    (the trail simply has not started yet).
    """
    return validate_audit_dir(paths.wiki_dir / AUDIT_DIR_NAME)


def validate_audit_dir(audit_dir: Path) -> list[str]:
    """Validate one `.audit/` directory directly (used by tests/fixtures).

    Same contract as validate_audit_tree but takes the `.audit/` path
    itself rather than a repo root.
    """
    if not audit_dir.is_dir():
        return []

    errors: list[str] = []

    # Closed top-level set: only ingest-log.md (file), proposals/ and
    # approvals/ (dirs). .audit/ is exempt from structural lint, so a stray
    # .audit/notes.md must be caught here or it is invisible.
    for child in sorted(audit_dir.iterdir()):
        if child.name == "ingest-log.md":
            if not child.is_file():
                errors.append(f"{child}: ingest-log.md must be a file")
        elif child.name == "proposals":
            if not child.is_dir():
                errors.append(f"{child}: proposals must be a directory")
        elif child.name == APPROVALS_DIR_NAME:
            errors.extend(_validate_approvals(child))
        else:
            errors.append(
                f"{child}: unexpected entry under .audit/ (only ingest-log.md, proposals/ and approvals/ are permitted)"
            )

    log = audit_dir / "ingest-log.md"
    if log.is_file():
        errors.extend(_validate_ingest_log(log))

    proposals = audit_dir / "proposals"
    if proposals.is_dir():
        for child in sorted(proposals.iterdir()):
            if child.is_dir():
                errors.extend(_validate_proposal_dir(child))
            else:
                errors.append(f"{child}: .audit/proposals/ may only contain <date>-<slug>/ directories")

    return errors


# ── .audit/approvals/ (0.7.0, FR-031) ─────────────────────────


def _kind(path: Path) -> str:
    """``symlink``, ``dir``, ``file`` or ``other``, by ``lstat``: the approval tree is never followed."""
    mode = os.lstat(path).st_mode
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISDIR(mode):
        return "dir"
    return "file" if stat.S_ISREG(mode) else "other"


def _manifest_wiki_id(wiki_dir: Path) -> str | None:
    """The ``wiki_id`` records are verified against; None when the manifest is absent, a symlink or unusable."""
    manifest = wiki_dir / MANIFEST_NAME
    if not manifest.is_file() or manifest.is_symlink():
        return None
    try:
        return parse_manifest(manifest.read_bytes(), str(manifest)).wiki_id
    except (OSError, ContractViolationError):
        return None


def _validate_approvals(approvals: Path) -> list[str]:
    """The approval tree: ``id/<page_id>/`` and ``path/<digest>/``, then ``<sha256>/<policy_sha256>/<decision>.json``.

    Every name is checked for its format, every record against its location
    (FR-024), no symlink is followed anywhere, and a temporary file left by an
    interrupted publication is reported for removal by hand.
    """
    if _kind(approvals) != "dir":
        return [f"{approvals}: approvals must be a directory (not a symlink)"]
    errors: list[str] = []
    wiki_id = _manifest_wiki_id(approvals.parent.parent)
    if wiki_id is None and any(approvals.iterdir()):
        errors.append(f"{approvals}: approval records need the wiki's manifest (its wiki_id) to be verified")
    for namespace in sorted(approvals.iterdir()):
        kind = _kind(namespace)
        if kind == "symlink":
            errors.append(f"{namespace}: symlink in the approval tree")
        elif kind != "dir" or namespace.name not in NAMESPACES:
            errors.append(f"{namespace}: unexpected entry under approvals/ (only id/ and path/ are permitted)")
        else:
            for key_dir in sorted(namespace.iterdir()):
                errors.extend(_validate_key_dir(key_dir, namespace.name, wiki_id))
    return errors


def _validate_key_dir(key_dir: Path, namespace: str, wiki_id: str | None) -> list[str]:
    kind = _kind(key_dir)
    if kind == "symlink":
        return [f"{key_dir}: symlink in the approval tree"]
    well_named = is_page_id(key_dir.name) if namespace == NAMESPACE_ID else is_sha256_hex(key_dir.name)
    if kind != "dir" or not well_named:
        expected = "a page_id (pg- and 32 lowercase hex)" if namespace == NAMESPACE_ID else "64 lowercase hex"
        return [f"{key_dir}: {namespace}/ entries must be directories named {expected}"]
    errors: list[str] = []
    for revision in sorted(key_dir.iterdir()):
        kind = _kind(revision)
        if kind == "symlink":
            errors.append(f"{revision}: symlink in the approval tree")
            continue
        if kind != "dir" or not is_sha256_hex(revision.name):
            errors.append(f"{revision}: revision entries must be directories named 64 lowercase hex")
            continue
        for policy in sorted(revision.iterdir()):
            kind = _kind(policy)
            if kind == "symlink":
                errors.append(f"{policy}: symlink in the approval tree")
                continue
            if kind != "dir" or not is_sha256_hex(policy.name):
                errors.append(f"{policy}: policy entries must be directories named 64 lowercase hex")
                continue
            for record in sorted(policy.iterdir()):
                errors.extend(_validate_record(record, namespace, key_dir.name, wiki_id))
    return errors


def _validate_record(record: Path, namespace: str, key_name: str, wiki_id: str | None) -> list[str]:
    kind = _kind(record)
    if kind == "symlink":
        return [f"{record}: symlink in the approval tree"]
    name = record.name
    if name.startswith(".") and name.endswith(RECORD_TMP_SUFFIX):
        return [f"{record}: stray temporary file from an interrupted publication; remove it by hand"]
    decision = name[: -len(RECORD_SUFFIX)] if name.endswith(RECORD_SUFFIX) else ""
    if kind != "file" or decision not in DECISIONS:
        return [f"{record}: approval records must be regular files named <decision>.json ({sorted(DECISIONS)})"]
    try:
        data = record.read_bytes()
    except OSError as exc:
        return [f"{record}: unreadable ({exc})"]
    page_key = key_name if namespace == NAMESPACE_ID else _path_key(data, key_name)
    if page_key is None:
        return [f"{record}: page_key is not a canonical path whose digest is its directory name"]
    if wiki_id is None:
        return []
    revision, policy = record.parent.parent.name, record.parent.name
    _obj, problem = record_problem(
        data, wiki_id=wiki_id, page_key=page_key, sha256=revision, policy_hash=policy, decision=decision
    )
    return [] if problem is None else [f"{record}: invalid approval record: {problem}"]


def _path_key(data: bytes, digest: str) -> str | None:
    """The canonical path a ``path/<digest>/`` record names, when its ``page_key`` digests to ``digest``."""
    try:
        key = json.loads(data.decode("utf-8")).get("page_key")
    except (UnicodeDecodeError, ValueError, AttributeError):
        return None
    if not isinstance(key, str):
        return None
    try:
        if canonical_path(key) != key or path_digest(key) != digest:
            return None
    except ValueError:
        return None
    return key
