# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wiki_studio.nightly — the propose-only curation pass and its report (FR-001).

One run reads the wiki and says what a curator should look at:

* structural lint (no health tier, no prose, not strict) and its audit-format
  errors (:func:`wiki_studio.api.lint`);
* the model-free findings (:func:`wiki_studio.api.findings`), with their
  counts by kind;
* the proposal directories still pending under the proposals directory.

With an explicit backend it then drafts at most ``max_proposals`` proposals
for the two kinds whose fix adds a link (``missing-cross-link`` and a
``weak-orphan`` not linked from ``index.md``), each written through
:func:`wiki_studio.api.propose`, and each refused unless the syntactic
:func:`link_only_problems` check shows it adds links and changes nothing else
(FR-019). It never promotes, approves or writes in the wiki directory; the
only lock it takes is the one ``api.propose`` takes per call.
"""

from __future__ import annotations

import contextlib
import datetime
import hashlib
import json
import os
import posixpath
import re
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from . import __version__, yaml_lite
from .contract import NIGHTLY_FORMAT_VERSION, check_write_contract
from .errors import (
    BackendInvocationError,
    ContractViolationError,
    DriftWarning,
    IngestError,
    OutputWriteError,
    PromoteApplyError,
)
from .findings import KIND_MISSING_CROSS_LINK, KIND_WEAK_ORPHAN
from .health_lint import _intra_wiki_links_from
from .lint import INDEX_NAME, LOG_NAME
from .prompt import compose_curate_prompt, load_schema_files, parse_patch_set_response
from .proposal import (
    PageAction,
    PageEdit,
    WikiPatchSet,
    check_reserved_edits,
    validate_page_edit_semantics,
    validate_patch_set,
)
from .prose_lint import closes_fence, open_fence
from .revisions import SUMMARY_PREFIX

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .api import LintResult, ReadResult
    from .findings import Finding, FindingsResult
    from .ingestor import Backend
    from .paths import WikiPaths

REPORT_TITLE = "# wiki-studio nightly report"

# The exit code of a run whose structural lint failed (FR-004, FR-010).
EXIT_LINT_FAILED = 1

# The deterministic proposal name (FR-015): nightly-<kind>-<first 12 hex of the key>.
NIGHTLY_PROPOSAL_PREFIX = "nightly-"
NIGHTLY_KEY_LENGTH = 12

# The default proposal cap and the derived attempt bound (FR-016).
DEFAULT_MAX_PROPOSALS = 5
ATTEMPTS_PER_PROPOSAL = 2

# The verbs a nightly log line may use (FR-019).
NIGHTLY_LOG_VERBS: tuple[str, ...] = ("link",)

# Drafting states and the reasons the report and the JSON form record (FR-022).
DRAFTING_OFF = "off"
DRAFTING_SKIPPED = "skipped"
DRAFTING_ON = "on"
DRAFTING_STOPPED = "stopped"
REASON_NO_BACKEND = "no --backend"
REASON_NO_PROPOSALS = "--max-proposals 0"
REASON_LINT_FAILED = "structural lint failed"
REASON_WRITE_FAILED = "write failed"
REASON_LOCK_TIMEOUT = "lock timeout"
SKIPPED_SCHEMA_CONTRACT = "drafting skipped: schema contract"

# One inline link (FR-019): group 1 the text, group 2 the target; an image is not a link.
INLINE_LINK_RE = re.compile(r"(?<!!)\[([^\[\]\n]*)\]\(([^()\s]+)\)")
_BACKTICK_RUN_RE = re.compile(r"`+")
# FR-019's fixed log-line form: '- <date> — <verb> <slug> (<page-type>): <why>'.
_LOG_LINE_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2}) — (\S+) (\S+) \(([^()\n]+)\): (\S.*)$")
_LOG_LINE_FORBIDDEN = ("](", "][", "<http", "://")


@dataclass(frozen=True)
class PendingProposal:
    """One proposal directory still pending: its ``name`` and its ``edits`` count (None when unknown)."""

    name: str
    edits: int | None

    def as_dict(self) -> dict[str, Any]:
        """``{"name", "edits"}`` as the JSON form records it (FR-006); ``edits`` is null when unreadable."""
        return {"name": self.name, "edits": self.edits}


@dataclass(frozen=True)
class DraftingState:
    """What one run did with drafting, and why (FR-002, FR-022)."""

    state: str
    reason: str | None
    backend: str | None
    max_proposals: int | None
    max_attempts: int | None
    attempts: int
    created: int

    def as_dict(self) -> dict[str, Any]:
        """The ``drafting`` object of ``--json`` (FR-002)."""
        return {
            "state": self.state,
            "reason": self.reason,
            "backend": self.backend,
            "max_proposals": self.max_proposals,
            "max_attempts": self.max_attempts,
            "attempts": self.attempts,
            "created": self.created,
        }

    def summary(self) -> str:
        """The one-line state the report shows (FR-022)."""
        if self.state == DRAFTING_ON:
            bounds = (
                f"{self.created} of {self.max_proposals} proposals, {self.attempts} of {self.max_attempts} attempts"
            )
            return f"on (backend {self.backend}; {bounds})"
        if self.state == DRAFTING_OFF:
            return f"off ({_collapse(self.reason or '')})"
        if self.state == DRAFTING_STOPPED:
            return f"stopped ({_collapse(self.reason or '')})"
        return f"skipped ({_collapse(self.reason or '')})"


@dataclass(frozen=True)
class CreatedProposal:
    """One proposal directory this run created (FR-022)."""

    name: str
    path: str
    kind: str
    pages: tuple[str, ...]
    edits: tuple[tuple[str, str], ...]
    fact_warnings: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "kind": self.kind,
            "pages": list(self.pages),
            "edits": [{"action": action, "path": path} for action, path in self.edits],
            "fact_warnings": self.fact_warnings,
        }


@dataclass(frozen=True)
class AlreadyProposed:
    """A draftable finding whose proposal directory was already pending (FR-025, FR-026)."""

    name: str
    kind: str
    pages: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "kind": self.kind, "pages": list(self.pages)}


@dataclass(frozen=True)
class NotDraftedProposal:
    """A draftable finding this run did not draft, and why (FR-022)."""

    name: str
    kind: str
    pages: tuple[str, ...]
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "kind": self.kind, "pages": list(self.pages), "reason": self.reason}


@dataclass(frozen=True)
class FailedDraft:
    """A draft this run attempted and refused or failed (FR-022)."""

    name: str
    kind: str
    pages: tuple[str, ...]
    reason: str
    exit_code: int
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "pages": list(self.pages),
            "reason": self.reason,
            "exit_code": self.exit_code,
            "message": self.message,
        }


@dataclass(frozen=True)
class NightlyResult:
    """One pass: what it found, what it drafted, what needs a curator and the report (FR-002).

    ``lint`` is the structural result (audit-format errors included), ``findings``
    the full model-free findings, ``needs_curator`` the findings the report lists
    for a person and ``pending`` the proposal directories still waiting.
    ``drafting`` says what drafting did; ``created``, ``already_proposed``,
    ``not_drafted`` and ``failed`` carry FR-022's proposal entries. ``exit_code``
    applies FR-010 (2)-(6); the CLI applies (1), the report write, after writing
    the report.
    """

    run_at: str
    package_version: str
    wiki_dir: Path
    proposals_dir: Path
    lint: LintResult
    findings: FindingsResult
    needs_curator: tuple[Finding, ...]
    pending: tuple[PendingProposal, ...]
    warnings: tuple[str, ...]
    drafting: DraftingState
    exit_code: int
    created: tuple[CreatedProposal, ...] = ()
    already_proposed: tuple[AlreadyProposed, ...] = ()
    not_drafted: tuple[NotDraftedProposal, ...] = ()
    failed: tuple[FailedDraft, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """The JSON form (``nightly_version: 1``); consumers read keys by name, not by order (FR-002)."""
        return {
            "nightly_version": NIGHTLY_FORMAT_VERSION,
            "package_version": self.package_version,
            "run_at": self.run_at,
            "wiki_dir": str(self.wiki_dir),
            "proposals_dir": str(self.proposals_dir),
            "lint": {
                "passed": self.lint.passed,
                "violations": list(self.lint.violations),
                "audit_errors": list(self.lint.audit_errors),
            },
            "findings": self.findings.as_dict(),
            "drafting": self.drafting.as_dict(),
            "proposals": {
                "created": [proposal.as_dict() for proposal in self.created],
                "already_proposed": [entry.as_dict() for entry in self.already_proposed],
                "not_drafted": [entry.as_dict() for entry in self.not_drafted],
                "failed": [entry.as_dict() for entry in self.failed],
            },
            "needs_curator": {
                "findings": [finding.as_dict() for finding in self.needs_curator],
                "pending": [pending.as_dict() for pending in self.pending],
            },
            "warnings": list(self.warnings),
            "exit_code": self.exit_code,
        }

    def render_markdown(self) -> str:
        """The report: fixed headings in order, every empty part saying so (FR-003)."""
        lines = [
            REPORT_TITLE,
            "",
            f"- Run time (UTC): {self.run_at}",
            f"- Wiki directory: {self.wiki_dir}",
            f"- Proposals directory: {self.proposals_dir}",
            f"- Package version: {self.package_version}",
            f"- Drafting: {self.drafting.summary()}",
            f"- Revision check: {self.findings.revision_check.summary().removeprefix(SUMMARY_PREFIX)}",
            "",
            "## Lint",
            "",
            *self._lint_lines(),
            "",
            "## Findings",
            "",
            *self._finding_lines(),
            "",
            "## Proposals",
            "",
            f"Drafting: {self.drafting.summary()}",
            "",
            "### Created",
            "",
            *self._created_lines(),
            "",
            "### Already proposed",
            "",
            *self._already_proposed_lines(),
            "",
            "### Not drafted",
            "",
            *self._not_drafted_lines(),
            "",
            "### Failed",
            "",
            *self._failed_lines(),
            "",
            "## Needs a curator",
            "",
            "### Findings",
            "",
            *self._curator_lines(),
            "",
            "### Pending proposals",
            "",
            *self._pending_lines(),
        ]
        return "\n".join(lines) + "\n"

    def exit_reason(self) -> str | None:
        """One line naming the cause of a non-zero exit, for stderr (FR-010); None for exit 0."""
        if self.exit_code == 0:
            return None
        if self.drafting.state == DRAFTING_STOPPED:
            return f"drafting stopped: {_collapse(self.drafting.reason or '')}"
        if not self.lint.passed:
            return "structural lint failed; no proposal was drafted"
        if self.failed:
            first = self.failed[0]
            return f"{first.reason} ({first.kind}: {', '.join(first.pages)}): {_collapse(first.message)}"
        if self.drafting.state == DRAFTING_SKIPPED:
            return f"drafting skipped: {_collapse(self.drafting.reason or '')}"
        return None

    def _lint_lines(self) -> list[str]:
        if not self.lint.violations and not self.lint.audit_errors:
            return ["clean"]
        lines: list[str] = []
        if self.lint.violations:
            lines.append("Lint failed with structural violations:")
            lines.extend(f"- {violation}" for violation in self.lint.violations)
        else:
            lines.append("Lint passed.")
        if self.lint.audit_errors:
            if self.lint.violations:
                lines.append("")
            lines.append("Audit-format errors (reported; they do not fail lint):")
            lines.extend(f"- {error}" for error in self.lint.audit_errors)
        return lines

    def _finding_lines(self) -> list[str]:
        if not self.findings.findings:
            return ["none"]
        counts = ", ".join(f"{kind} {count}" for kind, count in self.findings.counts.items() if count)
        lines = [f"Counts: {counts}", ""] if counts else []
        lines.extend(
            f"- [{finding.kind} / {finding.severity}] {', '.join(finding.pages)}: {finding.description}"
            for finding in self.findings.findings
        )
        return lines

    def _created_lines(self) -> list[str]:
        if not self.created:
            return ["none"]
        lines: list[str] = []
        for proposal in self.created:
            lines.append(f"- {proposal.name}  {proposal.path}")
            lines.extend(f"  - {action} {path}" for action, path in proposal.edits)
            lines.append(f"  - fact warnings: {proposal.fact_warnings}")
        return lines

    def _already_proposed_lines(self) -> list[str]:
        if not self.already_proposed:
            return ["none"]
        return [f"- [{entry.kind}] {', '.join(entry.pages)}: {entry.name}" for entry in self.already_proposed]

    def _not_drafted_lines(self) -> list[str]:
        if not self.not_drafted:
            return ["none"]
        return [f"- [{entry.kind}] {', '.join(entry.pages)}: {entry.reason}" for entry in self.not_drafted]

    def _failed_lines(self) -> list[str]:
        if not self.failed:
            return ["none"]
        return [
            f"- [{entry.kind}] {', '.join(entry.pages)}: {entry.reason} (exit {entry.exit_code}): "
            f"{_collapse(entry.message)}"
            for entry in self.failed
        ]

    def _curator_lines(self) -> list[str]:
        if not self.needs_curator:
            return ["none"]
        return [f"- [{finding.kind}] {', '.join(finding.pages)}" for finding in self.needs_curator]

    def _pending_lines(self) -> list[str]:
        if not self.pending:
            return ["none"]
        return [
            f"- {pending.name} (edits: {pending.edits})"
            if pending.edits is not None
            else f"- {pending.name} (edits unknown)"
            for pending in self.pending
        ]


# ── names, links and code regions (FR-015, FR-019) ────────────


def proposal_name(kind: str, pages: Sequence[str]) -> str:
    """The deterministic proposal name ``nightly-<kind>-<key>`` (FR-015)."""
    from . import api  # deferred: api imports this module's result type

    digest = hashlib.sha256((kind + "\n" + "\n".join(sorted(pages))).encode("utf-8")).hexdigest()
    name = f"{NIGHTLY_PROPOSAL_PREFIX}{kind}-{digest[:NIGHTLY_KEY_LENGTH]}"
    api.check_proposal_name(name)
    return name


def resolve_link_target(page: str, target: str) -> str | None:
    """The wiki path an inline link on ``page`` points at, or None for a URL, an absolute path or a bare fragment."""
    fragmentless = target.split("#", 1)[0]
    if not fragmentless or fragmentless.startswith("/") or ":" in fragmentless:
        return None
    return posixpath.normpath(posixpath.join(posixpath.dirname(page), fragmentless))


def strip_links_to(text: str, page: str, target: str) -> str:
    """``text`` with every inline link resolving to ``target`` replaced by its text (FR-019)."""

    def replace(match: re.Match[str]) -> str:
        return match.group(1) if resolve_link_target(page, match.group(2)) == target else match.group(0)

    return INLINE_LINK_RE.sub(replace, text)


def count_links_to(text: str, page: str, target: str) -> int:
    """How many inline links on ``page`` resolve to ``target`` (FR-019)."""
    return sum(1 for match in INLINE_LINK_RE.finditer(text) if resolve_link_target(page, match.group(2)) == target)


def _inline_code_spans(line: str) -> list[tuple[int, int]]:
    """Inline code spans on one line of prose, as (start, end) offsets; an unclosed run makes the rest code."""
    spans: list[tuple[int, int]] = []
    position = 0
    while True:
        opening = _BACKTICK_RUN_RE.search(line, position)
        if opening is None:
            return spans
        length = len(opening.group(0))
        closing = next(
            (run for run in _BACKTICK_RUN_RE.finditer(line, opening.end()) if len(run.group(0)) == length),
            None,
        )
        if closing is None:
            spans.append((opening.start(), len(line)))
            return spans
        spans.append((opening.start(), closing.end()))
        position = closing.end()


def code_regions(text: str) -> list[tuple[int, int]]:
    """Every code region of ``text`` as (start, end) offsets (FR-019).

    A fenced code block runs from its opening fence to its closing fence
    (``prose_lint.open_fence`` / ``closes_fence``; an unclosed fence runs to
    the end of the text); elsewhere each inline code span is a region.
    """
    regions: list[tuple[int, int]] = []
    offset = 0
    fence: str | None = None
    fence_start = 0
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        if fence is not None:
            if closes_fence(body, fence):
                regions.append((fence_start, offset + len(body)))
                fence = None
            offset += len(line)
            continue
        opened = open_fence(body)
        if opened is not None:
            fence, fence_start = opened, offset
            offset += len(line)
            continue
        regions.extend((offset + start, offset + end) for start, end in _inline_code_spans(body))
        offset += len(line)
    if fence is not None:
        regions.append((fence_start, len(text)))
    return regions


def _starts_in_regions(offset: int, regions: Sequence[tuple[int, int]]) -> bool:
    return any(start <= offset < end for start, end in regions)


@dataclass(frozen=True)
class _DraftEdit:
    """One edit a backend returned, after the wiki label was copied off its path."""

    path: str
    action: str
    new_content: str
    rationale: str


class _OutOfBoundsError(Exception):
    """A draft FR-019 refuses; ``problems`` are ``<path>: <rule>`` strings, the first the recorded reason."""

    def __init__(self, problems: Sequence[str]) -> None:
        super().__init__(problems[0] if problems else "")
        self.problems = tuple(problems)


def _one_line(content: str) -> str | None:
    """``content`` without one optional trailing newline, or None when more than one line remains."""
    entry = content[:-2] if content.endswith("\r\n") else content[:-1] if content.endswith("\n") else content
    return None if "\n" in entry or "\r" in entry else entry


def _frontmatter(text: str) -> dict[str, Any]:
    try:
        return yaml_lite.parse_frontmatter(text)
    except ContractViolationError:
        return {}


def _update_problems(edit: _DraftEdit, canonical: str, original: str) -> list[str]:
    """FR-019's per-page link-only check: the added link(s), outside code, from existing words only."""
    problems: list[str] = []
    regions = code_regions(edit.new_content)
    if count_links_to(edit.new_content, edit.path, canonical) <= count_links_to(original, edit.path, canonical):
        problems.append(f"{edit.path}: adds no link")
    for match in INLINE_LINK_RE.finditer(edit.new_content):
        if resolve_link_target(edit.path, match.group(2)) != canonical:
            continue
        if _starts_in_regions(match.start(), regions):
            problems.append(f"{edit.path}: link inside code")
            continue
        if not match.group(1).strip():
            problems.append(f"{edit.path}: empty link text")
    stripped_draft = strip_links_to(edit.new_content, edit.path, canonical)
    stripped_original = strip_links_to(original, edit.path, canonical)
    if stripped_draft.encode("utf-8") != stripped_original.encode("utf-8"):
        problems.append(f"{edit.path}: content changed")
    return problems


