# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wiki_studio.review — how a page is named for review, and what its approval records say (read side).

A page's **canonical path** is its wiki-relative path normalised with
``posixpath.normpath``, with forward slashes and no leading ``./`` or ``/``,
so ``./concepts/x.md`` and ``concepts/x.md`` are one page. A page's **key**
is its ``page_id`` when it carries a well-formed one, else its canonical path
(FR-016). Approval records, ``review_state`` and findings use the key.

An approval is one immutable file per decision (FR-023)::

    <wiki>/.audit/approvals/id/<page_id>/<sha256>/<policy_sha256>/<decision>.json
    <wiki>/.audit/approvals/path/<path-digest>/<sha256>/<policy_sha256>/<decision>.json

The path carries the whole decision tuple (page key, revision, policy,
decision). This module computes the policy hash and the path digest, reads
and verifies records without following a symlink, and derives a page's review
state from them. It never writes: ``promoter.py`` publishes records.
Frontmatter never makes a page approved; only a verified record does.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import posixpath
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Any

from .contract import POLICY_APPROVER_REQUIRED, read_manifest
from .errors import ContractViolationError, PathOutsideRootError, SourceMissingError
from .lint import INDEX_NAME, LOG_NAME, list_pages
from .paths import (
    ACTOR_SOURCE_NONE,
    ACTOR_SOURCES,
    AUDIT_DIR_NAME,
    CONTAIN_SYMLINK,
    ContainmentError,
    contain,
    is_absolute_path,
)
from .proposal import is_page_id, is_sha256_hex
from .schema import PAGE_ID_KEY, SUPERSEDED_BY_KEY
from .wiki_state import read_page_content

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from .paths import WikiPaths
    from .wiki_state import PageContent

# Frontmatter keys review reads (lifecycle labels; never approval).
STATUS_KEY = "status"
STATUS_DRAFT = "draft"

# The approval tree (FR-023).
APPROVALS_DIR_NAME = "approvals"
APPROVALS_REL = f"{AUDIT_DIR_NAME}/{APPROVALS_DIR_NAME}"
NAMESPACE_ID = "id"
NAMESPACE_PATH = "path"
NAMESPACES: tuple[str, ...] = (NAMESPACE_ID, NAMESPACE_PATH)
DECISION_APPROVED = "approved"
DECISIONS: frozenset[str] = frozenset({DECISION_APPROVED})
RECORD_SUFFIX = ".json"
# A record being published is written to ``.<decision>.json.<pid>.<hex>.tmp`` in its directory first.
RECORD_TMP_SUFFIX = ".tmp"

# The record format (FR-024).
APPROVAL_VERSION = 1
KEY_APPROVAL_VERSION = "approval_version"
KEY_WIKI_ID = "wiki_id"
KEY_PAGE_KEY = "page_key"
KEY_PATH = "path"
KEY_SHA256 = "sha256"
KEY_POLICY_SHA256 = "policy_sha256"
KEY_DECISION = "decision"
KEY_PROPOSAL = "proposal"
KEY_PROPOSER = "proposer"
KEY_APPROVER = "approver"
KEY_PROMOTER = "promoter"
KEY_TIMESTAMP = "timestamp"
RECORD_KEYS: tuple[str, ...] = (
    KEY_APPROVAL_VERSION,
    KEY_WIKI_ID,
    KEY_PAGE_KEY,
    KEY_PATH,
    KEY_SHA256,
    KEY_POLICY_SHA256,
    KEY_DECISION,
    KEY_PROPOSAL,
    KEY_PROPOSER,
    KEY_APPROVER,
    KEY_PROMOTER,
    KEY_TIMESTAMP,
)
PROPOSAL_KEYS: tuple[str, ...] = ("name", "submission_digest")
ACTOR_KEYS: frozenset[str] = frozenset({"name", "source"})
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z")

