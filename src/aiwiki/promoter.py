# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# aiwiki.promoter — Phase-2 patch-set promotion.
#
# THE ONLY MODULE IN THE PIPELINE THAT WRITES TO THE WIKI DIRECTORY.
#
# Promotion is atomic: build a staged tree (copy of the current wiki +
# the patch-set's edits applied), validate the staged tree end-to-end
# (per-edit semantic + structural lint), and only then commit the
# staged tree to the wiki directory. Any validation failure leaves
# the wiki untouched.
#
# The validation step intentionally runs against the staged tree, not
# the live wiki, so:
#   - an ``update`` to a path that was just ``create``-d in the same
#     patch-set is legitimate (it didn't exist pre-apply, it exists
#     post-apply)
#   - the wiki linter sees the post-apply state and judges link
#     integrity / orphan-from-index against the would-be wiki, not
#     the pre-apply wiki
#
# After a successful commit, the proposals dir is moved to
# ``<proposals_dir>/.applied/<source-stem>/`` (audit
# trail). Subsequent runs against the same dir are no-ops.

from __future__ import annotations

import difflib
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .errors import (
    PromoteApplyError,
    PromoteValidationError,
)
from .lint import lint_wiki
from .paths import APPLIED_DIR_NAME
from .proposal import (
    PageEdit,
    WikiPatchSet,
    validate_page_edit_semantics,
    validate_patch_set,
)

if TYPE_CHECKING:
    from .paths import WikiPaths


@dataclass(frozen=True)
class PromoteResult:
    """Outcome of a successful promote.

    Attributes
    ----------
    applied_paths : list[str]
        Wiki-relative paths affected (created/updated/appended-to).
    proposals_dir : Path
        Original proposals dir (now moved to ``.applied/`` unless
        ``dry_run`` was set).
    archived_dir : Path | None
        Where the proposals dir was moved to after commit. None if
        dry_run.
    dry_run : bool
        True if the staged tree was built and validated but never
        committed to the live wiki.
    """

    applied_paths: list[str]
    proposals_dir: Path
    archived_dir: Path | None
    dry_run: bool


def _load_patch_from_dir(proposals_dir: Path) -> WikiPatchSet:
    """Reconstruct a WikiPatchSet from a proposals dir on disk."""
    plan_path = proposals_dir / "plan.json"
    if not plan_path.exists():
        raise PromoteValidationError(f"plan.json not found in {proposals_dir}; not a valid proposals dir.")
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PromoteValidationError(f"plan.json at {plan_path} is not valid JSON: {exc}") from exc

    edits: list[PageEdit] = []
    for raw in plan.get("edits", []):
        # plan.json does not embed full new_content (Phase 1 stored it
        # only in preview/<path>) so we re-read from preview on apply.
        preview_rel = raw.get("preview")
        if not preview_rel:
            raise PromoteValidationError(f"plan.json edit missing 'preview' pointer: {raw!r}")
        preview_path = proposals_dir / preview_rel
        if not preview_path.exists():
            raise PromoteValidationError(f"preview file referenced by plan.json missing: {preview_path}")
        new_content = preview_path.read_text(encoding="utf-8")
        edits.append(
            PageEdit(
                path=str(raw["path"]),
                action=raw["action"],
                new_content=new_content,
                rationale=str(raw.get("rationale", "")),
            )
        )
    return WikiPatchSet(
        edits=edits,
        source_path=str(plan.get("source_path", "")),
        backend=str(plan.get("backend", "")),
        rationale=str(plan.get("rationale", "")),
    )