def _log_line_problems(
    content: str, run_date: str, edited_pages: Sequence[str], originals: Mapping[str, str]
) -> list[str]:
    """FR-019's fixed log-line form, naming the part that differs."""
    entry = _one_line(content)
    if entry is None:
        return [f"{LOG_NAME}: append line is not one line"]
    match = _LOG_LINE_RE.match(entry)
    if match is None:
        return [f"{LOG_NAME}: log line not in the fixed form"]
    date, verb, slug, page_type, why = match.groups()
    if date != run_date:
        return [f"{LOG_NAME}: log line not in the fixed form (the date is {date}, not the run's date {run_date})"]
    if verb not in NIGHTLY_LOG_VERBS:
        return [f"{LOG_NAME}: log line not in the fixed form (the verb is {verb!r})"]
    named = {
        (str(_frontmatter(originals[page]).get("slug", "")), str(_frontmatter(originals[page]).get("page_type", "")))
        for page in edited_pages
    }
    if (slug, page_type) not in named:
        return [
            f"{LOG_NAME}: log line not in the fixed form (no edited page has slug {slug!r} and page type {page_type!r})"
        ]
    forbidden = next((marker for marker in _LOG_LINE_FORBIDDEN if marker in why), None)
    if forbidden is not None:
        return [f"{LOG_NAME}: log line not in the fixed form (the why holds {forbidden!r})"]
    return []