# Review states (FR-026) and the reasons that accompany them.
STATE_APPROVED = "approved"
STATE_POLICY_CHANGED = "policy-changed"
STATE_STALE = "stale"
STATE_UNAPPROVED = "unapproved"
STATE_SUPERSEDED = "superseded"
REASON_MANIFEST_MISSING = "manifest_missing"
REASON_DRAFT = "draft"
REASON_NO_RECORD = "no_record"
REASON_SUPERSEDED_BY = "superseded_by"
REASON_RECORD_MATCHES = "record_matches_live"
REASON_NO_RECORD_SATISFIES_POLICY = "no_record_satisfies_policy"
REASON_LIVE_BYTES_DIFFER = "live_bytes_differ"

_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


# ── Naming a page ─────────────────────────────────────────────


def canonical_path(path: str) -> str:
    """The canonical wiki-relative form of ``path``; ``ValueError`` when it names the wiki itself or leaves it."""
    text = PurePath(path).as_posix().lstrip("/")
    rel = posixpath.normpath(text) if text else "."
    if rel == "." or rel == ".." or rel.startswith("../"):
        raise ValueError(f"not a wiki-relative page path: {path!r}")
    return rel


def frontmatter_value(text: str, key: str) -> str | None:
    """The raw value of a column-0 ``key:`` in the page's frontmatter (one pair of double quotes removed), or None.

    Read as the structural linter reads frontmatter, so a value lint accepts
    is the value review uses.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    prefix = f"{key}:"
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        if line.startswith(prefix):
            value = line[len(prefix) :].strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1]
            return value
    return None


def frontmatter_page_id(text: str) -> str | None:
    """The raw ``page_id`` value of the page's frontmatter, or None."""
    return frontmatter_value(text, PAGE_ID_KEY)


def page_key(path: str, text: str) -> str:
    """The page's ``page_id`` when its frontmatter carries a well-formed one, else :func:`canonical_path`."""
    page_id = frontmatter_page_id(text)
    if page_id is not None and is_page_id(page_id):
        return page_id
    return canonical_path(path)


def is_draft(text: str) -> bool:
    """True when the page's live ``status`` is ``draft``."""
    return frontmatter_value(text, STATUS_KEY) == STATUS_DRAFT


def superseded_by(text: str) -> str | None:
    """The page's ``superseded_by`` value when it carries the key, else None."""
    return frontmatter_value(text, SUPERSEDED_BY_KEY)


