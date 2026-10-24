# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# wiki-studio.fact_diff — facts an `update` edit removes from a live page.
#
# A rewrite for plain prose may drop a fact by accident. removed_facts()
# extracts three kinds of fact from the old and the new page, compares them
# as sets over the whole page and returns what the new page lost:
#   (a) citations: frontmatter `sources[].path` values, `path: <x>` and
#       `<file>:<line>` references in the body;
#   (b) inline backticked identifiers;
#   (c) numbers with a unit from schema.FACT_UNITS.
# Whole-page sets make a moved citation or a reflowed paragraph a no-op.
# The check is a heuristic over those three kinds of token: it does not
# detect a change of meaning, a reworded claim or a dropped sentence that
# carries no citation, identifier or quantity.
# The result is advisory: write_patch_set_dir records it in plan.json and
# the CLI prints it; promote never reads it.

from __future__ import annotations

import re

from . import yaml_lite
from .errors import ContractViolationError
from .prose_lint import closes_fence, open_fence
from .schema import FACT_UNITS

# A backtick span; it may wrap onto the next line but never across a blank line.
_BACKTICK_RE = re.compile(r"`((?:[^`\n]|\n(?![ \t]*\n))+)`")
# `<file>:<line>` or `<file>:<line>-<line>`: a path segment with an extension, then a line number.
_PATH_LINE_RE = re.compile(r"(?<![\w./-])((?:[\w.-]+/)*[\w.-]+\.\w+):(\d+(?:-\d+)?)\b")
# `path: <x>` written in the body (for example a citation moved out of the frontmatter).
_BODY_PATH_RE = re.compile(r"(?<![\w-])path:[ \t]*([^\s`)\],]+)")
_UNIT_ALT = "|".join(re.escape(u) for u in sorted(FACT_UNITS, key=len, reverse=True))
# A minus sign is part of the number ("-5 ms"); a range ("5-10 ms") is not, because
# the lookbehind refuses a sign glued to a word character. The integer part may be
# empty when a fraction follows (".5 s").
_NUMBER_RE = re.compile(
    rf"(?<![\w.,])(-?)(\d{{1,3}}(?:,\d{{3}})+|\d+|(?=\.\d))(\.\d+)?[ \t]*\n?[ \t]*({_UNIT_ALT})(?![A-Za-z0-9])",
    re.IGNORECASE,
)


# Prefix of the ``fact_check_error`` the plan writer records when the live page
# could not be read at all; the CLI prints such an error as "not compared".
FACT_ERROR_UNREADABLE = "live page not readable"


def _split_frontmatter(text: str) -> tuple[list[str], str, str | None]:
    """Frontmatter ``sources[].path`` values, the body, and why the sources could not be read, if they could not.

    No frontmatter gives ``([], text, None)``. A ``sources`` key that is not a
    list of mappings is reported rather than silently yielding no paths, so a
    dropped citation on such a page is never hidden behind a clean comparison.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], text, None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body = "\n".join(lines[i + 1 :])
            try:
                sources = yaml_lite.parse_frontmatter(text).get("sources")
            except ContractViolationError as exc:
                return [], body, f"frontmatter could not be parsed ({exc})"
            if sources is None:
                return [], body, None
            if not isinstance(sources, list) or not all(isinstance(entry, dict) for entry in sources):
                return [], body, "frontmatter `sources` is not a list of mappings"
            paths = [str(entry["path"]).strip() for entry in sources if entry.get("path")]
            return paths, body, None
    return [], text, None


def _without_fences(body: str) -> str:
    """The body with fenced code blocks blanked out (line count kept).

    A fence under a deep list item sits four or more spaces in; it counts
    when a matching close follows. An unclosed fence at the margin runs to
    the end of the page; an unclosed indented one is plain text.
    """
    lines = body.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        opened = open_fence(lines[i], indented=True)
        if opened is not None:
            close = next((j for j in range(i + 1, len(lines)) if closes_fence(lines[j], opened, indented=True)), None)
            if close is None and open_fence(lines[i]) is not None:
                close = len(lines) - 1
            if close is not None:
                out.extend([""] * (close - i + 1))
                i = close + 1
                continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def _normalize_identifier(raw: str) -> str:
    ident = " ".join(raw.split())
    return ident[:-2] if ident.endswith("()") else ident


def _normalize_number(sign: str, integer: str, fraction: str | None, unit: str) -> str:
    unit = unit.lower()
    number = sign + (integer.replace(",", "") or "0") + (fraction or "")
    return f"{number}{unit}" if unit == "%" else f"{number} {unit}"


def _facts_checked(text: str) -> tuple[list[str], str | None]:
    """Every fact on the page, normalized, in first-seen order, without duplicates, and any sources problem.

    All three kinds are taken from the fence-free text: a ``path:line``
    reference or a ``path:`` line inside a fenced block is a code sample, not
    a citation, exactly as a backticked word or a number there is not a fact.
    """
    source_paths, body, error = _split_frontmatter(text)
    prose = _without_fences(body)
    found: list[str] = list(source_paths)
    found += [m.group(1) for m in _BODY_PATH_RE.finditer(prose)]
    found += [f"{m.group(1)}:{m.group(2)}" for m in _PATH_LINE_RE.finditer(prose)]
    found += [_normalize_identifier(m.group(1)) for m in _BACKTICK_RE.finditer(prose)]
    found += [_normalize_number(*m.groups()) for m in _NUMBER_RE.finditer(prose)]
    return list(dict.fromkeys(f for f in found if f)), error


def removed_facts_checked(old: str, new: str) -> tuple[list[str], str | None]:
    """:func:`removed_facts` plus the reason, if any, that a page's ``sources`` could not be compared.

    When either page's frontmatter ``sources`` is malformed, the body facts
    are still compared and the second value names the page and the problem;
    the plan writer records it as ``fact_check_error`` beside any warnings.
    """
    new_facts, new_error = _facts_checked(new)
    old_facts, old_error = _facts_checked(old)
    kept = set(new_facts)
    kept |= {fact.rsplit(":", 1)[0] for fact in kept if _PATH_LINE_RE.fullmatch(fact)}
    removed = [fact for fact in old_facts if fact not in kept]
    problems = [f"live page: {old_error}" if old_error else "", f"new content: {new_error}" if new_error else ""]
    problem = "; ".join(x for x in problems if x)
    return removed, (f"sources not compared ({problem})" if problem else None)


def removed_facts(old: str, new: str) -> list[str]:
    """Facts in ``old`` that ``new`` no longer has, in the order ``old`` has them.

    A path-only citation counts as kept when the new page still cites that
    path with a line number. A number and its unit may be separated by
    spaces or by one line break with only whitespace around it (a wrapped
    line); sentence punctuation after the number, or a blank line, ends the
    number and no unit is joined to it. This is a heuristic and that rule is
    its contract.
    """
    return removed_facts_checked(old, new)[0]
