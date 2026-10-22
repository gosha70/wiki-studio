# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Prose scanner, sentence splitter and `lint --prose` checks 1-4 (0.5.0 FR-010, FR-011)."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from tests.conftest import FIXTURES_DIR
from wiki_studio.prose_lint import (
    CHECK_FILLER,
    CHECK_SECTION_LENGTH,
    CHECK_SEMICOLON,
    CHECK_SENTENCE_LENGTH,
    CODE_TOKEN,
    ProseSegment,
    lint_page_prose,
    run_prose_lint,
    scan_page,
    split_sentences,
)
from wiki_studio.schema import (
    FILLER_PHRASES,
    KEY_IDEA_MAX_SENTENCES,
    PROSE_ABBREVIATIONS,
    PROSE_MAX_WORDS,
    PROSE_MAX_WORDS_NUMBERED,
    SUMMARY_MAX_SENTENCES,
)

_FM = "---\npage_type: concept\nslug: demo\ntitle: Demo\nstatus: stable\nlast_reviewed: 2026-10-20\n---\n\n"
_PATH = "concepts/demo.md"


def _words(n: int) -> str:
    """A sentence of exactly ``n`` words."""
    return "Alpha " + " ".join(["word"] * (n - 1)) + "."


def _checks(body: str, path: str = _PATH) -> list[str]:
    return [finding.check for finding in lint_page_prose(path, _FM + body)]


def _texts(body: str, path: str = _PATH) -> list[str]:
    return [segment.text for segment in scan_page(path, _FM + body)]


class ConstantsTest(unittest.TestCase):
    def test_fr011_limits_and_lists(self) -> None:
        self.assertEqual(PROSE_MAX_WORDS, 25)
        self.assertEqual(PROSE_MAX_WORDS_NUMBERED, 20)
        self.assertEqual(SUMMARY_MAX_SENTENCES, 4)
        self.assertEqual(KEY_IDEA_MAX_SENTENCES, 2)
        for phrase in ("it is important to note", "in order to", "ensure that"):
            self.assertIn(phrase, FILLER_PHRASES)
        self.assertEqual(set(PROSE_ABBREVIATIONS), {"e.g.", "i.e.", "etc.", "vs."})


