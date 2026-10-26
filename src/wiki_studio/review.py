# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wiki_studio.review — how a page is named for review (read side).

A page's **canonical path** is its wiki-relative path normalised with
``posixpath.normpath``, with forward slashes and no leading ``./`` or ``/``,
so ``./concepts/x.md`` and ``concepts/x.md`` are one page. A page's **key**
is its ``page_id`` when it carries a well-formed one, else its canonical path
(FR-016). Approval records, ``review_state`` and findings use the key.
"""

from __future__ import annotations

import posixpath
from pathlib import PurePath

from .proposal import is_page_id
from .schema import PAGE_ID_KEY


def canonical_path(path: str) -> str:
    """The canonical wiki-relative form of ``path``; ``ValueError`` when it names the wiki itself or leaves it."""
    text = PurePath(path).as_posix().lstrip("/")
    rel = posixpath.normpath(text) if text else "."
    if rel == "." or rel == ".." or rel.startswith("../"):
        raise ValueError(f"not a wiki-relative page path: {path!r}")
    return rel


def frontmatter_page_id(text: str) -> str | None:
    """The raw ``page_id`` value of the page's frontmatter (column-0 key, one pair of double quotes removed), or None.

    Read as the structural linter reads it, so a value lint accepts is the
    value the page key uses.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    prefix = f"{PAGE_ID_KEY}:"
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        if line.startswith(prefix):
            value = line[len(prefix) :].strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1]
            return value
    return None


def page_key(path: str, text: str) -> str:
    """The page's ``page_id`` when its frontmatter carries a well-formed one, else :func:`canonical_path`."""
    page_id = frontmatter_page_id(text)
    if page_id is not None and is_page_id(page_id):
        return page_id
    return canonical_path(path)
