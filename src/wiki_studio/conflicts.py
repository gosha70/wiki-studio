# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wiki_studio.conflicts — the model-free scan behind the conflict kinds of ``findings`` (FR-005..FR-007).

A disagreement between two pages is recorded as an optional body convention
(``citation-rules.md``, "When sources disagree", ADR-0004): each page carries a
blockquote callout whose marker line names the other page with its first
``.md`` link. This module reads those marker lines without a model and pairs
them:

* ``open-conflict`` — both pages carry a callout naming the other;
* ``conflict-one-sided`` — one callout names a page that carries none back;
* ``conflict-dangling`` — the callout names no wiki page, a page outside the
  wiki, a missing page, a page that is not a content page, the page itself or
  a superseded page.

The scan is line-based, not a CommonMark parser: a marker must start a line
after at most three spaces and the ``>``, and fenced code is skipped. It reads
the whole default review set whatever scope ``findings`` was given, takes no
lock, no backend and writes nothing; ``findings.py`` is its only importer.
"""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .lint import _LINK_TITLE_RE, _MD_LINK_RE, PAGE_SUFFIX
from .paths import is_absolute_path
from .prose_lint import closes_fence, open_fence
from .review import default_review_pages, read_live_page, superseded_by

if TYPE_CHECKING:
    from pathlib import Path

    from .findings import Finding
    from .paths import WikiPaths

# The marker a conflict callout's first line carries (case-insensitive, optionally
# followed by Obsidian's fold sign). The regex is built from it: this is the only
# spelling of the marker in the package.
CONFLICT_MARKER = "[!conflict]"
CONFLICT_MARKER_RE = re.compile(rf"^ {{0,3}}>[ \t]*{re.escape(CONFLICT_MARKER)}[+-]?(?=[ \t]|$)", re.IGNORECASE)

# A URL-scheme link target (``https://…/b.md``) points outside the wiki.
_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


@dataclass(frozen=True)
class Callout:
    """One conflict callout's marker line: the ``page``, its 1-based ``line``, the raw link target and its resolution.

    ``raw_target`` is the first ``.md`` link target on the marker line as
    written (fragment and an optional title dropped), or None when the line
    carries no ``.md`` link. ``resolved`` is that target as a wiki-relative
    path resolved from the page's directory, or None for a target that leaves
    the wiki (an escape or a URL scheme).
    """

    page: str
    line: int
    raw_target: str | None
    resolved: str | None


def _body_lines(text: str) -> list[tuple[int, str]]:
    """The page's lines after its frontmatter as (1-based line number, line); all lines when there is none."""
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                start = index + 1
                break
    return list(enumerate(lines[start:], start=start + 1))


def _marker_target(line: str) -> str | None:
    """The first ``.md`` link target on a marker line, as :func:`wiki_studio.lint.md_links` reads one."""
    for match in _MD_LINK_RE.finditer(line):
        target = _LINK_TITLE_RE.sub("", match.group(1).split("#", 1)[0])
        if target.endswith(PAGE_SUFFIX):
            return target
    return None


def _resolve_target(page: str, target: str, wiki_dir: Path) -> str | None:
    """``target`` resolved from ``page``'s directory inside the resolved wiki, else None.

    Resolution follows the intra-wiki link rule: ``(page_dir / target).resolve()``
    must stay under the wiki directory; a URL-scheme or absolute target never does.
    """
    if _SCHEME_RE.match(target) or is_absolute_path(target):
        return None
    candidate = posixpath.join(posixpath.dirname(page), target)
    resolved = (wiki_dir / candidate).resolve()
    try:
        return resolved.relative_to(wiki_dir.resolve()).as_posix()
    except ValueError:
        return None


def scan_callouts(paths: WikiPaths) -> dict[str, list[Callout]]:
    """Every conflict callout of the default review set, by page, in page and line order (FR-006).

    A superseded page's callouts are not read (its text is replaced). Each page
    is read once through :func:`wiki_studio.review.read_live_page`; fenced code
    is skipped with the prose scanner's fence rules, and only the marker line
    itself is read for a link. Pages without callouts are absent from the map.
    """
    found: dict[str, list[Callout]] = {}
    for page in default_review_pages(paths):
        rel, content = read_live_page(page, paths)
        if superseded_by(content.text) is not None:
            continue
        callouts: list[Callout] = []
        fence: str | None = None
        for lineno, line in _body_lines(content.text):
            if fence is not None:
                if closes_fence(line, fence):
                    fence = None
                continue
            opened = open_fence(line)
            if opened is not None:
                fence = opened
                continue
            if CONFLICT_MARKER_RE.match(line) is None:
                continue
            raw = _marker_target(line)
            resolved = _resolve_target(rel, raw, paths.wiki_dir) if raw is not None else None
            callouts.append(Callout(rel, lineno, raw, resolved))
        if callouts:
            found[rel] = callouts
    return found


