# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wikistudio.lint — the six structural checks (FR-005), including the ports of the former shell-linter tests."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from wikistudio.lint import EXCLUDED_DIRS, PAGE_TYPE_DIRS, VALID_PAGE_TYPES, lint_wiki, list_pages, md_links

_FM = (
    "---\npage_type: {page_type}\nslug: {slug}\ntitle: {title}\nstatus: stable\nlast_reviewed: 2026-05-06\n{extra}---\n"
)
_SOURCES = "sources:\n  - path: README.md\n    sha: abc\n"


def _page(
    wiki: Path,
    rel: str,
    *,
    page_type: str,
    slug: str | None = None,
    title: str = "T",
    body: str = "Body.\n",
    sources: bool = True,
    extra: str = "",
) -> Path:
    target = wiki / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    fm_extra = (_SOURCES if sources and page_type not in ("index", "log") else "") + extra
    target.write_text(
        _FM.format(page_type=page_type, slug=slug or target.stem, title=title, extra=fm_extra)
        + "\n# "
        + title
        + "\n\n"
        + body,
        encoding="utf-8",
    )
    return target


def _clean_wiki(wiki: Path) -> None:
    """index + log + two cross-linked concepts: zero violations."""
    _page(
        wiki,
        "index.md",
        page_type="index",
        body="## Concepts\n\n- [Alpha](concepts/alpha.md)\n- [Beta](concepts/beta.md)\n",
    )
    _page(wiki, "log.md", page_type="log")
    _page(wiki, "concepts/alpha.md", page_type="concept", body="See [beta](beta.md).\n")
    _page(wiki, "concepts/beta.md", page_type="concept", body="See [alpha](alpha.md).\n")


class _WikiCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wikistudio-lint-")
        self.root = Path(self._tmp.name)
        self.wiki = self.root / "knowledge" / "wiki"
        self.wiki.mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def assertViolation(self, violations: list[str], fragment: str) -> None:  # noqa: N802 (unittest style)
        self.assertTrue(any(fragment in v for v in violations), f"{fragment!r} not in {violations}")


class TestCleanWiki(_WikiCase):
    def test_clean_wiki_has_no_violations(self) -> None:
        _clean_wiki(self.wiki)
        self.assertEqual(lint_wiki(self.wiki), [])

    def test_list_pages_is_sorted_and_skips_excluded_dirs(self) -> None:
        _clean_wiki(self.wiki)
        for excluded in EXCLUDED_DIRS:
            (self.wiki / excluded).mkdir()
            (self.wiki / excluded / "not-a-page.md").write_text("no frontmatter\n", encoding="utf-8")
        rels = [p.relative_to(self.wiki).as_posix() for p in list_pages(self.wiki)]
        self.assertEqual(rels, ["concepts/alpha.md", "concepts/beta.md", "index.md", "log.md"])

    def test_missing_wiki_dir_reports_missing_index(self) -> None:
        violations = lint_wiki(self.root / "nope")
        self.assertEqual(len(violations), 1)
        self.assertViolation(violations, "missing index.md")


class TestFrontmatter(_WikiCase):
    def setUp(self) -> None:
        super().setUp()
        _clean_wiki(self.wiki)

    def test_missing_opening_marker(self) -> None:
        (self.wiki / "concepts" / "alpha.md").write_text("# Alpha\n", encoding="utf-8")
        self.assertViolation(lint_wiki(self.wiki), "concepts/alpha.md: missing opening '---' on line 1")

    def test_missing_closing_marker(self) -> None:
        (self.wiki / "concepts" / "alpha.md").write_text("---\npage_type: concept\n# Alpha\n", encoding="utf-8")
        self.assertViolation(lint_wiki(self.wiki), "concepts/alpha.md: missing closing '---' for frontmatter")

    def test_closing_marker_beyond_line_50(self) -> None:
        text = "---\npage_type: concept\nslug: alpha\n" + "x: y\n" * 60 + "---\n# Alpha\n"
        (self.wiki / "concepts" / "alpha.md").write_text(text, encoding="utf-8")
        self.assertViolation(lint_wiki(self.wiki), "concepts/alpha.md: closing '---' beyond line 50 (got line 64)")

    def test_missing_required_keys(self) -> None:
        (self.wiki / "concepts" / "alpha.md").write_text(
            "---\npage_type: concept\nslug: alpha\n" + _SOURCES + "---\n# Alpha\n", encoding="utf-8"
        )
        violations = lint_wiki(self.wiki)
        for key in ("title", "status", "last_reviewed"):
            self.assertViolation(violations, f"concepts/alpha.md: missing required frontmatter key '{key}'")

    def test_quoted_values_are_unquoted(self) -> None:
        _page(self.wiki, "concepts/alpha.md", page_type="concept", slug='"alpha"', body="See [beta](beta.md).\n")
        self.assertEqual(lint_wiki(self.wiki), [])


