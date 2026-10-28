# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Structural linter: the six checks of the former bash linter, in Python.

Checks (per ``schema/lint-rules.md``):

1. Frontmatter present, well-formed (closing ``---`` within the first 50 lines), with the required keys.
2. ``page_type`` is one of the known types.
3. ``slug`` equals the filename stem (``<dir>/index.md`` uses the directory name) and is unique; an
   optional ``page_id`` matches ``pg-<32 lowercase hex>`` and is unique, and an optional
   ``superseded_by`` names another existing page that is not superseded in turn (ADR-0002).
4. ``page_type`` matches the directory the page lives in.
5. Every local link target is classified and checked (the link rule, FR-013):
   web (``http``, ``https``) and ``mailto`` targets are not filesystem links;
   a ``.md`` target that resolves inside the wiki is a wiki-page link and must
   exist; a ``.md`` target outside the wiki and any non-``.md`` target (image,
   data or source file) is a source reference and must resolve inside the
   project root or an allowed source root; an absolute target, a target that
   leaves the root, one that passes through a symlink, and an ``index.md``
   entry outside the wiki are violations. ``../`` targets that stay inside
   the root are legal.
6. Every page except ``index.md`` and ``log.md`` is reachable from ``index.md``
   over wiki-page links.

A symlink inside the wiki (file or directory) is a violation: pages are
regular files, and ``promote`` refuses to stage a symlink. Pages under
``schema/``, ``scripts/`` and ``.audit/`` are not wiki content and are
skipped. Messages keep the wording of the bash linter where a check is
unchanged so output stays stable for consumers that grep it.

``VALID_PAGE_TYPES``, ``PAGE_TYPE_DIRS`` and ``REQUIRED_KEYS`` are defined in
:mod:`wiki_studio.schema` and re-exported here for 0.1.0 compatibility.
"""

from __future__ import annotations

import os
import posixpath
import re
from pathlib import Path
from typing import TYPE_CHECKING

from .paths import CONTAIN_ABSOLUTE, CONTAIN_SYMLINK, ContainmentError, contain, default_root, is_absolute_path
from .schema import (
    PAGE_ID_KEY,
    PAGE_ID_PATTERN,
    PAGE_TYPE_DIRS,
    REQUIRED_KEYS,
    SOURCELESS_PAGE_TYPES,
    SUPERSEDED_BY_KEY,
    VALID_PAGE_TYPES,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

EXCLUDED_DIRS: frozenset[str] = frozenset({"schema", "scripts", ".audit"})

MAX_FRONTMATTER_CLOSE_LINE = 50
INDEX_NAME = "index.md"
LOG_NAME = "log.md"
PAGE_SUFFIX = ".md"

# Link targets that are not filesystem paths (the link rule, FR-013).
NON_FILESYSTEM_SCHEMES: tuple[str, ...] = ("http://", "https://", "mailto:")

_FM_CLOSE_RE = re.compile(r"^---\s*$")
_PAGE_ID_RE = re.compile(PAGE_ID_PATTERN)
_MD_LINK_RE = re.compile(r"\]\(([^)]+)\)")
# An optional link title after the target: ``[t](x.png "Title")``.
_LINK_TITLE_RE = re.compile(r"""\s+(?:"[^"]*"|'[^']*')\s*$""")
_SOURCES_KEY_RE = re.compile(r"^sources:\s*$")
_LIST_ITEM_RE = re.compile(r"^\s*-\s+")
_TOP_LEVEL_KEY_RE = re.compile(r"^[^\s-]")


def _walk_wiki(wiki_dir: Path) -> list[tuple[Path, list[str], list[str]]]:
    """``os.walk`` over the wiki without following symlinks, the excluded top-level directories pruned."""
    found: list[tuple[Path, list[str], list[str]]] = []
    for dirpath, dirnames, filenames in os.walk(wiki_dir, followlinks=False):
        base = Path(dirpath)
        if base == wiki_dir:
            dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        found.append((base, list(dirnames), filenames))
        # A symlinked directory is reported by ``symlinks_in`` and never descended into.
        dirnames[:] = [d for d in dirnames if not (base / d).is_symlink()]
    return found


def list_pages(wiki_dir: Path) -> list[Path]:
    """All ``*.md`` regular files under ``wiki_dir`` except under the excluded top-level directories, sorted.

    A symlink is not a page and is never followed (see :func:`symlinks_in`).
    """
    if not wiki_dir.is_dir():
        return []
    pages: list[Path] = []
    for base, _dirnames, filenames in _walk_wiki(wiki_dir):
        for name in filenames:
            path = base / name
            if name.endswith(PAGE_SUFFIX) and not path.is_symlink() and path.is_file():
                pages.append(path)
    return sorted(pages)


