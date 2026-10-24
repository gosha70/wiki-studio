# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# wiki-studio.promoter — Phase-2 patch-set promotion.
#
# THE ONLY MODULE IN THE PIPELINE THAT WRITES TO THE WIKI DIRECTORY.
#
# What a promotion guarantees: it is validated (per-edit semantics and the
# structural linter over a staged copy of the wiki), serialised against other
# wiki-studio writers on the same machine by the wiki lock (``wikilock``),
# and rolled back on an exception during the commit. It is not crash-safe
# across files: a process killed in the middle of the commit can leave some
# files written and others not, and uncoordinated readers may observe
# intermediate state. The receipt protocol below recovers from a failure
# between the protocol's steps, never from a crash inside the commit.
#
# The staged tree is a full copy because the linter needs a whole tree to
# judge reachability, but the commit writes back ONLY the paths the
# patch-set names plus this proposal's own archive under ``.audit/proposals/``
# (FR-001). Writing back "whatever differs" is what let one promote revert
# another's pages.
#
# Protocol, under the lock (FR-003, FR-004):
#   capture   every regular file of the proposal directory is read once into
#             memory (the submission manifest); parsing, the payload digest,
#             staging and the archive all use that capture
#   stage     copy of the wiki + the edits + the audit archive, then validate
#   check     revision preconditions against the live wiki (FR-008, FR-009):
#             a create needs absence, an update with ``base_sha256`` needs the
#             live page to still have that hash, an update without one is
#             refused unless compatibility mode is on (then recorded as
#             unguarded); appends landed on the staged copy of the current
#             content. A dry run stops here, releases the lock and validates
#             the staged snapshot outside it (FR-011).
#   step 1    receipt.json ``committing`` (tracked writes with pre/post sha256,
#             wiki identity by device and inode), fsynced; a failure here
#             commits nothing (exit 6)
#   step 2    commit the tracked writes (rollback on exception)
#   step 3    receipt.json ``committed``, fsynced
#   step 4    archive the capture plus the committed receipt into
#             ``<proposals>/.applied/.<name>.<pid>.tmp/``, fsync, publish by
#             rename to ``.applied/<name>/`` (``-2``, ``-3`` on a clash), then
#             remove the original only while it still matches the archive
#             (``receipt.json`` deleted last)
# A later promote of the same directory resolves the receipt instead of
# re-applying anything; see ``_resolve_receipt``.

from __future__ import annotations

import contextlib
import datetime
import difflib
import hashlib
import json
import os
import posixpath
import shutil
import stat
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import __version__
from .audit import HASH_RECIPE_PAYLOAD_DIGEST, PLAN_FILE_NAME, PREVIEW_DIR_NAME, payload_digest_from_files
from .errors import (
    REASON_PAYLOAD_CHANGED,
    REASON_UNCERTAIN_OUTCOME,
    REASON_WIKI_IDENTITY_UNAVAILABLE,
    REASON_WIKI_MISMATCH,
    ContractViolationError,
    OutputWriteError,
    PromoteApplyError,
    PromoteValidationError,
)
from .lint import lint_wiki
from .paths import APPLIED_DIR_NAME, AUDIT_DIR_NAME, ContainmentError, contain
from .proposal import (
    PageEdit,
    WikiPatchSet,
    is_sha256_hex,
    validate_page_edit_semantics,
    validate_patch_set,
)
from .wikilock import WikiLock

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from .paths import WikiPaths

# Fixed names inside a proposal directory and its archive.
RECEIPT_FILE_NAME = "receipt.json"
SNAPSHOT_DIR_NAME = ".ingest-snapshot"
_RECEIPT_TMP_NAME = ".receipt.json.tmp"
_ARCHIVE_TMP_SUFFIX = ".tmp"
# ``.audit/proposals`` inside the wiki: the archive the commit writes for this proposal.
_AUDIT_PROPOSALS_REL = f"{AUDIT_DIR_NAME}/proposals"

# receipt.json contract.
RECEIPT_VERSION = 1
STATE_COMMITTING = "committing"
STATE_COMMITTED = "committed"
PACKAGE_NAME = "wiki-studio"
PROMOTE_ENTRY_POINT_API = "api"
PROMOTE_ENTRY_POINT_CLI = "cli"

# Staging reads relative to the wiki-directory descriptor where the platform can
# (POSIX), so identity and staged reads refer to one directory object. Elsewhere
# staging reads by path: the weaker binding, unsupported in this release.
_FD_STAGING = os.scandir in os.supports_fd and os.open in os.supports_dir_fd
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


@dataclass(frozen=True)
class PromoteResult:
    """Outcome of a successful promote.

    Attributes
    ----------
    applied_paths : list[str]
        Wiki-relative paths actually written (created/updated/appended-to,
        plus this proposal's ``.audit/proposals/`` archive). Empty for a
        dry run of an empty patch-set, an already-archived proposal and a
        proposal whose every edit was a no-op.
    proposals_dir : Path
        Original proposals dir (now moved to ``.applied/`` unless
        ``dry_run`` was set or the archive step did not complete).
    archived_dir : Path | None
        Where the proposal was archived after commit. None on a dry run,
        and when the archive step failed after the commit (the receipt in
        ``proposals_dir`` records the outcome; promoting the directory
        again finishes the archive and applies nothing twice).
    dry_run : bool
        True if the staged tree was built and validated but never
        committed to the live wiki.
    unguarded_paths : list[str]
        Paths of ``update`` edits applied without a ``base_sha256`` under
        ``allow_unguarded_updates`` (compatibility mode with incomplete
        conflict protection); also recorded in the receipt. Empty
        otherwise. Added in 0.6.0 with a default.
    warnings : list[str]
        Human-readable findings that did not stop the promotion, one per
        unguarded path. Added in 0.6.0 with a default.
    """

    applied_paths: list[str]
    proposals_dir: Path
    archived_dir: Path | None
    dry_run: bool
    unguarded_paths: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_hex_digest(value: object) -> bool:
    """True for a lowercase 64-character hex string: the only form ``_sha256`` produces."""
    return is_sha256_hex(value)


def _unguarded_warnings(unguarded: list[str]) -> list[str]:
    return [
        f"{rel}: replaced without a base revision (compatibility mode with incomplete conflict protection)"
        for rel in unguarded
    ]


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── The submission: captured once, never reread ───────────────


@dataclass(frozen=True)
class _Capture:
    """The submission manifest: every regular file of the proposal directory, read once.

    ``files`` maps proposal-relative POSIX paths to bytes. The identity
    (``digest``) covers ``plan.json`` and everything under ``preview/``;
    ``.ingest-snapshot/`` and any other file are provenance, archived with
    the proposal but outside the identity.
    """

    files: dict[str, bytes]

    @property
    def digest(self) -> str:
        return payload_digest_from_files(self.files)

    @property
    def shas(self) -> dict[str, str]:
        return {rel: _sha256(data) for rel, data in self.files.items()}

    @property
    def manifest(self) -> list[dict[str, str]]:
        return [{"path": rel, "sha256": sha} for rel, sha in sorted(self.shas.items())]


def _proposal_file(rel: str, proposals_dir: Path) -> Path:
    """The proposal boundary (FR-012): ``rel`` must stay inside the proposal directory and reach no symlink.

    Checked before any proposal input is read (``plan.json``, each preview,
    every file an enumeration meets under ``preview/`` and
    ``.ingest-snapshot/``, ``receipt.json``). ``PromoteValidationError``
    names the offending path.
    """
    try:
        return contain(rel, proposals_dir)
    except ContainmentError as exc:
        raise PromoteValidationError(f"{rel} in {proposals_dir} is outside the proposal boundary ({exc})") from exc


