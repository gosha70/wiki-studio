# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""`wiki-studio lint --prose`: the term lock, the advisory default and the strict tier (0.5.0 FR-012, FR-013)."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from tests.conftest import FIXTURES_DIR, run_cli
from wiki_studio import api
from wiki_studio.paths import WikiPaths
from wiki_studio.prose_lint import CHECK_AVOID_FORMAT, CHECK_TERM_LOCK

_FM = (
    "---\npage_type: concept\nslug: {slug}\ntitle: {slug}\nstatus: stable\nlast_reviewed: 2026-10-20\n"
    "sources:\n  - path: README.md\n    sha: abc\n---\n\n"
)
_AVOID_LINE = "Avoid: changeset, edit bundle\n\n"


class _ProseWikiCase(unittest.TestCase):
    """The fixture wiki under ``knowledge/wiki`` of a temporary root."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-prose-")
        self.root = Path(self._tmp.name).resolve()
        self.wiki = self.root / "knowledge" / "wiki"
        shutil.copytree(FIXTURES_DIR / "wiki", self.wiki)
        self.paths = WikiPaths.for_root(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def lint(self, *flags: str):
        return run_cli("--root", str(self.root), "lint", *flags)

    def set_glossary_avoid(self, avoid_line: str = _AVOID_LINE) -> None:
        index = self.wiki / "glossary" / "index.md"
        text = index.read_text(encoding="utf-8")
        index.write_text(text.replace("### patch-set\n\n", "### patch-set\n\n" + avoid_line, 1), encoding="utf-8")

    def write_concept(self, slug: str, body: str) -> str:
        rel = f"concepts/{slug}.md"
        (self.wiki / rel).write_text(_FM.format(slug=slug) + body, encoding="utf-8")
        index = self.wiki / "index.md"
        index.write_text(index.read_text(encoding="utf-8") + f"- [{slug}]({rel}) — test page.\n", encoding="utf-8")
        return rel

    def term_lock_lines(self, stderr: str) -> list[str]:
        return [line.strip() for line in stderr.splitlines() if f"[{CHECK_TERM_LOCK}]" in line]


class TestProseCli(_ProseWikiCase):
    def test_fixture_wiki_is_advisory(self) -> None:
        result = self.lint("--prose")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout + result.stderr, r"prose: (clean|\d+ finding\(s\) across \d+ pages)")

    def test_planted_term_lock_finding_names_file_line_found_and_canonical(self) -> None:
        self.set_glossary_avoid()
        rel = self.write_concept("bundles", "# Bundles\n\nPromote applies the Edit Bundle.\n")
        advisory = self.lint("--prose")
        self.assertEqual(advisory.returncode, 0, advisory.stderr)
        self.assertRegex(advisory.stderr, r"prose: \d+ finding\(s\) across \d+ pages")
        self.assertEqual(
            self.term_lock_lines(advisory.stderr),
            [f"{rel}:14 [{CHECK_TERM_LOCK}] 'Edit Bundle' is an avoid term; use the glossary term 'patch-set'"],
        )
        strict = self.lint("--prose", "--strict")
        self.assertEqual(strict.returncode, 1)

    def test_strict_with_no_prose_findings_exits_zero(self) -> None:
        clean = self.write_concept("clean", "# Clean\n\nPromote applies the patch-set.\n")
        result = self.lint("--prose", "--strict", "--paths", clean)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("prose: clean (1 pages checked, 0 findings).", result.stdout)

    def test_heading_is_checked_and_glossary_page_is_not(self) -> None:
        self.set_glossary_avoid()
        rel = self.write_concept("heading", "# The changeset\n\nPromote applies it.\n")
        lines = self.term_lock_lines(self.lint("--prose").stderr)
        self.assertEqual([line.split(" ")[0] for line in lines], [f"{rel}:12"])

    def test_paths_scope_pages_but_avoid_map_is_whole_glossary(self) -> None:
        self.set_glossary_avoid()
        target = self.write_concept("target", "# Target\n\nA changeset is applied.\n")
        self.write_concept("other", "# Other\n\nAn edit bundle is applied.\n")
        result = self.lint("--prose", "--paths", target)
        self.assertIn("across 1 pages", result.stderr)
        lines = self.term_lock_lines(result.stderr)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith(f"{target}:14 "))

    def test_no_term_lock_inside_inline_code_fences_or_quotes(self) -> None:
        self.set_glossary_avoid()
        body = (
            "# Masked\n\nRun `edit bundle` here.\n\n```\nchangeset\n```\n\n~~~\nedit bundle\n~~~\n\n"
            "> A changeset is quoted.\n\nPlain text.\n"
        )
        rel = self.write_concept("masked", body)
        result = self.lint("--prose", "--paths", rel)
        self.assertEqual(self.term_lock_lines(result.stderr), [])

    def test_prose_and_health_report_a_malformed_list_once(self) -> None:
        self.set_glossary_avoid("Avoid: [changeset, edit bundle]\n\n")
        both = self.lint("--prose", "--health")
        self.assertEqual(both.returncode, 0, both.stderr)
        self.assertEqual(both.stderr.count("flow list is not supported"), 1, both.stderr)
        self.assertEqual(self.lint("--prose").stderr.count("flow list is not supported"), 1)
        self.assertIn(f"[{CHECK_AVOID_FORMAT}]", self.lint("--prose").stderr)

    def test_help_names_prose_and_shared_flags(self) -> None:
        result = self.lint("--help")
        self.assertEqual(result.returncode, 0)
        text = " ".join(result.stdout.split())
        self.assertIn("--prose", text)
        self.assertEqual(text.count("With --health or --prose"), 1)
        self.assertIn("--health or --prose, any knowledge-health or prose finding", text)


class TestApiLintProse(_ProseWikiCase):
    def test_prose_result_matches_cli_findings(self) -> None:
        self.set_glossary_avoid()
        rel = self.write_concept("bundles", "# Bundles\n\nPromote applies the changeset.\n")
        self.assertIsNone(api.lint(self.paths).prose)
        result = api.lint(self.paths, prose=True, only=[rel])
        assert result.prose is not None
        self.assertEqual(result.prose.pages_checked, 1)
        found = [(f.path, f.line, f.check) for f in result.prose.findings]
        self.assertEqual(found, [(rel, 14, CHECK_TERM_LOCK)])
        self.assertTrue(result.passed)
        self.assertFalse(api.lint(self.paths, prose=True, strict=True, only=[rel]).passed)

    def test_avoid_format_goes_to_health_when_both_run(self) -> None:
        self.set_glossary_avoid("Avoid: [changeset]\n\n")
        both = api.lint(self.paths, prose=True, health=True)
        assert both.prose is not None and both.health is not None
        self.assertFalse(any(f.check == CHECK_AVOID_FORMAT for f in both.prose.findings))
        self.assertEqual(sum(f.kind == "avoid-format" for f in both.health.findings), 1)
        alone = api.lint(self.paths, prose=True)
        assert alone.prose is not None
        self.assertEqual(sum(f.check == CHECK_AVOID_FORMAT for f in alone.prose.findings), 1)


if __name__ == "__main__":
    unittest.main()