def read_live_page(path: str, paths: WikiPaths) -> tuple[str, PageContent]:
    """Read one live page once through the wiki boundary: its canonical path and content.

    ``PathOutsideRootError`` (exit 7) for an absolute path, an escape or a
    symlink on the way; ``SourceMissingError`` (exit 5) when there is no
    such file; ``ContractViolationError`` (exit 4) when it is not UTF-8.
    """
    text = PurePath(path).as_posix()
    try:
        if is_absolute_path(text):
            raise ValueError(text)
        rel = canonical_path(text)
    except ValueError as exc:
        raise PathOutsideRootError(f"page path must be wiki-relative and stay inside the wiki: {path}") from exc
    try:
        contain(rel, paths.wiki_dir)
    except ContainmentError as exc:
        if exc.reason == CONTAIN_SYMLINK:
            raise PathOutsideRootError(
                f"page path passes through a symlink, which is outside the wiki boundary: {rel}"
            ) from exc
        raise PathOutsideRootError(f"page path escapes the wiki directory {paths.wiki_dir}: {rel}") from exc
    target = paths.wiki_dir / rel
    if not target.is_file():
        raise SourceMissingError(f"page not found: {paths.wiki_label}/{rel}")
    try:
        content = read_page_content(target)
    except OSError as exc:
        raise SourceMissingError(f"page not readable: {paths.wiki_label}/{rel}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ContractViolationError(f"page is not valid UTF-8: {paths.wiki_label}/{rel}: {exc}") from exc
    return rel, content


# ── The policy and the record location ────────────────────────


def policy_canonical_json(policy: Mapping[str, bool]) -> bytes:
    """The canonical JSON of the part of the policy that changes what an approval accepts (FR-020).

    Only ``approver_required``: sorted keys, ``,`` and ``:`` separators, no
    whitespace, UTF-8. ``approval_required`` and ``auto_approve_on_promote``
    never enter it, so turning a wiki governed or toggling auto-approval
    leaves every existing approval as it was.
    """
    obj = {POLICY_APPROVER_REQUIRED: bool(policy[POLICY_APPROVER_REQUIRED])}
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def policy_sha256(policy: Mapping[str, bool]) -> str:
    """Lowercase hex SHA-256 of :func:`policy_canonical_json`."""
    return hashlib.sha256(policy_canonical_json(policy)).hexdigest()


def path_digest(path: str) -> str:
    """Lowercase hex SHA-256 of the canonical wiki-relative path in UTF-8 (the ``path/`` directory name)."""
    return hashlib.sha256(canonical_path(path).encode("utf-8")).hexdigest()


def key_location(key: str) -> tuple[str, str]:
    """The namespace and directory name of a page key: ``("id", page_id)`` or ``("path", <path-digest>)``.

    A page path always ends in ``.md``, so it never reads as a ``page_id``.
    """
    if is_page_id(key):
        return NAMESPACE_ID, key
    return NAMESPACE_PATH, path_digest(key)


def record_rel(key: str, sha256: str, policy_hash: str, decision: str = DECISION_APPROVED) -> str:
    """The wiki-relative path of the record of one decision tuple."""
    namespace, name = key_location(key)
    return f"{APPROVALS_REL}/{namespace}/{name}/{sha256}/{policy_hash}/{decision}{RECORD_SUFFIX}"


def lookup_keys(rel: str, text: str) -> list[str]:
    """The keys a page's records are found under, in lookup order: its ``page_id`` (if any), then its path."""
    key = page_key(rel, text)
    path_key = canonical_path(rel)
    return [key, path_key] if key != path_key else [path_key]


# ── Records ───────────────────────────────────────────────────


@dataclass(frozen=True)
class ApprovalRecord:
    """One verified approval record: where it is, the tuple its path names, and its parsed content."""

    rel: str
    page_key: str
    sha256: str
    policy_sha256: str
    decision: str
    timestamp: str
    data: Mapping[str, Any]

    @property
    def approver_name(self) -> str | None:
        approver = self.data.get(KEY_APPROVER)
        return approver.get("name") if isinstance(approver, dict) else None


def is_actor(value: object) -> bool:
    """True for ``{"name": str | null, "source": flag | env | none}``, a name exactly when the source is not none."""
    if not isinstance(value, dict) or set(value) != ACTOR_KEYS:
        return False
    name, source = value["name"], value["source"]
    if source not in ACTOR_SOURCES:
        return False
    return name is None if source == ACTOR_SOURCE_NONE else isinstance(name, str)


def _is_proposal(value: object) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == set(PROPOSAL_KEYS)
        and isinstance(value["name"], str)
        and is_sha256_hex(value["submission_digest"])
    )


