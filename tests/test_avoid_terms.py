# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Glossary avoid terms, avoid-format problems and the whole-word matcher (0.5.0 FR-004..FR-007)."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from tests.conftest import FIXTURES_DIR
from wiki_studio.health_lint import _check_missing_cross_links, _entity_mentions, lint_health
from wiki_studio.paths import WikiPaths
from wiki_studio.prose_lint import contains_term, find_term, load_avoid_map, parse_avoid_value

_FM = (
    "---\npage_type: {page_type}\nslug: {slug}\ntitle: {title}\nstatus: stable\n"
    "last_reviewed: 2026-10-20\n{extra}---\n\n"
)

# code-copilot-team layout: page-level H2s first, then entries closing with an italic line.
_CCT_GLOSSARY_INDEX = (
    "---\npage_type: glossary\nslug: glossary\ntitle: Glossary\nstatus: stable\nlast_reviewed: 2026-10-20\n---\n\n"
    "# Glossary\n\n## Definition\n\nProject terms.\n\n## Where it appears\n\nEverywhere.\n\n"
    "### origin gate\n\nAvoid: alignment check, origin check\n\nThe check that compares a spec with its origin.\n\n"
    "*Where it appears:* `scripts/check-origin-alignment.sh`\n\n"
    "### patch-set\n\nA plan plus previews.\n\n*Where it appears:* promote.\n"
)


def _page(page_type: str, slug: str, body: str, extra: str = "") -> str:
    return _FM.format(page_type=page_type, slug=slug, title=slug.title(), extra=extra) + body


class _WikiCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.wiki = self.root / "knowledge" / "wiki"
        self.wiki.mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, rel: str, text: str) -> None:
        path = self.wiki / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def glossary(self, slug: str, avoid_line: str, rest: str = "") -> None:
        self.write(f"glossary/{slug}.md", _page("glossary", slug, "# T\n\n## Definition\n\nD.\n", avoid_line + rest))


class TestAcceptedForms(_WikiCase):
    def test_frontmatter_unquoted(self) -> None:
        self.glossary("origin-gate", "avoid: alignment check, origin check\n")
        avoid_map, problems = load_avoid_map(self.wiki)
        self.assertEqual(problems, [])
        entry = avoid_map["origin-gate"]
        self.assertEqual(entry.terms, ("alignment check", "origin check"))
        self.assertEqual(entry.page, "glossary/origin-gate.md")
        self.assertIsNone(entry.anchor)

    def test_frontmatter_double_quoted(self) -> None:
        self.glossary("origin-gate", 'avoid: "x: y, z"\n')
        avoid_map, problems = load_avoid_map(self.wiki)
        self.assertEqual(problems, [])
        self.assertEqual(avoid_map["origin-gate"].terms, ("x: y", "z"))

    def test_fixture_index_with_avoid_line(self) -> None:
        text = (FIXTURES_DIR / "wiki" / "glossary" / "index.md").read_text(encoding="utf-8")
        text = text.replace("### patch-set\n\n", "### patch-set\n\nAvoid: changeset, edit bundle\n\n", 1)
        self.write("glossary/index.md", text)
        avoid_map, problems = load_avoid_map(self.wiki)
        self.assertEqual(problems, [])
        entry = avoid_map["patch-set"]
        self.assertEqual(entry.terms, ("changeset", "edit bundle"))
        self.assertEqual((entry.page, entry.anchor), ("glossary/index.md", "patch-set"))

    def test_code_copilot_team_index_layout(self) -> None:
        self.write("glossary/index.md", _CCT_GLOSSARY_INDEX)
        avoid_map, problems = load_avoid_map(self.wiki)
        self.assertEqual(problems, [])
        self.assertEqual(list(avoid_map), ["origin gate"])
        self.assertEqual(avoid_map["origin gate"].terms, ("alignment check", "origin check"))
        self.assertEqual(avoid_map["origin gate"].anchor, "origin-gate")

    def test_avoid_on_non_glossary_page_is_ignored(self) -> None:
        self.write("concepts/lint.md", _page("concept", "lint", "# Lint\n", "avoid: [broken, form\n"))
        self.assertEqual(load_avoid_map(self.wiki), ({}, []))


