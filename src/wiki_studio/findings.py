# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wiki_studio.findings — what needs a curator's attention, without a model call (FR-037, FR-038).

One read-only pass over the wiki that a host can run at session start:

* the deterministic knowledge-health kinds (``stale-claim``, ``weak-orphan``,
  ``missing-cross-link``, ``avoid-format``): the health checks run with no
  backend, so ``contradiction`` never appears;
* the review kinds from ``review_state``: ``unapproved``, ``approval-stale``
  and ``approval-policy-changed``;
* ``superseded-still-indexed``: ``index.md`` links a page that carries
  ``superseded_by``;
* ``no-page-id``: a content page without a ``page_id``.

Nothing here takes a backend or resolves one, takes the wiki lock or writes.
The result is versioned (``findings_version``) and leads with ``counts`` by
kind, so a host can report curation debt without parsing descriptions.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from .contract import FINDINGS_FORMAT_VERSION
from .health_lint import _intra_wiki_links_from, lint_health
from .lint import INDEX_NAME
from .review import (
    REASON_MANIFEST_MISSING,
    STATE_POLICY_CHANGED,
    STATE_STALE,
    STATE_UNAPPROVED,
    default_review_pages,
    frontmatter_page_id,
    read_live_page,
    review_states,
    superseded_by,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .paths import WikiPaths
    from .review import ReviewState

FINDINGS_VERSION = FINDINGS_FORMAT_VERSION

SEVERITY_WARNING = "warning"

KIND_STALE_CLAIM = "stale-claim"
KIND_WEAK_ORPHAN = "weak-orphan"
KIND_MISSING_CROSS_LINK = "missing-cross-link"
KIND_AVOID_FORMAT = "avoid-format"
KIND_UNAPPROVED = "unapproved"
KIND_APPROVAL_STALE = "approval-stale"
KIND_APPROVAL_POLICY_CHANGED = "approval-policy-changed"
KIND_SUPERSEDED_STILL_INDEXED = "superseded-still-indexed"
KIND_NO_PAGE_ID = "no-page-id"
# Every kind this build can report, in the order a run lists them; ``counts`` names each one.
FINDING_KINDS: tuple[str, ...] = (
    KIND_STALE_CLAIM,
    KIND_WEAK_ORPHAN,
    KIND_MISSING_CROSS_LINK,
    KIND_AVOID_FORMAT,
    KIND_UNAPPROVED,
    KIND_APPROVAL_STALE,
    KIND_APPROVAL_POLICY_CHANGED,
    KIND_SUPERSEDED_STILL_INDEXED,
    KIND_NO_PAGE_ID,
)

# The review state each review kind reports.
_REVIEW_KINDS: Mapping[str, str] = MappingProxyType(
    {
        STATE_UNAPPROVED: KIND_UNAPPROVED,
        STATE_STALE: KIND_APPROVAL_STALE,
        STATE_POLICY_CHANGED: KIND_APPROVAL_POLICY_CHANGED,
    }
)


@dataclass(frozen=True)
class Finding:
    """One finding: its ``kind``, ``severity``, the wiki-relative ``pages`` involved and a ``description``."""

    kind: str
    severity: str
    pages: tuple[str, ...]
    description: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "severity": self.severity,
            "pages": list(self.pages),
            "description": self.description,
        }


@dataclass(frozen=True)
class FindingsResult:
    """What ``api.findings`` reports: ``counts`` by kind (zero included), the pages checked, the findings."""

    findings_version: int
    counts: Mapping[str, int]
    pages_checked: int
    findings: tuple[Finding, ...]

    def as_dict(self) -> dict[str, Any]:
        """The JSON form (``docs/knowledge-contract.md``); consumers read keys by name, not by order."""
        return {
            "findings_version": self.findings_version,
            "counts": dict(self.counts),
            "pages_checked": self.pages_checked,
            "findings": [finding.as_dict() for finding in self.findings],
        }


def _review_description(state: ReviewState) -> str:
    if state.state == STATE_STALE:
        return (
            f"the live revision {state.live_sha256} has no approval; the newest record approves "
            f"{state.approved_sha256} ({state.record_path}); review the change and run "
            f"`wiki-studio approve {state.path}`"
        )
    if state.state == STATE_POLICY_CHANGED:
        return (
            f"the live revision is approved ({state.record_path}) but no record satisfies the current policy "
            f"(an approver is required); run `wiki-studio approve {state.path} --by NAME`"
        )
    if state.reason == REASON_MANIFEST_MISSING:
        return "no approval can be recorded: the wiki has no manifest; run `wiki-studio init` to add one"
    return f"no approval for the live revision (reason {state.reason}); review it and run `wiki-studio approve`"


def _review_findings(states: list[ReviewState]) -> list[Finding]:
    return [
        Finding(_REVIEW_KINDS[state.state], SEVERITY_WARNING, (state.path,), _review_description(state))
        for state in states
        if state.state in _REVIEW_KINDS
    ]


def _page_findings(paths: WikiPaths, pages: list[str]) -> list[Finding]:
    """``no-page-id`` and ``superseded-still-indexed`` for the pages in scope, read through the wiki boundary."""
    indexed = set(_intra_wiki_links_from(paths.wiki_dir / INDEX_NAME, paths.wiki_dir))
    missing_id: list[Finding] = []
    still_indexed: list[Finding] = []
    for page in pages:
        rel, content = read_live_page(page, paths)
        if frontmatter_page_id(content.text) is None:
            missing_id.append(
                Finding(
                    KIND_NO_PAGE_ID,
                    SEVERITY_WARNING,
                    (rel,),
                    "content page without a page_id; add one through an ordinary guarded update",
                )
            )
        target = superseded_by(content.text)
        if target is not None and rel in indexed:
            still_indexed.append(
                Finding(
                    KIND_SUPERSEDED_STILL_INDEXED,
                    SEVERITY_WARNING,
                    (rel, INDEX_NAME),
                    f"index.md still links this page, which is superseded by {target}; point the entry at the "
                    "replacement",
                )
            )
    return [*still_indexed, *missing_id]


def findings(paths: WikiPaths, *, pages: list[str] | None = None) -> FindingsResult:
    """Collect the findings; reads only, takes no lock and no backend (FR-037).

    ``pages=None`` covers the default review set (every content page; the
    root ``index.md`` and ``log.md`` are excluded); an explicit list scopes
    every kind to those wiki-relative pages. Either way a finding reports
    only its pages inside the scope, and ``pages_checked`` counts the scope.
    The graph-based health checks still read the whole wiki to count edges.
    """
    states = review_states(paths, default_review_pages(paths) if pages is None else list(pages))
    canonical = [state.path for state in states]
    health = lint_health(paths, backend=None)
    # One scope for every kind and for the denominator: the requested pages, or
    # the default review set (every content page, root index.md and log.md
    # excluded). A multi-page health finding is kept when it touches the scope
    # and reports only its in-scope pages.
    in_scope = set(canonical)
    found: list[Finding] = []
    for f in health.findings:
        if f.kind not in FINDING_KINDS:
            continue
        scoped = tuple(page for page in f.pages if page in in_scope)
        if scoped:
            found.append(Finding(f.kind, f.severity, scoped, f.description))
    found.extend(_review_findings(states))
    found.extend(_page_findings(paths, canonical))
    counts = dict.fromkeys(FINDING_KINDS, 0)
    for finding in found:
        counts[finding.kind] += 1
    return FindingsResult(
        findings_version=FINDINGS_VERSION,
        counts=MappingProxyType(counts),
        pages_checked=len(canonical),
        findings=tuple(found),
    )
