# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Structural linter: the six checks of the former bash linter, in Python.

Checks (per ``schema/lint-rules.md``):

1. Frontmatter present, well-formed (closing ``---`` within the first 50 lines), with the required keys.
2. ``page_type`` is one of the known types.
3. ``slug`` equals the filename stem (``<dir>/index.md`` uses the directory name) and is unique.
4. ``page_type`` matches the directory the page lives in.
5. Intra-wiki ``[text](path.md)`` links resolve to an existing file.
6. Every page except ``index.md`` and ``log.md`` is reachable from ``index.md``.

Pages under ``schema/``, ``scripts/`` and ``.audit/`` are not wiki content and
are skipped. Messages keep the wording of the bash linter so output is
unchanged for consumers that grep it.

``VALID_PAGE_TYPES``, ``PAGE_TYPE_DIRS`` and ``REQUIRED_KEYS`` are defined in
:mod:`wiki_studio.schema` and re-exported here for 0.1.0 compatibility.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from .schema import PAGE_TYPE_DIRS, REQUIRED_KEYS, SOURCELESS_PAGE_TYPES, VALID_PAGE_TYPES

EXCLUDED_DIRS: frozenset[str] = frozenset({"schema", "scripts", ".audit"})

MAX_FRONTMATTER_CLOSE_LINE = 50
INDEX_NAME = "index.md"
LOG_NAME = "log.md"

_FM_CLOSE_RE = re.compile(r"^---\s*$")
_MD_LINK_RE = re.compile(r"\]\(([^)]+)\)")
_SOURCES_KEY_RE = re.compile(r"^sources:\s*$")
_LIST_ITEM_RE = re.compile(r"^\s*-\s+")
_TOP_LEVEL_KEY_RE = re.compile(r"^[^\s-]")


def list_pages(wiki_dir: Path) -> list[Path]:
    """All ``*.md`` files under ``wiki_dir`` except those under the excluded top-level directories, sorted."""
    if not wiki_dir.is_dir():
        return []
    pages: list[Path] = []
    for path in sorted(wiki_dir.rglob("*.md")):
        if not path.is_file():
            continue
        parts = path.relative_to(wiki_dir).parts
        if parts and parts[0] in EXCLUDED_DIRS:
            continue
        pages.append(path)
    return pages


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _frontmatter(lines: list[str]) -> tuple[list[str] | None, int | None]:
    """Split off the frontmatter.

    Returns ``(body lines, 1-based line of the closing marker)``. Two failure shapes are
    distinguished for the two different violations: ``(None, 0)`` when line 1 is not the
    opening ``---``; ``(None, None)`` when the opening marker has no closing one.
    """
    if not lines or lines[0] != "---":
        return None, 0
    for i in range(1, len(lines)):
        if _FM_CLOSE_RE.match(lines[i]):
            return lines[1:i], i + 1
    return None, None


def _field(fm_lines: list[str], key: str) -> str:
    """First ``key: value`` line's value, with the key, following spaces and surrounding double quotes removed.

    Keys are matched at column 0 only, as the bash linter did: an indented ``key:`` inside a
    nested mapping is not a required top-level key.
    """
    prefix = key + ":"
    for line in fm_lines:
        if line.startswith(prefix):
            value = line[len(prefix) :].lstrip()
            if value.startswith('"'):
                value = value[1:]
            if value.endswith('"'):
                value = value[:-1]
            return value
    return ""


def _has_sources(fm_lines: list[str]) -> bool:
    """True when a ``sources:`` key is followed by at least one ``- `` list item."""
    in_sources = False
    for line in fm_lines:
        if _SOURCES_KEY_RE.match(line):
            in_sources = True
            continue
        if in_sources and _LIST_ITEM_RE.match(line):
            return True
        if in_sources and _TOP_LEVEL_KEY_RE.match(line):
            in_sources = False
    return False


def md_links(text: str) -> list[str]:
    """Intra-wiki ``.md`` link targets (fragment stripped); external, mailto and fragment-only links are dropped."""
    targets: list[str] = []
    for match in _MD_LINK_RE.finditer(text):
        raw = match.group(1)
        if not raw or raw.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = raw.split("#", 1)[0]
        if target and target.endswith(".md"):
            targets.append(target)
    return targets


def _canonical(path: Path) -> Path:
    """Resolve the directory part (symlinks included) and keep the file name, like ``cd dir && pwd``."""
    return path.parent.resolve() / path.name