def _stage_wiki(paths: WikiPaths, dest: Path) -> None:
    """Copy the current wiki tree to ``dest``."""
    wiki_src = paths.wiki_dir
    if not wiki_src.is_dir():
        raise PromoteApplyError(f"wiki source not found at {wiki_src}; cannot stage.")
    if dest.exists():
        shutil.rmtree(dest)
    # Shallow copy via copytree — a wiki is small (tens of pages),
    # full copy is the simplest atomicity primitive.
    shutil.copytree(wiki_src, dest)


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
    target = stage_dir / edit.path
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
    elif edit.action == "append-log":
        if not target.exists():
            raise PromoteApplyError(f"append-log edit to {edit.path}: log.md does not exist in staged tree.")
        existing = target.read_text(encoding="utf-8")
        suffix = edit.new_content if edit.new_content.endswith("\n") else edit.new_content + "\n"
        prefix = existing if existing.endswith("\n") else existing + "\n"
        target.write_text(prefix + suffix, encoding="utf-8")
    elif edit.action == "append-index":
        if not target.exists():
            raise PromoteApplyError(f"append-index edit to {edit.path}: index.md does not exist in staged tree.")
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
    """Run the structural linter over the staged wiki with escape links resolvable.

    Pages may link outside the wiki (``../../docs/...``). Those targets live
    in the real project, so the staged wiki is mirrored at its own relative
    location under a temporary root whose other entries are symlinks to the
    live ones. A wiki outside the root is linted in place (escape links
    cannot be mirrored, as for the live wiki).
    """
    try:
        rel = paths.wiki_dir.resolve().relative_to(paths.root.resolve())
    except ValueError:
        return lint_wiki(stage_dir)

    with tempfile.TemporaryDirectory(prefix="wiki-lint-stage-") as tmp:
        tmp_root = Path(tmp)
        mirrored = tmp_root / rel
        shutil.copytree(stage_dir, mirrored, dirs_exist_ok=True)
        # Symlink the siblings of every ancestor of the wiki (root entries
        # except ``knowledge``, then ``knowledge`` entries except ``wiki``,
        # for the default layout) so escape paths resolve identically.
        real_dir = paths.root.resolve()
        tmp_dir = tmp_root
        for part in rel.parts:
            for entry in real_dir.iterdir():
                if entry.name == part:
                    continue
                link = tmp_dir / entry.name
                if link.exists() or link.is_symlink():
                    continue
                try:
                    link.symlink_to(entry)
                except OSError:
                    if entry.is_file():
                        shutil.copy(entry, link)
            real_dir = real_dir / part
            tmp_dir = tmp_dir / part
        return lint_wiki(mirrored)


def _stage_audit_archive(
    stage_dir: Path,
    proposals_dir: Path,
    patch: WikiPatchSet,
) -> None:
    """Stage the accepted-proposal archive into stage_dir/.audit/proposals/<name>/.

    Written AFTER the _apply_edit loop and BEFORE _validate_staged_tree so
    the validator sees the final tree and the existing atomic apply commits
    it.

    Contents:
      plan.json  — verbatim copy of proposals_dir/plan.json
      proposal.md — human-readable render of the patch-set
      curator-delta.md — present only when the curator hand-edited
                          preview/ between ingest and promote (diff of
                          .ingest-snapshot/ vs current preview/)

    Collision handling: if stage_dir/.audit/proposals/<name>/ already
    exists in the live wiki (mirrored into stage_dir by _stage_wiki), a
    deterministic numeric suffix is appended: <name>-2, <name>-3, ...

    A proposal dir lacking .ingest-snapshot/ means no snapshot was taken
    (pre-Phase-2 proposal or --dry-run); curator-delta.md is omitted
    silently (not an error).
    """
    archive_root = stage_dir / ".audit" / "proposals"
    archive_root.mkdir(parents=True, exist_ok=True)

    base_name = proposals_dir.name
    archive_name = base_name
    suffix = 2
    while (archive_root / archive_name).exists():
        archive_name = f"{base_name}-{suffix}"
        suffix += 1

    archive_dir = archive_root / archive_name
    archive_dir.mkdir(parents=True, exist_ok=True)

    # plan.json — verbatim copy.
    src_plan = proposals_dir / "plan.json"
    if src_plan.is_file():
        shutil.copy2(str(src_plan), str(archive_dir / "plan.json"))

    # proposal.md — human-readable render.
    lines = [f"# Proposal: {base_name}\n"]
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

    # curator-delta.md — diff snapshot preview vs live preview (if snapshot present).
    # The snapshot contains plan.json + preview/ as siblings; compare only the
    # preview/ subdirectories so the diff is over the proposal page content only.
    snapshot_dir = proposals_dir / ".ingest-snapshot"
    snapshot_preview = snapshot_dir / "preview"
    preview_dir = proposals_dir / "preview"
    if snapshot_preview.is_dir() and preview_dir.is_dir():
        delta_lines: list[str] = []
        # Collect all preview files from both snapshot preview and live preview.
        snap_files: set[str] = set()
        live_files: set[str] = set()
        for p in snapshot_preview.rglob("*"):
            if p.is_file():
                try:
                    rel = p.relative_to(snapshot_preview)
                    snap_files.add(rel.as_posix())
                except ValueError:
                    pass
        for p in preview_dir.rglob("*"):
            if p.is_file():
                try:
                    rel = p.relative_to(preview_dir)
                    live_files.add(rel.as_posix())
                except ValueError:
                    pass

        all_files = sorted(snap_files | live_files)
        for rel_path in all_files:
            snap_file = snapshot_preview / rel_path
            live_file = preview_dir / rel_path

            snap_text = snap_file.read_text(encoding="utf-8") if snap_file.is_file() else ""
            live_text = live_file.read_text(encoding="utf-8") if live_file.is_file() else ""

            if snap_text == live_text:
                continue

            snap_label = f"a/{rel_path}"
            live_label = f"b/{rel_path}"
            diff = difflib.unified_diff(
                snap_text.splitlines(keepends=True),
                live_text.splitlines(keepends=True),
                fromfile=snap_label,
                tofile=live_label,
                n=3,
            )
            delta_lines.extend(diff)

        if delta_lines:
            (archive_dir / "curator-delta.md").write_text("".join(delta_lines), encoding="utf-8")


