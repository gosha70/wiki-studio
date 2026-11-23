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
* ``no-page-id``: a content page without a ``page_id``;
* the conflict kinds of ``conflicts``: ``open-conflict`` (two pages each
  carry a conflict callout naming the other), ``conflict-one-sided``
  (a callout names a page that carries none back) and ``conflict-dangling``
  (a callout names no wiki page, or one that cannot be its other page);
* ``source-not-at-revision`` (FR-025): a cited ``path:`` absent at its
  ``sha:`` in the matched repository, a ``sha:`` no repository has while every
  repository was usable, or a malformed ``sha:``; ``revision_check`` reports
  whether the check could run, every repository and the sources not checked
  (FR-026). Git is read only through ``revisions``;
* ``source-revision-changed`` (FR-032): a cited file changed in place since
  its ``sha:`` in a way the page's anchor check flags (a changed line names
  one of the page's identifiers or ``file:line`` references, or a changed
  Markdown section's heading occurs in the page; a page that names none is
  flagged by any change beyond whitespace). The description quotes the
  page's ``Revisit when:`` line. It flags and still returns: review state,
  approvals and ``find`` are unchanged.

Nothing here takes a backend or resolves one, takes the wiki lock or writes.
The result is versioned (``findings_version``) and leads with ``counts`` by
kind, so a host can report curation debt without parsing descriptions.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from .conflicts import conflict_findings
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
from .revisions import (
    CAUSE_COMMIT_NOT_FOUND,
    CAUSE_NOT_AT_COMMIT,
    OUTCOME_CHANGED,
    OUTCOME_NOT_AT_REVISION,
    REVISIT_PREFIX,
    check_sources,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .paths import WikiPaths
    from .review import ReviewState
    from .revisions import Repository, RevisionCheck, SourceCheck

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
KIND_OPEN_CONFLICT = "open-conflict"
KIND_CONFLICT_ONE_SIDED = "conflict-one-sided"
KIND_CONFLICT_DANGLING = "conflict-dangling"
KIND_SOURCE_NOT_AT_REVISION = "source-not-at-revision"
KIND_SOURCE_REVISION_CHANGED = "source-revision-changed"
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
    KIND_OPEN_CONFLICT,
    KIND_CONFLICT_ONE_SIDED,
    KIND_CONFLICT_DANGLING,
    KIND_SOURCE_NOT_AT_REVISION,
    KIND_SOURCE_REVISION_CHANGED,
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
    """What ``api.findings`` reports: ``counts`` by kind (zero included), the pages checked, the findings.

    ``revision_check`` is the run state of the revision check (FR-026).
    """

    findings_version: int
    counts: Mapping[str, int]
    pages_checked: int
    findings: tuple[Finding, ...]
    revision_check: RevisionCheck

    def as_dict(self) -> dict[str, Any]:
        """The JSON form (``docs/knowledge-contract.md``); consumers read keys by name, not by order."""
        return {
            "findings_version": self.findings_version,
            "counts": dict(self.counts),
            "pages_checked": self.pages_checked,
            "findings": [finding.as_dict() for finding in self.findings],
            "revision_check": self.revision_check.as_dict(),
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


def _revision_changed_description(source: SourceCheck, repository: Repository) -> str:
    """FR-032: path, ``sha:``, repository, HEAD, and the page's ``Revisit when:`` line quoted (or its absence)."""
    revisit = (
        f'the page says "{source.revisit_when}"'
        if source.revisit_when is not None
        else f"the page records no `{REVISIT_PREFIX}` line"
    )
    return (
        f"cites {source.path} at {source.sha}; in {repository.path} the file changed between that commit and HEAD "
        f"{repository.head}, and the change touches what the page names (an identifier, a file:line reference or "
        f"a section heading; for a page naming none, any change beyond whitespace); {revisit}; review the page "
        "against the change and update the sha:"
    )


def _revision_findings(check: RevisionCheck) -> list[Finding]:
    """One ``source-not-at-revision`` per source for FR-025's causes, one ``source-revision-changed`` per flag."""
    searched = ", ".join(str(repository.path) for repository in check.repositories)
    found: list[Finding] = []
    for source in check.sources:
        repository = source.repository
        if source.outcome == OUTCOME_CHANGED and source.revision_changed and repository is not None:
            description = _revision_changed_description(source, repository)
            found.append(Finding(KIND_SOURCE_REVISION_CHANGED, SEVERITY_WARNING, (source.page,), description))
            continue
        if source.outcome != OUTCOME_NOT_AT_REVISION:
            continue
        if source.reason == CAUSE_NOT_AT_COMMIT and repository is not None:
            description = (
                f"cites {source.path} at {source.sha}, a commit of {repository.path} that does not contain it; "
                f"the path exists at that repository's HEAD {repository.head}; correct the sha: or the path"
            )
        elif source.reason == CAUSE_COMMIT_NOT_FOUND:
            description = (
                f"cites {source.path} at {source.sha}, a commit none of the repositories searched has "
                f"({searched}); correct the sha: or add the repository that has it as a source root"
            )
        else:
            description = (
                f"cites {source.path} with a malformed sha: {source.sha!r} (expected 7-40 lowercase hex "
                "characters); correct it"
            )
        found.append(Finding(KIND_SOURCE_NOT_AT_REVISION, SEVERITY_WARNING, (source.page,), description))
    return found


def findings(paths: WikiPaths, *, pages: list[str] | None = None) -> FindingsResult:
    """Collect the findings; reads only, takes no lock and no backend (FR-037).

    ``pages=None`` covers the default review set (every content page; the
    root ``index.md`` and ``log.md`` are excluded); an explicit list scopes
    every kind to those wiki-relative pages. Either way a finding reports
    only its pages inside the scope, and ``pages_checked`` counts the scope.
    The graph-based health checks still read the whole wiki to count edges.
    The revision check reads the cited sources of the in-scope pages that do
    not carry ``superseded_by``, read-only, through ``revisions``.
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
    # The conflict scan reads the whole review set whatever the scope, so a
    # scoped run still sees the page that answers back; the same scope rule as
    # the health findings keeps it and lists only its in-scope pages.
    for conflict in conflict_findings(paths):
        scoped = tuple(page for page in conflict.pages if page in in_scope)
        if scoped:
            found.append(Finding(conflict.kind, conflict.severity, scoped, conflict.description))
    revision_check = check_sources(paths, canonical)
    found.extend(_revision_findings(revision_check))
    counts = dict.fromkeys(FINDING_KINDS, 0)
    for finding in found:
        counts[finding.kind] += 1
    return FindingsResult(
        findings_version=FINDINGS_VERSION,
        counts=MappingProxyType(counts),
        pages_checked=len(canonical),
        findings=tuple(found),
        revision_check=revision_check,
    )