def _link_resolves(page: Path, target: str, wiki_dir: Path, live_wiki_dir: Path | None) -> bool:
    """True when ``target`` (relative to ``page``) exists.

    A link that escapes the wiki (``../docs/x.md``) is checked at the live
    wiki's location when ``live_wiki_dir`` is given: a staged copy carries the
    wiki's pages but not its neighbours. Links inside the wiki are always
    judged against the tree being linted.
    """
    candidate = page.parent / target
    if candidate.exists():
        return True
    if live_wiki_dir is None:
        return False
    normalized = Path(os.path.normpath(candidate))
    if normalized.is_relative_to(Path(os.path.normpath(wiki_dir))):
        return False
    return (live_wiki_dir / page.parent.relative_to(wiki_dir) / target).exists()


def lint_wiki(wiki_dir: Path, *, live_wiki_dir: Path | None = None) -> list[str]:
    """Run the six structural checks over ``wiki_dir`` and return the violations (empty when clean).

    ``live_wiki_dir`` is where the wiki really lives when ``wiki_dir`` is a
    staged copy of it (``promote``): escape links are resolved there.
    """
    wiki_dir = Path(wiki_dir)
    violations: list[str] = []
    pages = list_pages(wiki_dir)
    slugs_seen: dict[str, str] = {}

    # ── Per-page checks ──────────────────────────────────────
    for page in pages:
        rel = page.relative_to(wiki_dir).as_posix()
        lines = _read(page).splitlines()
        fm_lines, close_line = _frontmatter(lines)
        if close_line == 0:
            violations.append(f"{rel}: missing opening '---' on line 1")
            continue
        if fm_lines is None or close_line is None:
            violations.append(f"{rel}: missing closing '---' for frontmatter")
            continue
        if close_line > MAX_FRONTMATTER_CLOSE_LINE:
            violations.append(f"{rel}: closing '---' beyond line {MAX_FRONTMATTER_CLOSE_LINE} (got line {close_line})")
            continue

        fields = {key: _field(fm_lines, key) for key in REQUIRED_KEYS}
        for key in REQUIRED_KEYS:
            if not fields[key]:
                violations.append(f"{rel}: missing required frontmatter key '{key}'")
        page_type = fields["page_type"]
        slug = fields["slug"]

        if page_type and page_type not in VALID_PAGE_TYPES:
            violations.append(f"{rel}: page_type '{page_type}' is not one of: {' '.join(VALID_PAGE_TYPES)}")

        # slug == filename stem; <dir>/index.md uses the directory name.
        stem = page.stem
        expected_slug = page.parent.name if stem == "index" and page.parent != wiki_dir else stem
        if slug and slug != expected_slug:
            violations.append(f"{rel}: slug '{slug}' should be '{expected_slug}'")
        if slug:
            prior = slugs_seen.get(slug)
            if prior is not None:
                violations.append(f"{rel}: duplicate slug '{slug}' (also in {prior})")
            else:
                slugs_seen[slug] = rel

        if page_type:
            expected_dir = PAGE_TYPE_DIRS.get(page_type, "")
            page_parent = Path(rel).parent.as_posix()
            if expected_dir and page_parent != expected_dir:
                violations.append(
                    f"{rel}: page_type '{page_type}' should live under '{expected_dir}/' but found in '{page_parent}/'"
                )

        if page_type not in SOURCELESS_PAGE_TYPES and not _has_sources(fm_lines):
            violations.append(f"{rel}: missing 'sources:' frontmatter (or empty list)")

    # ── Intra-wiki link integrity ────────────────────────────
    for page in pages:
        rel = page.relative_to(wiki_dir).as_posix()
        for target in md_links(_read(page)):
            if not _link_resolves(page, target, wiki_dir, live_wiki_dir):
                violations.append(f"{rel}: broken intra-wiki link → {target}")

    # ── Orphan check: BFS from index.md over links that stay inside the wiki ──
    index = wiki_dir / INDEX_NAME
    if not index.is_file():
        violations.append(f"wiki: missing {INDEX_NAME} at {index}")
        return violations

    wiki_canonical = wiki_dir.resolve()
    reached: set[Path] = {_canonical(index)}
    queue: list[Path] = [index]
    while queue:
        current = queue.pop(0)
        for target in md_links(_read(current)):
            resolved = current.parent / target
            if not resolved.is_file():
                continue
            canonical = _canonical(resolved)
            if not canonical.is_relative_to(wiki_canonical) or canonical in reached:
                continue
            reached.add(canonical)
            queue.append(resolved)
    for page in pages:
        rel = page.relative_to(wiki_dir).as_posix()
        if rel == LOG_NAME:
            continue
        if _canonical(page) not in reached:
            violations.append(f"{rel}: orphan — not reachable from {INDEX_NAME}")

    return violations