def record_problem(
    data: bytes, *, wiki_id: str | None, page_key: str, sha256: str, policy_hash: str, decision: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Verify one record's bytes against its location (FR-024); ``(record, None)`` or ``(None, problem)``.

    ``page_key`` is the key the record must name (the ``page_id`` for a
    record under ``id/``, the canonical path for one under ``path/``);
    ``sha256``, ``policy_hash`` and ``decision`` are its directory and file
    names. ``wiki_id`` None means the wiki has no manifest to compare with.
    """
    try:
        obj = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return None, f"not a UTF-8 JSON document ({exc})"
    if not isinstance(obj, dict):
        return None, "not a JSON object"
    missing = [key for key in RECORD_KEYS if key not in obj]
    if missing:
        return None, f"missing keys {missing}"
    version = obj[KEY_APPROVAL_VERSION]
    if isinstance(version, bool) or version != APPROVAL_VERSION:
        return None, f"approval_version {version!r} is not {APPROVAL_VERSION}"
    if wiki_id is None:
        return None, "the wiki has no manifest, so the record's wiki_id cannot be verified"
    if obj[KEY_WIKI_ID] != wiki_id:
        return None, f"wiki_id {obj[KEY_WIKI_ID]!r} is not this wiki's ({wiki_id})"
    if obj[KEY_PAGE_KEY] != page_key:
        return None, f"page_key {obj[KEY_PAGE_KEY]!r} is not the key it is filed under ({page_key})"
    for key, expected in ((KEY_SHA256, sha256), (KEY_POLICY_SHA256, policy_hash), (KEY_DECISION, decision)):
        if obj[key] != expected:
            return None, f"{key} {obj[key]!r} differs from its location ({expected})"
    if not isinstance(obj[KEY_PATH], str) or not obj[KEY_PATH]:
        return None, "path must be a non-empty string"
    if obj[KEY_PROPOSAL] is not None and not _is_proposal(obj[KEY_PROPOSAL]):
        return None, "proposal must be null or {name, submission_digest}"
    for key in (KEY_PROPOSER, KEY_APPROVER, KEY_PROMOTER):
        if obj[key] is not None and not is_actor(obj[key]):
            return None, f"{key} must be null or {{name, source}}"
    if not isinstance(obj[KEY_TIMESTAMP], str) or _TIMESTAMP_RE.fullmatch(obj[KEY_TIMESTAMP]) is None:
        return None, f"timestamp {obj[KEY_TIMESTAMP]!r} is not ISO 8601 UTC"
    return obj, None


def record_satisfies(record: ApprovalRecord, policy: Mapping[str, bool]) -> bool:
    """Whether a verified record satisfies the current policy (FR-026), judged by content, not by policy hash.

    Any record does when ``approver_required`` is false; when it is true the
    record must name its approver. Relaxing the policy therefore never
    reopens an approval made under the stricter rule.
    """
    return not policy[POLICY_APPROVER_REQUIRED] or record.approver_name is not None


def _kind(path: Path) -> str:
    """``missing``, ``symlink``, ``dir``, ``file`` or ``other``, judged by ``lstat`` (never following a link)."""
    try:
        mode = os.lstat(path).st_mode
    except (FileNotFoundError, NotADirectoryError):
        return "missing"
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISDIR(mode):
        return "dir"
    return "file" if stat.S_ISREG(mode) else "other"


def _read_nofollow(path: Path) -> bytes:
    """Read a regular file with ``O_NOFOLLOW``; ``OSError`` for a symlink or a non-regular entry."""
    fd = os.open(path, os.O_RDONLY | _O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError(errno.EINVAL, "not a regular file", str(path))
        with os.fdopen(fd, "rb") as handle:
            fd = -1
            return handle.read()
    finally:
        if fd >= 0:
            os.close(fd)


@dataclass
class RecordScan:
    """What one lookup found: the verified records, the records skipped (with why), and symlinks met on the way."""

    records: list[ApprovalRecord] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    symlinks: list[str] = field(default_factory=list)

    @property
    def warnings(self) -> list[str]:
        return [*(f"{rel}: symlink in the approval tree, skipped" for rel in self.symlinks), *self.skipped]


def scan_key(paths: WikiPaths, wiki_id: str | None, key: str, *, sha256: str | None = None) -> RecordScan:
    """Every record filed under one page key (only ``sha256``'s revision when given), verified, never following a link.

    A record that fails verification is skipped and reported, so an
    enumeration never attributes another page's history to this one; a
    symlink anywhere on the way is skipped and reported in ``symlinks``.
    """
    scan = RecordScan()
    namespace, name = key_location(key)
    base_rel = f"{APPROVALS_REL}/{namespace}/{name}"
    try:
        contain(base_rel, paths.wiki_dir)
    except ContainmentError as exc:
        if exc.reason == CONTAIN_SYMLINK:
            scan.symlinks.append(base_rel)
            return scan
        raise ContractViolationError(f"{base_rel} is outside the wiki boundary ({exc})") from exc
    base = paths.wiki_dir / base_rel
    if _kind(base) != "dir":
        return scan
    revisions = [sha256] if sha256 is not None else sorted(os.listdir(base))
    for revision in revisions:
        _scan_revision(scan, paths.wiki_dir, wiki_id, key, f"{base_rel}/{revision}", revision)
    return scan


def _scan_revision(scan: RecordScan, wiki_dir: Path, wiki_id: str | None, key: str, rev_rel: str, rev: str) -> None:
    kind = _kind(wiki_dir / rev_rel)
    if kind == "symlink":
        scan.symlinks.append(rev_rel)
        return
    if kind == "missing":
        return
    if kind != "dir" or not is_sha256_hex(rev):
        scan.skipped.append(f"{rev_rel}: not a revision directory (64 lowercase hex), skipped")
        return
    for policy_hash in sorted(os.listdir(wiki_dir / rev_rel)):
        policy_rel = f"{rev_rel}/{policy_hash}"
        kind = _kind(wiki_dir / policy_rel)
        if kind == "symlink":
            scan.symlinks.append(policy_rel)
            continue
        if kind != "dir" or not is_sha256_hex(policy_hash):
            scan.skipped.append(f"{policy_rel}: not a policy directory (64 lowercase hex), skipped")
            continue
        for file_name in sorted(os.listdir(wiki_dir / policy_rel)):
            _scan_record(scan, wiki_dir, wiki_id, key, rev, policy_hash, f"{policy_rel}/{file_name}", file_name)


def _scan_record(
    scan: RecordScan,
    wiki_dir: Path,
    wiki_id: str | None,
    key: str,
    rev: str,
    policy_hash: str,
    rel: str,
    file_name: str,
) -> None:
    kind = _kind(wiki_dir / rel)
    if kind == "symlink":
        scan.symlinks.append(rel)
        return
    decision = file_name[: -len(RECORD_SUFFIX)] if file_name.endswith(RECORD_SUFFIX) else ""
    if kind != "file" or decision not in DECISIONS:
        scan.skipped.append(f"{rel}: not an approval record (<decision>.json, a regular file), skipped")
        return
    try:
        data = _read_nofollow(wiki_dir / rel)
    except OSError as exc:
        scan.skipped.append(f"{rel}: approval record unreadable ({exc}), skipped")
        return
    obj, problem = record_problem(
        data, wiki_id=wiki_id, page_key=key, sha256=rev, policy_hash=policy_hash, decision=decision
    )
    if obj is None:
        scan.skipped.append(f"{rel}: approval record skipped: {problem}")
        return
    scan.records.append(
        ApprovalRecord(
            rel=rel,
            page_key=key,
            sha256=rev,
            policy_sha256=policy_hash,
            decision=decision,
            timestamp=obj[KEY_TIMESTAMP],
            data=obj,
        )
    )


def scan_page(paths: WikiPaths, wiki_id: str | None, rel: str, text: str, *, sha256: str | None = None) -> RecordScan:
    """The records of one page: under ``id/<page_id>/`` first when it has one, then under ``path/<digest>/``."""
    total = RecordScan()
    for key in lookup_keys(rel, text):
        scan = scan_key(paths, wiki_id, key, sha256=sha256)
        total.records.extend(scan.records)
        total.skipped.extend(scan.skipped)
        total.symlinks.extend(scan.symlinks)
    return total


def newest(records: Iterable[ApprovalRecord]) -> ApprovalRecord | None:
    """The record with the latest ``timestamp``; on a tie the one found first (``id/`` before ``path/``)."""
    best: ApprovalRecord | None = None
    for record in records:
        if best is None or record.timestamp > best.timestamp:
            best = record
    return best


# ── Review state ──────────────────────────────────────────────


@dataclass(frozen=True)
class ReviewState:
    """One page's review state (FR-026): advisory and point-in-time, read without the lock.

    ``state`` is ``superseded``, ``approved``, ``policy-changed``, ``stale``
    or ``unapproved``; ``reason`` a stable tag (``manifest_missing``,
    ``draft``, ``no_record``, ``superseded_by``, ``record_matches_live``,
    ``no_record_satisfies_policy``, ``live_bytes_differ``).
    ``approved_sha256`` and ``record_path`` (wiki-relative) name the newest
    record the state rests on, or None; ``warnings`` the records skipped.
    """

    path: str
    page_key: str
    state: str
    reason: str
    live_sha256: str
    approved_sha256: str | None = None
    record_path: str | None = None
    warnings: tuple[str, ...] = ()


def default_review_pages(paths: WikiPaths) -> list[str]:
    """Every page the structural linter lists except the root ``index.md`` and ``log.md``."""
    rels = [page.relative_to(paths.wiki_dir).as_posix() for page in list_pages(paths.wiki_dir)]
    return [rel for rel in rels if rel not in (INDEX_NAME, LOG_NAME)]


def _state_from_records(rel: str, key: str, live_sha: str, scan: RecordScan, policy: Mapping[str, bool]) -> ReviewState:
    warnings = tuple(scan.warnings)
    live = [r for r in scan.records if r.sha256 == live_sha]
    satisfying = newest(r for r in live if record_satisfies(r, policy))
    if satisfying is not None:
        return ReviewState(
            rel, key, STATE_APPROVED, REASON_RECORD_MATCHES, live_sha, satisfying.sha256, satisfying.rel, warnings
        )
    unsatisfying = newest(live)
    if unsatisfying is not None:
        return ReviewState(
            rel,
            key,
            STATE_POLICY_CHANGED,
            REASON_NO_RECORD_SATISFIES_POLICY,
            live_sha,
            unsatisfying.sha256,
            unsatisfying.rel,
            warnings,
        )
    earlier = newest(scan.records)
    if earlier is not None:
        return ReviewState(
            rel, key, STATE_STALE, REASON_LIVE_BYTES_DIFFER, live_sha, earlier.sha256, earlier.rel, warnings
        )
    return ReviewState(rel, key, STATE_UNAPPROVED, REASON_NO_RECORD, live_sha, None, None, warnings)


def review_states(paths: WikiPaths, pages: list[str] | None = None) -> list[ReviewState]:
    """The review state of each page, decided in the order of FR-026; reads only, takes no lock.

    Legacy wiki: ``unapproved`` / ``manifest_missing``. Then ``superseded``
    for a page carrying ``superseded_by``, ``unapproved`` / ``draft`` for a
    live ``status: draft``, and otherwise what the verified records for the
    page say: ``approved`` when one for the live bytes satisfies the current
    policy, ``policy-changed`` when records for the live bytes exist but none
    satisfies it, ``stale`` when only records for other bytes exist, else
    ``unapproved``. ``status: stable`` alone is ``unapproved``.
    """
    manifest = read_manifest(paths)
    wanted = default_review_pages(paths) if pages is None else list(pages)
    states: list[ReviewState] = []
    seen: set[str] = set()
    for page in wanted:
        rel, content = read_live_page(page, paths)
        if rel in seen:
            continue
        seen.add(rel)
        key = page_key(rel, content.text)
        if manifest is None:
            states.append(ReviewState(rel, key, STATE_UNAPPROVED, REASON_MANIFEST_MISSING, content.sha256))
            continue
        if superseded_by(content.text) is not None:
            states.append(ReviewState(rel, key, STATE_SUPERSEDED, REASON_SUPERSEDED_BY, content.sha256))
            continue
        if is_draft(content.text):
            states.append(ReviewState(rel, key, STATE_UNAPPROVED, REASON_DRAFT, content.sha256))
            continue
        scan = scan_page(paths, manifest.wiki_id, rel, content.text)
        states.append(_state_from_records(rel, key, content.sha256, scan, manifest.policy))
    return states
