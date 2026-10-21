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
# The result is advisory: write_patch_set_dir records it in plan.json and
# the CLI prints it; promote never reads it.

from __future__ import annotations

import re

from . import yaml_lite
from .errors import ContractViolationError
from .schema import FACT_UNITS

_FENCE_RE = re.compile(r"^\s*(```|~~~)")
# A backtick span; it may wrap onto the next line but never across a blank line.
_BACKTICK_RE = re.compile(r"`((?:[^`\n]|\n(?![ \t]*\n))+)`")
# `<file>:<line>` or `<file>:<line>-<line>`: a path segment with an extension, then a line number.
_PATH_LINE_RE = re.compile(r"(?<![\w./-])((?:[\w.-]+/)*[\w.-]+\.\w+):(\d+(?:-\d+)?)\b")
# `path: <x>` written in the body (for example a citation moved out of the frontmatter).
_BODY_PATH_RE = re.compile(r"(?<![\w-])path:[ \t]*([^\s`)\],]+)")
_UNIT_ALT = "|".join(re.escape(u) for u in sorted(FACT_UNITS, key=len, reverse=True))
_NUMBER_RE = re.compile(
    rf"(?<![\w.,])(\d{{1,3}}(?:,\d{{3}})+|\d+)(\.\d+)?[ \t]*\n?[ \t]*({_UNIT_ALT})(?![A-Za-z0-9])",
    re.IGNORECASE,
)


def _split_frontmatter(text: str) -> tuple[list[str], str]:
    """Frontmatter ``sources[].path`` values and the body; no frontmatter gives ``([], text)``."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], text
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body = "\n".join(lines[i + 1 :])
            try:
                sources = yaml_lite.parse_frontmatter(text).get("sources") or []
            except ContractViolationError:
                return [], body
            paths = [str(s["path"]).strip() for s in sources if isinstance(s, dict) and s.get("path")]
            return paths, body
    return [], text


def _without_fences(body: str) -> str:
    """The body with fenced code blocks blanked out (line count kept)."""
    out: list[str] = []
    fence: str | None = None
    for line in body.splitlines():
        m = _FENCE_RE.match(line)
        if fence is None and m:
            fence = m.group(1)
            out.append("")
        elif fence is not None:
            if line.strip().startswith(fence):
                fence = None
            out.append("")
        else:
            out.append(line)
    return "\n".join(out)


def _normalize_identifier(raw: str) -> str:
    ident = " ".join(raw.split())
    return ident[:-2] if ident.endswith("()") else ident


def _normalize_number(integer: str, fraction: str | None, unit: str) -> str:
    unit = unit.lower()
    number = integer.replace(",", "") + (fraction or "")
    return f"{number}{unit}" if unit == "%" else f"{number} {unit}"


def _facts(text: str) -> list[str]:
    """Every fact on the page, normalized, in first-seen order, without duplicates."""
    source_paths, body = _split_frontmatter(text)
    found: list[str] = list(source_paths)
    found += [m.group(1) for m in _BODY_PATH_RE.finditer(body)]
    found += [f"{m.group(1)}:{m.group(2)}" for m in _PATH_LINE_RE.finditer(body)]
    prose = _without_fences(body)
    found += [_normalize_identifier(m.group(1)) for m in _BACKTICK_RE.finditer(prose)]
    found += [_normalize_number(m.group(1), m.group(2), m.group(3)) for m in _NUMBER_RE.finditer(prose)]
    return list(dict.fromkeys(f for f in found if f))


def removed_facts(old: str, new: str) -> list[str]:
    """Facts in ``old`` that ``new`` no longer has, in the order ``old`` has them.

    A path-only citation counts as kept when the new page still cites that
    path with a line number.
    """
    kept = set(_facts(new))
    kept |= {fact.rsplit(":", 1)[0] for fact in kept if _PATH_LINE_RE.fullmatch(fact)}
    return [fact for fact in _facts(old) if fact not in kept]
