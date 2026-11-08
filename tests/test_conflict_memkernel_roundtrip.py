# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.9.0 (US4): memkernel v0.6.0's page parser keeps a conflict callout (FR-020).

The parser functions below are copied verbatim from the pinned tag so the
evidence does not move when memkernel does. ``WikiPage`` is the one departure:
a standard-library dataclass with the same fields and defaults stands in for
the pydantic model, because pydantic is not a dependency of this package.
"""

from __future__ import annotations

import re
import unittest
from dataclasses import dataclass, field

from tests.test_conflict_callouts import _documented_example
from wiki_studio.yaml_lite import parse_frontmatter

_KNOWN_SCALARS = frozenset({"page_type", "slug", "title", "status", "last_reviewed"})

MID_BODY_PAGE = (
    "---\n"
    "page_type: decision\n"
    "slug: mid-body-callout\n"
    "title: Mid-body callout\n"
    "status: stable\n"
    "last_reviewed: 2026-11-07\n"
    "sources:\n"
    "  - issue: 12\n"
    "---\n"
    "\n"
    "# Mid-body callout\n"
    "\n"
    "## Decision\n"
    "\n"
    "The first paragraph makes the claim.\n"
    "\n"
    "> [!conflict] Disagrees with [Retry policy](../decisions/retry-policy.md)\n"
    "> This page: issue: 12. That page: pr: 22.\n"
    "\n"
    "The last paragraph still belongs to the page.\n"
)


# Copied from gosha70/memkernel src/memkernel/wiki/pages.py at tag v0.6.0,
# `WikiPage` lines 24-34 (citation verified 2026-11-07, see the spec FR-020), as a
# standard-library dataclass: the one departure from the source, where it is a
# pydantic model with the same fields and defaults. Test fixture only.
@dataclass
class WikiPage:
    """A single markdown page with its frontmatter."""

    page_type: str
    slug: str
    title: str
    status: str = "draft"
    last_reviewed: str = ""
    sources: list[dict[str, str]] = field(default_factory=list)
    body: str = ""
    extra: dict[str, str] = field(default_factory=dict)


# Copied from gosha70/memkernel src/memkernel/wiki/pages.py at tag v0.6.0,
# `_FRONTMATTER_RE` line 20 (citation verified 2026-11-07, see the spec FR-020). Test fixture only.
_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*\n?", re.DOTALL)


# Copied from gosha70/memkernel src/memkernel/wiki/pages.py at tag v0.6.0,
# `_unquote` lines 45-49 (citation verified 2026-11-07, see the spec FR-020). Test fixture only.
def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


# Copied from gosha70/memkernel src/memkernel/wiki/pages.py at tag v0.6.0,
# `_parse_frontmatter` lines 52-86 (citation verified 2026-11-07, see the spec FR-020). Test fixture only.
def _parse_frontmatter(block: str) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Parse the supported YAML subset into (scalars, sources)."""
    scalars: dict[str, str] = {}
    sources: list[dict[str, str]] = []
    in_sources = False
    current: dict[str, str] | None = None
    for raw in block.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indented = raw[0] in " \t"
        line = raw.strip()
        if not indented:
            in_sources = False
            current = None
            key, sep, value = line.partition(":")
            if not sep:
                continue
            key = key.strip()
            if key == "sources":
                in_sources = True
                continue
            scalars[key] = _unquote(value)
            continue
        if not in_sources:
            continue
        if line.startswith("- "):
            current = {}
            sources.append(current)
            line = line[2:].strip()
        if current is None:
            continue
        key, sep, value = line.partition(":")
        if sep:
            current[key.strip()] = _unquote(value)
    return scalars, sources


# Copied from gosha70/memkernel src/memkernel/wiki/pages.py at tag v0.6.0,
# `parse_page` lines 89-110 (citation verified 2026-11-07, see the spec FR-020). Test fixture only.
def parse_page(text: str) -> WikiPage | None:
    """Parse a markdown document with YAML frontmatter. Returns None if it has none."""
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return None
    scalars, sources = _parse_frontmatter(match.group(1))
    body = text[match.end() :]
    known = {"page_type", "slug", "title", "status", "last_reviewed"}
    page_type = scalars.get("page_type", "")
    slug = scalars.get("slug", "")
    if not page_type or not slug:
        return None
    return WikiPage(
        page_type=page_type,
        slug=slug,
        title=scalars.get("title", slug),
        status=scalars.get("status", "draft"),
        last_reviewed=scalars.get("last_reviewed", ""),
        sources=sources,
        body=body.strip("\n") + "\n" if body.strip() else "",
        extra={k: v for k, v in scalars.items() if k not in known},
    )