def _commit_stage_to_wiki(stage_dir: Path, paths: WikiPaths) -> list[str]:
    """Copy staged tree files back into the live wiki atomically.

    Atomicity is the load-bearing guarantee here: every patch-set is
    a single curator decision, and the wiki must not end up in a
    partial state if any per-file write fails midway. The strategy:
      1. Plan the writes (collect every (target, new_content) pair
         and snapshot the existing content so we can restore).
      2. Apply each write, tracking which targets we created vs
         updated.
      3. On any OSError during the apply loop, restore originals
         (rewriting updated files, removing newly-created files),
         then raise PromoteApplyError. The wiki ends up in its
         pre-commit state.
      4. Only on full success does the function return without
         raising.

    Returns the list of wiki-relative paths actually written
    (excluding no-op files whose content was already identical).
    """
    wiki_dst = paths.wiki_dir

    # Plan phase — read existing state for every file we'd write.
    @dataclass
    class _PlannedWrite:
        target: Path
        new_content: str
        original: str | None  # None ⇒ file did not exist pre-commit (created)
        original_bytes: bytes | None  # for binary files (plan.json)
        new_bytes: bytes | None
        rel: str
        is_text: bool

    planned: list[_PlannedWrite] = []

    def _collect_md(stage_root: Path) -> None:
        """Collect all *.md files from stage_root except schema/ and scripts/."""
        for staged in stage_root.rglob("*.md"):
            rel = staged.relative_to(stage_dir)
            rel_str = rel.as_posix()
            if rel.parts and rel.parts[0] in ("schema", "scripts"):
                continue
            target = wiki_dst / rel
            new_content = staged.read_text(encoding="utf-8")
            original: str | None = None
            if target.exists():
                try:
                    original = target.read_text(encoding="utf-8")
                except OSError as exc:
                    raise PromoteApplyError(
                        f"could not read existing wiki file for backup: {paths.relative_to_root(target)}: {exc}"
                    ) from exc
                if original == new_content:
                    continue  # no-op for this file
            planned.append(
                _PlannedWrite(
                    target=target,
                    new_content=new_content,
                    original=original,
                    original_bytes=None,
                    new_bytes=None,
                    rel=rel_str,
                    is_text=True,
                )
            )

    def _collect_plan_json(stage_root: Path) -> None:
        """Collect all .audit/**/plan.json files."""
        audit_dir = stage_root / ".audit"
        if not audit_dir.is_dir():
            return
        for staged in audit_dir.rglob("plan.json"):
            rel = staged.relative_to(stage_dir)
            rel_str = rel.as_posix()
            target = wiki_dst / rel
            new_bytes = staged.read_bytes()
            original_bytes: bytes | None = None
            if target.exists():
                try:
                    original_bytes = target.read_bytes()
                except OSError as exc:
                    raise PromoteApplyError(
                        f"could not read existing wiki file for backup: {paths.relative_to_root(target)}: {exc}"
                    ) from exc
                if original_bytes == new_bytes:
                    continue  # no-op
            planned.append(
                _PlannedWrite(
                    target=target,
                    new_content="",
                    original=None,
                    original_bytes=original_bytes,
                    new_bytes=new_bytes,
                    rel=rel_str,
                    is_text=False,
                )
            )

    _collect_md(stage_dir)
    _collect_plan_json(stage_dir)

    # Apply phase — write each file, tracking what we did so we can
    # roll back on any failure.
    applied: list[_PlannedWrite] = []
    try:
        for plan in planned:
            plan.target.parent.mkdir(parents=True, exist_ok=True)
            if plan.is_text:
                plan.target.write_text(plan.new_content, encoding="utf-8")
            else:
                assert plan.new_bytes is not None
                plan.target.write_bytes(plan.new_bytes)
            applied.append(plan)
    except OSError as exc:
        # Roll back every applied write before re-raising. Rollback
        # itself can fail (rare); we surface both errors.
        rollback_errors: list[str] = []
        for done in applied:
            try:
                if done.original is None and done.original_bytes is None:
                    # We created this file; remove it to restore the
                    # pre-commit state.
                    if done.target.exists():
                        done.target.unlink()
                elif done.is_text:
                    # We updated this text file; rewrite the original
                    # contents.
                    assert done.original is not None
                    done.target.write_text(done.original, encoding="utf-8")
                else:
                    # We updated this binary file; rewrite the original.
                    assert done.original_bytes is not None
                    done.target.write_bytes(done.original_bytes)
            except OSError as rb_exc:
                rollback_errors.append(f"rollback failed for {done.rel}: {rb_exc}")
        msg = (
            f"live wiki write failed for {planned[len(applied)].rel}: {exc}; rolled back {len(applied)} prior write(s)."
        )
        if rollback_errors:
            msg += " Rollback also raised: " + "; ".join(rollback_errors)
        raise PromoteApplyError(msg) from exc

    return [p.rel for p in applied]


