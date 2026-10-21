# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# wiki-studio.prose_lint — glossary avoid terms and the whole-word matcher.
#
# A glossary term can name the synonyms the wiki should not use, in one
# accepted form (docs/adr/0001-glossary-avoid-key.md):
#
#   per-file glossary page   avoid: alignment check, origin check
#   glossary/index.md entry  ### <term>
#                            Avoid: alignment check, origin check
#
# The value is one line of comma-separated terms, unquoted or wrapped in one
# pair of double quotes. Every other form is a FormatProblem and contributes
# no terms; nothing is silently changed or dropped. yaml_lite is not extended:
# the raw frontmatter line is read here so quoting can be checked.
#
# find_term / contains_term are the one whole-word matcher, used for avoid
# terms and for entity slugs in health_lint.

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

from . import yaml_lite
from .errors import ContractViolationError
from .wiki_state import _read_text_or_empty

if TYPE_CHECKING:
    from pathlib import Path

GLOSSARY_PAGE_TYPE = "glossary"
GLOSSARY_DIR = "glossary"
GLOSSARY_INDEX = "index.md"
INDEX_STEM = "index"

_WORD = "A-Za-z0-9_-"
# A whitespace run inside a term: at least one blank or line break, at most
# one line break, so a wrapped line matches and a blank line never does.
_INNER_SPACE = r"(?:[ \t]+(?:\r?\n[ \t]*)?|\r?\n[ \t]*)"

_FM_AVOID_RE = re.compile(r"^avoid:[ \t]*(.*)$")
_FM_BLOCK_ITEM_RE = re.compile(r"^\s+-(?:\s|$)")
_ENTRY_HEADING_RE = re.compile(r"^###[ \t]+(.+?)[ \t]*$")
_INDEX_AVOID_RE = re.compile(r"^Avoid:[ \t]*(.*)$")
# Any line that looks like an index Avoid: line, bulleted or indented.
_ANY_AVOID_LINE_RE = re.compile(r"^[ \t]*(?:[-*+][ \t]+)?Avoid:")
_BULLET_RE = re.compile(r"^[ \t]*(?:[-*+]|\d+[.)])[ \t]+")
_FENCE_RE = re.compile(r"^[ \t]*(```|~~~)")


@dataclass(frozen=True)
class AvoidEntry:
    """One glossary term and the synonyms the wiki should not use for it.

    ``canonical`` is the page's file stem for a per-file glossary page and the
    ``### <term>`` text for a ``glossary/index.md`` entry; ``anchor`` is None
    for a per-file page and the entry's heading anchor otherwise.
    """

    canonical: str
    page: str
    anchor: str | None
    terms: tuple[str, ...]


@dataclass(frozen=True)
class FormatProblem:
    """An avoid list in a refused form; it contributes no terms."""

    path: str
    line: int
    message: str


def parse_avoid_value(raw: str) -> tuple[list[str], str | None]:
    """Split one avoid value into terms, or return why the form is refused.

    Returns ``(terms, None)`` for the accepted form and ``([], reason)``
    otherwise.
    """
    value = raw.strip()
    if not value:
        return [], "empty avoid value"
    if value.startswith("["):
        return [], "flow list is not supported; write one line of comma-separated terms"
    if value.startswith("'"):
        return [], "single-quoted value is not supported; leave it unquoted or use double quotes"
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        value = value[1:-1]
    if '"' in value:
        return [], 'a term contains a double quote (")'
    if "\\" in value:
        return [], "a term contains a backslash (\\)"
    terms = [part.strip() for part in value.split(",")]
    if any(not term for term in terms):
        return [], "empty term after splitting on commas"
    return terms, None


@lru_cache(maxsize=1024)
def _term_pattern(term: str) -> re.Pattern[str]:
    words = term.split()
    body = _INNER_SPACE.join(re.escape(word) for word in words)
    return re.compile(rf"(?<![{_WORD}]){body}(?![{_WORD}])", re.IGNORECASE)


def find_term(text: str, term: str) -> list[re.Match[str]]:
    """Every whole-word, case-insensitive match of ``term`` in ``text``.

    Letters, digits, underscore and hyphen are word characters on both sides.
    A space inside the term matches a whitespace run with at most one line
    break, so a term wrapped inside one paragraph matches and a term split by
    a blank line, a list marker or a heading marker does not.
    """
    if not text or not term.strip():
        return []
    return list(_term_pattern(term).finditer(text))


def contains_term(text: str, term: str) -> bool:
    """True when ``term`` occurs in ``text`` as a whole word (see ``find_term``)."""
    if not text or not term.strip():
        return False
    return _term_pattern(term).search(text) is not None


def strip_index_avoid_lines(text: str) -> str:
    """Blank every ``Avoid:`` line of a glossary index outside fenced code.

    The line is replaced by an empty line, so line numbers stay and the text
    around it does not join into one paragraph.
    """
    out: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
        elif not in_fence and _ANY_AVOID_LINE_RE.match(line):
            line = ""
        out.append(line)
    return "\n".join(out)


def _anchor(heading: str) -> str:
    lowered = heading.strip().lower()
    kept = re.sub(r"[^\w\s-]", "", lowered)
    return re.sub(r"\s", "-", kept)


def _frontmatter_end(lines: list[str]) -> int:
    """Index of the closing ``---`` line, or 0 when there is no frontmatter."""
    if not lines or lines[0].strip() != "---":
        return 0
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return i
    return 0


