# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.8.0 (US1): ranked discovery with a context budget (FR-001..FR-011).

Every case runs over ``tests/fixtures/discovery/wiki`` copied into a temporary
root. The FTS5 fallback is tested by patching ``discovery.fts5_available``,
never by building a Python without FTS5.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.conftest import FIXTURES_DIR, run_cli
from wiki_studio import api, discovery, search_index
from wiki_studio.discovery import (
    DEFAULT_MAX_CONTEXT_BYTES,
    DEFAULT_MAX_QUERY_PAGES,
    DEFAULT_RANKER_CONFIG,
    ENV_RANKER,
    RANKER_FTS5,
    RANKER_INDEX_FIRST,
    Fts5Probe,
    RankerConfig,
    ranker_config_hash,
    resolve_ranker,
)
from wiki_studio.errors import SourceMissingError
from wiki_studio.paths import WikiPaths
from wiki_studio.querier import _select_query_candidates
from wiki_studio.search_index import build_query

DISCOVERY_WIKI = FIXTURES_DIR / "discovery" / "wiki"
RANKERS = (RANKER_FTS5, RANKER_INDEX_FIRST)
NO_FTS5 = Fts5Probe(available=False, sqlite_version=sqlite3.sqlite_version, reason="no such module: fts5")
HAS_FTS5 = discovery.fts5_available().available

# Questions carrying FTS5 query syntax and non-ASCII letters (FR-005): none may raise through either ranker.
OPERATOR_QUESTIONS = (
    'what is "retry backoff',
    'retry "" backoff ""',
    "retry NEAR backoff",
    "retry AND backoff OR breaker NOT jitter",
    "-retry backoff",
    "retry* back*",
    "title:retry",
    "^retry",
    "(retry) (backoff",
    "{retry} {backoff}",
    "naïve café retry über",
    "日本語 の 質問",
    "NEAR(retry backoff, 2)",
    "",
    "   ",
    '"',
)

FIND_JSON_KEYS = {
    "question",
    "index",
    "pages",
    "ranker",
    "fallback_reason",
    "bytes_loaded",
    "max_bytes",
    "ranker_config_hash",
    "omitted",
    "ineligible",
    "warnings",
}


def tree_hash(directory: Path) -> str:
    """sha256 over every path under ``directory``: file bytes, symlinks by target, directories by name."""
    digest = hashlib.sha256()
    for base, dirnames, filenames in sorted(os.walk(directory, followlinks=False)):
        dirnames.sort()
        for name in sorted([*dirnames, *filenames]):
            path = Path(base) / name
            rel = path.relative_to(directory).as_posix()
            if path.is_symlink():
                digest.update(f"L {rel} -> {os.readlink(path)}\n".encode())
            elif path.is_file():
                digest.update(f"F {rel} {hashlib.sha256(path.read_bytes()).hexdigest()}\n".encode())
            else:
                digest.update(f"D {rel}\n".encode())
    return digest.hexdigest()


