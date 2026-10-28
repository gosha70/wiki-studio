# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.8.0 (US1, FR-003): a page that is not valid UTF-8 is one structural violation, never a silent empty read."""

from __future__ import annotations

from tests.test_discovery import HAS_FTS5, RANKER_FTS5, RANKERS, DiscoveryCase
from wiki_studio import api
from wiki_studio.errors import PromoteValidationError
from wiki_studio.lint import lint_wiki
from wiki_studio.proposal import PageEdit
from wiki_studio.wiki_state import _read_text_or_empty

BAD_PAGE = "concepts/twin-alpha.md"
LOG_LINE = "- 2026-10-27 — an unrelated log entry"


class Utf8Case(DiscoveryCase):
    def setUp(self) -> None:
        super().setUp()
        self.assertEqual(lint_wiki(self.wiki, root=self.root), [], "the fixture starts clean")
        page = self.page(BAD_PAGE)
        self.good = page.read_bytes()
        self.bad = self.good.replace(b"Plums ripen", b"Pl\xffums ripen")
        page.write_bytes(self.bad)
        self.bad_offset = self.bad.index(b"\xff")

    def reencode(self) -> None:
        self.page(BAD_PAGE).write_bytes(self.bad.decode("latin-1").encode("utf-8"))

    def log_only_proposal(self, name: str):  # noqa: ANN201 - test helper
        return api.propose([PageEdit("log.md", "append-log", LOG_LINE, "r")], self.paths, name=name)


class TestLintRule(Utf8Case):
    def test_exactly_one_violation_naming_the_page(self) -> None:
        self.assertEqual(
            lint_wiki(self.wiki, root=self.root),
            [f"{BAD_PAGE}: not valid UTF-8 (invalid start byte at byte {self.bad_offset})"],
        )

    def test_lint_exits_1_and_the_health_and_prose_tiers_complete(self) -> None:
        for argv in (("lint",), ("lint", "--health"), ("lint", "--prose"), ("lint", "--health", "--prose")):
            with self.subTest(argv):
                result = self.cli(*argv)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(f"{BAD_PAGE}: not valid UTF-8", result.stdout + result.stderr)
        result = api.lint(self.paths, health=True, prose=True)
        self.assertEqual(len(result.violations), 1)

    def test_index_and_log_are_checked_too(self) -> None:
        for name in ("index.md", "log.md"):
            with self.subTest(name):
                page = self.page(name)
                original = page.read_bytes()
                page.write_bytes(original + b"\n\xc3(\n")
                self.assertIn(
                    f"{name}: not valid UTF-8 (invalid continuation byte at byte {len(original) + 1})",
                    lint_wiki(self.wiki, root=self.root),
                )
                page.write_bytes(original)

    def test_the_helper_reads_the_page_as_empty(self) -> None:
        self.assertEqual(_read_text_or_empty(self.page(BAD_PAGE)), "")


class TestDiscoverySkipsIt(Utf8Case):
    def test_find_counts_it_not_utf8_with_either_ranker(self) -> None:
        for ranker in RANKERS:
            with self.subTest(ranker):
                if ranker == RANKER_FTS5 and not HAS_FTS5:
                    self.skipTest("this Python's SQLite has no FTS5")
                result = api.find("plums twin alpha", self.paths, ranker=ranker)
                self.assertNotIn(BAD_PAGE, [p.path for p in result.pages])
                self.assertEqual([(i.path, i.reason) for i in result.ineligible], [(BAD_PAGE, "not-utf8")])


class TestPromoteRefuses(Utf8Case):
    def test_an_unrelated_promote_exits_9_until_the_page_is_reencoded(self) -> None:
        refused = self.log_only_proposal("log-only")
        before = self.page("log.md").read_bytes()
        with self.assertRaises(PromoteValidationError) as ctx:
            api.promote(refused, self.paths)
        self.assertIn(BAD_PAGE, str(ctx.exception))
        result = self.cli("promote", str(refused))
        self.assertEqual(result.returncode, 9, result.stderr)
        self.assertIn(BAD_PAGE, result.stderr)
        self.assertEqual(self.page("log.md").read_bytes(), before, "nothing written")

        self.reencode()
        self.assertEqual(lint_wiki(self.wiki, root=self.root), [])
        api.promote(refused, self.paths)
        self.assertIn(LOG_LINE, self.page("log.md").read_text(encoding="utf-8"))