def _read_page_avoid(page: Path, rel: str, text: str) -> tuple[tuple[AvoidEntry, int] | None, list[FormatProblem]]:
    """The ``avoid:`` key of a per-file glossary page."""
    lines = text.splitlines()
    end = _frontmatter_end(lines)
    if not end:
        return None, []
    try:
        page_type = yaml_lite.parse_frontmatter(text).get("page_type")
    except ContractViolationError:
        return None, []
    if page_type != GLOSSARY_PAGE_TYPE:
        return None, []
    for i in range(1, end):
        match = _FM_AVOID_RE.match(lines[i])
        if not match:
            continue
        lineno = i + 1
        if page.stem == INDEX_STEM:
            message = "avoid: in the glossary index frontmatter; put an 'Avoid:' line under each '### <term>' entry"
            return None, [FormatProblem(rel, lineno, message)]
        raw = match.group(1)
        if not raw.strip():
            nxt = lines[i + 1] if i + 1 < end else ""
            if _FM_BLOCK_ITEM_RE.match(nxt):
                return None, [FormatProblem(rel, lineno, "block list is not supported; write one line of terms")]
            return None, [FormatProblem(rel, lineno, "empty avoid value")]
        terms, reason = parse_avoid_value(raw)
        if reason:
            return None, [FormatProblem(rel, lineno, reason)]
        return (AvoidEntry(page.stem, rel, None, tuple(terms)), lineno), []
    return None, []


def _read_index_avoid(rel: str, text: str) -> tuple[list[tuple[AvoidEntry, int]], list[FormatProblem]]:
    """The ``Avoid:`` line of each ``### <term>`` entry in ``glossary/index.md``."""
    lines = text.splitlines()
    end = _frontmatter_end(lines)
    start = end + 1 if end else 0
    entries: list[tuple[AvoidEntry, int]] = []
    problems: list[FormatProblem] = []

    # Pass 1: entry headings and Avoid-looking lines, outside fenced code.
    headings: list[tuple[int, str]] = []
    avoid_lines: list[int] = []
    in_fence = False
    for i in range(start, len(lines)):
        line = lines[i]
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading = _ENTRY_HEADING_RE.match(line)
        if heading:
            headings.append((i, heading.group(1)))
        elif _ANY_AVOID_LINE_RE.match(line):
            avoid_lines.append(i)

    # Pass 2: the first non-blank line after each heading may carry the list.
    accepted: set[int] = set()
    for i, term in headings:
        first = next((j for j in range(i + 1, len(lines)) if lines[j].strip()), None)
        if first is None or first not in avoid_lines:
            continue
        accepted.add(first)
        match = _INDEX_AVOID_RE.match(lines[first])
        if not match:
            problems.append(FormatProblem(rel, first + 1, "bulleted or indented 'Avoid:' line; write it unindented"))
            continue
        following = next((j for j in range(first + 1, len(lines)) if lines[j].strip()), None)
        if following is not None and _BULLET_RE.match(lines[following]):
            problems.append(FormatProblem(rel, first + 1, "'Avoid:' followed by bullet items; write one line of terms"))
            continue
        terms, reason = parse_avoid_value(match.group(1))
        if reason:
            problems.append(FormatProblem(rel, first + 1, reason))
            continue
        entries.append((AvoidEntry(term, rel, _anchor(term), tuple(terms)), first + 1))

    for i in avoid_lines:
        if i not in accepted:
            message = "'Avoid:' line is not the first line after a '### <term>' heading"
            problems.append(FormatProblem(rel, i + 1, message))
    return entries, problems


def load_avoid_map(wiki_dir: Path) -> tuple[dict[str, AvoidEntry], list[FormatProblem]]:
    """Read every avoid list in the wiki.

    Per-file glossary pages (``page_type: glossary``) give their ``avoid:``
    frontmatter key; ``glossary/index.md`` gives the ``Avoid:`` line of each
    entry. ``avoid:`` on any other page type is ignored. The map is keyed by
    canonical term. A term listed under two canonical terms is a problem and
    is dropped from both.
    """
    from .health_lint import _list_wiki_pages  # health_lint imports this module

    raw_entries: list[tuple[AvoidEntry, int]] = []
    problems: list[FormatProblem] = []
    for page in _list_wiki_pages(wiki_dir):
        rel = page.relative_to(wiki_dir).as_posix()
        text = _read_text_or_empty(page)
        if not text:
            continue
        page_entry, found = _read_page_avoid(page, rel, text)
        problems.extend(found)
        if page_entry is not None:
            raw_entries.append(page_entry)
        if rel == f"{GLOSSARY_DIR}/{GLOSSARY_INDEX}":
            index_entries, index_problems = _read_index_avoid(rel, text)
            raw_entries.extend(index_entries)
            problems.extend(index_problems)

    owners: dict[str, list[tuple[AvoidEntry, int]]] = {}
    for entry, line in raw_entries:
        for term in dict.fromkeys(t.lower() for t in entry.terms):
            owners.setdefault(term, []).append((entry, line))
    shared = {term for term, found in owners.items() if len({e.canonical.lower() for e, _ in found}) > 1}
    for term in sorted(shared):
        names = ", ".join(sorted({e.canonical for e, _ in owners[term]}))
        last, line = owners[term][-1]
        problems.append(FormatProblem(last.page, line, f"avoid term {term!r} is listed under: {names}"))

    avoid_map: dict[str, AvoidEntry] = {}
    seen: set[str] = set()
    for entry, line in raw_entries:
        if entry.canonical.lower() in seen:
            message = f"canonical term {entry.canonical!r} has more than one avoid list"
            problems.append(FormatProblem(entry.page, line, message))
            continue
        seen.add(entry.canonical.lower())
        terms = tuple(t for t in entry.terms if t.lower() not in shared)
        if terms:
            avoid_map[entry.canonical] = AvoidEntry(entry.canonical, entry.page, entry.anchor, terms)
    return avoid_map, problems