class DiscoveryCase(unittest.TestCase):
    """The discovery fixture under ``knowledge/wiki`` of a temporary root, no ranker in the environment."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-discovery-")
        self.root = Path(self._tmp.name).resolve()
        shutil.copytree(DISCOVERY_WIKI, self.root / "knowledge" / "wiki")
        (self.root / "doc_internal" / "proposals").mkdir(parents=True)
        self.paths = WikiPaths.for_root(self.root)
        self.wiki = self.paths.wiki_dir
        env = mock.patch.dict(os.environ, {ENV_RANKER: ""})
        env.start()
        self.addCleanup(env.stop)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def cli(self, *argv: str):  # noqa: ANN201 - test helper
        return run_cli(*argv, cwd=self.root)

    def found(self, question: str, **kwargs: object) -> list[str]:
        return [page.path for page in api.find(question, self.paths, **kwargs).pages]  # type: ignore[arg-type]

    def selector(self, question: str, max_pages: int = 5) -> list[str]:
        return _select_query_candidates(self.paths, question, max_pages)[1]

    def page(self, rel: str) -> Path:
        return self.wiki / rel

    def mark_superseded(self, rel: str, target: str) -> None:
        text = self.page(rel).read_text(encoding="utf-8")
        self.page(rel).write_text(text.replace("status: draft\n", f"status: draft\nsuperseded_by: {target}\n", 1))


class TestResolveRanker(unittest.TestCase):
    def test_flag_over_env_over_default(self) -> None:
        self.assertEqual(resolve_ranker("fts5", env={ENV_RANKER: "index-first"}), ("fts5", "flag"))
        self.assertEqual(resolve_ranker(None, env={ENV_RANKER: "fts5"}), ("fts5", "env"))
        self.assertEqual(resolve_ranker("", env={ENV_RANKER: "fts5"}), ("fts5", "env"))
        self.assertEqual(resolve_ranker(None, env={}), (discovery.DEFAULT_RANKER, "default"))
        self.assertEqual(resolve_ranker(None, env={ENV_RANKER: "  "}), (discovery.DEFAULT_RANKER, "default"))

    def test_the_shipped_default_is_fts5(self) -> None:
        """Decided by the held-out run (FR-029): fts5 was no worse at hit at 1 and 5 with both floors met."""
        self.assertEqual(discovery.DEFAULT_RANKER, RANKER_FTS5)
        self.assertEqual(discovery.RANKERS, ("fts5", "index-first"))

    def test_an_unknown_name_is_a_value_error_naming_both_rankers(self) -> None:
        for flag, env in (("bm25", {}), (None, {ENV_RANKER: "grep"})):
            with self.subTest(flag=flag, env=env), self.assertRaises(ValueError) as ctx:
                resolve_ranker(flag, env=env)
            message = str(ctx.exception)
            self.assertIn("fts5", message)
            self.assertIn("index-first", message)


class TestRankerConfigHash(unittest.TestCase):
    def test_the_hash_is_over_the_canonical_json(self) -> None:
        canonical = (
            '{"max_pages":5,"min_match_tokens":1,"ranker":"fts5",'
            '"tokenizer":"porter unicode61","weights":[4.0,4.0,2.0,1.0]}'
        )
        self.assertEqual(ranker_config_hash(), hashlib.sha256(canonical.encode("utf-8")).hexdigest())
        self.assertEqual(DEFAULT_RANKER_CONFIG, RankerConfig("porter unicode61", (4.0, 4.0, 2.0, 1.0), 1, 5))

    def test_two_configurations_never_share_a_hash(self) -> None:
        other = RankerConfig("unicode61", DEFAULT_RANKER_CONFIG.weights, 1, 5)
        self.assertNotEqual(ranker_config_hash(other), ranker_config_hash())


class TestProbe(unittest.TestCase):
    def test_the_probe_is_cached_and_reports_the_sqlite_version(self) -> None:
        probe = discovery.fts5_available()
        self.assertIs(probe, discovery.fts5_available())
        self.assertEqual(probe.sqlite_version, sqlite3.sqlite_version)
        self.assertEqual(probe.reason is None, probe.available)

    def test_an_operational_error_is_unavailable_with_its_reason(self) -> None:
        discovery.fts5_available.cache_clear()
        self.addCleanup(discovery.fts5_available.cache_clear)
        with mock.patch.object(
            search_index, "create_table", side_effect=sqlite3.OperationalError("no such module: fts5")
        ):
            probe = discovery.fts5_available()
        self.assertFalse(probe.available)
        self.assertEqual(probe.reason, "no such module: fts5")


class TestQueryBuilder(unittest.TestCase):
    def test_tokens_are_quoted_and_joined_with_or(self) -> None:
        self.assertEqual(build_query('the "retry" Backoff'), '"backoff" OR "retry"')

    def test_a_question_without_tokens_selects_nothing(self) -> None:
        self.assertIsNone(build_query("the of and"))
        self.assertIsNone(build_query('" * ( ) :'))


@unittest.skipUnless(HAS_FTS5, "this Python's SQLite has no FTS5")
class TestFts5Ranker(DiscoveryCase):
    def test_bm25_reads_the_whole_body(self) -> None:
        # "quarantine" sits past the first 400 characters: index-first misses it, fts5 does not.
        self.assertEqual(self.found("quarantine flag", ranker=RANKER_INDEX_FIRST), [])
        self.assertEqual(self.found("quarantine flag", ranker=RANKER_FTS5), ["concepts/release-notes.md"])

    def test_the_result_names_its_ranker_and_configuration(self) -> None:
        result = api.find("retry", self.paths, ranker=RANKER_FTS5)
        self.assertEqual(result.ranker, RANKER_FTS5)
        self.assertIsNone(result.fallback_reason)
        self.assertEqual(result.ranker_config_hash, ranker_config_hash())
        self.assertIsNone(api.find("retry", self.paths, ranker=RANKER_INDEX_FIRST).ranker_config_hash)

    def test_the_title_weight_ranks_the_named_page_first(self) -> None:
        self.assertEqual(self.found("retry backoff", ranker=RANKER_FTS5)[0], "concepts/retry-backoff.md")

    def test_the_minimum_match_rule_drops_single_token_pages(self) -> None:
        config = RankerConfig(DEFAULT_RANKER_CONFIG.tokenizer, DEFAULT_RANKER_CONFIG.weights, 2, 5)
        loose = self.found("retry jitter", ranker=RANKER_FTS5)
        strict = self.found("retry jitter", ranker=RANKER_FTS5, ranker_config=config)
        self.assertIn("concepts/circuit-breaker.md", loose)
        self.assertEqual(strict, ["concepts/retry-backoff.md"])


class TestIndexFirstRanker(DiscoveryCase):
    def test_equals_the_selector_on_a_clean_wiki(self) -> None:
        for question in ("retry backoff", "plums", "sqlite cache", "circuit breaker retry", "nothing here", ""):
            with self.subTest(question):
                self.assertEqual(self.found(question, ranker=RANKER_INDEX_FIRST), self.selector(question))
                self.assertEqual(
                    self.found(question, ranker=RANKER_INDEX_FIRST, max_pages=1), self.selector(question, 1)
                )


class TestFallback(DiscoveryCase):
    def test_without_fts5_find_falls_back_with_one_notice_and_exit_0(self) -> None:
        with mock.patch.object(discovery, "fts5_available", return_value=NO_FTS5):
            result = self.cli("find", "retry backoff", "--ranker", "fts5", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["ranker"], RANKER_INDEX_FIRST)
        self.assertEqual(data["fallback_reason"], "no such module: fts5")
        self.assertIsNone(data["ranker_config_hash"])
        self.assertEqual([p["path"] for p in data["pages"]], self.selector("retry backoff"))
        notice = "find: FTS5 is not available in this Python's SQLite (no such module: fts5); using index-first"
        self.assertEqual(result.stderr.count(notice), 1, result.stderr)

    def test_without_fts5_the_environment_choice_falls_back_too(self) -> None:
        with (
            mock.patch.object(discovery, "fts5_available", return_value=NO_FTS5),
            mock.patch.dict(os.environ, {ENV_RANKER: "fts5"}),
        ):
            result = api.find("plums", self.paths)
        self.assertEqual(result.ranker, RANKER_INDEX_FIRST)
        self.assertIsNotNone(result.fallback_reason)
        self.assertEqual([p.path for p in result.pages], self.selector("plums"))

    def test_index_first_never_reports_a_fallback(self) -> None:
        with mock.patch.object(discovery, "fts5_available", return_value=NO_FTS5):
            result = self.cli("find", "retry", "--ranker", "index-first")
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("FTS5", result.stderr)

    def test_query_prints_the_notice_and_still_answers(self) -> None:
        with mock.patch.object(discovery, "fts5_available", return_value=NO_FTS5):
            result = self.cli("query", "retry backoff", "--backend", "test", "--ranker", "fts5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("query: FTS5 is not available", result.stderr)


class TestOperatorQuestions(DiscoveryCase):
    def test_no_question_raises_through_either_ranker(self) -> None:
        for ranker in RANKERS:
            for question in OPERATOR_QUESTIONS:
                with self.subTest(ranker=ranker, question=question):
                    if ranker == RANKER_FTS5 and not HAS_FTS5:
                        self.skipTest("this Python's SQLite has no FTS5")
                    api.find(question, self.paths, ranker=ranker)
                    result = self.cli("find", question, "--ranker", ranker, "--json")
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_question_without_tokens_selects_nothing(self) -> None:
        for ranker in RANKERS:
            with self.subTest(ranker):
                if ranker == RANKER_FTS5 and not HAS_FTS5:
                    self.skipTest("this Python's SQLite has no FTS5")
                self.assertEqual(self.found("the of and", ranker=ranker), [])


class TestEligibility(DiscoveryCase):
    def test_a_superseded_page_is_never_selected_and_counted(self) -> None:
        self.mark_superseded("concepts/retry-backoff.md", "concepts/circuit-breaker.md")
        for ranker in RANKERS:
            with self.subTest(ranker):
                if ranker == RANKER_FTS5 and not HAS_FTS5:
                    self.skipTest("this Python's SQLite has no FTS5")
                result = api.find("retry backoff jitter", self.paths, ranker=ranker)
                self.assertNotIn("concepts/retry-backoff.md", [p.path for p in result.pages])
                self.assertIn(
                    ("concepts/retry-backoff.md", "superseded"), [(i.path, i.reason) for i in result.ineligible]
                )

    def test_missing_and_non_regular_links_are_counted(self) -> None:
        self.page("concepts/retry-backoff.md").unlink()
        self.page("concepts/twin-beta.md").unlink()
        self.page("concepts/twin-beta.md").mkdir()
        result = api.find("plums retry", self.paths)
        self.assertEqual(
            sorted((i.path, i.reason) for i in result.ineligible),
            [("concepts/retry-backoff.md", "missing"), ("concepts/twin-beta.md", "not-regular-file")],
        )

    def test_index_and_log_are_never_candidates(self) -> None:
        index = self.page("index.md")
        index.write_text(index.read_text(encoding="utf-8") + "- [Log](log.md) — history.\n- [Home](index.md)\n")
        for ranker in RANKERS:
            with self.subTest(ranker):
                if ranker == RANKER_FTS5 and not HAS_FTS5:
                    self.skipTest("this Python's SQLite has no FTS5")
                result = api.find("log fixture created discovery", self.paths, ranker=ranker)
                self.assertFalse({"log.md", "index.md"} & {p.path for p in result.pages})

    def test_symlinked_and_escaping_links_are_never_candidates(self) -> None:
        outside = self.root / "secret.md"
        outside.write_text(
            self.page("concepts/twin-alpha.md").read_text(encoding="utf-8").replace("Plums", "Launch codes")
        )
        (self.wiki / "concepts" / "linked.md").symlink_to(outside)
        index = self.page("index.md")
        index.write_text(
            index.read_text(encoding="utf-8") + "- [Linked](concepts/linked.md)\n- [Escape](../../secret.md)\n"
        )
        for ranker in RANKERS:
            with self.subTest(ranker):
                if ranker == RANKER_FTS5 and not HAS_FTS5:
                    self.skipTest("this Python's SQLite has no FTS5")
                result = api.find("launch codes", self.paths, ranker=ranker)
                self.assertEqual(result.pages, ())
                self.assertEqual(result.ineligible, ())

    def test_a_page_swapped_for_a_symlink_after_the_link_check_is_never_read(self) -> None:
        page = self.page("concepts/twin-alpha.md")
        original = page.read_text(encoding="utf-8")
        outside = self.root / "secret.md"
        outside.write_text(original.replace("Plums", "Launch codes"))
        real_links = discovery._extract_index_links

        def select_after_swap(ranker: str) -> discovery.Selection:
            swapped = {"done": False}

            def links_then_swap(*args: object, **kwargs: object) -> list[str]:
                # The containment check passed on a regular page; the read must still refuse the symlink.
                links = real_links(*args, **kwargs)  # type: ignore[arg-type]
                if not swapped["done"]:
                    swapped["done"] = True
                    page.unlink()
                    page.symlink_to(outside)
                return links

            with mock.patch.object(discovery, "_extract_index_links", links_then_swap):
                selection = discovery.select(self.paths, "launch codes plums", ranker=ranker)
            self.assertTrue(swapped["done"])
            return selection

        for ranker in RANKERS:
            with self.subTest(ranker):
                if ranker == RANKER_FTS5 and not HAS_FTS5:
                    self.skipTest("this Python's SQLite has no FTS5")
                selection = select_after_swap(ranker)
                self.assertEqual(selection.pages_loaded, ["concepts/twin-beta.md"])
                self.assertFalse(any("Launch codes" in loaded.text for loaded in selection.pages))
                ineligible = [(i.path, i.reason) for i in selection.ineligible]
                self.assertIn(("concepts/twin-alpha.md", "not-regular-file"), ineligible)
                cache = self.paths.search_cache_file()
                if cache.exists():
                    self.assertNotIn(b"Launch codes", cache.read_bytes())
                # Restore the regular page for the next ranker.
                page.unlink()
                page.write_text(original, encoding="utf-8")

    def test_a_symlinked_index_reads_as_empty(self) -> None:
        outside = self.root / "index-copy.md"
        outside.write_text(self.page("index.md").read_text(encoding="utf-8"))
        self.page("index.md").unlink()
        self.page("index.md").symlink_to(outside)
        selection = discovery.select(self.paths, "retry backoff")
        self.assertEqual((selection.index_md, selection.pages, selection.bytes_loaded), ("", (), 0))
        with self.assertRaises(SourceMissingError):
            api.find("retry backoff", self.paths)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFOs are POSIX")
    def test_a_fifo_linked_from_the_index_is_skipped_instead_of_hanging(self) -> None:
        """A FIFO at a linked page path opens non-blocking and reads as non-regular under both rankers."""
        page = self.page("concepts/twin-alpha.md")
        page.unlink()
        os.mkfifo(page)
        for ranker in (discovery.RANKER_INDEX_FIRST, discovery.RANKER_FTS5):
            with self.subTest(ranker=ranker):
                selection = discovery.select(self.paths, "retry backoff", ranker=ranker)
                self.assertIn(
                    ("concepts/twin-alpha.md", discovery.INELIGIBLE_NOT_REGULAR_FILE),
                    [(i.path, i.reason) for i in selection.ineligible],
                )
                self.assertNotIn("concepts/twin-alpha.md", [p.path for p in selection.pages])
        found = api.find("retry backoff", self.paths, ranker=discovery.RANKER_INDEX_FIRST)
        self.assertNotIn("concepts/twin-alpha.md", [p.path for p in found.pages])

    def test_two_spellings_of_one_link_load_the_page_once(self) -> None:
        index = self.page("index.md")
        index.write_text(index.read_text(encoding="utf-8") + "- [Twin beta again](./concepts/twin-beta.md)\n")
        expected_bytes = sum(
            len(self.page(rel).read_bytes()) for rel in ("index.md", "concepts/twin-beta.md", "concepts/twin-alpha.md")
        )
        for ranker in RANKERS:
            with self.subTest(ranker):
                if ranker == RANKER_FTS5 and not HAS_FTS5:
                    self.skipTest("this Python's SQLite has no FTS5")
                result = api.find("plums", self.paths, ranker=ranker)
                self.assertEqual([p.path for p in result.pages], ["concepts/twin-beta.md", "concepts/twin-alpha.md"])
                self.assertEqual((result.bytes_loaded, result.ineligible), (expected_bytes, ()))
                self.assertEqual(self.found("plums", ranker=ranker, max_pages=1), ["concepts/twin-beta.md"])

    def test_each_page_reports_the_sha256_and_length_of_its_bytes(self) -> None:
        data = self.page("concepts/retry-backoff.md").read_bytes()
        (page, *_rest) = api.find("retry backoff", self.paths).pages
        self.assertEqual(
            (page.path, page.sha256, page.bytes),
            ("concepts/retry-backoff.md", hashlib.sha256(data).hexdigest(), len(data)),
        )


class TestBudget(DiscoveryCase):
    def index_bytes(self) -> int:
        return len(self.page("index.md").read_bytes())

    def test_an_oversized_page_is_skipped_and_the_next_one_tried(self) -> None:
        first = "concepts/retry-backoff.md"
        with self.page(first).open("a", encoding="utf-8") as handle:
            handle.write("\n## Notes\n\n" + "Retry retry retry, then retry again.\n" * 100)
        for ranker in RANKERS:
            with self.subTest(ranker):
                if ranker == RANKER_FTS5 and not HAS_FTS5:
                    self.skipTest("this Python's SQLite has no FTS5")
                ranked = self.found("retry", ranker=ranker)
                self.assertEqual(ranked[0], first)
                second = ranked[1]
                budget = self.index_bytes() + len(self.page(second).read_bytes())
                result = api.find("retry", self.paths, max_bytes=budget, ranker=ranker)
                self.assertEqual([p.path for p in result.pages], [second])
                self.assertEqual(
                    [(o.path, o.bytes) for o in result.omitted], [(first, len(self.page(first).read_bytes()))]
                )
                self.assertEqual(result.bytes_loaded, budget)
                self.assertEqual(result.max_bytes, budget)

    def test_an_index_over_budget_loads_no_page_with_one_warning(self) -> None:
        result = api.find("retry", self.paths, max_bytes=self.index_bytes() - 1)
        self.assertEqual(result.pages, ())
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("index.md", result.warnings[0])
        self.assertEqual(result.bytes_loaded, self.index_bytes())
        cli = self.cli("find", "retry", "--max-bytes", str(self.index_bytes() - 1))
        self.assertEqual(cli.returncode, 0)
        self.assertEqual(cli.stderr.count("warning:"), 1)

    def test_the_default_budget_counts_index_and_pages(self) -> None:
        result = api.find("retry", self.paths)
        self.assertEqual(result.max_bytes, DEFAULT_MAX_CONTEXT_BYTES)
        self.assertEqual(result.bytes_loaded, self.index_bytes() + sum(p.bytes for p in result.pages))

    def test_max_bytes_must_be_a_positive_integer(self) -> None:
        for bad in (0, -1):
            with self.subTest(bad), self.assertRaises(ValueError):
                api.find("retry", self.paths, max_bytes=bad)
            result = self.cli("find", "retry", "--max-bytes", str(bad))
            self.assertEqual(result.returncode, 1)
            self.assertIn("max_bytes", result.stderr)


class TestCapAndTies(DiscoveryCase):
    def test_equal_scores_follow_index_order_and_the_cap_holds(self) -> None:
        for ranker in RANKERS:
            with self.subTest(ranker):
                if ranker == RANKER_FTS5 and not HAS_FTS5:
                    self.skipTest("this Python's SQLite has no FTS5")
                self.assertEqual(
                    self.found("plums", ranker=ranker), ["concepts/twin-beta.md", "concepts/twin-alpha.md"]
                )
                self.assertEqual(self.found("plums", ranker=ranker, max_pages=1), ["concepts/twin-beta.md"])
                self.assertLessEqual(len(self.found("retry sqlite plums release circuit", ranker=ranker)), 5)

    def test_max_pages_outside_one_to_five_is_refused(self) -> None:
        self.assertEqual(DEFAULT_MAX_QUERY_PAGES, 5)
        self.assertLessEqual(len(self.found("retry sqlite plums release circuit", max_pages=5)), 5)
        for bad in (0, 6, 100, True, "5"):
            with self.subTest(bad), self.assertRaisesRegex(ValueError, r"1 to 5"):
                api.find("plums", self.paths, max_pages=bad)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, r"1 to 5"):
            api.query("plums", self.paths, backend="test", max_pages=6)
        result = self.cli("find", "plums", "--max-pages", "6")
        self.assertEqual(result.returncode, 1)
        self.assertIn("1 to 5", result.stderr)
        result = self.cli("query", "plums", "--backend", "test", "--max-pages", "0")
        self.assertEqual(result.returncode, 1)
        self.assertIn("1 to 5", result.stderr)

    @unittest.skipUnless(HAS_FTS5, "this Python's SQLite has no FTS5")
    def test_reordering_the_index_reorders_the_tie(self) -> None:
        index = self.page("index.md")
        text = index.read_text(encoding="utf-8")
        beta = "- [Twin beta](concepts/twin-beta.md) — one of two equal pages.\n"
        index.write_text(text.replace(beta, "").replace("- [Release notes]", beta + "- [Release notes]"))
        self.assertEqual(self.found("plums", ranker=RANKER_FTS5), ["concepts/twin-alpha.md", "concepts/twin-beta.md"])


class TestReadOnly(DiscoveryCase):
    def test_find_and_query_leave_the_wiki_byte_identical(self) -> None:
        (self.wiki / "concepts" / "linked.md").symlink_to(self.page("concepts/twin-alpha.md"))
        before = tree_hash(self.wiki)
        for ranker in RANKERS:
            with self.subTest(ranker):
                api.find("retry backoff", self.paths, ranker=ranker)
                self.assertEqual(self.cli("find", "plums", "--ranker", ranker, "--json").returncode, 0)
                api.query("retry backoff", self.paths, backend="test", ranker=ranker)
                self.assertEqual(self.cli("query", "plums", "--backend", "test", "--ranker", ranker).returncode, 0)
                self.assertEqual(tree_hash(self.wiki), before)


class TestQuery(DiscoveryCase):
    def test_query_selects_through_discovery_and_logs_the_ranker(self) -> None:
        answer = api.query("retry backoff", self.paths, backend="test", ranker=RANKER_INDEX_FIRST).answer
        self.assertEqual(answer.pages_loaded, self.selector("retry backoff"))
        entry = json.loads(self.paths.query_log.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(entry["ranker"], RANKER_INDEX_FIRST)
        loaded = len(self.page("index.md").read_bytes()) + sum(
            len(self.page(p).read_bytes()) for p in answer.pages_loaded
        )
        self.assertEqual(entry["bytes_loaded"], loaded)
        for key in ("ts", "question", "pages_loaded", "citations", "answer_chars"):
            self.assertIn(key, entry)

    def test_query_honours_the_budget(self) -> None:
        budget = len(self.page("index.md").read_bytes())
        answer = api.query("retry backoff", self.paths, backend="test", max_bytes=budget).answer
        self.assertEqual(answer.pages_loaded, [])

    @unittest.skipUnless(HAS_FTS5, "this Python's SQLite has no FTS5")
    def test_query_ranks_under_the_given_ranker_configuration(self) -> None:
        strict = RankerConfig(DEFAULT_RANKER_CONFIG.tokenizer, DEFAULT_RANKER_CONFIG.weights, 2, 5)
        loose = api.query("retry jitter", self.paths, backend="test", ranker=RANKER_FTS5).answer.pages_loaded
        self.assertIn("concepts/circuit-breaker.md", loose)
        with mock.patch.object(discovery, "select", wraps=discovery.select) as spy:
            answer = api.query(
                "retry jitter", self.paths, backend="test", ranker=RANKER_FTS5, ranker_config=strict
            ).answer
        self.assertEqual(answer.pages_loaded, ["concepts/retry-backoff.md"])
        self.assertIs(spy.call_args.kwargs["config"], strict)

    def test_a_bad_ranker_is_refused_before_the_backend(self) -> None:
        with self.assertRaises(ValueError):
            api.query("retry", self.paths, backend="test", ranker="grep")
        self.assertEqual(self.cli("query", "retry", "--backend", "test", "--ranker", "grep").returncode, 1)


class TestCli(DiscoveryCase):
    def test_find_json_carries_every_key(self) -> None:
        result = self.cli("find", "retry backoff", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(set(data), FIND_JSON_KEYS)
        self.assertEqual(set(data["pages"][0]), {"path", "file", "title", "sha256", "bytes"})

    def test_find_text_names_the_ranker_first_and_each_page_size(self) -> None:
        result = self.cli("find", "retry backoff", "--ranker", "index-first")
        lines = result.stdout.splitlines()
        self.assertTrue(lines[0].startswith("ranker: index-first"), lines[0])
        size = len(self.page("concepts/retry-backoff.md").read_bytes())
        self.assertIn(f"knowledge/wiki/concepts/retry-backoff.md  Retry Backoff  ({size} bytes)", result.stdout)

    def test_flag_over_environment_over_default(self) -> None:
        def ranker_of(*argv: str) -> str:
            result = self.cli("find", "retry", "--json", *argv)
            self.assertEqual(result.returncode, 0, result.stderr)
            return str(json.loads(result.stdout)["ranker"])

        with mock.patch.object(discovery, "fts5_available", return_value=Fts5Probe(True, sqlite3.sqlite_version)):
            self.assertEqual(ranker_of(), discovery.DEFAULT_RANKER)
            with mock.patch.dict(os.environ, {ENV_RANKER: "fts5"}):
                if HAS_FTS5:
                    self.assertEqual(ranker_of(), RANKER_FTS5)
                self.assertEqual(ranker_of("--ranker", "index-first"), RANKER_INDEX_FIRST)

    def test_a_bad_ranker_value_exits_1(self) -> None:
        result = self.cli("find", "retry", "--ranker", "bm25")
        self.assertEqual(result.returncode, 1)
        self.assertIn("bm25", result.stderr)
        with mock.patch.dict(os.environ, {ENV_RANKER: "grep"}):
            result = self.cli("find", "retry")
        self.assertEqual(result.returncode, 1)
        self.assertIn(ENV_RANKER, result.stderr)


if __name__ == "__main__":
    unittest.main()