def _capture_submission(proposals_dir: Path, *, skip: frozenset[str] = frozenset()) -> _Capture:
    """Read every regular file under ``proposals_dir`` once; refuse symlinks and other non-regular entries.

    The enumeration never follows a symlink: a symlinked directory or file
    anywhere under the proposal, referenced by a pointer or not, is refused
    before any byte of it is read, and every file passes the proposal
    boundary (:func:`_proposal_file`) before its read.
    """
    files: dict[str, bytes] = {}
    for dirpath, dirnames, filenames in os.walk(proposals_dir, followlinks=False):
        base = Path(dirpath)
        for name in sorted(dirnames):
            if (base / name).is_symlink():
                rel = (base / name).relative_to(proposals_dir).as_posix()
                raise PromoteValidationError(f"{rel} in {proposals_dir} is a symlink; refusing to read through it")
        for name in sorted(filenames):
            path = base / name
            rel = path.relative_to(proposals_dir).as_posix()
            if rel in skip:
                continue
            if path.is_symlink():
                raise PromoteValidationError(f"{rel} in {proposals_dir} is a symlink; refusing to read through it")
            if not path.is_file():
                raise PromoteValidationError(f"{rel} in {proposals_dir} is not a regular file; refusing to read it")
            try:
                files[rel] = _proposal_file(rel, proposals_dir).read_bytes()
            except OSError as exc:
                raise PromoteApplyError(f"could not read {rel} in {proposals_dir}: {exc}") from exc
    return _Capture(files)


def _preview_pointer(pointer: str, proposals_dir: Path) -> str:
    """Normalise a ``preview`` pointer; it must name a file under ``preview/`` of the proposal (exit 4)."""
    normalised = posixpath.normpath(pointer)
    parts = normalised.split("/")
    if posixpath.isabs(pointer) or ".." in parts or parts[0] != PREVIEW_DIR_NAME or len(parts) < 2:
        raise ContractViolationError(
            f"plan.json edit 'preview' pointer {pointer!r} does not point to a regular file under "
            f"{PREVIEW_DIR_NAME}/ of {proposals_dir}"
        )
    return normalised


