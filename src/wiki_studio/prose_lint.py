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
#
# The prose scanner (scan_page) turns a page into ProseSegments: paragraphs,
# list items and headings, with code, tables, quotes and comments removed.
# run_prose_lint runs the checks of `lint --prose` over them: 1-4 (sentence
# length, semicolons, filler phrases, Summary and Key-ideas length) and 5,
# the term lock (avoid terms on non-glossary pages), plus the avoid-format
# problems of the glossary. The limits live in wiki_studio.schema;
# lint-rules.md documents them and the scanner's known limits. Findings are
# advisory.

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from . import yaml_lite
from .errors import ContractViolationError
from .schema import (
    FILLER_PHRASES,
    KEY_IDEA_MAX_SENTENCES,
    PROSE_ABBREVIATIONS,
    PROSE_MAX_WORDS,
    PROSE_MAX_WORDS_NUMBERED,
    SUMMARY_MAX_SENTENCES,
)
from .wiki_state import _read_text_or_empty

if TYPE_CHECKING:
    from collections.abc import Iterable

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
# A fence is three or more backticks or tildes indented at most three spaces
# (CommonMark); a deeper indent, or a tab, is indented code. The run is the delimiter.
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def open_fence(line: str) -> str | None:
    """The delimiter that ``line`` opens a fenced code block with, or None.

    A backtick fence's info string may not hold a backtick, so a line that is
    an inline code span (```` ```x``` ````) does not open a block.
    """
    match = _FENCE_RE.match(line)
    if not match:
        return None
    run = match.group(1)
    if run[0] == "`" and "`" in line[match.end() :]:
        return None
    return run


def closes_fence(line: str, fence: str) -> bool:
    """True when ``line`` closes a block opened by ``fence``.

    The closing run uses the same character, is at least as long as the
    opening run and carries nothing else on the line, so a shorter fence
    inside a longer one, or an info string, never closes the block.
    """
    match = _FENCE_RE.match(line)
    if not match:
        return False
    run = match.group(1)
    return run[0] == fence[0] and len(run) >= len(fence) and not line[match.end() :].strip()


def term_key(term: str) -> str:
    """The key under which the matcher treats two avoid terms as the same term.

    ``find_term`` ignores case and matches a space inside a term against any
    whitespace run, so collision checks compare terms by this key.
    """
    return " ".join(term.split()).lower()


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
    fence: str | None = None
    for line in text.split("\n"):
        if fence is not None:
            if closes_fence(line, fence):
                fence = None
        elif (opened := open_fence(line)) is not None:
            fence = opened
        elif _ANY_AVOID_LINE_RE.match(line):
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
    fence: str | None = None
    for i in range(start, len(lines)):
        line = lines[i]
        if fence is not None:
            if closes_fence(line, fence):
                fence = None
            continue
        if (opened := open_fence(line)) is not None:
            fence = opened
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
        for term in dict.fromkeys(term_key(t) for t in entry.terms):
            owners.setdefault(term, []).append((entry, line))
    shared = {term for term, found in owners.items() if len({term_key(e.canonical) for e, _ in found}) > 1}
    for term in sorted(shared):
        names = ", ".join(sorted({e.canonical for e, _ in owners[term]}))
        last, line = owners[term][-1]
        problems.append(FormatProblem(last.page, line, f"avoid term {term!r} is listed under: {names}"))

    avoid_map: dict[str, AvoidEntry] = {}
    seen: set[str] = set()
    for entry, line in raw_entries:
        if term_key(entry.canonical) in seen:
            message = f"canonical term {entry.canonical!r} has more than one avoid list"
            problems.append(FormatProblem(entry.page, line, message))
            continue
        seen.add(term_key(entry.canonical))
        terms = tuple(t for t in entry.terms if term_key(t) not in shared)
        if terms:
            avoid_map[entry.canonical] = AvoidEntry(entry.canonical, entry.page, entry.anchor, terms)
    return avoid_map, problems


# --- Prose scanner and checks 1-4 (FR-010, FR-011) --------------------------

ProseSegmentKind = Literal["paragraph", "bullet", "numbered", "heading"]
SEGMENT_PARAGRAPH: ProseSegmentKind = "paragraph"
SEGMENT_BULLET: ProseSegmentKind = "bullet"
SEGMENT_NUMBERED: ProseSegmentKind = "numbered"
SEGMENT_HEADING: ProseSegmentKind = "heading"