class SkipRulesTest(unittest.TestCase):
    LONG_BAD = _words(30)[:-1] + "; in order to fail."

    def _assert_nothing(self, body: str, path: str = _PATH) -> None:
        self.assertEqual(lint_page_prose(path, _FM + body), [])

    def test_frontmatter_is_skipped(self) -> None:
        segments = scan_page(_PATH, _FM + "Body text.\n")
        self.assertEqual([s.text for s in segments], ["Body text."])
        self.assertEqual(segments[0].line, 9)

    def test_backtick_fence_is_skipped(self) -> None:
        self._assert_nothing(f"```bash\n{self.LONG_BAD}\n```\n")

    def test_tilde_fence_is_skipped_and_backticks_do_not_close_it(self) -> None:
        self._assert_nothing(f"~~~\n```\n{self.LONG_BAD}\n~~~\n")

    def test_shorter_fence_inside_a_longer_one_does_not_close_it(self) -> None:
        self._assert_nothing(f"````markdown\n```\n{self.LONG_BAD}\n```\n````\n")
        self._assert_nothing(f"~~~~\n~~~\n{self.LONG_BAD}\n~~~\n~~~~\n")
        texts = _texts(f"Before.\n\n````md\n```\n{self.LONG_BAD}\n```\n````\n\nAfter.\n")
        self.assertEqual(texts, ["Before.", "After."])

    def test_closing_fence_may_be_longer_but_carries_no_info_string(self) -> None:
        self.assertEqual(_texts(f"```\n{self.LONG_BAD}\n````\n\nAfter.\n"), ["After."])
        self._assert_nothing(f"```\n```bash\n{self.LONG_BAD}\n```\n")

    def test_indented_backticks_are_code_not_a_fence(self) -> None:
        # FR-010: indented code after a blank line ends at the next prose; the prose stays visible.
        body = f"Intro.\n\n    ```\n    code\n\nCall `required_id` within 5 ms; {self.LONG_BAD}\n"
        self.assertEqual(_texts(body), ["Intro.", f"Call `…` within 5 ms; {self.LONG_BAD}"])
        self.assertTrue(lint_page_prose(_PATH, _FM + body))
        self.assertEqual(_texts("\t```\n\tcode\n\nAfter.\n"), ["After."])
        self.assertEqual(_texts("   ```\nhidden; text\n   ```\n\nAfter.\n"), ["After."])

    def test_inline_code_span_line_does_not_open_a_fence(self) -> None:
        self.assertEqual(_texts("```x```\n\nAfter.\n"), ["`…`", "After."])
        self.assertEqual(_texts("~~~ `x`\nhidden\n~~~\n\nAfter.\n"), ["After."])

    def test_table_rows_are_skipped(self) -> None:
        self._assert_nothing(f"| a | b |\n|---|---|\n| {self.LONG_BAD} | x |\n")

    def test_blockquotes_are_skipped(self) -> None:
        self._assert_nothing(f"> {self.LONG_BAD}\n> more; quoted\n")

    def test_html_comments_are_skipped(self) -> None:
        self._assert_nothing(f"<!-- {self.LONG_BAD} -->\n\n<!--\n{self.LONG_BAD}\n-->\n")

    def test_text_around_an_inline_comment_is_kept(self) -> None:
        self.assertEqual(_texts("Kept text <!-- a; b --> and more.\n"), ["Kept text  and more."])

    def test_index_avoid_line_is_skipped(self) -> None:
        body = "### origin gate\n\nAvoid: alignment check; origin check\n\nThe gate.\n"
        texts = _texts(body, path="glossary/index.md")
        self.assertEqual(texts, ["origin gate", "The gate."])

    def test_indented_code_after_blank_line_is_skipped(self) -> None:
        self._assert_nothing(f"Intro.\n\n    {self.LONG_BAD}\n\n    more; code\n\nAfter.\n")

    def test_indented_line_without_blank_line_joins_the_paragraph(self) -> None:
        self.assertEqual(_texts("First line\n    second line.\n"), ["First line\nsecond line."])

    def test_indented_text_in_a_list_after_blank_line_is_prose(self) -> None:
        texts = _texts("- Item one.\n\n    Continued; here.\n")
        self.assertEqual(texts, ["Item one.", "Continued; here."])

    def test_inline_code_is_one_token_and_hides_semicolons(self) -> None:
        segment = scan_page(_PATH, _FM + "Run `a; b; c` now.\n")[0]
        self.assertEqual(segment.text, f"Run {CODE_TOKEN} now.")
        self.assertEqual(_checks("Run `a; b; c` now.\n"), [])

    def test_link_is_replaced_by_its_text(self) -> None:
        self.assertEqual(_texts("See [the guide](../x.md#a;b) now.\n"), ["See the guide now."])

    def test_bare_url_is_one_token(self) -> None:
        text = "Read https://example.com/a;b?Q=1. Then stop.\n"
        self.assertEqual(_checks(text), [])
        segment = scan_page(_PATH, _FM + text)[0]
        self.assertEqual(len(split_sentences(segment)), 2)


class SegmentsTest(unittest.TestCase):
    def test_wrapped_paragraph_is_one_segment(self) -> None:
        segments = scan_page(_PATH, _FM + "One line\nwraps here\nand ends.\n\nNext paragraph.\n")
        self.assertEqual([(s.kind, s.line) for s in segments], [("paragraph", 9), ("paragraph", 13)])
        self.assertEqual(segments[0].text, "One line\nwraps here\nand ends.")

    def test_each_list_item_is_a_segment(self) -> None:
        body = "- first item\n  wraps.\n- second.\n1. step one.\n2) step two.\n"
        segments = scan_page(_PATH, _FM + body)
        self.assertEqual(
            [(s.kind, s.line) for s in segments], [("bullet", 9), ("bullet", 11), ("numbered", 12), ("numbered", 13)]
        )
        self.assertEqual(segments[0].text, "first item\nwraps.")

    def test_headings_are_segments_with_their_section(self) -> None:
        segments = scan_page(_PATH, _FM + "# Demo\n\n## Summary\n\nText.\n\n### Detail\n\nMore.\n")
        self.assertEqual(
            [(s.kind, s.text, s.section) for s in segments],
            [
                ("heading", "Demo", ""),
                ("heading", "Summary", "Summary"),
                ("paragraph", "Text.", "Summary"),
                ("heading", "Detail", "Summary"),
                ("paragraph", "More.", "Summary"),
            ],
        )

    def test_thematic_break_is_not_a_bullet(self) -> None:
        self.assertEqual(_texts("Above.\n\n---\n\n* * *\n\nBelow.\n"), ["Above.", "Below."])


