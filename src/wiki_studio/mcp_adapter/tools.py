# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The eight MCP tools (FR-035..FR-040): each one call into :mod:`wiki_studio.api`, each result a JSON object.

Standard library only: :mod:`.server` registers these methods with the SDK
and turns their results and errors into tool results. The layout, the actor
and the default ranker come from the launch configuration; no tool takes a
root, directory, backend, actor or escape-hatch argument, and none reaches a
model (``lint`` passes ``backend=None``).
"""

from __future__ import annotations

import datetime
import importlib.metadata
import secrets
import threading
import warnings
from typing import TYPE_CHECKING, Any

from .. import __version__, api
from ..contract import POLICY_AUTO_APPROVE_ON_PROMOTE
from ..discovery import DEFAULT_MAX_CONTEXT_BYTES, RANKER_SOURCE_FLAG, resolve_ranker
from ..errors import DriftWarning, IngestError
from ..promoter import PROMOTE_ENTRY_POINT_MCP
from ..querier import DEFAULT_MAX_QUERY_PAGES
from .config import (
    TOOL_FIND,
    TOOL_FINDINGS,
    TOOL_INFO,
    TOOL_LINT,
    TOOL_PROMOTE,
    TOOL_PROPOSE,
    TOOL_READ_PAGE,
    TOOL_REVIEW_STATE,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from .config import LaunchConfig

MIN_FIND_PAGES = 1
PROPOSE_SOURCE = "mcp"
PROPOSE_BACKEND = "mcp"
PROPOSAL_NAME_PREFIX = "mcp"
PROPOSAL_NAME_TIME_FORMAT = "%Y%m%dT%H%M%SZ"
PROPOSAL_NAME_HEX_BYTES = 4
SDK_DISTRIBUTION = "mcp"
INTERNAL_ERROR = "InternalError"
VALUE_ERROR_EXIT_CODE = 1

# The keys of one ``propose`` edit; ``base_sha256`` is optional.
EDIT_PATH = "path"
EDIT_ACTION = "action"
EDIT_CONTENT = "content"
EDIT_BASE_SHA256 = "base_sha256"
_EDIT_REQUIRED = (EDIT_PATH, EDIT_ACTION, EDIT_CONTENT)
_EDIT_KEYS = frozenset((*_EDIT_REQUIRED, EDIT_BASE_SHA256))

# warnings.catch_warnings is process-wide; tool calls run on worker threads.
_WARNINGS_LOCK = threading.Lock()


def error_payload(exc: BaseException) -> dict[str, Any]:
    """``{error, exit_code, message}`` for a tool error result (FR-040).

    An ``IngestError`` carries its class's exit code and ``ValueError`` is 1,
    both with the message; anything else is ``InternalError`` with the class
    name only, so no traceback or path reaches the client.
    """
    if isinstance(exc, IngestError):
        return {"error": type(exc).__name__, "exit_code": exc.exit_code, "message": str(exc)}
    if isinstance(exc, ValueError):
        return {"error": type(exc).__name__, "exit_code": VALUE_ERROR_EXIT_CODE, "message": str(exc)}
    return {"error": INTERNAL_ERROR, "exit_code": VALUE_ERROR_EXIT_CODE, "message": type(exc).__name__}


def default_proposal_name() -> str:
    """``mcp-<UTC yyyymmddThhmmssZ>-<8 hex>``."""
    stamp = datetime.datetime.now(datetime.UTC).strftime(PROPOSAL_NAME_TIME_FORMAT)
    return f"{PROPOSAL_NAME_PREFIX}-{stamp}-{secrets.token_hex(PROPOSAL_NAME_HEX_BYTES)}"


def sdk_version() -> str | None:
    """The installed ``mcp`` distribution's version, or None without the extra."""
    try:
        return importlib.metadata.version(SDK_DISTRIBUTION)
    except importlib.metadata.PackageNotFoundError:
        return None


