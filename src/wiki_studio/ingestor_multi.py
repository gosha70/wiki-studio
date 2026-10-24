# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# wiki-studio.ingestor_multi — Phase-1 multi-page ingest orchestrator.
#
# Stage 1's DefaultIngestor (in ingestor.py) reads ONE source and
# returns ONE IngestProposal. Phase 1's DefaultMultiIngestor reads ONE
# source PLUS the existing wiki state and returns a WikiPatchSet — a
# multi-page write plan that updates index.md, log.md, and the relevant
# existing/new pages.
#
# Pipeline:
#   1. Read source (raises SourceMissingError if missing).
#   2. Load WikiState (index.md + log.md + candidate pages).
#   3. compose_multi_prompt(source, wiki_state, schema files).
#   4. Backend invocation.
#   5. parse_patch_set_response (shape check).
#   6. Build WikiPatchSet.
#   7. validate_patch_set (set-level invariants).
#   8. Return WikiPatchSet — caller writes the proposals dir on disk.

from __future__ import annotations

import contextlib
import json
import os
import posixpath
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

from .errors import BackendInvocationError, ContractViolationError, SourceMissingError
from .fact_diff import removed_facts
from .paths import DEFAULT_LOCK_TIMEOUT
from .prompt import (
    compose_multi_prompt,
    load_schema_files,
    parse_patch_set_response,
)
from .proposal import (
    IngestRequest,
    PageEdit,
    WikiPatchSet,
    validate_page_edit_semantics,
    validate_patch_set,
)
from .wiki_state import load_wiki_state
from .wikilock import WikiLock, lock_path_for

if TYPE_CHECKING:
    from .ingestor import Backend
    from .paths import WikiPaths

# What ``write_patch_set_dir`` does when ``output_dir`` already exists: ``"error"`` raises
# ``FileExistsError`` (caller-selected names: ``api.propose``); ``"suffix"`` creates the
# next free ``<name>-2``, ``-3``, ... (generated names: ``ingest``, ``query --file-back``).
CollisionPolicy = Literal["error", "suffix"]
COLLISION_ERROR: CollisionPolicy = "error"
COLLISION_SUFFIX: CollisionPolicy = "suffix"


@runtime_checkable
class MultiIngestor(Protocol):
    """Public protocol: takes an IngestRequest, returns a WikiPatchSet."""

    def ingest_multi(self, request: IngestRequest) -> WikiPatchSet: ...