class TestPageTypeSlugAndPlacement(_WikiCase):
    def setUp(self) -> None:
        super().setUp()
        _clean_wiki(self.wiki)

    def test_unknown_page_type(self) -> None:
        _page(self.wiki, "concepts/alpha.md", page_type="essay", body="See [beta](beta.md).\n")
        violations = lint_wiki(self.wiki)
        self.assertViolation(
            violations, "concepts/alpha.md: page_type 'essay' is not one of: " + " ".join(VALID_PAGE_TYPES)
        )

    def test_slug_must_match_filename_stem(self) -> None:
        _page(self.wiki, "concepts/alpha.md", page_type="concept", slug="alpha-x", body="See [beta](beta.md).\n")
        self.assertViolation(lint_wiki(self.wiki), "concepts/alpha.md: slug 'alpha-x' should be 'alpha'")

    def test_slugs_must_be_unique(self) -> None:
        _page(self.wiki, "concepts/beta.md", page_type="concept", slug="alpha", body="See [alpha](alpha.md).\n")
        violations = lint_wiki(self.wiki)
        self.assertViolation(violations, "concepts/beta.md: slug 'alpha' should be 'beta'")
        self.assertViolation(violations, "concepts/beta.md: duplicate slug 'alpha' (also in concepts/alpha.md)")

    def test_directory_index_uses_directory_name_as_slug(self) -> None:
        index = self.wiki / "index.md"
        index.write_text(index.read_text(encoding="utf-8") + "- [Glossary](glossary/index.md)\n", encoding="utf-8")
        _page(self.wiki, "glossary/index.md", page_type="glossary", slug="glossary")
        self.assertEqual(lint_wiki(self.wiki), [])

    def test_page_type_must_match_directory(self) -> None:
        _page(self.wiki, "concepts/alpha.md", page_type="incident", body="See [beta](beta.md).\n")
        self.assertViolation(
            lint_wiki(self.wiki),
            "concepts/alpha.md: page_type 'incident' should live under 'incidents/' but found in 'concepts/'",
        )

    def test_every_page_type_has_a_directory(self) -> None:
        self.assertEqual(set(PAGE_TYPE_DIRS), set(VALID_PAGE_TYPES))


class TestSources(_WikiCase):
    def setUp(self) -> None:
        super().setUp()
        _clean_wiki(self.wiki)

    def test_missing_sources_is_a_violation_except_for_index_and_log(self) -> None:
        _page(self.wiki, "concepts/alpha.md", page_type="concept", sources=False, body="See [beta](beta.md).\n")
        violations = lint_wiki(self.wiki)
        self.assertViolation(violations, "concepts/alpha.md: missing 'sources:' frontmatter (or empty list)")
        self.assertFalse(any(v.startswith(("index.md", "log.md")) for v in violations))

    def test_empty_sources_list_is_a_violation(self) -> None:
        _page(
            self.wiki,
            "concepts/alpha.md",
            page_type="concept",
            sources=False,
            extra="sources:\n",
            body="See [beta](beta.md).\n",
        )
        self.assertViolation(lint_wiki(self.wiki), "concepts/alpha.md: missing 'sources:'")