class TestRefusedForms(_WikiCase):
    def assert_one_problem(self, line: int | None = None) -> None:
        avoid_map, problems = load_avoid_map(self.wiki)
        self.assertEqual(avoid_map, {})
        self.assertEqual(len(problems), 1, problems)
        if line is not None:
            self.assertEqual(problems[0].line, line)

    def test_frontmatter_forms(self) -> None:
        cases = {
            "block list": "avoid:\n  - alignment check\n",
            "empty": "avoid:\n",
            "flow list": "avoid: [alignment check, origin check]\n",
            "single quoted": "avoid: 'alignment check'\n",
            "raw double quote": 'avoid: the "old" gate\n',
            "raw backslash": "avoid: C:\\cache\n",
            "escaped double quote": 'avoid: "the \\"old\\" gate"\n',
            "escaped backslash": 'avoid: "C:\\\\cache"\n',
            "empty term": "avoid: a,,b\n",
        }
        for name, line in cases.items():
            with self.subTest(form=name):
                self.glossary("origin-gate", line)
                self.assert_one_problem(line=7)

    def test_index_line_not_first(self) -> None:
        self.write("glossary/index.md", _CCT_GLOSSARY_INDEX.replace("Avoid: alignment", "Lead.\n\nAvoid: alignment"))
        self.assert_one_problem()

    def test_index_line_bulleted(self) -> None:
        self.write("glossary/index.md", _CCT_GLOSSARY_INDEX.replace("Avoid: alignment", "- Avoid: alignment"))
        self.assert_one_problem()

    def test_index_line_followed_by_bullets(self) -> None:
        text = _CCT_GLOSSARY_INDEX.replace("Avoid: alignment check, origin check", "Avoid:\n- alignment check")
        self.write("glossary/index.md", text)
        self.assert_one_problem()

    def test_one_term_under_two_canonicals(self) -> None:
        self.glossary("origin-gate", "avoid: alignment check, origin check\n")
        self.glossary("spec-gate", "avoid: alignment check\n")
        avoid_map, problems = load_avoid_map(self.wiki)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("alignment check", problems[0].message)
        self.assertEqual(avoid_map["origin-gate"].terms, ("origin check",))
        self.assertNotIn("spec-gate", avoid_map)

    def test_parse_value_names_the_character(self) -> None:
        self.assertIn('"', parse_avoid_value('the "old" gate')[1] or "")
        self.assertIn("\\", parse_avoid_value("C:\\cache")[1] or "")


class TestMatcher(unittest.TestCase):
    def test_no_match(self) -> None:
        cases = [
            ("the pre-origin-gate step", "origin-gate"),
            ("see lint-rules.md", "lint"),
            ("run the linter", "lint"),
            ("an origin checklist", "origin check"),
            ("an origin check-in", "origin check"),
            ("- ends with origin\n- check starts the next", "origin check"),
            ("ends with origin\n\ncheck after a blank line", "origin check"),
        ]
        for text, term in cases:
            with self.subTest(text=text):
                self.assertFalse(contains_term(text, term))
                self.assertEqual(find_term(text, term), [])

    def test_match(self) -> None:
        cases = [
            ("Run lint.", "lint"),
            ("the gate (origin-gate) runs", "origin-gate"),
            ("the wrapped origin\n  check in one paragraph", "origin check"),
            ("The ORIGIN CHECK", "origin check"),
        ]
        for text, term in cases:
            with self.subTest(text=text):
                self.assertTrue(contains_term(text, term))
        matches = find_term("lint here, lint there", "lint")
        self.assertEqual([m.start() for m in matches], [0, 11])


class TestMentions(_WikiCase):
    def _concept(self, slug: str, body: str) -> None:
        self.write(f"concepts/{slug}.md", _page("concept", slug, f"# {slug}\n\n{body}\n"))

    def test_synonym_only_page_triggers_missing_cross_link(self) -> None:
        self.glossary("origin-gate", "avoid: alignment check, origin check\n")
        for i in range(3):
            self._concept(f"page-{i}", "Run the alignment check before the build.")
        self.assertEqual(_entity_mentions("Run the alignment check.", ["origin-gate"]), set())
        self.assertEqual(
            _entity_mentions("Run the alignment check.", ["origin-gate"], {"origin-gate": ["alignment check"]}),
            {"origin-gate"},
        )
        findings = _check_missing_cross_links(self.wiki)
        flagged = [f for f in findings if f.pages[0] == "glossary/origin-gate.md"]
        self.assertEqual(len(flagged), 1, findings)
        self.assertEqual(flagged[0].pages[1:], ["concepts/page-0.md", "concepts/page-1.md", "concepts/page-2.md"])

    def test_index_avoid_line_is_not_a_mention(self) -> None:
        self._concept("lint", "The structural linter.")
        self._concept("page-a", "Run lint first.")
        self._concept("page-b", "Then lint again.")
        self.write(
            "glossary/index.md",
            _page("glossary", "glossary", "# Glossary\n\n### lint-gate\n\nAvoid: lint check\n\nThe gate.\n"),
        )
        self.assertEqual([f for f in _check_missing_cross_links(self.wiki) if f.pages[0] == "concepts/lint.md"], [])
        # One more real mention crosses the threshold, so the count itself works.
        self._concept("page-c", "And lint once more.")
        flagged = [f for f in _check_missing_cross_links(self.wiki) if f.pages[0] == "concepts/lint.md"]
        self.assertEqual(len(flagged), 1)
        self.assertNotIn("glossary/index.md", flagged[0].pages)

    def test_health_tier_reports_avoid_format(self) -> None:
        self.glossary("origin-gate", "avoid: [a, b]\n")
        result = lint_health(WikiPaths.for_root(self.root), backend=None)
        avoid = [f for f in result.findings if f.kind == "avoid-format"]
        self.assertEqual(len(avoid), 1)
        self.assertEqual(avoid[0].pages, ["glossary/origin-gate.md"])
        self.assertIn("line 7", avoid[0].description)

    def test_fixture_wiki_has_no_avoid_problems(self) -> None:
        shutil.copytree(FIXTURES_DIR / "wiki", self.wiki, dirs_exist_ok=True)
        self.assertEqual(load_avoid_map(self.wiki), ({}, []))


if __name__ == "__main__":
    unittest.main()