def _index_line_problems(edit: _DraftEdit, orphan: str | None, originals: Mapping[str, str]) -> list[str]:
    """FR-019(b)'s fixed index line: exactly ``- [<title>](<orphan path>)``."""
    entry = _one_line(edit.new_content)
    if entry is None:
        return [f"{INDEX_NAME}: append line is not one line"]
    title = _frontmatter(originals.get(orphan or "", "")).get("title") if orphan else None
    if not isinstance(title, str) or not title or entry != f"- [{title}]({orphan})":
        return [f"{INDEX_NAME}: index line not in the fixed form"]
    return []


def _append_log_problems(
    logs: Sequence[_DraftEdit], run_date: str, edited_pages: Sequence[str], originals: Mapping[str, str]
) -> list[str]:
    """Exactly one one-line ``append-log`` on ``log.md`` in FR-019's fixed form."""
    if not logs:
        return [f"{LOG_NAME}: lacks a required edit"]
    problems = [f"{entry.path}: more than one append-log" for entry in logs[1:]]
    entry = logs[0]
    if entry.path != LOG_NAME:
        problems.append(f"{entry.path}: not an editable page")
        return problems
    problems.extend(_log_line_problems(entry.new_content, run_date, edited_pages, originals))
    return problems


def link_only_problems(
    kind: str,
    edits: Sequence[_DraftEdit],
    *,
    canonical: str | None,
    orphan: str | None,
    editable: Sequence[str],
    originals: Mapping[str, str],
    run_date: str,
) -> list[str]:
    """Every way ``edits`` leaves FR-019's bounds; empty means the draft may be proposed."""
    problems: list[str] = []
    for edit in edits:
        if edit.action == "create":
            problems.append(f"{edit.path}: create is not allowed")
        elif edit.action not in ("update", "append-log", "append-index"):
            problems.append(f"{edit.path}: action {edit.action!r} is not allowed")
    updates = [edit for edit in edits if edit.action == "update"]
    append_logs = [edit for edit in edits if edit.action == "append-log"]
    append_indexes = [edit for edit in edits if edit.action == "append-index"]

    if kind == KIND_MISSING_CROSS_LINK:
        used: set[str] = set()
        for edit in updates:
            if canonical is None or edit.path not in editable:
                problems.append(f"{edit.path}: not an editable page")
                continue
            if edit.path in used:
                problems.append(f"{edit.path}: more than one update for this page")
                continue
            used.add(edit.path)
            problems.extend(_update_problems(edit, canonical, originals[edit.path]))
        problems.extend(f"{page}: lacks a required edit" for page in editable if page not in used)
        problems.extend(f"{edit.path}: action 'append-index' is not allowed" for edit in append_indexes)
        problems.extend(_append_log_problems(append_logs, run_date, list(editable), originals))
    else:
        problems.extend(f"{edit.path}: action 'update' is not allowed" for edit in updates)
        problems.extend(f"{edit.path}: more than one append-index" for edit in append_indexes[1:])
        if not append_indexes:
            problems.append(f"{INDEX_NAME}: lacks a required edit")
        elif append_indexes[0].path != INDEX_NAME:
            problems.append(f"{append_indexes[0].path}: not an editable page")
        else:
            problems.extend(_index_line_problems(append_indexes[0], orphan, originals))
        pages = [orphan] if orphan is not None else []
        problems.extend(_append_log_problems(append_logs, run_date, pages, originals))
    return problems