class TestLinksAndReachability(_WikiCase):
    def setUp(self) -> None:
        super().setUp()
        _clean_wiki(self.wiki)

    def test_md_links_extraction(self) -> None:
        text = "[a](x.md) [b](y.md#frag) [c](https://e.com/z.md) [d](mailto:x) [e](#frag) [f](img.png) [g](../out.md)"
        self.assertEqual(md_links(text), ["x.md", "y.md", "../out.md"])

    def test_broken_intra_wiki_link(self) -> None:
        _page(self.wiki, "concepts/alpha.md", page_type="concept", body="See [gone](gone.md) and [beta](beta.md).\n")
        self.assertViolation(lint_wiki(self.wiki), "concepts/alpha.md: broken intra-wiki link → gone.md")

    def test_external_links_are_ignored(self) -> None:
        _page(
            self.wiki, "concepts/alpha.md", page_type="concept", body="[x](https://example.com/a.md) [beta](beta.md)\n"
        )
        self.assertEqual(lint_wiki(self.wiki), [])

    def test_escape_link_to_project_file_resolves(self) -> None:
        (self.root / "README.md").write_text("# root\n", encoding="utf-8")
        _page(
            self.wiki, "concepts/alpha.md", page_type="concept", body="[readme](../../../README.md) [beta](beta.md)\n"
        )
        self.assertEqual(lint_wiki(self.wiki), [])

    def test_orphan_page_is_reported(self) -> None:
        _page(self.wiki, "concepts/gamma.md", page_type="concept")
        self.assertViolation(lint_wiki(self.wiki), "concepts/gamma.md: orphan — not reachable from index.md")

    def test_page_reachable_through_another_page_is_not_an_orphan(self) -> None:
        _page(self.wiki, "concepts/gamma.md", page_type="concept")
        _page(self.wiki, "concepts/beta.md", page_type="concept", body="[alpha](alpha.md) [gamma](gamma.md)\n")
        self.assertEqual(lint_wiki(self.wiki), [])

    def test_log_is_exempt_from_the_orphan_check(self) -> None:
        self.assertEqual(lint_wiki(self.wiki), [])
        self.assertNotIn("- [Log](log.md)", (self.wiki / "index.md").read_text(encoding="utf-8"))

    def test_missing_index_is_reported(self) -> None:
        (self.wiki / "index.md").unlink()
        violations = lint_wiki(self.wiki)
        self.assertViolation(violations, f"wiki: missing index.md at {self.wiki / 'index.md'}")
        self.assertFalse(any("orphan" in v for v in violations))


class TestLiveWikiDir(_WikiCase):
    """``live_wiki_dir``: escape links resolve at the live wiki; intra-wiki links stay authoritative in the copy."""

    def setUp(self) -> None:
        super().setUp()
        _clean_wiki(self.wiki)
        (self.root / "knowledge" / "guide.md").write_text("# guide\n", encoding="utf-8")
        _page(self.wiki, "concepts/alpha.md", page_type="concept", body="[guide](../../guide.md) [beta](beta.md)\n")
        self.copy = self.root / "staged-copy"
        shutil.copytree(self.wiki, self.copy)

    def test_live_wiki_passes_and_bare_copy_fails(self) -> None:
        self.assertEqual(lint_wiki(self.wiki), [])
        self.assertViolation(lint_wiki(self.copy), "concepts/alpha.md: broken intra-wiki link → ../../guide.md")

    def test_copy_with_live_wiki_dir_resolves_escape_links(self) -> None:
        self.assertEqual(lint_wiki(self.copy, live_wiki_dir=self.wiki), [])

    def test_intra_wiki_links_are_judged_against_the_copy(self) -> None:
        (self.copy / "concepts" / "beta.md").unlink()
        violations = lint_wiki(self.copy, live_wiki_dir=self.wiki)
        self.assertViolation(violations, "concepts/alpha.md: broken intra-wiki link → beta.md")


class TestAuditExclusion(_WikiCase):
    """Ports of the shell-linter tests: .audit/ (and schema/, scripts/) are never linted."""

    def test_lint_output_excludes_audit_path(self) -> None:
        _clean_wiki(self.wiki)
        audit_dir = self.wiki / ".audit"
        audit_dir.mkdir()
        (audit_dir / "ingest-log.md").write_text("<!-- ingest-log schema v1 -->\n\n{}\n", encoding="utf-8")
        (self.wiki / "schema").mkdir()
        (self.wiki / "schema" / "page-types.md").write_text("# not a page\n", encoding="utf-8")
        violations = lint_wiki(self.wiki)
        self.assertEqual(violations, [])
        self.assertFalse(any(".audit/" in v or "schema/" in v for v in violations))

    def test_audit_exclusion_is_load_bearing(self) -> None:
        self.assertIn(".audit", EXCLUDED_DIRS)
        self.assertIn("schema", EXCLUDED_DIRS)
        self.assertIn("scripts", EXCLUDED_DIRS)


class TestSourcesInlineForm(_WikiCase):
    def test_inline_empty_list_is_a_violation(self) -> None:
        _clean_wiki(self.wiki)
        _page(
            self.wiki,
            "concepts/alpha.md",
            page_type="concept",
            sources=False,
            extra="sources: []\n",
            body="[b](beta.md)\n",
        )
        self.assertViolation(lint_wiki(self.wiki), "concepts/alpha.md: missing 'sources:' frontmatter (or empty list)")


if __name__ == "__main__":
    unittest.main()