class SentenceSplitterTest(unittest.TestCase):
    def _split(self, text: str, line: int = 1) -> list[tuple[int, str]]:
        segment = ProseSegment(_PATH, line, "paragraph", text)
        return [(s.line, s.text) for s in split_sentences(segment)]

    def test_splits_before_a_capital_a_backtick_or_the_end(self) -> None:
        got = self._split(f"One. Two! Three? {CODE_TOKEN} is four.")
        self.assertEqual([t for _, t in got], ["One.", "Two!", "Three?", f"{CODE_TOKEN} is four."])

    def test_no_split_before_lowercase_or_inside_a_version(self) -> None:
        self.assertEqual(len(self._split("Use 0.4.1 here. and lowercase continues.")), 1)

    def test_abbreviations_are_not_boundaries(self) -> None:
        for abbreviation in PROSE_ABBREVIATIONS:
            with self.subTest(abbreviation=abbreviation):
                self.assertEqual(len(self._split(f"Tools, {abbreviation} Vale, are slow.")), 1)

    def test_sentence_line_is_its_first_line(self) -> None:
        got = self._split("First sentence\nends here. Second starts\nhere and ends.", line=10)
        self.assertEqual([line for line, _ in got], [10, 11])
        self.assertEqual(got[1][1], "Second starts here and ends.")


class ChecksTest(unittest.TestCase):
    def test_check1_sentence_over_25_words(self) -> None:
        self.assertEqual(_checks(_words(26) + "\n"), [CHECK_SENTENCE_LENGTH])
        self.assertEqual(_checks(_words(25) + "\n"), [])

    def test_check1_numbered_item_limit_is_20(self) -> None:
        self.assertEqual(_checks(f"1. {_words(21)}\n"), [CHECK_SENTENCE_LENGTH])
        self.assertEqual(_checks(f"1. {_words(20)}\n"), [])
        self.assertEqual(_checks(f"- {_words(21)}\n"), [])

    def test_check1_counts_a_wrapped_sentence_once(self) -> None:
        words = _words(26).split()
        body = " ".join(words[:13]) + "\n" + " ".join(words[13:]) + "\n"
        findings = lint_page_prose(_PATH, _FM + body)
        self.assertEqual([(f.check, f.line) for f in findings], [(CHECK_SENTENCE_LENGTH, 9)])

    def test_check1_masked_code_counts_as_one_word(self) -> None:
        code = "`" + " ".join(["x"] * 30) + "`"
        self.assertEqual(_checks(f"Run {code} now.\n"), [])

    def test_check2_semicolon(self) -> None:
        self.assertEqual(_checks("One part; another part.\n"), [CHECK_SEMICOLON])
        self.assertEqual(_checks("One part. Another part.\n"), [])

    def test_check3_filler_phrase(self) -> None:
        self.assertEqual(_checks("It is important to note that X holds.\n"), [CHECK_FILLER])
        self.assertEqual(_checks("Run it in order to build.\n"), [CHECK_FILLER])
        self.assertEqual(_checks("Ensure that X holds.\n"), [CHECK_FILLER])
        self.assertEqual(_checks("Keep the pages in ordered lists to build.\n"), [])

    def test_check4_summary_over_4_sentences(self) -> None:
        five = "## Summary\n\nOne. Two. Three.\n\nFour. Five.\n\n## Key ideas\n\nSix.\n"
        findings = lint_page_prose(_PATH, _FM + five)
        self.assertEqual([(f.check, f.line) for f in findings], [(CHECK_SECTION_LENGTH, 11)])
        self.assertIn("5 sentences", findings[0].message)
        self.assertEqual(_checks("## Summary\n\nOne. Two. Three. Four.\n\n## Key ideas\n\nFive. Six.\n"), [])

    def test_check4_key_ideas_bullet_over_2_sentences(self) -> None:
        body = "## Key ideas\n\n- One. Two.\n- One. Two. Three.\n"
        findings = lint_page_prose(_PATH, _FM + body)
        self.assertEqual([(f.check, f.line) for f in findings], [(CHECK_SECTION_LENGTH, 12)])
        self.assertEqual(_checks("## Related\n\n- One. Two. Three.\n"), [])

    def test_headings_are_exempt_from_checks_1_to_4(self) -> None:
        self.assertEqual(_checks(f"## {_words(30)[:-1]}; in order to\n"), [])

    def test_finding_line_is_the_sentence_line(self) -> None:
        body = "Short intro\nsentence. This one; has\na semicolon.\n"
        findings = lint_page_prose(_PATH, _FM + body)
        self.assertEqual([(f.check, f.line) for f in findings], [(CHECK_SEMICOLON, 10)])
        self.assertEqual(findings[0].path, _PATH)


class RunProseLintTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.wiki = Path(self._tmp.name).resolve() / "wiki"
        shutil.copytree(FIXTURES_DIR / "wiki", self.wiki)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_fixture_wiki_completes(self) -> None:
        result = run_prose_lint(FIXTURES_DIR / "wiki")
        pages = [p for p in (FIXTURES_DIR / "wiki").rglob("*.md") if p.name != "log.md" or p.parent.name != "wiki"]
        self.assertEqual(result.pages_checked, len(pages))
        for finding in result.findings:
            self.assertTrue((FIXTURES_DIR / "wiki" / finding.path).is_file())

    def test_no_finding_inside_code_tables_quotes_or_comments(self) -> None:
        bad = _words(30)[:-1] + "; in order to fail."
        body = (
            f"```\n{bad}\n```\n\n~~~\n{bad}\n~~~\n\n| {bad} |\n\n> {bad}\n\n<!-- {bad} -->\n\n"
            f"Use `{bad}` once.\n\nVisible; prose.\n"
        )
        (self.wiki / "concepts" / "noisy.md").write_text(_FM + body, encoding="utf-8")
        result = run_prose_lint(self.wiki, paths=["concepts/noisy.md"])
        self.assertEqual(result.pages_checked, 1)
        self.assertEqual([(f.check, f.line) for f in result.findings], [(CHECK_SEMICOLON, 25)])

    def test_log_md_is_exempt(self) -> None:
        log = self.wiki / "log.md"
        log.write_text(log.read_text(encoding="utf-8") + "\nOne part; another part.\n", encoding="utf-8")
        result = run_prose_lint(self.wiki)
        self.assertNotIn("log.md", {f.path for f in result.findings})
        self.assertEqual(run_prose_lint(self.wiki, paths=["log.md"]).pages_checked, 0)

    def test_paths_limit_the_pages_scanned(self) -> None:
        (self.wiki / "concepts" / "noisy.md").write_text(_FM + "One part; another.\n", encoding="utf-8")
        scoped = run_prose_lint(self.wiki, paths=[Path("concepts/prefer-small-commits.md")])
        self.assertEqual(scoped.pages_checked, 1)
        self.assertNotIn("concepts/noisy.md", {f.path for f in scoped.findings})
        self.assertIn("concepts/noisy.md", {f.path for f in run_prose_lint(self.wiki).findings})

    def test_missing_wiki_dir_checks_nothing(self) -> None:
        result = run_prose_lint(self.wiki / "absent")
        self.assertEqual((result.findings, result.pages_checked), ([], 0))


if __name__ == "__main__":
    unittest.main()