# ── the pass ──────────────────────────────────────────────────


def _utc_now() -> str:
    """UTC ISO 8601 to the second with ``Z`` (FR-002)."""
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _collapse(text: str) -> str:
    """One line: every whitespace run becomes a single space."""
    return " ".join(text.split())


def _edits_count(plan_path: Path) -> int | None:
    """The number of entries in ``plan.json``'s ``edits`` list, or None when it cannot be read (FR-006)."""
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(plan, dict):
        return None
    edits = plan.get("edits")
    return len(edits) if isinstance(edits, list) else None


def _pending_proposals(proposals_dir: Path) -> tuple[PendingProposal, ...]:
    """Directories directly under the proposals directory, hidden ones excluded, sorted by name (FR-006)."""
    try:
        entries = sorted(proposals_dir.iterdir(), key=lambda entry: entry.name)
    except OSError:  # missing, or not a directory: nothing to list (FR-006)
        return ()
    return tuple(
        PendingProposal(entry.name, _edits_count(entry / "plan.json"))
        for entry in entries
        if not entry.name.startswith(".") and entry.is_dir()
    )


def _fact_warnings(proposal_dir: Path) -> int:
    """How many fact warnings ``plan.json`` records for the proposal's edits (FR-022)."""
    try:
        plan = json.loads((proposal_dir / "plan.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    edits = plan.get("edits") if isinstance(plan, dict) else None
    if not isinstance(edits, list):
        return 0
    return sum(len(edit.get("fact_warnings") or []) for edit in edits if isinstance(edit, dict))


def _refuse_proposals_inside_wiki(paths: WikiPaths) -> None:
    """Refuse a proposals directory that is or resolves inside the wiki with drafting on (FR-013)."""
    proposals = Path(paths.proposals_dir).resolve()
    wiki = Path(paths.wiki_dir).resolve()
    if proposals == wiki or proposals.is_relative_to(wiki):
        raise ValueError(
            f"proposals directory {proposals} is inside the wiki directory {wiki}; with drafting on the pass "
            "would write in the wiki, so the proposals directory must lie outside it"
        )


@dataclass(frozen=True)
class _Draftable:
    """A finding the pass may draft, with the pages it shows and edits (FR-014)."""

    finding: Finding
    canonical: str | None
    orphan: str | None
    editable: tuple[str, ...]
    shown: tuple[str, ...]


def _draftable(finding: Finding, paths: WikiPaths) -> _Draftable | None:
    """The draftable view of ``finding`` or None when it is report-only (FR-014)."""
    if finding.kind == KIND_MISSING_CROSS_LINK:
        if len(finding.pages) < 2:
            return None
        canonical = finding.pages[0]
        if f"canonical page {canonical}" not in finding.description:
            return None
        return _Draftable(finding, canonical, None, tuple(finding.pages[1:]), tuple(finding.pages))
    if finding.kind == KIND_WEAK_ORPHAN:
        if not finding.pages:
            return None
        orphan = finding.pages[0]
        if orphan in _intra_wiki_links_from(paths.wiki_dir / INDEX_NAME, paths.wiki_dir):
            return None
        return _Draftable(finding, None, orphan, (), (orphan, INDEX_NAME))
    return None


@dataclass(frozen=True)
class _DraftOutcome:
    """What the drafting phase of one run produced (FR-021, FR-022)."""

    drafting: DraftingState
    created: tuple[CreatedProposal, ...] = ()
    already_proposed: tuple[AlreadyProposed, ...] = ()
    not_drafted: tuple[NotDraftedProposal, ...] = ()
    failed: tuple[FailedDraft, ...] = ()
    failure_codes: tuple[int, ...] = ()
    write_failed: bool = False
    lock_timeout: bool = False
    warnings: tuple[str, ...] = ()


def _not_drafted(draftable: _Draftable, reason: str) -> NotDraftedProposal:
    finding = draftable.finding
    return NotDraftedProposal(proposal_name(finding.kind, finding.pages), finding.kind, finding.pages, reason)


def _draft_one(
    paths: WikiPaths,
    draftable: _Draftable,
    reads: Mapping[str, ReadResult],
    *,
    backend: Backend,
    backend_name: str,
    by: str | None,
    run_at: str,
) -> tuple[Path, tuple[PageEdit, ...], list[str]]:
    """Compose the curate prompt, call the backend, check FR-019 and write the proposal (FR-017 - FR-020)."""
    from . import api  # deferred: api imports this module's result type

    finding = draftable.finding
    shown = {page: reads[page].text for page in draftable.shown}
    index_md = shown.get(INDEX_NAME, "") if draftable.orphan is not None else ""
    prompt = compose_curate_prompt(
        finding=finding,
        shown=shown,
        editable=draftable.editable,
        index_md=index_md,
        run_date=run_at[:10],
        schema_files=load_schema_files(paths),
    )
    try:
        response = backend.call(prompt)
    except BackendInvocationError:
        raise
    except Exception as exc:
        raise BackendInvocationError(f"Backend {backend_name!r} raised an unexpected error: {exc}") from exc
    if isinstance(response, str):
        raw_response = response
    else:
        try:
            raw_response = json.dumps(response)
        except (TypeError, ValueError) as exc:
            raise ContractViolationError(f"backend response is not JSON-serialisable: {exc}") from exc
    validated = parse_patch_set_response(raw_response)
    edits: list[_DraftEdit] = []
    for raw in validated["edits"]:
        if not isinstance(raw, dict):
            raise ContractViolationError(f"WikiPatchSet.edits[*] must be objects, got {type(raw).__name__}")
        for required in ("path", "action", "new_content", "rationale"):
            if required not in raw:
                raise ContractViolationError(f"WikiPatchSet.edits[*] missing required key: {required!r}")
        action = str(raw["action"])
        path = paths.strip_wiki_label(str(raw["path"]), must_exist=action != "create")
        edits.append(_DraftEdit(path, action, str(raw["new_content"]), str(raw["rationale"])))
    problems = link_only_problems(
        finding.kind,
        edits,
        canonical=draftable.canonical,
        orphan=draftable.orphan,
        editable=draftable.editable,
        originals={page: reads[page].text for page in draftable.shown},
        run_date=run_at[:10],
    )
    if problems:
        raise _OutOfBoundsError(problems)
    page_edits = [
        PageEdit(
            path=edit.path,
            action=cast("PageAction", edit.action),
            new_content=edit.new_content,
            rationale=edit.rationale,
            # The base revision is the sha256 of the bytes the prompt showed, never the reply's value (FR-018).
            base_sha256=reads[edit.path].sha256 if edit.action == "update" else None,
        )
        for edit in edits
    ]
    errors = [error for edit in page_edits for error in validate_page_edit_semantics(edit, paths)]
    if errors:
        raise ContractViolationError("nightly draft failed per-edit semantic validation:\n  - " + "\n  - ".join(errors))
    patch = WikiPatchSet(
        edits=page_edits,
        source_path=f"nightly {finding.kind}: {', '.join(finding.pages)}",
        backend=backend_name,
        rationale=finding.description,
    )
    errors = validate_patch_set(patch)
    if errors:
        raise ContractViolationError("nightly draft failed set-level validation:\n  - " + "\n  - ".join(errors))
    check_reserved_edits(page_edits)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DriftWarning)
        written = api.propose(
            page_edits,
            paths,
            name=proposal_name(finding.kind, finding.pages),
            source=f"nightly {finding.kind}: {', '.join(finding.pages)}",
            rationale=finding.description,
            backend=backend_name,
            by=by,
        )
    drift = [str(warning.message) for warning in caught if issubclass(warning.category, DriftWarning)]
    return written, tuple(page_edits), drift


def _draft_all(
    paths: WikiPaths,
    draftables: Sequence[_Draftable],
    *,
    backend: Backend,
    backend_name: str,
    max_proposals: int,
    by: str | None,
    run_at: str,
) -> _DraftOutcome:
    """Draft each finding in order under FR-016's bounds (FR-016 - FR-021)."""
    from . import api  # deferred: api imports this module's result type

    attempt_bound = ATTEMPTS_PER_PROPOSAL * max_proposals
    created: list[CreatedProposal] = []
    already_proposed: list[AlreadyProposed] = []
    not_drafted: list[NotDraftedProposal] = []
    failed: list[FailedDraft] = []
    collected: list[str] = []
    failure_codes: list[int] = []
    used_update_targets: set[str] = set()
    attempts = 0
    stopped_reason: str | None = None
    write_failed = False
    lock_timeout = False

    if draftables:
        try:
            collected.extend(check_write_contract(paths))
        except ContractViolationError as exc:
            for draftable in draftables:
                not_drafted.append(_not_drafted(draftable, SKIPPED_SCHEMA_CONTRACT))
            return _DraftOutcome(
                DraftingState(DRAFTING_SKIPPED, str(exc), backend_name, max_proposals, attempt_bound, 0, 0),
                not_drafted=tuple(not_drafted),
                failure_codes=(ContractViolationError.exit_code,),
            )

    for draftable in draftables:
        finding = draftable.finding
        name = proposal_name(finding.kind, finding.pages)
        if stopped_reason is not None:
            not_drafted.append(_not_drafted(draftable, f"drafting stopped: {stopped_reason}"))
            continue
        if (paths.proposals_dir / name).is_dir():
            # A pending proposal of this name: no page read, no backend call, no bound used (FR-025).
            already_proposed.append(AlreadyProposed(name, finding.kind, finding.pages))
            continue
        if set(draftable.editable) & used_update_targets:
            not_drafted.append(_not_drafted(draftable, "overlaps an earlier draft"))
            continue
        if len(created) >= max_proposals:
            not_drafted.append(_not_drafted(draftable, "cap: proposals"))
            continue
        if attempts >= attempt_bound:
            not_drafted.append(_not_drafted(draftable, "cap: attempts"))
            continue
        reads: dict[str, ReadResult] = {}
        unreadable: str | None = None
        for page in draftable.shown:
            try:
                reads[page] = api.read_page(page, paths)
            except IngestError as exc:
                unreadable = str(exc)
                break
        if unreadable is not None:
            not_drafted.append(_not_drafted(draftable, f"page unreadable: {unreadable}"))
            continue
        attempts += 1
        try:
            written, page_edits, drift = _draft_one(
                paths, draftable, reads, backend=backend, backend_name=backend_name, by=by, run_at=run_at
            )
        except _OutOfBoundsError as exc:
            failed.append(
                FailedDraft(
                    name,
                    finding.kind,
                    finding.pages,
                    f"out of bounds: {exc.problems[0]}",
                    ContractViolationError.exit_code,
                    "; ".join(exc.problems),
                )
            )
            failure_codes.append(ContractViolationError.exit_code)
            continue
        except BackendInvocationError as exc:
            failed.append(
                FailedDraft(
                    name, finding.kind, finding.pages, "backend error", BackendInvocationError.exit_code, str(exc)
                )
            )
            failure_codes.append(BackendInvocationError.exit_code)
            continue
        except ContractViolationError as exc:
            failed.append(
                FailedDraft(
                    name, finding.kind, finding.pages, "invalid response", ContractViolationError.exit_code, str(exc)
                )
            )
            failure_codes.append(ContractViolationError.exit_code)
            continue
        except PromoteApplyError as exc:
            failed.append(
                FailedDraft(
                    name, finding.kind, finding.pages, REASON_LOCK_TIMEOUT, PromoteApplyError.exit_code, str(exc)
                )
            )
            failure_codes.append(PromoteApplyError.exit_code)
            stopped_reason, lock_timeout = REASON_LOCK_TIMEOUT, True
            continue
        except (OutputWriteError, OSError) as exc:
            if isinstance(exc, OutputWriteError) and (paths.proposals_dir / name).is_dir():
                # Another run created the directory between the pending check and the write (FR-026).
                already_proposed.append(AlreadyProposed(name, finding.kind, finding.pages))
                continue
            failed.append(
                FailedDraft(
                    name, finding.kind, finding.pages, REASON_WRITE_FAILED, OutputWriteError.exit_code, str(exc)
                )
            )
            failure_codes.append(OutputWriteError.exit_code)
            stopped_reason, write_failed = REASON_WRITE_FAILED, True
            continue
        created.append(
            CreatedProposal(
                name=name,
                path=str(written),
                kind=finding.kind,
                pages=finding.pages,
                edits=tuple((edit.action, edit.path) for edit in page_edits),
                fact_warnings=_fact_warnings(written),
            )
        )
        used_update_targets.update(edit.path for edit in page_edits if edit.action == "update")
        for message in drift:
            if message not in collected:
                collected.append(message)

    state = DRAFTING_STOPPED if stopped_reason is not None else DRAFTING_ON
    return _DraftOutcome(
        DraftingState(state, stopped_reason, backend_name, max_proposals, attempt_bound, attempts, len(created)),
        created=tuple(created),
        already_proposed=tuple(already_proposed),
        not_drafted=tuple(not_drafted),
        failed=tuple(failed),
        failure_codes=tuple(failure_codes),
        write_failed=write_failed,
        lock_timeout=lock_timeout,
        warnings=tuple(collected),
    )


def _exit_code(lint_passed: bool, outcome: _DraftOutcome) -> int:
    """FR-010 (2)-(6): lock timeout, then a failed write, then lint, then the first draft failure."""
    if outcome.lock_timeout:
        return PromoteApplyError.exit_code
    if outcome.write_failed:
        return OutputWriteError.exit_code
    if not lint_passed:
        return EXIT_LINT_FAILED
    if outcome.failure_codes:
        return outcome.failure_codes[0]
    return 0


def run(
    paths: WikiPaths,
    *,
    backend: Backend | None = None,
    backend_name: str | None = None,
    max_proposals: int = DEFAULT_MAX_PROPOSALS,
    by: str | None = None,
) -> NightlyResult:
    """Run the pass: structural lint, findings, drafting with a given backend, then the pending listing (FR-001).

    No lock is taken and nothing is written but the proposal directories
    ``api.propose`` writes; an exception from either read propagates and no
    report is produced. A given ``backend`` is already resolved by the caller
    (:func:`wiki_studio.api.nightly`); ``backend_name`` is the name recorded in
    ``plan.json``.
    """
    from . import api  # deferred: api imports this module's result type

    if backend is not None and max_proposals > 0:
        _refuse_proposals_inside_wiki(paths)
    run_at = _utc_now()
    lint_result = api.lint(paths)
    findings_result = api.findings(paths)
    draftables = [
        draftable
        for draftable in (_draftable(finding, paths) for finding in findings_result.findings)
        if draftable is not None
    ]

    if backend is None:
        outcome = _DraftOutcome(
            DraftingState(DRAFTING_OFF, REASON_NO_BACKEND, None, None, None, 0, 0),
            not_drafted=tuple(
                _not_drafted(draftable, f"drafting off: {REASON_NO_BACKEND}") for draftable in draftables
            ),
        )
    elif max_proposals == 0:
        outcome = _DraftOutcome(
            DraftingState(DRAFTING_OFF, REASON_NO_PROPOSALS, backend_name, 0, 0, 0, 0),
            not_drafted=tuple(
                _not_drafted(draftable, f"drafting off: {REASON_NO_PROPOSALS}") for draftable in draftables
            ),
        )
    elif not lint_result.passed:
        outcome = _DraftOutcome(
            DraftingState(DRAFTING_SKIPPED, REASON_LINT_FAILED, backend_name, max_proposals, max_proposals * 2, 0, 0),
            not_drafted=tuple(
                _not_drafted(draftable, f"drafting skipped: {REASON_LINT_FAILED}") for draftable in draftables
            ),
        )
    else:
        resolved_name = backend_name or api.backend_display_name(backend, None)
        outcome = _draft_all(
            paths,
            draftables,
            backend=backend,
            backend_name=resolved_name,
            max_proposals=max_proposals,
            by=by,
            run_at=run_at,
        )

    pending = _pending_proposals(paths.proposals_dir)
    draftable_keys = {(draftable.finding.kind, draftable.finding.pages) for draftable in draftables}
    settled = {(proposal.kind, proposal.pages) for proposal in outcome.created} | {
        (entry.kind, entry.pages) for entry in outcome.already_proposed
    }
    needs_curator = tuple(
        finding
        for finding in findings_result.findings
        if (finding.kind, finding.pages) not in draftable_keys or (finding.kind, finding.pages) not in settled
    )
    return NightlyResult(
        run_at=run_at,
        package_version=__version__,
        wiki_dir=paths.wiki_dir.resolve(),
        proposals_dir=paths.proposals_dir.resolve(),
        lint=lint_result,
        findings=findings_result,
        needs_curator=needs_curator,
        pending=pending,
        warnings=outcome.warnings,
        drafting=outcome.drafting,
        exit_code=_exit_code(lint_result.passed, outcome),
        created=outcome.created,
        already_proposed=outcome.already_proposed,
        not_drafted=outcome.not_drafted,
        failed=outcome.failed,
    )


def check_report_path(report: str | os.PathLike[str], paths: WikiPaths) -> Path:
    """The fully resolved report path; ``ValueError`` when it is the wiki or lies inside it (FR-005).

    Every existing symlink is followed, so a path outside the wiki whose
    parent links into it is refused as well; a refusal names both paths.
    """
    resolved = Path(report).resolve()
    wiki_dir = paths.wiki_dir.resolve()
    if resolved == wiki_dir or resolved.is_relative_to(wiki_dir):
        raise ValueError(f"report path {resolved} is inside the wiki directory {wiki_dir}; it must lie outside it")
    return resolved


def write_report(text: str, path: str | os.PathLike[str]) -> None:
    """Write ``text`` as UTF-8 to ``path`` atomically: a temporary sibling, then ``os.replace`` (FR-005).

    Missing parents are created. On any ``OSError`` the temporary file is
    removed and the error re-raised, so a failed write leaves no partial
    report and no temporary file behind.
    """
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    handle_fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temp_path, target)
    except OSError:
        with contextlib.suppress(OSError):
            temp_path.unlink()
        raise