def symlinks_in(wiki_dir: Path) -> list[str]:
    """Wiki-relative POSIX paths of every symlink (file or directory) under ``wiki_dir`` outside the excluded dirs."""
    if not wiki_dir.is_dir():
        return []
    links: list[str] = []
    for base, dirnames, filenames in _walk_wiki(wiki_dir):
        for name in (*dirnames, *filenames):
            if (base / name).is_symlink():
                links.append((base / name).relative_to(wiki_dir).as_posix())
    return sorted(links)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _utf8_violation(path: Path, rel: str) -> str | None:
    """The violation for a page whose bytes are not valid UTF-8, else None (0.8.0, FR-003).

    Decodes strictly; :func:`_read` keeps replacing undecodable bytes for the
    checks that still read the page.
    """
    try:
        data = path.read_bytes()
    except OSError:
        return None
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return f"{rel}: not valid UTF-8 ({exc.reason} at byte {exc.start})"
    return None


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
    """Every local link target in ``text`` (fragment and title stripped), in order of appearance.

    Pages, images, data and source files alike: a non-``.md`` local target is
    part of the containment boundary (FR-013). Web (``http``, ``https``),
    ``mailto`` and fragment-only links are not filesystem links and are
    dropped. :func:`md_page_links` is the wiki-page view used for reachability.
    """
    targets: list[str] = []
    for match in _MD_LINK_RE.finditer(text):
        raw = match.group(1)
        if not raw or raw.startswith((*NON_FILESYSTEM_SCHEMES, "#")):
            continue
        target = _LINK_TITLE_RE.sub("", raw.split("#", 1)[0])
        if target:
            targets.append(target)
    return targets


def md_page_links(text: str) -> list[str]:
    """The ``.md`` targets among :func:`md_links`: the links that can reach another wiki page."""
    return [target for target in md_links(text) if target.endswith(PAGE_SUFFIX)]


def _canonical(path: Path) -> Path:
    """Resolve the directory part (symlinks included) and keep the file name, like ``cd dir && pwd``."""
    return path.parent.resolve() / path.name


def _link_violation(
    rel: str,
    target: str,
    *,
    wiki_dir: Path,
    live_wiki_dir: Path,
    boundaries: Sequence[Path],
) -> str | None:
    """Classify one local link target of page ``rel`` and return its violation, or None when it is legal.

    The target is resolved from the page's directory at the live wiki (a
    staged copy carries the wiki's pages but not its neighbours) with
    :func:`wiki_studio.paths.contain`, so a symlink on the way and an
    absolute target are refused before anything else. A ``.md`` target that
    lands inside the wiki is a wiki-page link and must exist in the tree
    being linted; any other target is a source reference and must exist
    inside the first of ``boundaries`` (the root, then the allowed source
    roots) that contains it. A root ``index.md`` entry must land inside the
    wiki.
    """
    page_dir = posixpath.dirname(rel)
    candidate = posixpath.join(page_dir, target) if page_dir else target
    live_real = live_wiki_dir.resolve()
    try:
        real: Path | None = contain(candidate, live_wiki_dir)
    except ContainmentError as exc:
        if exc.reason == CONTAIN_ABSOLUTE:
            return f"{rel}: absolute link target → {target}"
        if exc.reason == CONTAIN_SYMLINK:
            return f"{rel}: link target passes through a symlink → {target}"
        real = None
    if real is not None:
        # Inside the wiki: a page link, or a source reference the wiki carries itself (an image).
        in_tree = wiki_dir / real.relative_to(live_real)
        if target.endswith(PAGE_SUFFIX):
            return None if in_tree.is_file() else f"{rel}: broken intra-wiki link → {target}"
        return None if in_tree.exists() else f"{rel}: broken source reference → {target}"
    if rel == INDEX_NAME:
        return f"{rel}: index entry outside the wiki → {target}"
    for boundary in boundaries:
        try:
            real = contain(candidate, boundary, base=live_wiki_dir)
        except ContainmentError as exc:
            if exc.reason == CONTAIN_SYMLINK:
                return f"{rel}: link target passes through a symlink → {target}"
            continue
        return None if real.exists() else f"{rel}: broken source reference → {target}"
    return f"{rel}: link target escapes the project root → {target}"


def _superseded_by_violation(
    rel: str, target: str, wiki_dir: Path, pages: set[str], superseded: set[str]
) -> str | None:
    """Check one ``superseded_by`` value of page ``rel`` (a wiki-relative path); its violation, or None (FR-034)."""
    prefix = f"{rel}: {SUPERSEDED_BY_KEY}"
    if not target:
        return f"{prefix} is empty (expected a wiki-relative page path)"
    if is_absolute_path(target):
        return f"{prefix} target is absolute → {target}"
    normalised = posixpath.normpath(target)
    if normalised == ".." or normalised.startswith("../"):
        return f"{prefix} target escapes the wiki → {target}"
    if normalised == rel:
        return f"{prefix} target is the page itself → {target}"
    if normalised not in pages:
        if os.path.lexists(wiki_dir / normalised):
            return f"{prefix} target is not a page → {target}"
        return f"{prefix} target does not exist → {target}"
    if normalised in superseded:
        return f"{prefix} target is itself superseded (no chains) → {target}"
    return None