CHECK_SENTENCE_LENGTH = "sentence-length"
CHECK_SEMICOLON = "semicolon"
CHECK_FILLER = "filler"
CHECK_SECTION_LENGTH = "section-length"
CHECK_TERM_LOCK = "term-lock"
CHECK_AVOID_FORMAT = "avoid-format"

SUMMARY_SECTION = "summary"
KEY_IDEAS_SECTION = "key ideas"
LOG_PAGE = "log.md"

# Masked inline code and bare URLs hold no word character, so the term
# matcher never sees inside them; each counts as one word.
CODE_TOKEN = "`…`"
URL_TOKEN = "<…>"

_HEADING_RE = re.compile(r"^[ \t]{0,3}(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
_LIST_ITEM_RE = re.compile(r"^[ \t]*(?:[-*+]|(\d+)[.)])[ \t]+(.*)$")
_THEMATIC_BREAK_RE = re.compile(r"^[ \t]{0,3}(?:[-*_=][ \t]*){3,}$")
_INDENTED_CODE_RE = re.compile(r"^(?: {4}|\t)")
_INLINE_CODE_RE = re.compile(r"(`+)(.+?)\1", re.DOTALL)
_LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
# Trailing punctuation before whitespace stays outside the URL, so a URL can end a sentence.
_URL_RE = re.compile(r"\b(?:(?:https?|ftp)://|www\.)\S+?(?=[.,;:!?)\]]*(?:\s|$))")
_ENTITY_RE = re.compile(r"&#?\w+;")
_SENTENCE_END_RE = re.compile(r"[.!?]+(?=\s+(?:[A-Z`]|$)|$)")
_WORD_TOKEN_RE = re.compile(r"[^\W_]|…")


@dataclass(frozen=True)
class ProseSegment:
    """One block of prose on a page, after masking.

    ``line`` is the 1-based line the block starts on; wrapped lines are
    joined with ``\\n`` so a sentence's line can be recovered. ``section`` is
    the enclosing ``##`` heading's text ("" before the first one), which
    check 4 uses to find Summary and Key ideas.
    """

    path: str
    line: int
    kind: ProseSegmentKind
    text: str
    section: str = ""


@dataclass(frozen=True)
class Sentence:
    """One sentence of a segment and the line it starts on."""

    line: int
    text: str


@dataclass(frozen=True)
class ProseFinding:
    """One prose problem; ``check`` names the rule and ``line`` is 1-based."""

    path: str
    line: int
    check: str
    message: str


@dataclass(frozen=True)
class ProseLintResult:
    """Aggregated output of a prose pass."""

    findings: list[ProseFinding]
    pages_checked: int


def mask_inline(text: str) -> str:
    """Mask inline code and bare URLs as one token each and unwrap ``[text](target)``.

    Line breaks inside a code span are kept so line numbers stay right.
    """
    text = _INLINE_CODE_RE.sub(lambda m: CODE_TOKEN + "\n" * m.group(0).count("\n"), text)
    text = _LINK_RE.sub(lambda m: m.group(1), text)
    text = _URL_RE.sub(URL_TOKEN, text)
    return _ENTITY_RE.sub("&", text)


def _strip_comment(line: str, in_comment: bool) -> tuple[str, bool]:
    """Remove HTML comment text from one line; return the rest and the open state."""
    kept = ""
    rest = line
    while rest:
        if in_comment:
            end = rest.find("-->")
            if end < 0:
                return kept, True
            rest = rest[end + 3 :]
            in_comment = False
        else:
            start = rest.find("<!--")
            if start < 0:
                return kept + rest, False
            kept += rest[:start]
            rest = rest[start + 4 :]
            in_comment = True
    return kept, in_comment


def scan_page(path: str, text: str) -> list[ProseSegment]:
    """Split a page into prose segments (FR-010).

    Skips frontmatter, fenced code, table rows, blockquotes, HTML comments,
    a glossary index's ``Avoid:`` lines, thematic breaks, and indented code
    that follows a blank line outside a list. Consecutive lines join into one
    paragraph; each list item and each heading is its own segment.
    """
    if path == f"{GLOSSARY_DIR}/{GLOSSARY_INDEX}":
        text = strip_index_avoid_lines(text)
    lines = text.splitlines()
    end = _frontmatter_end(lines)

    segments: list[ProseSegment] = []
    section = ""
    current: list[str] = []
    current_kind = SEGMENT_PARAGRAPH
    current_line = 0
    fence: str | None = None
    in_comment = False
    in_list = False
    in_indented_code = False
    previous_blank = True

    def flush() -> None:
        nonlocal current
        if current:
            joined = mask_inline("\n".join(current)).strip()
            if joined:
                segments.append(ProseSegment(path, current_line, current_kind, joined, section))
        current = []

    for index in range(end + 1 if end else 0, len(lines)):
        lineno = index + 1
        if fence is not None:
            if closes_fence(lines[index], fence):
                fence = None
            continue
        opened = None if in_comment else open_fence(lines[index])
        if opened is not None:
            flush()
            fence = opened
            previous_blank = False
            continue

        raw, in_comment = _strip_comment(lines[index], in_comment)
        stripped = raw.strip()
        if not stripped:
            flush()
            previous_blank = True
            continue

        if in_indented_code:
            if _INDENTED_CODE_RE.match(raw):
                continue
            in_indented_code = False
        if previous_blank and not in_list and _INDENTED_CODE_RE.match(raw):
            flush()
            in_indented_code = True
            continue
        after_blank = previous_blank
        previous_blank = False

        if stripped.startswith(("|", ">")) or _THEMATIC_BREAK_RE.match(raw):
            flush()
            continue

        heading = _HEADING_RE.match(raw)
        if heading:
            flush()
            level = len(heading.group(1))
            if level <= 2:
                section = heading.group(2) if level == 2 else ""
            title = mask_inline(heading.group(2)).strip()
            if title:
                segments.append(ProseSegment(path, lineno, SEGMENT_HEADING, title, section))
            in_list = False
            continue

        item = _LIST_ITEM_RE.match(raw)
        if item:
            flush()
            current_kind = SEGMENT_NUMBERED if item.group(1) else SEGMENT_BULLET
            current_line = lineno
            current = [item.group(2).strip()]
            in_list = True
            continue

        if current and not after_blank:
            current.append(stripped)
            continue
        if not raw[:1].isspace():
            in_list = False
        flush()
        current_kind = SEGMENT_PARAGRAPH
        current_line = lineno
        current = [stripped]
    flush()
    return segments


def _ends_with_abbreviation(text: str) -> bool:
    lowered = text.lower()
    for abbreviation in PROSE_ABBREVIATIONS:
        if lowered.endswith(abbreviation):
            before = lowered[: -len(abbreviation)]
            if not before or not before[-1].isalnum():
                return True
    return False


def split_sentences(segment: ProseSegment) -> list[Sentence]:
    """Split a segment at ``[.!?]`` + whitespace + a capital, a backtick or the end.

    A period that ends "e.g.", "i.e.", "etc." or "vs." is not a boundary. A
    sentence's line is the line its first character is on.
    """
    text = segment.text
    sentences: list[Sentence] = []
    start = 0
    for match in _SENTENCE_END_RE.finditer(text):
        if _ends_with_abbreviation(text[start : match.end()]):
            continue
        _append_sentence(sentences, segment, start, match.end())
        start = match.end()
    _append_sentence(sentences, segment, start, len(text))
    return sentences


def _append_sentence(sentences: list[Sentence], segment: ProseSegment, start: int, end: int) -> None:
    chunk = segment.text[start:end]
    body = chunk.strip()
    if not body:
        return
    offset = start + len(chunk) - len(chunk.lstrip())
    line = segment.line + segment.text.count("\n", 0, offset)
    sentences.append(Sentence(line, " ".join(body.split())))


def count_words(sentence: str) -> int:
    """Whitespace-separated tokens that hold a letter, a digit or a masked token."""
    return sum(1 for token in sentence.split() if _WORD_TOKEN_RE.search(token))


def check_segment(segment: ProseSegment) -> list[ProseFinding]:
    """Checks 1-3 (sentence length, semicolon, filler) on one segment; headings are exempt."""
    if segment.kind == SEGMENT_HEADING:
        return []
    limit = PROSE_MAX_WORDS_NUMBERED if segment.kind == SEGMENT_NUMBERED else PROSE_MAX_WORDS
    findings: list[ProseFinding] = []
    for sentence in split_sentences(segment):
        words = count_words(sentence.text)
        if words > limit:
            message = f"sentence has {words} words (limit {limit}); split it"
            findings.append(ProseFinding(segment.path, sentence.line, CHECK_SENTENCE_LENGTH, message))
        if ";" in sentence.text:
            findings.append(ProseFinding(segment.path, sentence.line, CHECK_SEMICOLON, "semicolon; split the sentence"))
        for phrase in FILLER_PHRASES:
            if contains_term(sentence.text, phrase):
                message = f"filler phrase {phrase!r}; remove it or state the fact directly"
                findings.append(ProseFinding(segment.path, sentence.line, CHECK_FILLER, message))
    return findings


def check_sections(segments: list[ProseSegment]) -> list[ProseFinding]:
    """Check 4: sentences in ``## Summary`` and in each ``## Key ideas`` bullet."""
    findings: list[ProseFinding] = []
    summary: list[ProseSegment] = []
    for segment in segments:
        if segment.kind == SEGMENT_HEADING:
            continue
        name = segment.section.strip().lower()
        if name == SUMMARY_SECTION:
            summary.append(segment)
        elif name == KEY_IDEAS_SECTION and segment.kind in (SEGMENT_BULLET, SEGMENT_NUMBERED):
            count = len(split_sentences(segment))
            if count > KEY_IDEA_MAX_SENTENCES:
                message = f"Key ideas bullet has {count} sentences (limit {KEY_IDEA_MAX_SENTENCES})"
                findings.append(ProseFinding(segment.path, segment.line, CHECK_SECTION_LENGTH, message))
    if summary:
        count = sum(len(split_sentences(segment)) for segment in summary)
        if count > SUMMARY_MAX_SENTENCES:
            message = f"Summary has {count} sentences (limit {SUMMARY_MAX_SENTENCES})"
            findings.append(ProseFinding(summary[0].path, summary[0].line, CHECK_SECTION_LENGTH, message))
    return findings


def check_term_lock(segments: list[ProseSegment], avoid_map: dict[str, AvoidEntry]) -> list[ProseFinding]:
    """Check 5: every avoid term in a prose segment, headings included (FR-013).

    Segments are already masked, so inline code, fences and quotes are never
    matched. A finding's line is the line the found term starts on.
    """
    findings: list[ProseFinding] = []
    for segment in segments:
        for entry in avoid_map.values():
            for term in entry.terms:
                for match in find_term(segment.text, term):
                    line = segment.line + segment.text.count("\n", 0, match.start())
                    found = " ".join(match.group(0).split())
                    message = f"{found!r} is an avoid term; use the glossary term {entry.canonical!r}"
                    findings.append(ProseFinding(segment.path, line, CHECK_TERM_LOCK, message))
    return findings


def _is_glossary_page(rel: str, text: str) -> bool:
    if rel.startswith(f"{GLOSSARY_DIR}/"):
        return True
    try:
        return bool(yaml_lite.parse_frontmatter(text).get("page_type") == GLOSSARY_PAGE_TYPE)
    except ContractViolationError:
        return False


def lint_page_prose(path: str, text: str, avoid_map: dict[str, AvoidEntry] | None = None) -> list[ProseFinding]:
    """Checks 1-4 on one page, and check 5 when ``avoid_map`` is given, ordered by line.

    The term lock never runs on a glossary page, which names the avoid terms.
    """
    segments = scan_page(path, text)
    findings: list[ProseFinding] = []
    for segment in segments:
        findings.extend(check_segment(segment))
    findings.extend(check_sections(segments))
    if avoid_map and not _is_glossary_page(path, text):
        findings.extend(check_term_lock(segments, avoid_map))
    return sorted(findings, key=lambda finding: finding.line)


def run_prose_lint(
    wiki_dir: Path,
    *,
    paths: Iterable[str | Path] | None = None,
    avoid_format: bool = True,
) -> ProseLintResult:
    """Run prose checks 1-5 over the wiki's pages (FR-011, FR-013).

    Pages come from the health lint's page list (``schema/``, ``scripts/``
    and ``.audit/`` are excluded); ``log.md`` is exempt as append-only
    history. ``paths`` (wiki-relative) limits the pages scanned; the avoid
    map is always read from the whole glossary. ``avoid_format`` adds the
    glossary's avoid-format problems on scanned pages; turn it off when the
    health tier reports them in the same call (FR-005).
    """
    from .health_lint import _list_wiki_pages  # health_lint imports this module

    avoid_map, problems = load_avoid_map(wiki_dir)
    scoped = {Path(p).as_posix() for p in paths} if paths is not None else None
    findings: list[ProseFinding] = []
    checked = 0
    for page in _list_wiki_pages(wiki_dir):
        rel = page.relative_to(wiki_dir).as_posix()
        if rel == LOG_PAGE or (scoped is not None and rel not in scoped):
            continue
        checked += 1
        findings.extend(lint_page_prose(rel, _read_text_or_empty(page), avoid_map))
    if avoid_format:
        findings.extend(
            ProseFinding(problem.path, problem.line, CHECK_AVOID_FORMAT, problem.message)
            for problem in problems
            if scoped is None or problem.path in scoped
        )
    return ProseLintResult(findings=findings, pages_checked=checked)