def _archive_proposals_dir(proposals_dir: Path, paths: WikiPaths) -> Path:
    """Move the proposals dir into ``<proposals_dir>/.applied/``.

    The .applied/ subdir serves as an audit trail. Idempotent: a second call with the same
    dir is a no-op when the dir has already been archived.
    """
    applied_root = paths.applied_dir
    applied_root.mkdir(parents=True, exist_ok=True)
    target = applied_root / proposals_dir.name
    if target.exists():
        # Archived already; nothing to do.
        return target
    shutil.move(str(proposals_dir), str(target))
    return target


def _is_already_applied(proposals_dir: Path) -> bool:
    """True when proposals_dir lives under the proposals ``.applied/`` archive."""
    return APPLIED_DIR_NAME in proposals_dir.parts


def promote(
    proposals_dir: Path,
    paths: WikiPaths,
    dry_run: bool = False,
) -> PromoteResult:
    """Apply a proposals dir's patch-set to the wiki atomically.

    Parameters
    ----------
    proposals_dir : Path
        Directory containing plan.json + preview/<path>.md (output of
        Phase-1 ``wiki ingest``).
    paths : WikiPaths
        The resolved layout (wiki directory, proposals archive).
    dry_run : bool
        When True, build and validate the staged tree but do not
        commit to the wiki and do not move the proposals dir
        to .applied/.

    Returns
    -------
    PromoteResult
        Summary of what was applied (or would be applied, on dry-run).
    """
    if _is_already_applied(proposals_dir):
        # Idempotency: a second promote on an already-archived dir
        # is a no-op. Caller can detect via applied_paths == [].
        return PromoteResult(
            applied_paths=[],
            proposals_dir=proposals_dir,
            archived_dir=proposals_dir,
            dry_run=dry_run,
        )

    if not proposals_dir.is_dir():
        raise PromoteValidationError(f"proposals dir not found: {proposals_dir}")

    patch = _load_patch_from_dir(proposals_dir)
    if not patch.edits:
        # Empty patch-set (gate reject) — nothing to apply.
        archived: Path | None = None
        if not dry_run:
            archived = _archive_proposals_dir(proposals_dir, paths)
        return PromoteResult(
            applied_paths=[],
            proposals_dir=proposals_dir,
            archived_dir=archived,
            dry_run=dry_run,
        )

    with tempfile.TemporaryDirectory(prefix="wiki-stage-") as stage:
        stage_dir = Path(stage) / "wiki"
        _stage_wiki(paths, stage_dir)

        for edit in patch.edits:
            _apply_edit(stage_dir, edit)

        # Phase-3: stage the accepted-proposal archive AFTER the edit
        # loop and BEFORE validation so the validator sees the full tree
        # (including .audit/) and the existing atomic apply commits it.
        _stage_audit_archive(stage_dir, proposals_dir, patch)

        # Validation gate. Raises PromoteValidationError on any
        # failure; the wiki tree is unchanged because we haven't
        # committed yet.
        _validate_staged_tree(stage_dir, paths, patch)

        if dry_run:
            return PromoteResult(
                applied_paths=[e.path for e in patch.edits],
                proposals_dir=proposals_dir,
                archived_dir=None,
                dry_run=True,
            )

        applied = _commit_stage_to_wiki(stage_dir, paths)

    # Archive is post-commit and best-effort. The wiki is already
    # updated; failing to move the proposals dir is a curator-fixable
    # housekeeping issue, not a promote failure. Log and continue.
    try:
        archived = _archive_proposals_dir(proposals_dir, paths)
    except OSError:
        archived = None
    return PromoteResult(
        applied_paths=applied,
        proposals_dir=proposals_dir,
        archived_dir=archived,
        dry_run=False,
    )