def _page_edit(index: int, edit: object, rationale: str) -> api.PageEdit:
    """One ``{path, action, content, base_sha256?}`` object as a :class:`~wiki_studio.api.PageEdit`."""
    if not isinstance(edit, dict):
        raise ValueError(f"edits[{index}] must be an object with {', '.join(_EDIT_REQUIRED)}")
    unknown = sorted(set(edit) - _EDIT_KEYS)
    if unknown:
        raise ValueError(f"edits[{index}] has unknown keys: {', '.join(unknown)}")
    missing = [key for key in _EDIT_REQUIRED if not isinstance(edit.get(key), str)]
    if missing:
        raise ValueError(f"edits[{index}] needs string values for: {', '.join(missing)}")
    base = edit.get(EDIT_BASE_SHA256)
    if base is not None and not isinstance(base, str):
        raise ValueError(f"edits[{index}].{EDIT_BASE_SHA256} must be a string")
    return api.PageEdit(
        path=edit[EDIT_PATH],
        action=edit[EDIT_ACTION],
        new_content=edit[EDIT_CONTENT],
        rationale=rationale,
        base_sha256=base,
    )


class WikiTools:
    """The tool implementations over one launch configuration.

    ``protocol_version`` reports the negotiated MCP protocol version (None
    before initialisation) for ``info``'s ``adapter``.
    """

    def __init__(self, config: LaunchConfig, *, protocol_version: Callable[[], str | None] = lambda: None) -> None:
        self.config = config
        self._protocol_version = protocol_version

    def registry(self) -> dict[str, Callable[..., dict[str, Any]]]:
        """The live tools by name, in surface order (``--disable-tool`` already applied)."""
        every: dict[str, Callable[..., dict[str, Any]]] = {
            TOOL_FIND: self.find,
            TOOL_READ_PAGE: self.read_page,
            TOOL_PROPOSE: self.propose,
            TOOL_PROMOTE: self.promote,
            TOOL_LINT: self.lint,
            TOOL_INFO: self.info,
            TOOL_FINDINGS: self.findings,
            TOOL_REVIEW_STATE: self.review_state,
        }
        return {name: every[name] for name in self.config.tools}

    def _relative(self, path: Path | None) -> str | None:
        return None if path is None else self.config.paths.relative_to_root(path)

    def find(
        self,
        question: str,
        max_pages: int = DEFAULT_MAX_QUERY_PAGES,
        max_bytes: int = DEFAULT_MAX_CONTEXT_BYTES,
        ranker: str | None = None,
    ) -> dict[str, Any]:
        """Select the pages to read for a question, without a model.

        index.md first, then at most max_pages (1..5) index-linked pages within
        max_bytes, ranked by `ranker` (fts5 or index-first; default: the
        server's). Returns the `find --json` object.
        """
        if isinstance(max_pages, bool) or not isinstance(max_pages, int):
            raise ValueError(f"max_pages must be an integer from {MIN_FIND_PAGES} to {DEFAULT_MAX_QUERY_PAGES}")
        if not MIN_FIND_PAGES <= max_pages <= DEFAULT_MAX_QUERY_PAGES:
            raise ValueError(f"max_pages must be from {MIN_FIND_PAGES} to {DEFAULT_MAX_QUERY_PAGES}, got {max_pages}")
        chosen = resolve_ranker(ranker)[0] if ranker is not None and ranker.strip() else self.config.ranker
        result = api.find(question, self.config.paths, max_pages=max_pages, max_bytes=max_bytes, ranker=chosen)
        return result.as_dict(self.config.paths)

    def read_page(self, path: str) -> dict[str, Any]:
        """Read one wiki page (a wiki-relative path) once: its text and the sha256 an update records as base_sha256."""
        result = api.read_page(path, self.config.paths)
        return {"path": result.path, "sha256": result.sha256, "content": result.text}

    def propose(self, edits: list[dict[str, Any]], name: str | None = None, rationale: str = "") -> dict[str, Any]:
        """Write edits as a proposal under the proposals directory; the wiki is not touched.

        Each edit is {path, action, content, base_sha256?} with action create,
        update, append-index or append-log; an update carries read_page's
        sha256. Every create gets a page_id. `name` defaults to
        mcp-<utc>-<hex>. Promote it with the promote tool, or leave it for a
        person.
        """
        if not isinstance(edits, list):
            raise ValueError("edits must be a list of objects")
        page_edits = [_page_edit(i, edit, rationale) for i, edit in enumerate(edits)]
        chosen = default_proposal_name() if name is None else name
        with _WARNINGS_LOCK, warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DriftWarning)
            written = api.propose(
                page_edits,
                self.config.paths,
                name=chosen,
                source=PROPOSE_SOURCE,
                rationale=rationale,
                backend=PROPOSE_BACKEND,
                by=self.config.launch_by,
                assign_page_ids=True,
            )
        drift = []
        for warning in caught:
            if issubclass(warning.category, DriftWarning):
                drift.append(str(warning.message))
            else:
                warnings.showwarning(warning.message, warning.category, warning.filename, warning.lineno)
        return {"name": chosen, "proposal_dir": self._relative(written), "warnings": drift}

    def promote(self, name: str, dry_run: bool = False) -> dict[str, Any]:
        """Apply the proposal `name` (one path component under the proposals directory) to the wiki.

        Lint-gated, under the wiki lock; an update whose page changed since
        read_page is refused. On a wiki whose policy sets
        auto_approve_on_promote the promoted pages are approved by that policy
        and listed in approved_paths.
        """
        api.check_proposal_name(name)
        result = api.promote(
            self.config.paths.proposals_dir / name,
            self.config.paths,
            dry_run=dry_run,
            entry_point=PROMOTE_ENTRY_POINT_MCP,
            by=self.config.launch_by,
        )
        notes = list(result.warnings)
        if result.approved_paths:
            actor = self.config.actor
            notes.append(
                f"policy {POLICY_AUTO_APPROVE_ON_PROMOTE}: {', '.join(result.approved_paths)} approved by policy as "
                f"part of this promotion, attributed to the server's actor {actor.name or '(unnamed)'} "
                f"(source {actor.source})"
            )
        return {
            "applied_paths": list(result.applied_paths),
            "archived_dir": self._relative(result.archived_dir),
            "dry_run": result.dry_run,
            "unguarded_paths": list(result.unguarded_paths),
            "warnings": notes,
            "approved_paths": list(result.approved_paths),
        }

    def lint(self, health: bool = False, prose: bool = False, strict: bool = False) -> dict[str, Any]:
        """Structural lint and the audit-format pass; health and prose add their checks. Never calls a model."""
        result = api.lint(self.config.paths, health=health, prose=prose, strict=strict, backend=None)
        return {
            "violations": list(result.violations),
            "pages_checked": result.pages_checked,
            "audit_errors": list(result.audit_errors),
            "health": None
            if result.health is None
            else {
                "pages_checked": result.health.pages_checked,
                "findings": [
                    {"kind": f.kind, "severity": f.severity, "pages": list(f.pages), "description": f.description}
                    for f in result.health.findings
                ],
            },
            "prose": None
            if result.prose is None
            else {
                "pages_checked": result.prose.pages_checked,
                "findings": [
                    {"path": f.path, "line": f.line, "check": f.check, "message": f.message}
                    for f in result.prose.findings
                ],
            },
            "passed": result.passed,
        }

    def info(self) -> dict[str, Any]:
        """The build's and the wiki's knowledge contract, discovery, and this server's adapter settings."""
        data = api.info(self.config.paths).as_dict()
        if self.config.ranker_source == RANKER_SOURCE_FLAG and isinstance(data.get("discovery"), dict):
            data["discovery"]["default_ranker"] = self.config.ranker
            data["discovery"]["default_ranker_source"] = RANKER_SOURCE_FLAG
        data["adapter"] = {
            "adapter_version": __version__,
            "sdk_version": sdk_version(),
            "protocol_version": self._protocol_version(),
            "tools": list(self.config.tools),
            "actor": self.config.actor.as_dict(),
            "ranker": {"name": self.config.ranker, "source": self.config.ranker_source},
            "disabled_tools": list(self.config.disabled_tools),
        }
        return data

    def findings(self, pages: list[str] | None = None) -> dict[str, Any]:
        """What needs a curator's attention, from code that calls no model; `pages` scopes it."""
        return api.findings(self.config.paths, pages=pages).as_dict()

    def review_state(self, pages: list[str] | None = None) -> dict[str, Any]:
        """Each page's review state from its verified approval records; `pages` scopes it."""
        states = api.review_state(self.config.paths, pages=pages)
        return {
            "states": [
                {
                    "path": s.path,
                    "page_key": s.page_key,
                    "state": s.state,
                    "reason": s.reason,
                    "live_sha256": s.live_sha256,
                    "approved_sha256": s.approved_sha256,
                    "record_path": s.record_path,
                    "warnings": list(s.warnings),
                }
                for s in states
            ]
        }