def _parse_patch(capture: _Capture, proposals_dir: Path) -> tuple[WikiPatchSet, str]:
    """Reconstruct the patch-set from the captured ``plan.json`` and previews; also the plan's sha256."""
    plan_bytes = capture.files.get(PLAN_FILE_NAME)
    if plan_bytes is None:
        raise PromoteValidationError(f"plan.json not found in {proposals_dir}; not a valid proposals dir.")
    plan_path = proposals_dir / PLAN_FILE_NAME
    try:
        plan = json.loads(plan_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PromoteValidationError(f"plan.json at {plan_path} is not valid JSON: {exc}") from exc
    if not isinstance(plan, dict):
        raise PromoteValidationError(f"plan.json at {plan_path} must be a JSON object")

    edits: list[PageEdit] = []
    for raw in plan.get("edits", []):
        if not isinstance(raw, dict) or "path" not in raw or "action" not in raw:
            raise PromoteValidationError(f"plan.json edit must be an object with 'path' and 'action': {raw!r}")
        # plan.json does not embed new_content: it lives in preview/<path>, read
        # from the capture, never from the directory again.
        preview_rel = raw.get("preview")
        if not preview_rel:
            raise PromoteValidationError(f"plan.json edit missing 'preview' pointer: {raw!r}")
        pointer = _preview_pointer(str(preview_rel), proposals_dir)
        data = capture.files.get(pointer)
        if data is None:
            if (proposals_dir / pointer).exists():
                raise ContractViolationError(
                    f"plan.json edit 'preview' pointer {preview_rel!r} is not a regular file under "
                    f"{PREVIEW_DIR_NAME}/ of {proposals_dir}"
                )
            raise PromoteValidationError(f"preview file referenced by plan.json missing: {proposals_dir / pointer}")
        try:
            new_content = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PromoteValidationError(f"preview file {pointer} in {proposals_dir} is not valid UTF-8") from exc
        # The optional base revision (FR-005) is read back as written; its shape
        # is judged by the set-level validator, never filled in here.
        base_sha256 = raw.get("base_sha256")
        if base_sha256 is not None and not isinstance(base_sha256, str):
            raise PromoteValidationError(f"plan.json edit 'base_sha256' must be a string when present: {raw!r}")
        edits.append(
            PageEdit(
                path=str(raw["path"]),
                action=raw["action"],
                new_content=new_content,
                rationale=str(raw.get("rationale", "")),
                base_sha256=base_sha256,
            )
        )
    patch = WikiPatchSet(
        edits=edits,
        source_path=str(plan.get("source_path", "")),
        backend=str(plan.get("backend", "")),
        rationale=str(plan.get("rationale", "")),
    )
    return patch, _sha256(plan_bytes)


# ── The wiki: identity and staging ────────────────────────────


@dataclass
class _WikiHandle:
    """The wiki directory opened for this promotion: its identity and, on POSIX, a descriptor to read from."""

    fd: int | None
    st_dev: int
    st_ino: int
    resolved: str

    def close(self) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def _open_wiki(wiki_dir: Path) -> _WikiHandle:
    """Open the wiki directory and take its identity (``st_dev``, ``st_ino``) from the open descriptor.

    Where a directory cannot be opened as a descriptor (Windows), the identity
    comes from ``os.stat`` and staging reads by path; zero device or inode
    values are recorded as given and count as unavailable in recovery.
    """
    if not wiki_dir.is_dir():
        raise PromoteApplyError(f"wiki source not found at {wiki_dir}; cannot stage.")
    fd: int | None = None
    try:
        fd = os.open(wiki_dir, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        st = os.fstat(fd)
    except OSError:
        if fd is not None:
            os.close(fd)
        fd = None
        st = os.stat(wiki_dir)
    return _WikiHandle(fd=fd, st_dev=int(st.st_dev), st_ino=int(st.st_ino), resolved=str(wiki_dir.resolve()))


def _symlink_in_wiki(rel: str) -> PromoteValidationError:
    return PromoteValidationError(
        f"{rel}: symlink inside the wiki; promote refuses to stage or write through it "
        "(pages and their directories must be regular files)"
    )


def _refuse_entry(entry: os.DirEntry[str], rel: str) -> None:
    """Refuse a staging entry that is a symlink or neither a file nor a directory (FR-012)."""
    if entry.is_symlink():
        raise _symlink_in_wiki(rel)
    if not entry.is_dir(follow_symlinks=False) and not entry.is_file(follow_symlinks=False):
        raise PromoteValidationError(f"{rel}: not a regular file or directory inside the wiki; refusing to stage it")


def _copy_tree_from_fd(dir_fd: int, dest: Path, rel: str = "") -> None:
    """Copy the directory behind ``dir_fd`` into ``dest``, opening every entry relative to the descriptor.

    No symlink is followed: one anywhere in the wiki stops the staging with
    ``PromoteValidationError`` naming it; ``O_NOFOLLOW`` guards each open.
    """
    dest.mkdir(parents=True, exist_ok=True)
    with os.scandir(dir_fd) as it:
        entries = sorted(it, key=lambda entry: entry.name)
    for entry in entries:
        entry_rel = f"{rel}{entry.name}"
        _refuse_entry(entry, entry_rel)
        if entry.is_dir(follow_symlinks=False):
            child = os.open(entry.name, os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW, dir_fd=dir_fd)
            try:
                _copy_tree_from_fd(child, dest / entry.name, f"{entry_rel}/")
            finally:
                os.close(child)
        else:
            fd = os.open(entry.name, os.O_RDONLY | _O_NOFOLLOW, dir_fd=dir_fd)
            with os.fdopen(fd, "rb") as handle:
                data = handle.read()
            (dest / entry.name).write_bytes(data)


def _copy_tree_by_path(src: Path, dest: Path, rel: str = "") -> None:
    """The path-based staging copy (no ``dir_fd`` support): same walk, same symlink refusal."""
    dest.mkdir(parents=True, exist_ok=True)
    with os.scandir(src) as it:
        entries = sorted(it, key=lambda entry: entry.name)
    for entry in entries:
        entry_rel = f"{rel}{entry.name}"
        _refuse_entry(entry, entry_rel)
        if entry.is_dir(follow_symlinks=False):
            _copy_tree_by_path(src / entry.name, dest / entry.name, f"{entry_rel}/")
        else:
            (dest / entry.name).write_bytes((src / entry.name).read_bytes())


def _stage_wiki(handle: _WikiHandle, wiki_dir: Path, dest: Path) -> None:
    """Copy the current wiki tree to ``dest`` (relative to the open descriptor where supported).

    Staging refuses any symlink inside the wiki, file or directory, with
    ``PromoteValidationError`` naming it (FR-012).
    """
    if dest.exists():
        shutil.rmtree(dest)
    if _FD_STAGING and handle.fd is not None:
        _copy_tree_from_fd(handle.fd, dest)
        return
    # A wiki is small (tens of pages); a full copy is the simplest staging primitive.
    _copy_tree_by_path(wiki_dir, dest)


def _wiki_write_target(rel: str, wiki_dir: Path) -> Path:
    """The wiki boundary for a write (FR-012): ``rel`` must stay inside ``wiki_dir`` and reach no symlink.

    Used for every staged write and, under the lock, for every live path the
    commit will write. ``PromoteValidationError`` names the path.
    """
    try:
        contain(rel, wiki_dir)
    except ContainmentError as exc:
        raise PromoteValidationError(f"{rel}: path escapes the wiki directory ({exc})") from exc
    return wiki_dir / rel


def _recheck_write_targets(planned: list[_PlannedWrite], wiki_dir: Path) -> None:
    """Immediately before the commit, under the lock: ``os.lstat`` every component of every planned write.

    A symlink that appeared since staging (the page itself or a directory on
    the way) is refused with ``PromoteValidationError``; nothing has been
    written, and no receipt exists yet.
    """
    for plan in planned:
        probe = wiki_dir
        for part in Path(plan.rel).parts:
            probe = probe / part
            try:
                st = os.lstat(probe)
            except (FileNotFoundError, NotADirectoryError):
                break  # the commit creates the rest
            if stat.S_ISLNK(st.st_mode):
                raise _symlink_in_wiki(probe.relative_to(wiki_dir).as_posix())


def _apply_edit(stage_dir: Path, edit: PageEdit) -> None:
    """Apply one edit to the staged tree.

    - create        : write new file (parent dirs created)
    - update        : overwrite existing file
    - append-log    : append a line to log.md (or <subdir>/log.md)
    - append-index  : append a line to index.md (or <subdir>/index.md)

    Raises PromoteApplyError if the edit is unapplicable (e.g.
    update to a path that doesn't exist in the staged tree). The
    per-edit validator catches most of these earlier; this is a
    defense-in-depth check at apply time.
    """
    target = _wiki_write_target(edit.path, stage_dir)
    if edit.action == "create":
        if target.exists():
            raise PromoteApplyError(
                f"create edit to {edit.path}: already exists in staged tree (caught at apply time)."
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(edit.new_content, encoding="utf-8")
    elif edit.action == "update":
        if not target.exists():
            raise PromoteApplyError(
                f"update edit to {edit.path}: does not exist in staged tree (caught at apply time)."
            )
        target.write_text(edit.new_content, encoding="utf-8")
    elif edit.action in ("append-log", "append-index"):
        if not target.exists():
            raise PromoteApplyError(f"{edit.action} edit to {edit.path}: {target.name} does not exist in staged tree.")
        existing = target.read_text(encoding="utf-8")
        suffix = edit.new_content if edit.new_content.endswith("\n") else edit.new_content + "\n"
        prefix = existing if existing.endswith("\n") else existing + "\n"
        target.write_text(prefix + suffix, encoding="utf-8")
    else:
        raise PromoteApplyError(f"unknown action {edit.action!r} in edit for {edit.path}")


def _validate_staged_tree(
    stage_dir: Path,
    paths: WikiPaths,
    patch: WikiPatchSet,
) -> None:
    """Re-run per-edit semantic + structural lint against the staged tree.

    The staged tree is the post-apply view of the wiki, so
    create/update edits that depend on each other (e.g. an append-log
    that targets a log.md created earlier in the same patch-set) are
    judged against the right state.

    Raises PromoteValidationError on any failure; the wiki tree is
    not touched.
    """
    # Per-edit validation against the staged tree, so the update-exists and
    # create-clobber checks see post-apply state.
    staged = paths.with_wiki_dir(stage_dir)
    per_edit_errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="wiki-no-wiki-") as empty:
        # For ``create`` edits the file exists in the staged tree by design
        # (post-apply), so the create-clobber check would fire. Those edits
        # re-run the remaining checks (slug==stem, page_type promotable, dir
        # placement, sources non-empty) against one empty wiki so existence
        # checks skip.
        no_wiki = paths.with_wiki_dir(Path(empty))
        for edit in patch.edits:
            per_edit_errors.extend(validate_page_edit_semantics(edit, no_wiki if edit.action == "create" else staged))
    if per_edit_errors:
        raise PromoteValidationError("Staged-tree per-edit validation failed:\n  - " + "\n  - ".join(per_edit_errors))

    set_errors = validate_patch_set(patch)
    if set_errors:
        raise PromoteValidationError("Staged-tree set-level validation failed:\n  - " + "\n  - ".join(set_errors))

    # Structural lint of the staged tree (post-apply state).
    violations = _lint_staged_tree(stage_dir, paths)
    if violations:
        raise PromoteValidationError(
            "Structural linter rejected staged tree:\n" + "\n".join(f"  ✗ {v}" for v in violations)
        )


def _lint_staged_tree(stage_dir: Path, paths: WikiPaths) -> list[str]:
    """Run the structural linter over the staged wiki.

    Pages may link outside the wiki (``../../docs/...``). Those targets live
    next to the real wiki, not next to the staged copy, so escape links are
    resolved at ``paths.wiki_dir`` while every intra-wiki link is judged
    against the staged (post-apply) tree.
    """
    return lint_wiki(stage_dir, live_wiki_dir=paths.wiki_dir, root=paths.root, source_roots=paths.source_roots)


def _validate_before_staging(patch: WikiPatchSet, paths: WikiPaths) -> None:
    """Reject a bad patch-set before a single byte is staged.

    Set-level checks (paths must be wiki-relative, append targets, duplicate
    creates) and the per-edit checks against the live wiki (create must not
    clobber, update must exist, frontmatter consistency) all surface as
    PromoteValidationError (exit 9) here. The staged-tree pass later re-checks
    the post-apply state.
    """
    set_errors = validate_patch_set(patch)
    if set_errors:
        raise PromoteValidationError("Patch-set validation failed:\n  - " + "\n  - ".join(set_errors))
    per_edit_errors: list[str] = []
    for edit in patch.edits:
        per_edit_errors.extend(validate_page_edit_semantics(edit, paths))
    if per_edit_errors:
        raise PromoteValidationError("Per-edit validation failed:\n  - " + "\n  - ".join(per_edit_errors))


def _check_preconditions(patch: WikiPatchSet, paths: WikiPaths, *, allow_unguarded_updates: bool) -> list[str]:
    """Revision preconditions against the live wiki, under the lock, after staging (FR-008, FR-009).

    - ``create`` requires the live target to be absent.
    - ``update`` with ``base_sha256`` requires the live page's sha256 to equal it.
    - ``update`` without one is refused unless ``allow_unguarded_updates``;
      then it is applied and its path returned (recorded as unguarded).
    - ``append-index`` / ``append-log`` need no comparison: the staged copy
      was taken from the live file under this same lock, so the appended
      line lands on the current content.

    Every mismatch is collected and raised as one PromoteValidationError
    (exit 9) naming each page; nothing has been written at this point.
    Returns the unguarded update paths, in edit order, without duplicates.
    """
    problems: list[str] = []
    unguarded: list[str] = []
    for edit in patch.edits:
        live = paths.wiki_dir / edit.path
        if edit.action == "create":
            if os.path.lexists(live):
                problems.append(f"{edit.path}: create requires absence, but a live page now exists at that path")
        elif edit.action == "update":
            if edit.base_sha256 is None:
                if not allow_unguarded_updates:
                    problems.append(
                        f"{edit.path}: update carries no base_sha256, so a stale draft cannot be detected. Either "
                        f"regenerate the proposal from a fresh `wiki-studio read {edit.path}` and record its sha256 "
                        "as the edit's base_sha256, or pass --allow-unguarded-updates / allow_unguarded_updates=True "
                        "(compatibility mode with incomplete conflict protection; the path is recorded as unguarded)"
                    )
                elif edit.path not in unguarded:
                    unguarded.append(edit.path)
                continue
            try:
                live_sha = _sha256(live.read_bytes()) if live.is_file() else None
            except OSError as exc:
                raise PromoteApplyError(f"could not read the live page for {edit.path}: {exc}") from exc
            if live_sha != edit.base_sha256:
                problems.append(
                    f"{edit.path}: the live page is not the revision this update was drafted from "
                    f"(base_sha256 {edit.base_sha256}, live {live_sha or 'absent'}); read it again and redraft"
                )
    if problems:
        raise PromoteValidationError(
            "Revision preconditions failed; nothing was written:\n  - " + "\n  - ".join(problems)
        )
    return unguarded


def _stage_audit_archive(
    stage_dir: Path,
    proposal_name: str,
    capture: _Capture,
    patch: WikiPatchSet,
) -> str:
    """Stage the accepted-proposal archive into ``stage_dir/.audit/proposals/<name>/``; return its wiki-relative path.

    Written AFTER the _apply_edit loop and BEFORE _validate_staged_tree so
    the validator sees the final tree and the commit writes it with the
    patch-set's own paths.

    Contents:
      plan.json  — the captured plan.json, byte for byte
      proposal.md — human-readable render of the patch-set
      curator-delta.md — present only when the curator hand-edited
                          preview/ between ingest and promote (diff of
                          .ingest-snapshot/ vs the captured preview/)

    Collision handling: if stage_dir/.audit/proposals/<name>/ already
    exists in the live wiki (mirrored into stage_dir by _stage_wiki), a
    deterministic numeric suffix is appended: <name>-2, <name>-3, ...

    A proposal dir lacking .ingest-snapshot/ means no snapshot was taken
    (pre-Phase-2 proposal or --dry-run); curator-delta.md is omitted
    silently (not an error).
    """
    archive_root = stage_dir / _AUDIT_PROPOSALS_REL
    archive_root.mkdir(parents=True, exist_ok=True)

    archive_name = proposal_name
    suffix = 2
    while (archive_root / archive_name).exists():
        archive_name = f"{proposal_name}-{suffix}"
        suffix += 1

    archive_dir = archive_root / archive_name
    archive_dir.mkdir(parents=True, exist_ok=True)

    # plan.json — the captured bytes, verbatim.
    plan_bytes = capture.files.get(PLAN_FILE_NAME)
    if plan_bytes is not None:
        (archive_dir / PLAN_FILE_NAME).write_bytes(plan_bytes)

    # proposal.md — human-readable render.
    lines = [f"# Proposal: {proposal_name}\n"]
    lines.append(f"\n**Rationale:** {patch.rationale}\n")
    for edit in patch.edits:
        lines.append(f"\n## {edit.path}\n")
        lines.append(f"**Action:** {edit.action}  \n")
        lines.append(f"**Rationale:** {edit.rationale}\n")
        lines.append("\n")
        lines.append("```markdown\n")
        lines.append(edit.new_content)
        if not edit.new_content.endswith("\n"):
            lines.append("\n")
        lines.append("```\n")
    (archive_dir / "proposal.md").write_text("".join(lines), encoding="utf-8")

    # curator-delta.md — diff of the snapshot preview vs the captured preview (if a snapshot is present).
    # The snapshot contains plan.json + preview/ as siblings; compare only the
    # preview/ subdirectories so the diff is over the proposal page content only.
    snapshot_prefix = f"{SNAPSHOT_DIR_NAME}/{PREVIEW_DIR_NAME}/"
    preview_prefix = f"{PREVIEW_DIR_NAME}/"
    snap_files = {
        rel[len(snapshot_prefix) :]: data for rel, data in capture.files.items() if rel.startswith(snapshot_prefix)
    }
    live_files = {
        rel[len(preview_prefix) :]: data for rel, data in capture.files.items() if rel.startswith(preview_prefix)
    }
    if snap_files and live_files:
        delta_lines: list[str] = []
        for rel_path in sorted(set(snap_files) | set(live_files)):
            snap_text = snap_files.get(rel_path, b"").decode("utf-8", errors="replace")
            live_text = live_files.get(rel_path, b"").decode("utf-8", errors="replace")
            if snap_text == live_text:
                continue
            diff = difflib.unified_diff(
                snap_text.splitlines(keepends=True),
                live_text.splitlines(keepends=True),
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
                n=3,
            )
            delta_lines.extend(diff)
        if delta_lines:
            (archive_dir / "curator-delta.md").write_text("".join(delta_lines), encoding="utf-8")
    return f"{_AUDIT_PROPOSALS_REL}/{archive_name}"


# ── Commit: scoped to the patch-set, rolled back on exception ─


@dataclass
class _PlannedWrite:
    """One file the commit will write: exact pre-commit bytes (None = absent) and the bytes it will hold."""

    target: Path
    rel: str
    original_bytes: bytes | None
    new_bytes: bytes


def _plan_commit(stage_dir: Path, paths: WikiPaths, patch: WikiPatchSet, archive_rel: str) -> list[_PlannedWrite]:
    """Plan the writes: the patch-set's edit paths plus this proposal's archive, and nothing else (FR-001).

    A staged file outside that set is never written back, whatever differs.
    A path whose live bytes already equal the staged bytes is a no-op and is
    not planned (so it is not tracked by the receipt either). Planned paths
    (and so the receipt's ``planned_writes``) are ``posixpath.normpath`` of
    ``edit.path``, not its verbatim spelling in ``plan.json``.
    """
    wiki_dst = paths.wiki_dir
    rels: list[str] = []
    seen: set[str] = set()
    for edit in patch.edits:
        rel = posixpath.normpath(edit.path)
        if rel not in seen:
            seen.add(rel)
            rels.append(rel)
    archive_dir = stage_dir / archive_rel
    for staged in sorted(archive_dir.rglob("*")):
        if staged.is_file():
            rel = staged.relative_to(stage_dir).as_posix()
            if rel not in seen:
                seen.add(rel)
                rels.append(rel)

    planned: list[_PlannedWrite] = []
    for rel in rels:
        staged = stage_dir / rel
        if not staged.is_file():
            continue
        new_bytes = staged.read_bytes()
        # The live target passes the wiki boundary (no escape, no symlink on the way) before it is read.
        target = _wiki_write_target(rel, wiki_dst)
        original_bytes: bytes | None = None
        if target.exists():
            try:
                original_bytes = target.read_bytes()
            except OSError as exc:
                raise PromoteApplyError(
                    f"could not read existing wiki file for backup: {paths.relative_to_root(target)}: {exc}"
                ) from exc
            if original_bytes == new_bytes:
                continue  # no-op for this file
        planned.append(_PlannedWrite(target=target, rel=rel, original_bytes=original_bytes, new_bytes=new_bytes))
    return planned


def _apply_planned(planned: list[_PlannedWrite], paths: WikiPaths) -> list[str]:
    """Write the planned files into the live wiki; on any exception restore every touched file first.

    A target is recorded before its write: ``write_bytes`` is not atomic, so
    the in-flight file may be half-written or truncated and must be restored
    as well. An ``Exception`` is raised as PromoteApplyError; anything else
    (KeyboardInterrupt, SystemExit) is re-raised as is. Either way the wiki
    ends up in its pre-commit state, unless the rollback itself is interrupted
    or fails (failures are reported). Returns the wiki-relative paths written.
    """
    applied: list[_PlannedWrite] = []
    created_dirs: list[Path] = []
    try:
        for plan in planned:
            applied.append(plan)
            missing = [d for d in (plan.target.parent, *plan.target.parent.parents) if not d.exists()]
            created_dirs.extend(reversed(missing))
            plan.target.parent.mkdir(parents=True, exist_ok=True)
            plan.target.write_bytes(plan.new_bytes)
    except BaseException as exc:
        # Roll back every touched file before re-raising. Rollback
        # itself can fail (rare); we surface both errors.
        rollback_errors: list[str] = []
        for done in reversed(applied):
            try:
                if done.original_bytes is None:
                    # We created this file; remove it to restore the
                    # pre-commit state.
                    if done.target.exists():
                        done.target.unlink()
                else:
                    # We updated this file; rewrite its original bytes.
                    done.target.write_bytes(done.original_bytes)
            except Exception as rb_exc:  # one failed restore must not stop the others
                rollback_errors.append(f"rollback failed for {done.rel}: {rb_exc}")
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except FileNotFoundError:
                pass  # mkdir never got that far
            except OSError as rb_exc:
                rollback_errors.append(f"rollback failed for {paths.relative_to_root(directory)}/: {rb_exc}")
        if not isinstance(exc, Exception):
            for note in rollback_errors:
                exc.add_note(note)
            raise
        failed = applied[-1].rel
        msg = f"live wiki write failed for {failed}: {exc}; rolled back {len(applied)} file(s), including {failed}."
        if rollback_errors:
            msg += " Rollback also raised: " + "; ".join(rollback_errors)
        raise PromoteApplyError(msg) from exc

    return [p.rel for p in applied]


# ── receipt.json ──────────────────────────────────────────────


def _fsync_dir(path: Path) -> None:
    """Flush a directory's entries to disk where the platform allows opening a directory."""
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError:
        return
    try:
        with contextlib.suppress(OSError):
            os.fsync(fd)
    finally:
        os.close(fd)


def _receipt_bytes(receipt: dict[str, Any]) -> bytes:
    return (json.dumps(receipt, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _write_receipt(proposals_dir: Path, receipt: dict[str, Any]) -> bytes:
    """Write ``receipt.json`` through a temporary file, fsync it and the directory; return the exact bytes.

    ``OSError`` propagates; the caller decides what the failure means for its step.
    """
    payload = _receipt_bytes(receipt)
    tmp = proposals_dir / _RECEIPT_TMP_NAME
    with tmp.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, proposals_dir / RECEIPT_FILE_NAME)
    _fsync_dir(proposals_dir)
    return payload


def _discard_receipt_tmp(proposals_dir: Path) -> None:
    """Remove a temporary receipt a failed earlier write left behind (never part of any manifest)."""
    with contextlib.suppress(OSError):
        (proposals_dir / _RECEIPT_TMP_NAME).unlink()


def _corrupt_receipt(receipt_path: Path, why: str) -> PromoteApplyError:
    return PromoteApplyError(
        f"{receipt_path} is not a usable receipt ({why}). A missing or corrupt receipt is never taken to mean the "
        "proposal was committed, and nothing is re-applied. Compare the proposal's previews with the live pages, "
        "then either remove the receipt and promote afresh, or move the directory aside.",
        reason=REASON_UNCERTAIN_OUTCOME,
    )


def _load_receipt(proposals_dir: Path) -> dict[str, Any] | None:
    """The receipt in ``proposals_dir``, None when there is none; a corrupt one is refused (exit 10)."""
    receipt_path = proposals_dir / RECEIPT_FILE_NAME
    if receipt_path.is_symlink():
        raise PromoteValidationError(f"{receipt_path} is a symlink; refusing to read through it")
    _proposal_file(RECEIPT_FILE_NAME, proposals_dir)
    if not receipt_path.exists():
        return None
    try:
        data = json.loads(receipt_path.read_bytes().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise _corrupt_receipt(receipt_path, f"not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise _corrupt_receipt(receipt_path, "not a JSON object")
    state = data.get("state")
    if state not in (STATE_COMMITTING, STATE_COMMITTED):
        raise _corrupt_receipt(receipt_path, f"unknown state {state!r}")
    if not _is_hex_digest(data.get("submission_digest")):
        raise _corrupt_receipt(receipt_path, "missing or malformed submission_digest")
    manifest = data.get("submission_manifest")
    if not isinstance(manifest, list) or not all(
        isinstance(e, dict) and isinstance(e.get("path"), str) and _is_hex_digest(e.get("sha256")) for e in manifest
    ):
        raise _corrupt_receipt(receipt_path, "missing or malformed submission_manifest")
    if not isinstance(data.get("wiki_target"), dict):
        raise _corrupt_receipt(receipt_path, "missing wiki_target")
    writes = data.get("planned_writes")
    if not isinstance(writes, list) or not all(
        isinstance(w, dict)
        and isinstance(w.get("path"), str)
        and _is_hex_digest(w.get("post_sha256"))
        and (w.get("pre_sha256") is None or _is_hex_digest(w.get("pre_sha256")))
        for w in writes
    ):
        raise _corrupt_receipt(receipt_path, "missing or malformed planned_writes")
    return data


def _build_receipt(
    *,
    proposals_dir: Path,
    capture: _Capture,
    plan_sha256: str,
    planned: list[_PlannedWrite],
    handle: _WikiHandle,
    lock_wait: float,
    entry_point: str,
    started_at: str,
    unguarded: list[str],
) -> dict[str, Any]:
    """The ``committing`` receipt: identity of the submission and of the wiki, and every write the commit will make."""
    return {
        "receipt_version": RECEIPT_VERSION,
        "state": STATE_COMMITTING,
        "proposal": proposals_dir.name,
        "submission_digest": capture.digest,
        "digest_recipe": HASH_RECIPE_PAYLOAD_DIGEST,
        "submission_manifest": capture.manifest,
        "plan_sha256": plan_sha256,
        "wiki_target": {"st_dev": handle.st_dev, "st_ino": handle.st_ino, "path": handle.resolved},
        "planned_writes": [
            {
                "path": p.rel,
                "pre_sha256": None if p.original_bytes is None else _sha256(p.original_bytes),
                "post_sha256": _sha256(p.new_bytes),
            }
            for p in planned
        ],
        "written_paths": [],
        "unguarded_paths": list(unguarded),
        "lock_wait_seconds": round(lock_wait, 6),
        "started_at": started_at,
        "committing_at": _now(),
        "committed_at": None,
        "promoter": {"package": PACKAGE_NAME, "version": __version__, "entry_point": entry_point},
    }


def _check_wiki_target(receipt: dict[str, Any], receipt_path: Path, handle: _WikiHandle) -> None:
    """Refuse a receipt written for another wiki (device and inode) or one whose identity cannot be verified."""
    target = receipt["wiki_target"]
    dev, ino = target.get("st_dev"), target.get("st_ino")
    recorded_path = target.get("path", "?")
    usable = (
        isinstance(dev, int)
        and isinstance(ino, int)
        and not isinstance(dev, bool)
        and not isinstance(ino, bool)
        and dev != 0
        and ino != 0
    )
    if not usable or handle.st_dev == 0 or handle.st_ino == 0:
        raise PromoteApplyError(
            f"cannot verify which wiki {receipt_path} was written for: the filesystem reports no usable identity "
            f"(recorded device {dev}, inode {ino} for {recorded_path}; now device {handle.st_dev}, inode "
            f"{handle.st_ino} for {handle.resolved}). Recovery of an interrupted promotion needs a filesystem with "
            "stable inode identity. Compare the receipt's tracked writes (pre- and post-commit sha256) with the "
            "live pages by hand, then promote afresh or discard the proposal directory; nothing was written.",
            reason=REASON_WIKI_IDENTITY_UNAVAILABLE,
        )
    if (dev, ino) != (handle.st_dev, handle.st_ino):
        raise PromoteApplyError(
            f"{receipt_path} was written for wiki {recorded_path} (device {dev}, inode {ino}); this run targets "
            f"{handle.resolved} (device {handle.st_dev}, inode {handle.st_ino}). Nothing was written. If the wiki "
            "was legitimately restored or re-cloned at the same path, compare the receipt's tracked writes (pre- "
            "and post-commit sha256) with the live pages, then either finish by promoting afresh or discard the "
            "proposal directory by hand.",
            reason=REASON_WIKI_MISMATCH,
        )


# ── Step 4: the archive, written from the capture, published by rename ──


def _write_archive_file(path: Path, data: bytes) -> None:
    """Write one archive file and fsync it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _publish_archive(tmp: Path, target: Path) -> None:
    """Publish the complete temporary archive with one ``rename``: a reader sees no archive or the whole one."""
    os.rename(tmp, target)


def _remove_source_entry(path: Path) -> None:
    """Remove one file or empty directory of the original proposal directory."""
    if path.is_dir():
        path.rmdir()
    else:
        path.unlink()


def _fsync_tree(root: Path) -> None:
    for dirpath, _dirnames, _filenames in os.walk(root):
        _fsync_dir(Path(dirpath))


def _remove_leftover_tmp(applied_root: Path, name: str) -> None:
    """Remove ``.applied/.<name>.<pid>.tmp`` siblings an earlier failed run left; they are never published."""
    if not applied_root.is_dir():
        return
    for leftover in applied_root.glob(f".{name}.*{_ARCHIVE_TMP_SUFFIX}"):
        if leftover.is_dir() and not leftover.is_symlink():
            shutil.rmtree(leftover, ignore_errors=True)


def _directory_files(directory: Path) -> dict[str, Path]:
    """Every entry under ``directory`` that is not a directory, keyed by relative POSIX path."""
    found: dict[str, Path] = {}
    for dirpath, dirnames, filenames in os.walk(directory, followlinks=False):
        base = Path(dirpath)
        for name in dirnames:
            if (base / name).is_symlink():
                found[(base / name).relative_to(directory).as_posix()] = base / name
        for name in filenames:
            found[(base / name).relative_to(directory).as_posix()] = base / name
    return found


def _mismatches(directory: Path, expected: Mapping[str, str], *, ignore: Iterable[str] = ()) -> list[str]:
    """Files in ``directory`` that are new or differ from ``expected`` (relative path -> sha256).

    Files of ``expected`` that are absent are not reported: a partial cleanup
    may already have removed them.
    """
    skipped = set(ignore)
    problems: list[str] = []
    for rel, path in sorted(_directory_files(directory).items()):
        if rel in skipped:
            continue
        if path.is_symlink() or not path.is_file():
            problems.append(f"{rel} (not a regular file)")
        elif rel not in expected:
            problems.append(f"{rel} (new)")
        elif _sha256(path.read_bytes()) != expected[rel]:
            problems.append(f"{rel} (changed)")
    return problems


def _archive_is_complete(candidate: Path, manifest: Mapping[str, str]) -> bool:
    """True when ``candidate`` holds every manifest file with the right sha256 and nothing else but the receipt."""
    files = _directory_files(candidate)
    if set(files) - {RECEIPT_FILE_NAME} != set(manifest):
        return False
    return not _mismatches(candidate, manifest, ignore=(RECEIPT_FILE_NAME,))


def _find_complete_archive(applied_root: Path, name: str, digest: str, manifest: Mapping[str, str]) -> Path | None:
    """An already published archive of this submission: same ``submission_digest`` and files matching the manifest."""
    if not applied_root.is_dir():
        return None
    for candidate in sorted(applied_root.iterdir()):
        if not candidate.is_dir() or candidate.is_symlink() or candidate.name.startswith("."):
            continue
        if candidate.name != name and not (
            candidate.name.startswith(f"{name}-") and candidate.name[len(name) + 1 :].isdigit()
        ):
            continue
        if (candidate / RECEIPT_FILE_NAME).is_symlink():
            continue  # never read through a symlink, even in the archive
        try:
            data = json.loads((candidate / RECEIPT_FILE_NAME).read_bytes().decode("utf-8"))
        except (OSError, ValueError):
            continue
        if (
            isinstance(data, dict)
            and data.get("submission_digest") == digest
            and _archive_is_complete(candidate, manifest)
        ):
            return candidate
    return None


def _archive_submission(proposals_dir: Path, paths: WikiPaths, archive_files: Mapping[str, bytes], digest: str) -> Path:
    """Publish ``archive_files`` as ``.applied/<name>/`` (``-2``, ``-3`` on a clash) and return the directory.

    Idempotent: an existing complete archive of the same submission is
    returned instead of a new one. The archive is written into
    ``.applied/.<name>.<pid>.tmp/``, fsynced, and renamed into place, so a
    consumer never sees a partial archive at an applied name. ``OSError``
    propagates.
    """
    applied_root = paths.applied_dir
    applied_root.mkdir(parents=True, exist_ok=True)
    name = proposals_dir.name
    _remove_leftover_tmp(applied_root, name)
    manifest = {rel: _sha256(data) for rel, data in archive_files.items() if rel != RECEIPT_FILE_NAME}
    existing = _find_complete_archive(applied_root, name, digest, manifest)
    if existing is not None:
        return existing
    tmp = applied_root / f".{name}.{os.getpid()}{_ARCHIVE_TMP_SUFFIX}"
    if tmp.exists():
        shutil.rmtree(tmp)
    try:
        for rel in sorted(archive_files):
            _write_archive_file(tmp / rel, archive_files[rel])
        _fsync_tree(tmp)
        target = applied_root / name
        suffix = 2
        while target.exists():
            target = applied_root / f"{name}-{suffix}"
            suffix += 1
        _publish_archive(tmp, target)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    _fsync_dir(applied_root)
    return target


def _payload_changed_after_archive(proposals_dir: Path, archive: Path, problems: list[str]) -> PromoteApplyError:
    return PromoteApplyError(
        f"the proposal directory {proposals_dir} changed after its payload was captured. Its archive {archive} is "
        "complete and correct (it holds the bytes that were applied); these files in the directory differ from the "
        f"archive or are new: {', '.join(problems)}. The directory was left in place. Remedy: delete the leftover "
        "directory, or promote it afresh if it is a new proposal.",
        reason=REASON_PAYLOAD_CHANGED,
    )


def _remove_source_dir(proposals_dir: Path, archive_files: Mapping[str, bytes], archive: Path) -> None:
    """Remove the original directory, only while every file in it matches the archive; ``receipt.json`` last.

    The receipt itself is not compared: it is the promoter's own file, outside
    the submission identity, and the archive carries its own copy. A file
    removed from the directory after capture is not a mismatch either (the
    archive holds the captured bytes). ``OSError`` from a deletion
    propagates: the archive is complete, and a retry finishes the cleanup
    from the receipt's manifest.
    """
    expected = {rel: _sha256(data) for rel, data in archive_files.items()}
    problems = _mismatches(proposals_dir, expected, ignore=(RECEIPT_FILE_NAME, _RECEIPT_TMP_NAME))
    if problems:
        raise _payload_changed_after_archive(proposals_dir, archive, problems)
    _discard_receipt_tmp(proposals_dir)
    for dirpath, dirnames, filenames in os.walk(proposals_dir, topdown=False):
        base = Path(dirpath)
        for name in sorted(filenames):
            if base == proposals_dir and name == RECEIPT_FILE_NAME:
                continue
            _remove_source_entry(base / name)
        for name in sorted(dirnames):
            _remove_source_entry(base / name)
    receipt_path = proposals_dir / RECEIPT_FILE_NAME
    if receipt_path.exists():
        _remove_source_entry(receipt_path)
    _remove_source_entry(proposals_dir)


# ── The protocol ──────────────────────────────────────────────


def _commit_and_archive(
    *,
    proposals_dir: Path,
    paths: WikiPaths,
    capture: _Capture,
    plan_sha256: str,
    planned: list[_PlannedWrite],
    handle: _WikiHandle,
    lock_wait: float,
    entry_point: str,
    started_at: str,
    unguarded: list[str],
) -> PromoteResult:
    """Steps 1 to 4 for a fresh promotion whose stage validated and whose preconditions held."""
    # FR-012: the last look at the live targets before anything is written.
    _recheck_write_targets(planned, paths.wiki_dir)
    receipt = _build_receipt(
        proposals_dir=proposals_dir,
        capture=capture,
        plan_sha256=plan_sha256,
        planned=planned,
        handle=handle,
        lock_wait=lock_wait,
        entry_point=entry_point,
        started_at=started_at,
        unguarded=unguarded,
    )
    # Step 1: the recovery marker, before any wiki write.
    try:
        _write_receipt(proposals_dir, receipt)
    except OSError as exc:
        _discard_receipt_tmp(proposals_dir)
        raise OutputWriteError(
            f"could not write {RECEIPT_FILE_NAME} in {proposals_dir}: {exc}; nothing was committed"
        ) from exc
    # Step 2: the commit (rolled back on exception; the ``committing`` receipt
    # then reads as not committed on the next promote).
    applied = _apply_planned(planned, paths)
    # Step 3: the outcome.
    receipt["state"] = STATE_COMMITTED
    receipt["written_paths"] = list(applied)
    receipt["committed_at"] = _now()
    try:
        receipt_bytes = _write_receipt(proposals_dir, receipt)
    except OSError as exc:
        raise OutputWriteError(
            f"the edits were committed to the wiki, but {RECEIPT_FILE_NAME} in {proposals_dir} could not be "
            f"rewritten as committed: {exc}. Promote the directory again to finish; nothing is applied twice."
        ) from exc
    # Step 4: archive from the capture, then remove the original.
    archived = _archive_and_cleanup(proposals_dir, paths, {**capture.files, RECEIPT_FILE_NAME: receipt_bytes}, receipt)
    return PromoteResult(
        applied_paths=applied,
        proposals_dir=proposals_dir,
        archived_dir=archived,
        dry_run=False,
        unguarded_paths=list(unguarded),
        warnings=_unguarded_warnings(unguarded),
    )


def _archive_and_cleanup(
    proposals_dir: Path, paths: WikiPaths, archive_files: Mapping[str, bytes], receipt: dict[str, Any]
) -> Path | None:
    """Step 4. A filesystem failure here is housekeeping: the wiki is updated and the receipt says so.

    Returns None in that case; a later promote of the directory finishes the
    step. ``payload_changed`` (the directory no longer matches the archive)
    is raised: the archive is complete, the directory is left in place.
    """
    try:
        archive = _archive_submission(proposals_dir, paths, archive_files, str(receipt["submission_digest"]))
        _remove_source_dir(proposals_dir, archive_files, archive)
    except OSError:
        return None
    return archive


def _written_paths(receipt: dict[str, Any]) -> list[str]:
    written = receipt.get("written_paths")
    if isinstance(written, list) and all(isinstance(p, str) for p in written):
        return list(written)
    return [str(w["path"]) for w in receipt["planned_writes"]]


def _unguarded_paths(receipt: dict[str, Any]) -> list[str]:
    unguarded = receipt.get("unguarded_paths")
    if isinstance(unguarded, list) and all(isinstance(p, str) for p in unguarded):
        return list(unguarded)
    return []


def _finish_committed(proposals_dir: Path, paths: WikiPaths, receipt: dict[str, Any]) -> PromoteResult:
    """Resolve a ``committed`` receipt: finish step 4 only, with no appends and no wiki writes."""
    digest = str(receipt["submission_digest"])
    manifest = {str(e["path"]): str(e["sha256"]) for e in receipt["submission_manifest"]}
    receipt_path = proposals_dir / RECEIPT_FILE_NAME
    applied_root = paths.applied_dir
    _remove_leftover_tmp(applied_root, proposals_dir.name)
    archive = _find_complete_archive(applied_root, proposals_dir.name, digest, manifest)
    if archive is None:
        # No archive yet: it can be written only from the directory's bytes, and
        # only while they are the bytes that were promoted.
        capture = _capture_submission(proposals_dir, skip=frozenset({RECEIPT_FILE_NAME, _RECEIPT_TMP_NAME}))
        shas = capture.shas
        missing = sorted(rel for rel in manifest if rel not in shas)
        changed = sorted(rel for rel in manifest if rel in shas and shas[rel] != manifest[rel])
        if capture.digest != digest or missing or changed:
            applied = "; ".join(f"{w['path']} -> {w['post_sha256']}" for w in receipt["planned_writes"])
            raise PromoteApplyError(
                f"{proposals_dir} was committed to the wiki but its files no longer match the promoted payload "
                f"(digest {digest}): missing {missing or 'none'}, changed {changed or 'none'}. No archive could be "
                "written, because the promoted bytes now exist only in the wiki. The applied pages are identified "
                f"by the receipt's tracked post-commit sha256: {applied or 'no writes'}. Remedy: move the directory "
                "aside and keep its receipt.json as the record of what was applied, or promote it afresh if it is "
                "a new proposal.",
                reason=REASON_PAYLOAD_CHANGED,
            )
        archive_files: dict[str, bytes] = {rel: capture.files[rel] for rel in manifest}
        archive_files[RECEIPT_FILE_NAME] = receipt_path.read_bytes()
    else:
        archive_files = {rel: path.read_bytes() for rel, path in _directory_files(archive).items()}
    archived = _archive_and_cleanup(proposals_dir, paths, archive_files, receipt)
    unguarded = _unguarded_paths(receipt)
    return PromoteResult(
        applied_paths=_written_paths(receipt),
        proposals_dir=proposals_dir,
        archived_dir=archived,
        dry_run=False,
        unguarded_paths=unguarded,
        warnings=_unguarded_warnings(unguarded),
    )


def _classify_committing(receipt: dict[str, Any], paths: WikiPaths, receipt_path: Path) -> bool:
    """True when every tracked write is at its post-commit state, False when every one is at its pre-commit state.

    Any other combination, including a tracked path matching neither, is
    refused with ``uncertain_outcome`` (exit 10) and no writes.
    """
    all_pre = all_post = True
    report: list[str] = []
    for write in receipt["planned_writes"]:
        live = paths.wiki_dir / str(write["path"])
        # A tracked path that is not a regular file, or cannot be read, matches
        # neither state: the outcome is uncertain, not "absent".
        live_sha: str | None = None
        problem: str | None = None
        try:
            if live.is_symlink() or (live.exists() and not live.is_file()):
                problem = "not a regular file"
            elif live.is_file():
                live_sha = _sha256(live.read_bytes())
        except OSError as exc:
            problem = f"unreadable: {exc}"
        at_pre = problem is None and live_sha == write.get("pre_sha256")
        at_post = problem is None and live_sha == write["post_sha256"]
        all_pre &= at_pre
        all_post &= at_post
        state = "post-commit" if at_post else ("pre-commit" if at_pre else "neither")
        report.append(f"{write['path']}: {state} (live {problem or live_sha or 'absent'})")
    if all_post:
        return True
    if all_pre:
        return False
    raise PromoteApplyError(
        f"{receipt_path} records a promotion interrupted during its commit, and the live pages are neither all at "
        "their pre-commit state nor all at their post-commit state; nothing was written. Tracked writes: "
        + "; ".join(report)
        + ". Compare them with the receipt and repair the wiki by hand before promoting again.",
        reason=REASON_UNCERTAIN_OUTCOME,
    )


def _resolve_receipt(
    proposals_dir: Path, paths: WikiPaths, receipt: dict[str, Any], handle: _WikiHandle
) -> PromoteResult | None:
    """Resolve an existing receipt under the lock; None means "not committed, promote afresh"."""
    receipt_path = proposals_dir / RECEIPT_FILE_NAME
    _check_wiki_target(receipt, receipt_path, handle)
    if receipt["state"] == STATE_COMMITTED:
        return _finish_committed(proposals_dir, paths, receipt)
    if _classify_committing(receipt, paths, receipt_path):
        # Committed in full; only step 3 was missed. Finish steps 3 and 4.
        receipt["state"] = STATE_COMMITTED
        receipt["written_paths"] = [str(w["path"]) for w in receipt["planned_writes"]]
        receipt["committed_at"] = _now()
        try:
            _write_receipt(proposals_dir, receipt)
        except OSError as exc:
            raise OutputWriteError(f"could not rewrite {receipt_path} as committed: {exc}") from exc
        return _finish_committed(proposals_dir, paths, receipt)
    # Nothing was committed: the receipt is the only trace, and it goes.
    receipt_path.unlink()
    return None


def _is_already_applied(proposals_dir: Path) -> bool:
    """True when proposals_dir is an entry of a ``.applied/`` archive (its parent, not any ancestor)."""
    return proposals_dir.parent.name == APPLIED_DIR_NAME


@dataclass(frozen=True)
class _StagedDryRun:
    """A dry run's staged tree and preconditions outcome, handed out of the lock for validation (FR-011)."""

    patch: WikiPatchSet
    unguarded: list[str]


def _promote_locked(
    proposals_dir: Path,
    paths: WikiPaths,
    *,
    dry_run: bool,
    allow_unguarded_updates: bool,
    entry_point: str,
    handle: _WikiHandle,
    lock_wait: float,
    started_at: str,
    stage_dir: Path,
) -> PromoteResult | _StagedDryRun:
    """Everything that happens under the lock; ``stage_dir`` (absent on entry) receives the staged copy.

    A dry run returns ``_StagedDryRun`` once the preconditions have been
    checked against the live wiki; the caller validates the staged snapshot
    after releasing the lock.
    """
    _discard_receipt_tmp(proposals_dir)
    receipt = _load_receipt(proposals_dir)
    if receipt is not None:
        if dry_run:
            raise PromoteValidationError(
                f"{proposals_dir} carries {RECEIPT_FILE_NAME} from an interrupted promotion; a dry run cannot "
                "resolve it. Run promote without --dry-run to finish or discard it."
            )
        resolved = _resolve_receipt(proposals_dir, paths, receipt, handle)
        if resolved is not None:
            return resolved

    if not (proposals_dir / PLAN_FILE_NAME).exists():
        # Neither a receipt nor a plan: an empty leftover is removed (a dry run
        # only reports it); anything else is not a proposal.
        if not any(proposals_dir.iterdir()):
            if not dry_run:
                proposals_dir.rmdir()
            return PromoteResult(applied_paths=[], proposals_dir=proposals_dir, archived_dir=None, dry_run=dry_run)
        raise PromoteValidationError(f"plan.json not found in {proposals_dir}; not a valid proposals dir.")

    capture = _capture_submission(proposals_dir)
    patch, plan_sha256 = _parse_patch(capture, proposals_dir)
    planned: list[_PlannedWrite] = []
    unguarded: list[str] = []
    if patch.edits:
        _validate_before_staging(patch, paths)
        _stage_wiki(handle, paths.wiki_dir, stage_dir)
        for edit in patch.edits:
            _apply_edit(stage_dir, edit)
        # The accepted-proposal archive is staged AFTER the edit loop and
        # BEFORE validation so the validator sees the full tree (including
        # .audit/) and the commit writes it with the patch-set's paths.
        archive_rel = _stage_audit_archive(stage_dir, proposals_dir.name, capture, patch)
        if dry_run:
            # FR-011: the preconditions are checked against live while the lock
            # is held; the staged snapshot is validated by the caller after the
            # lock is released. Nothing is written either way.
            unguarded = _check_preconditions(patch, paths, allow_unguarded_updates=allow_unguarded_updates)
            return _StagedDryRun(patch=patch, unguarded=unguarded)
        # Validation gate. Raises PromoteValidationError on any failure; the
        # wiki tree is unchanged because nothing has been committed yet.
        _validate_staged_tree(stage_dir, paths, patch)
        # FR-008 / FR-009: immediately before the commit, against the live wiki.
        unguarded = _check_preconditions(patch, paths, allow_unguarded_updates=allow_unguarded_updates)
        planned = _plan_commit(stage_dir, paths, patch, archive_rel)
    elif dry_run:
        # Empty patch-set (gate reject): nothing to stage or apply.
        return PromoteResult(applied_paths=[], proposals_dir=proposals_dir, archived_dir=None, dry_run=True)
    return _commit_and_archive(
        proposals_dir=proposals_dir,
        paths=paths,
        capture=capture,
        plan_sha256=plan_sha256,
        planned=planned,
        handle=handle,
        lock_wait=lock_wait,
        entry_point=entry_point,
        started_at=started_at,
        unguarded=unguarded,
    )


def promote(
    proposals_dir: Path,
    paths: WikiPaths,
    dry_run: bool = False,
    *,
    entry_point: str = PROMOTE_ENTRY_POINT_API,
    allow_unguarded_updates: bool = False,
) -> PromoteResult:
    """Apply a proposals dir's patch-set to the wiki under the wiki lock.

    The promotion is validated, serialised against other wiki-studio writers
    on the same machine, and rolled back on failure; it is not crash-safe
    across files, and uncoordinated readers may observe intermediate state.
    The lock is held from before staging to after the archive move. Before
    the commit, still under the lock, the revision preconditions are checked
    against the live wiki: a ``create`` needs its target absent, an
    ``update`` with ``base_sha256`` needs the live page to still carry that
    hash, and an ``update`` without one is refused (exit 9) unless
    ``allow_unguarded_updates`` is set.

    Parameters
    ----------
    proposals_dir : Path
        Directory containing plan.json + preview/<path>.md (output of
        ``wiki-studio ingest`` or ``api.propose``), possibly with a
        ``receipt.json`` from an interrupted earlier promotion.
    paths : WikiPaths
        The resolved layout (wiki directory, proposals archive, lock timeout).
    dry_run : bool
        When True: take the lock, stage, check the preconditions against the
        live wiki, release the lock, then validate the staged snapshot. It
        writes nothing: no wiki content, no receipt, no proposal change (the
        lock file itself may be created). The result is point-in-time
        evidence; a real promote checks again.
    entry_point : str
        ``"api"`` or ``"cli"``, recorded in the receipt as software identity.
    allow_unguarded_updates : bool
        Compatibility mode with incomplete conflict protection: apply
        ``update`` edits that carry no ``base_sha256`` (proposals written
        before 0.6.0, drafts without a ``.base.json`` manifest) and list
        them in ``PromoteResult.unguarded_paths`` and the receipt. A stale
        draft can then overwrite a newer page; this option does not prevent
        that.

    Returns
    -------
    PromoteResult
        Summary of what was applied (or would be applied, on dry-run). A
        later promote of a directory with a ``committed`` receipt finishes
        the archive and reports the recorded writes without applying them
        again; a directory already under ``.applied/`` reports ``[]``.
    """
    if _is_already_applied(proposals_dir):
        # Idempotency: a second promote on an already-archived dir is a no-op
        # (callers detect it via applied_paths == []). A receipt from another
        # wiki is still refused before the outcome is reported.
        receipt = _load_receipt(proposals_dir) if proposals_dir.is_dir() else None
        if receipt is not None:
            handle = _open_wiki(paths.wiki_dir)
            try:
                _check_wiki_target(receipt, proposals_dir / RECEIPT_FILE_NAME, handle)
            finally:
                handle.close()
        return PromoteResult(applied_paths=[], proposals_dir=proposals_dir, archived_dir=proposals_dir, dry_run=dry_run)

    if not proposals_dir.is_dir():
        raise PromoteValidationError(f"proposals dir not found: {proposals_dir}")

    started_at = _now()
    lock = WikiLock(paths.wiki_dir, paths.lock_timeout)
    # The staging directory outlives the lock: a dry run validates its
    # snapshot after the release (FR-011), a real promote commits from it
    # before.
    with tempfile.TemporaryDirectory(prefix="wiki-stage-") as stage:
        stage_dir = Path(stage) / "wiki"
        with lock:
            handle = _open_wiki(paths.wiki_dir)
            try:
                outcome = _promote_locked(
                    proposals_dir,
                    paths,
                    dry_run=dry_run,
                    allow_unguarded_updates=allow_unguarded_updates,
                    entry_point=entry_point,
                    handle=handle,
                    lock_wait=lock.wait_seconds,
                    started_at=started_at,
                    stage_dir=stage_dir,
                )
            finally:
                handle.close()
        if not isinstance(outcome, _StagedDryRun):
            return outcome
        # Lock released: the staged tree is a point-in-time snapshot of the
        # wiki plus the edits, validated here without holding other writers up.
        _validate_staged_tree(stage_dir, paths, outcome.patch)
        return PromoteResult(
            applied_paths=[e.path for e in outcome.patch.edits],
            proposals_dir=proposals_dir,
            archived_dir=None,
            dry_run=True,
            unguarded_paths=list(outcome.unguarded),
            warnings=_unguarded_warnings(outcome.unguarded),
        )


# ── init: the scaffold every other verb needs ─────────────────

INDEX_NAME = "index.md"
LOG_NAME = "log.md"
DEFAULT_WIKI_TITLE = "Wiki"

_INDEX_TEMPLATE = (
    "---\npage_type: index\nslug: index\ntitle: {title}\nstatus: stable\nlast_reviewed: {date}\n---\n\n# {title}\n"
)
_LOG_TEMPLATE = (
    "---\npage_type: log\nslug: log\ntitle: {title} log\nstatus: stable\nlast_reviewed: {date}\n---\n\n# {title} log\n"
)


@dataclass(frozen=True)
class InitResult:
    """What ``init_wiki`` did: the wiki directory and the files it created (wiki-relative)."""

    wiki_dir: Path
    created: list[str]


def init_wiki(paths: WikiPaths, *, title: str = DEFAULT_WIKI_TITLE) -> InitResult:
    """Create the wiki directory with a minimal ``index.md`` and ``log.md`` when they are absent.

    ``promote`` stages a copy of the wiki and appends index and log lines, so
    both files must exist before the first patch-set; a fresh wiki gets them
    here. Existing files are never touched, so running it twice is a no-op.
    The scaffold lints clean.
    """
    today = datetime.date.today().isoformat()
    paths.wiki_dir.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    for name, template in ((INDEX_NAME, _INDEX_TEMPLATE), (LOG_NAME, _LOG_TEMPLATE)):
        target = paths.wiki_dir / name
        try:
            # Exclusive create: a concurrent init or an existing file wins, never overwritten.
            with target.open("x", encoding="utf-8") as handle:
                handle.write(template.format(title=title, date=today))
        except FileExistsError:
            continue
        created.append(name)
    return InitResult(wiki_dir=paths.wiki_dir, created=created)