class DefaultMultiIngestor:
    """Default multi-page ingestor: source + wiki state → WikiPatchSet."""

    def __init__(self, backend: Backend, paths: WikiPaths) -> None:
        self._backend = backend
        self._paths = paths

    def ingest_multi(self, request: IngestRequest) -> WikiPatchSet:
        # 1. Read source.
        source_path = Path(request.source_path)
        if not source_path.exists():
            raise SourceMissingError(f"Source file not found or unreadable: {source_path}")
        try:
            source_content = source_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SourceMissingError(f"Cannot read source file {source_path}: {exc}") from exc

        # 2. Load wiki state. Empty state on a fresh repo is fine —
        #    the backend will treat missing pages as creates.
        wiki_state = load_wiki_state(
            paths=self._paths,
            source_path=source_path,
            source_content=source_content,
        )

        # 3. Compose prompt.
        schema_files = load_schema_files(self._paths)
        prompt_dict = compose_multi_prompt(
            source_path=source_path,
            source_content=source_content,
            schema_files=schema_files,
            wiki_state=wiki_state,
            source_kind=request.source_kind,
        )
        # WIKI_INGEST_TASK env override (parity with Stage-1 ingestor).
        # Multi-page gate-only is meaningful too: the backend can return
        # an empty edits list with rationale "gate rejected" without
        # drafting any pages.
        env_task = os.environ.get("WIKI_INGEST_TASK")
        if env_task:
            prompt_dict["task"] = env_task

        # 4. Backend.
        try:
            response = self._backend.call(prompt_dict)
        except BackendInvocationError:
            raise
        except Exception as exc:
            raise BackendInvocationError(f"Backend {request.backend_name!r} raised an unexpected error: {exc}") from exc

        # 5. Shape check.
        if isinstance(response, str):
            validated = parse_patch_set_response(response)
        else:
            validated = parse_patch_set_response(json.dumps(response))

        # 6. Build WikiPatchSet.
        edits: list[PageEdit] = []
        candidate_hashes = wiki_state.candidate_hashes
        for raw_edit in validated["edits"]:
            if not isinstance(raw_edit, dict):
                raise ContractViolationError(f"WikiPatchSet.edits[*] must be objects, got {type(raw_edit).__name__}")
            for required in ("path", "action", "new_content", "rationale"):
                if required not in raw_edit:
                    raise ContractViolationError(f"WikiPatchSet.edits[*] missing required key: {required!r}")
            action = str(raw_edit["action"])
            # The prompt labels wiki files "<label>/<path>"; a copied label is
            # removed here, exactly once, before per-edit validation (issue #11).
            # Targets of update/append edits already exist, which settles the
            # case where the wiki directory is named like a page directory.
            path = self._paths.strip_wiki_label(str(raw_edit["path"]), must_exist=action != "create")
            edits.append(
                PageEdit(
                    path=path,
                    action=raw_edit["action"],
                    new_content=str(raw_edit["new_content"]),
                    rationale=str(raw_edit["rationale"]),
                    # The base revision of an update is the hash of the bytes whose text
                    # the prompt showed (FR-007). It comes from the wiki state alone: a
                    # ``base_sha256`` in the backend's reply is ignored, and a page the
                    # prompt did not show gets none (the update is then unguarded).
                    base_sha256=candidate_hashes.get(path) if action == "update" else None,
                )
            )

        patch = WikiPatchSet(
            edits=edits,
            source_path=str(source_path),
            backend=request.backend_name,
            rationale=str(validated.get("rationale", "")),
        )

        # 7a. Per-edit semantic validation. Mirrors v1 two-layer
        #     validation at the per-edit grain so frontmatter mismatches,
        #     missing sources, root-only page types as create targets,
        #     and updates to non-existent pages all fail fast — before
        #     the curator sees a patch-set that would later fail the
        #     wiki linter at promote time.
        if patch.edits:
            per_edit_errors: list[str] = []
            for edit in patch.edits:
                per_edit_errors.extend(validate_page_edit_semantics(edit, self._paths))
            if per_edit_errors:
                raise ContractViolationError(
                    "WikiPatchSet failed per-edit semantic validation:\n  - " + "\n  - ".join(per_edit_errors)
                )

        # 7b. Set-level validation.
        # Empty edits is OK (gate reject); only fail if non-empty edits
        # have invariant violations.
        if patch.edits:
            errors = validate_patch_set(patch)
            if errors:
                raise ContractViolationError("WikiPatchSet failed set-level validation:\n  - " + "\n  - ".join(errors))

        return patch


def _create_patch_set_dir(output_dir: Path, on_collision: CollisionPolicy) -> Path:
    """Create the proposal directory exclusively (``exist_ok=False``) and return the one created.

    A proposal directory is never reused: a second writer must not overwrite
    a proposal that may be mid-promotion. With ``"suffix"`` an existing
    directory makes this one ``<name>-2``, ``-3``, ...; with ``"error"`` the
    ``FileExistsError`` propagates.
    """
    if on_collision == COLLISION_ERROR:
        output_dir.mkdir(parents=True, exist_ok=False)
        return output_dir
    candidate, suffix = output_dir, 2
    while True:
        try:
            candidate.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            candidate = output_dir.with_name(f"{output_dir.name}-{suffix}")
            suffix += 1
            continue
        return candidate