def _dangling_reason(
    callout: Callout,
    page: str,
    paths: WikiPaths,
    content_pages: set[str],
    superseded_cache: dict[str, str | None],
) -> str | None:
    """Why the callout is dangling (FR-007's words), or None when its target is a content page."""
    if callout.raw_target is None:
        return "conflict callout names no wiki page"
    if callout.resolved is None:
        return f"conflict callout target {callout.raw_target} points outside the wiki"
    target = callout.resolved
    if not (paths.wiki_dir / target).is_file():
        return f"conflict callout target {callout.raw_target} names a missing page"
    if target not in content_pages:
        return f"conflict callout target {callout.raw_target} names {target}, which is not a content page"
    if target == page:
        return f"conflict callout target {callout.raw_target} names the page itself"
    if target not in superseded_cache:
        _, content = read_live_page(target, paths)
        superseded_cache[target] = superseded_by(content.text)
    superseded = superseded_cache[target]
    if superseded is not None:
        return f"conflict callout target {callout.raw_target} names {target}, which is superseded by {superseded}"
    return None


def conflict_findings(paths: WikiPaths) -> list[Finding]:
    """The three conflict kinds for the whole review set, in a deterministic order (FR-007).

    Each page's repeated callout to the same other page counts once. A dangling
    callout never pairs. Findings are listed ``open-conflict`` (by pages),
    ``conflict-one-sided`` (by pages) and ``conflict-dangling`` (by page, then
    line); the caller applies the ``findings`` page scope.
    """
    from .findings import (
        KIND_CONFLICT_DANGLING,
        KIND_CONFLICT_ONE_SIDED,
        KIND_OPEN_CONFLICT,
        SEVERITY_WARNING,
        Finding,
    )

    content_pages = set(default_review_pages(paths))
    callouts = scan_callouts(paths)
    targets: dict[str, set[str]] = {}
    deduped: dict[str, list[Callout]] = {}
    for page in sorted(callouts):
        seen: set[tuple[str, str | None]] = set()
        kept: list[Callout] = []
        resolved_targets: set[str] = set()
        for callout in callouts[page]:
            key = ("resolved", callout.resolved) if callout.resolved is not None else ("raw", callout.raw_target)
            if key in seen:
                continue
            seen.add(key)
            kept.append(callout)
            if callout.resolved is not None:
                resolved_targets.add(callout.resolved)
        deduped[page] = kept
        targets[page] = resolved_targets

    paired: set[tuple[str, str]] = set()
    open_findings: list[Finding] = []
    one_sided: list[Finding] = []
    dangling: list[tuple[str, int, Finding]] = []
    superseded_cache: dict[str, str | None] = {}
    for page in sorted(deduped):
        for callout in deduped[page]:
            reason = _dangling_reason(callout, page, paths, content_pages, superseded_cache)
            if reason is not None:
                description = f"line {callout.line}: {reason}"
                finding = Finding(KIND_CONFLICT_DANGLING, SEVERITY_WARNING, (page,), description)
                dangling.append((page, callout.line, finding))
                continue
            other = callout.resolved
            if other is None:  # unreachable: an unresolved target is always dangling
                continue
            if page in targets.get(other, set()):
                pair = (page, other) if page <= other else (other, page)
                if pair in paired:
                    continue
                paired.add(pair)
                open_findings.append(
                    Finding(
                        KIND_OPEN_CONFLICT,
                        SEVERITY_WARNING,
                        pair,
                        f"{pair[0]} and {pair[1]} mark a conflict with each other; resolve it in one patch-set: "
                        "remove both callouts and add the deciding source to the page that keeps the claim "
                        "(citation-rules.md, When sources disagree)",
                    )
                )
            else:
                one_sided.append(
                    Finding(
                        KIND_CONFLICT_ONE_SIDED,
                        SEVERITY_WARNING,
                        (page, other),
                        f"{other} carries no callout naming {page} back; add the matching callout or remove this one",
                    )
                )
    open_findings.sort(key=lambda finding: finding.pages)
    one_sided.sort(key=lambda finding: finding.pages)
    in_order = [finding for _, _, finding in sorted(dangling, key=lambda entry: (entry[0], entry[1]))]
    return [*open_findings, *one_sided, *in_order]