# Copied from gosha70/memkernel src/memkernel/wiki/pages.py at tag v0.6.0,
# `_quote` lines 113-117 (citation verified 2026-11-07, see the spec FR-020). Test fixture only.
def _quote(value: str) -> str:
    """Quote a scalar when YAML would otherwise misread it."""
    if value == "" or any(ch in value for ch in ":#\"'[]{}") or value != value.strip():
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


# Copied from gosha70/memkernel src/memkernel/wiki/pages.py at tag v0.6.0,
# `render_page` lines 120-142 (citation verified 2026-11-07, see the spec FR-020). Test fixture only.
def render_page(page: WikiPage) -> str:
    """Render a WikiPage back to markdown with frontmatter."""
    lines = [
        "---",
        f"page_type: {page.page_type}",
        f"slug: {page.slug}",
        f"title: {_quote(page.title)}",
        f"status: {page.status}",
        f"last_reviewed: {page.last_reviewed}",
    ]
    for key, value in page.extra.items():
        lines.append(f"{key}: {_quote(value)}")
    if page.sources:
        lines.append("sources:")
        for source in page.sources:
            first = True
            for key, value in source.items():
                prefix = "  - " if first else "    "
                lines.append(f"{prefix}{key}: {_quote(value)}")
                first = False
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + page.body


def _frontmatter_lines(text: str) -> list[str]:
    """The lines between the opening and closing ``---`` delimiters."""
    lines = text.splitlines()
    return lines[1 : lines.index("---", 1)]


def _body_after_frontmatter(text: str) -> str:
    """Everything after the closing ``---``, with the blank line there removed (the one accepted difference)."""
    lines = text.splitlines()
    return "\n".join(lines[lines.index("---", 1) + 1 :]).lstrip("\n")


class TestMemkernelRoundTrip(unittest.TestCase):
    def assert_page_keeps_its_callout(self, text: str) -> WikiPage:
        page = parse_page(text)
        self.assertIsNotNone(page, "memkernel did not parse the page")
        assert page is not None

        callout = "\n".join(line for line in text.splitlines() if line.startswith(">"))
        self.assertIn("[!conflict]", callout, "the page carries no callout to test")
        self.assertIn(callout, page.body, "the callout is not in the body byte for byte")

        frontmatter = parse_frontmatter(text)
        self.assertEqual(page.sources, frontmatter["sources"], "the sources entries changed")
        self.assertEqual(
            set(page.extra), set(frontmatter) - _KNOWN_SCALARS - {"sources"}, "the parse added a frontmatter key"
        )

        rendered = render_page(page)
        self.assertEqual(_frontmatter_lines(rendered), _frontmatter_lines(text), "a frontmatter line changed")
        self.assertEqual(
            _body_after_frontmatter(rendered),
            _body_after_frontmatter(text),
            "render changed more than the blank line after the closing '---'",
        )

        again = parse_page(rendered)
        self.assertIsNotNone(again)
        assert again is not None
        self.assertEqual(again.body, page.body, "parse -> render -> parse changed the body")
        return page

    def test_the_documented_example_pages_keep_their_callouts(self) -> None:
        example = _documented_example()
        self.assertEqual(len(example), 2)
        for rel, text in example:
            with self.subTest(page=rel):
                self.assert_page_keeps_its_callout(text)

    def test_a_callout_in_the_middle_of_the_body_survives(self) -> None:
        page = self.assert_page_keeps_its_callout(MID_BODY_PAGE)
        self.assertTrue(page.body.startswith("# Mid-body callout\n\n## Decision\n"))
        self.assertTrue(page.body.endswith("The last paragraph still belongs to the page.\n"))


if __name__ == "__main__":
    unittest.main()