def write_patch_set_dir(
    patch: WikiPatchSet,
    output_dir: Path,
    wiki_dir: Path | None = None,
    *,
    on_collision: CollisionPolicy = COLLISION_ERROR,
    lock_timeout: float | None = None,
    lock: WikiLock | None = None,
) -> Path:
    """Write a WikiPatchSet to disk under output_dir.

    Layout:
        <output_dir>/
            plan.json                    — full patch-set as JSON; an edit's ``base_sha256``
                                           is written when the PageEdit carries one
            preview/<edit.path>          — one preview file per edit (path normalised); a second,
                                           third ... edit to the same path (several
                                           append-index or append-log lines) gets
                                           preview/<edit.path>.2, .3, ... so no
                                           edit's content overwrites another's

    With ``wiki_dir``, an ``update`` edit whose live page exists gets
    ``fact_warnings`` in plan.json: the citations, backticked identifiers and
    numbers with units the new content drops (fact_diff.removed_facts). The
    key is written only when the list is non-empty. When the live page cannot
    be read or decoded, ``fact_check_error`` records why and no comparison
    is claimed. Promote ignores both keys.

    The directory is created exclusively (``exist_ok=False``), under the wiki
    lock when ``wiki_dir`` is given, so no writer ever writes into an existing
    proposal directory. ``on_collision`` says what an existing ``output_dir``
    means: ``"error"`` (the default, for caller-selected names) lets the
    ``FileExistsError`` propagate; ``"suffix"`` (generated names) creates the
    next free ``<name>-2``, ``-3``, ... instead. ``lock_timeout`` defaults to
    the package default (``paths.DEFAULT_LOCK_TIMEOUT``). A caller that
    already holds the wiki lock passes it as ``lock`` (it must be held and
    be this wiki's), so one lock covers the proposal files and whatever the
    caller publishes next (snapshot, audit record); no second lock is taken.

    Returns the absolute path of the directory actually created.
    Raises OSError if the filesystem operations fail; the caller maps
    to OutputWriteError exit code 6.
    """
    timeout = DEFAULT_LOCK_TIMEOUT if lock_timeout is None else lock_timeout
    held: contextlib.AbstractContextManager[object]
    if lock is not None:
        if wiki_dir is None or not lock.held or lock.lock_path != lock_path_for(wiki_dir):
            raise ValueError("write_patch_set_dir: `lock` must be the held WikiLock of `wiki_dir`")
        held = contextlib.nullcontext()
    else:
        held = WikiLock(wiki_dir, timeout) if wiki_dir is not None else contextlib.nullcontext()
    with held:
        output_dir = _create_patch_set_dir(output_dir, on_collision)
        return _write_patch_set_files(patch, output_dir, wiki_dir)


def _write_patch_set_files(patch: WikiPatchSet, output_dir: Path, wiki_dir: Path | None) -> Path:
    """Fill a freshly created proposal directory (see :func:`write_patch_set_dir`)."""
    preview_dir = output_dir / "preview"
    preview_dir.mkdir(exist_ok=True)

    # Issue #18: one preview file per edit, not per path. plan.json points each
    # edit at its own file, and promote reads the pointer, so order is kept.
    # Issue #23: count by normalised path, so equivalent spellings of one file
    # (index.md, ./index.md) never share a preview file.
    seen: dict[str, int] = {}
    preview_rels: list[str] = []
    for edit in patch.edits:
        key = posixpath.normpath(edit.path)
        seen[key] = seen.get(key, 0) + 1
        n = seen[key]
        preview_rels.append(f"preview/{key}" if n == 1 else f"preview/{key}.{n}")

    plan_edits: list[dict[str, object]] = []
    for e, rel in zip(patch.edits, preview_rels, strict=True):
        # new_content is stored in the preview file; the plan.json stays
        # small + grep-friendly. Curator reads the preview to see the full content.
        entry: dict[str, object] = {"path": e.path, "action": e.action, "rationale": e.rationale, "preview": rel}
        if e.base_sha256 is not None:
            # Written only when the author supplied it; never filled from the live page here.
            entry["base_sha256"] = e.base_sha256
        live = wiki_dir / e.path if wiki_dir is not None else None
        if e.action == "update" and live is not None and live.is_file():
            # The check is advisory: a live page that cannot be read or decoded is
            # reported as "not compared" and never blocks the proposal.
            try:
                old_content = live.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                entry["fact_check_error"] = "live page not readable: not valid UTF-8"
            except OSError as exc:
                # The plan is archived into the wiki on promote: record the error kind, not a machine path.
                entry["fact_check_error"] = f"live page not readable: {exc.strerror or type(exc).__name__}"
            else:
                warnings = removed_facts(old_content, e.new_content)
                if warnings:
                    entry["fact_warnings"] = warnings
        plan_edits.append(entry)
    plan = {
        "version": 1,
        "source_path": patch.source_path,
        "backend": patch.backend,
        "rationale": patch.rationale,
        "edits": plan_edits,
    }
    (output_dir / "plan.json").write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    for edit, rel in zip(patch.edits, preview_rels, strict=True):
        # preview/<path> replicates the wiki's directory shape so the curator
        # can diff against the live wiki later.
        preview_path = output_dir / rel
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.write_text(edit.new_content, encoding="utf-8")
    return output_dir.resolve()