def lint_wiki(
    wiki_dir: Path,
    *,
    live_wiki_dir: Path | None = None,
    root: Path | None = None,
    source_roots: Sequence[Path] = (),
) -> list[str]:
    """Run the structural checks (UTF-8 first, 0.8.0) over ``wiki_dir`` and return the violations (empty when clean).

    ``live_wiki_dir`` is where the wiki really lives when ``wiki_dir`` is a
    staged copy of it (``promote``): link targets are resolved there. ``root``
    is the project root that bounds source references (default: the git
    toplevel containing the wiki, else the wiki directory itself, as
    ``WikiPaths`` would resolve it) and ``source_roots`` the directories
    ``--source-root`` admits besides it.
    """
    wiki_dir = Path(wiki_dir)
    live = Path(live_wiki_dir) if live_wiki_dir is not None else wiki_dir
    boundaries: list[Path] = [Path(root) if root is not None else default_root(wiki_dir), *map(Path, source_roots)]
    violations: list[str] = []
    pages = list_pages(wiki_dir)
    slugs_seen: dict[str, str] = {}
    page_ids: dict[str, list[str]] = {}
    superseded: dict[str, str] = {}
    # Pages whose bytes are not UTF-8: one violation each, and their other checks are skipped.
    not_utf8: set[str] = set()

    # ── Symlinks: not pages, never followed, refused by promote ──
    for rel in symlinks_in(wiki_dir):
        violations.append(f"{rel}: symlink inside the wiki (pages and their directories must be regular files)")

    # ── Per-page checks ──────────────────────────────────────
    for page in pages:
        rel = page.relative_to(wiki_dir).as_posix()
        encoding_problem = _utf8_violation(page, rel)
        if encoding_problem is not None:
            violations.append(encoding_problem)
            not_utf8.add(rel)
            continue
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

        # The optional page identity (ADR-0002): well formed, and unique across the wiki.
        if any(line.startswith(f"{PAGE_ID_KEY}:") for line in fm_lines):
            page_id = _field(fm_lines, PAGE_ID_KEY)
            if _PAGE_ID_RE.fullmatch(page_id) is None:
                violations.append(f"{rel}: malformed {PAGE_ID_KEY} '{page_id}' (expected pg- and 32 lowercase hex)")
            else:
                page_ids.setdefault(page_id, []).append(rel)

        if any(line.startswith(f"{SUPERSEDED_BY_KEY}:") for line in fm_lines):
            superseded[rel] = _field(fm_lines, SUPERSEDED_BY_KEY).strip()

    page_rels = {page.relative_to(wiki_dir).as_posix() for page in pages}
    for rel, target in superseded.items():
        problem = _superseded_by_violation(rel, target, wiki_dir, page_rels, set(superseded))
        if problem is not None:
            violations.append(problem)

    for page_id, holders in page_ids.items():
        if len(holders) > 1:
            for rel in holders:
                others = ", ".join(other for other in holders if other != rel)
                violations.append(f"{rel}: duplicate {PAGE_ID_KEY} '{page_id}' (also in {others})")

    # ── The link rule: every local target classified and checked ──
    for page in pages:
        rel = page.relative_to(wiki_dir).as_posix()
        if rel in not_utf8:
            continue
        for target in md_links(_read(page)):
            problem = _link_violation(rel, target, wiki_dir=wiki_dir, live_wiki_dir=live, boundaries=boundaries)
            if problem is not None:
                violations.append(problem)

    # ── Orphan check: BFS from index.md over wiki-page links that stay inside the wiki ──
    index = wiki_dir / INDEX_NAME
    if not index.is_file():
        violations.append(f"wiki: missing {INDEX_NAME} at {index}")
        return violations

    wiki_canonical = wiki_dir.resolve()
    reached: set[Path] = {_canonical(index)}
    queue: list[Path] = [index]
    while queue:
        current = queue.pop(0)
        for target in md_page_links(_read(current)):
            resolved = current.parent / target
            if resolved.is_symlink() or not resolved.is_file():
                continue
            canonical = _canonical(resolved)
            if not canonical.is_relative_to(wiki_canonical) or canonical in reached:
                continue
            reached.add(canonical)
            queue.append(resolved)
    for page in pages:
        rel = page.relative_to(wiki_dir).as_posix()
        if rel == LOG_NAME or rel in not_utf8:
            continue
        if _canonical(page) not in reached:
            violations.append(f"{rel}: orphan — not reachable from {INDEX_NAME}")

    return violations
