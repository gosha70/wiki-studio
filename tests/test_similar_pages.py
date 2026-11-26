# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""US4: the similar-pages hint in the library and in ``plan.json`` (issue 121, FR-019 to FR-022).

The replay binds the hint to the study: on a wiki holding every corpus page at its title-slug path, and on a copy of
the issue 54 fixture, ``discovery.similar_pages`` lists exactly what ``eval/similar/rank.py`` listed for each try,
with the query page absent as a proposed page is. The behaviour cases build small wikis in temporary directories:
which pages are never listed, which edits get a key, the switch, FTS5 missing, an unusable cache, the caught errors,
the ranking before the lock, the exit codes and promote, and the wiki left untouched. A 500-page wiki computes one
list within the bound recomputed from ``results/timing.json``. Cases that rank skip, with the reason, without FTS5.
"""

from __future__ import annotations

import contextlib
import json
import math
import os
import shutil
import sqlite3
import tempfile
import time
import unittest
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Final
from unittest import mock

from eval.similar import rank
from tests.conftest import make_repo_layout, run_cli
from wiki_studio import api, discovery
from wiki_studio.discovery import (
    SIMILAR_ERROR_NO_FTS5,
    SIMILAR_PAGES_K,
    DiscoveryWarning,
    Fts5Probe,
    SimilarList,
    similar_pages,
    similar_query,
)
from wiki_studio.errors import ContractViolationError
from wiki_studio.ingestor_multi import SIMILAR_PAGES_ERROR_KEY, SIMILAR_PAGES_KEY
from wiki_studio.paths import ENV_SIMILAR_PAGES, WikiPaths
from wiki_studio.proposal import PageEdit
from wiki_studio.wikilock import WikiLock

if TYPE_CHECKING:
    from collections.abc import Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "eval" / "similar" / "results"

FTS5 = discovery.fts5_available()
NO_FTS5 = f"this Python's SQLite has no FTS5, so the hint cannot rank: {FTS5.reason}"

INDEX_MD = "index.md"
LOG_MD = "log.md"
PLAN_JSON = "plan.json"
NOTES = "notes.md"
CREATE: Final = "create"
APPEND_INDEX: Final = "append-index"
UPDATE: Final = "update"
NO_FTS5_REASON = "no such module: fts5"
NOT_COMPUTED = "not computed"

# The 500-page bound (FR-022): pages in the synthetic wiki, the pages each study try ranked over, the headroom.
BOUND_PAGES = 500
STUDY_INDEX_PAGES = 298
BOUND_HEADROOM = 10
BOUND_FLOOR_SECONDS = 10

DECISION_TEMPLATE = (
    "---\npage_type: decision\nslug: {slug}\ntitle: {title}\nstatus: draft\nlast_reviewed: 2026-11-25\n"
    "sources:\n  - path: notes.md\n{extra}---\n\n# {title}\n\n## Decision\n\n{body}\n\n"
    "## Context\n\nAgreed with the platform team.\n\n## Alternatives considered\n\nNone recorded.\n\n"
    "## Consequences\n\nNone recorded.\n"
)
CONCEPT_TEMPLATE = (
    "---\npage_type: concept\nslug: {slug}\ntitle: {title}\nstatus: draft\nlast_reviewed: 2026-11-25\n"
    "sources:\n  - path: notes.md\n---\n\n# {title}\n\n## Summary\n\n{body}\n\n## Key ideas\n\n{body}\n\n"
    "## Where this shows up\n\nEverywhere.\n\n## Related\n\nNone.\n"
)

BACKOFF = "decisions/retry-backoff.md"
BUDGET = "decisions/retry-budget.md"
EVICTION = "decisions/cache-eviction.md"
JITTER = "decisions/retry-backoff-jitter.md"
WARMUP = "decisions/cache-warmup.md"
SUPERSEDED = "decisions/retry-backoff-old.md"
CONCEPT = "concepts/retry-backoff-concept.md"
UNLINKED = "decisions/retry-backoff-unlinked.md"

BACKOFF_BODY = "Retries back off exponentially, doubling the delay after each failed attempt."
JITTER_BODY = "Retries back off exponentially with random jitter after each failed attempt."


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def stem(path: str) -> str:
    return Path(path).stem


def decision(path: str, title: str, body: str, extra: str = "") -> str:
    return DECISION_TEMPLATE.format(slug=stem(path), title=title, body=body, extra=extra)


def concept(path: str, title: str, body: str) -> str:
    return CONCEPT_TEMPLATE.format(slug=stem(path), title=title, body=body)


BASE_PAGES = {
    BACKOFF: decision(BACKOFF, "Retry backoff", BACKOFF_BODY),
    BUDGET: decision(BUDGET, "Retry budget", "Each client spends retries from a shared retry budget per minute."),
    EVICTION: decision(EVICTION, "Cache eviction", "Evict the least recently used cache entries first."),
}
JITTER_PAGE = decision(JITTER, "Retry backoff jitter", JITTER_BODY)
WARMUP_PAGE = decision(WARMUP, "Cache warmup", "Warm the cache entries before traffic arrives.")


def index_line(path: str, title: str) -> str:
    return f"- [{title}]({path})"


def snapshot(directory: Path) -> dict[str, bytes | None]:
    """Every entry under ``directory``: a file's bytes, None for a directory."""
    return {p.relative_to(directory).as_posix(): (None if p.is_dir() else p.read_bytes()) for p in directory.rglob("*")}


@contextlib.contextmanager
def page_absent(page: Path, holding: Path) -> Iterator[None]:
    """``page`` moved out of the wiki for the block, as a proposed page is not yet in it, then put back."""
    held = holding / "held.md"
    page.rename(held)
    try:
        yield
    finally:
        held.rename(page)


def listed_paths(result: SimilarList) -> list[str]:
    return [page.path for page in result.pages]


def bound_seconds(timing: dict[str, Any]) -> int:
    """FR-022's bound: ``max(10, ceil(10 * t * 500 / 298))``, ``t`` the binding seconds per try."""
    per_try = timing["seconds"][rank.BINDING] / timing["tries"]
    return max(BOUND_FLOOR_SECONDS, math.ceil(BOUND_HEADROOM * per_try * BOUND_PAGES / STUDY_INDEX_PAGES))


# ── The replay (FR-022): the hint lists what rank.py listed ─────


class QueryAndConfigurationTest(unittest.TestCase):
    """``similar_query`` is ``rank.query_text``; k and the configuration hash are the measured ones (FR-022)."""

    ranks: ClassVar[dict[str, Any]]
    protocol: ClassVar[dict[str, Any]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.ranks = load_json(RESULTS_DIR / rank.RANKS_NAME)
        cls.protocol = load_json(REPO_ROOT / rank.PROTOCOL_PATH)

    def test_the_query_equals_rank_query_text_on_every_corpus_page(self) -> None:
        corpus_root = REPO_ROOT / self.protocol["corpus_pages"]["root"]
        entries = load_json(REPO_ROOT / rank.CORPUS_JSON_PATH)[rank.PAGES_KEY]
        self.assertTrue(entries)
        for entry in entries:
            text = (corpus_root / entry[rank.PAGE_KEY]).read_text(encoding="utf-8")
            with self.subTest(page=entry[rank.PAGE_KEY]):
                self.assertEqual(similar_query(text), rank.query_text(text))

    def test_the_query_equals_rank_query_text_on_every_fixture_page(self) -> None:
        wiki = REPO_ROOT / self.protocol["not_binding"][rank.FIXTURE]["wiki"]
        pages = sorted(p for p in wiki.rglob("*.md") if p.is_file() and not p.is_symlink())
        self.assertTrue(pages)
        for page in pages:
            try:
                text = page.read_bytes().decode("utf-8")
            except UnicodeDecodeError:
                continue
            with self.subTest(page=page.relative_to(wiki).as_posix()):
                self.assertEqual(similar_query(text), rank.query_text(text))

    def test_k_is_the_protocols_k(self) -> None:
        self.assertEqual(SIMILAR_PAGES_K, self.protocol["k"])
        self.assertEqual(SIMILAR_PAGES_K, self.ranks["k"])

    def test_the_configuration_hash_is_the_measured_one(self) -> None:
        self.assertEqual(discovery.ranker_config_hash(), self.ranks["ranker"]["ranker_config_hash"])


@unittest.skipUnless(FTS5.available, NO_FTS5)
class CorpusReplayTest(unittest.TestCase):
    """Each of the 13 tries, the query page absent, lists exactly ``ranks.json``'s list (FR-022)."""

    ranks: ClassVar[dict[str, Any]]
    texts: ClassVar[dict[str, str]]
    base: ClassVar[Path]
    root: ClassVar[Path]
    wiki: ClassVar[Path]
    _tmp: ClassVar[tempfile.TemporaryDirectory[str]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.ranks = load_json(RESULTS_DIR / rank.RANKS_NAME)
        protocol = load_json(REPO_ROOT / rank.PROTOCOL_PATH)
        corpus_root = REPO_ROOT / protocol["corpus_pages"]["root"]
        entries = load_json(REPO_ROOT / rank.CORPUS_JSON_PATH)[rank.PAGES_KEY]
        cls._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-similar-corpus-")
        cls.base = Path(cls._tmp.name).resolve()
        cls.root = cls.base / "root"
        cls.wiki = cls.root / "wiki"
        (cls.wiki / "decisions").mkdir(parents=True)
        cls.texts = {}
        links: list[str] = []
        for entry in entries:
            page = entry[rank.PAGE_KEY]
            path = cls.ranks["paths"][page]
            # Read as rank.py read it, so the wiki holds the text the study ranked.
            text = (corpus_root / page).read_text(encoding="utf-8")
            (cls.wiki / path).write_text(text, encoding="utf-8")
            cls.texts[page] = text
            links.append(index_line(path, path))
        (cls.wiki / INDEX_MD).write_text("# Index\n\n" + "\n".join(links) + "\n", encoding="utf-8")
        (cls.wiki / LOG_MD).write_text("# Log\n", encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_there_are_13_tries(self) -> None:
        self.assertEqual(len(self.ranks["tries"]), self.ranks["summary"]["tries"])
        self.assertEqual(len(self.ranks["tries"]), 13)

    def test_each_try_lists_what_the_study_listed(self) -> None:
        paths = self.ranks["paths"]
        for number, record in enumerate(self.ranks["tries"], start=1):
            query_path = paths[record["query"]]
            # A fresh cache per try: the ranking is built from this try's eligible pages only.
            wiki_paths = WikiPaths.for_root(
                self.root, wiki_dir=self.wiki, search_cache=self.base / f"cache-{number}.sqlite"
            )
            with self.subTest(try_number=number, query=record["query"]), page_absent(self.wiki / query_path, self.base):
                result, notes = similar_pages(wiki_paths, self.texts[record["query"]], exclude=frozenset({query_path}))
                self.assertIsNone(result.error)
                self.assertEqual(notes, ())
                self.assertEqual(listed_paths(result), [paths[page] for page in record["list"]])


@unittest.skipUnless(FTS5.available, NO_FTS5)
class FixtureReplayTest(unittest.TestCase):
    """On a copy of the issue 54 fixture, every ranked try lists ``ranks.json``'s list; the cross-type pair never."""

    ranks: ClassVar[dict[str, Any]]
    base: ClassVar[Path]
    root: ClassVar[Path]
    wiki: ClassVar[Path]
    _tmp: ClassVar[tempfile.TemporaryDirectory[str]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.ranks = load_json(RESULTS_DIR / rank.RANKS_NAME)
        protocol = load_json(REPO_ROOT / rank.PROTOCOL_PATH)
        cls._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-similar-fixture-")
        cls.base = Path(cls._tmp.name).resolve()
        cls.root = cls.base / "root"
        cls.wiki = cls.root / "wiki"
        shutil.copytree(REPO_ROOT / protocol["not_binding"][rank.FIXTURE]["wiki"], cls.wiki, symlinks=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _similar(self, query: str, number: int) -> SimilarList:
        wiki_paths = WikiPaths.for_root(
            self.root, wiki_dir=self.wiki, search_cache=self.base / f"cache-{number}.sqlite"
        )
        page = self.wiki / query
        text = page.read_bytes().decode("utf-8")
        with page_absent(page, self.base):
            result, notes = similar_pages(wiki_paths, text, exclude=frozenset({query}))
        self.assertIsNone(result.error)
        self.assertEqual(notes, ())
        return result

    def test_each_ranked_fixture_try_lists_what_the_study_listed(self) -> None:
        tries = self.ranks["fixture"]["tries"]
        self.assertTrue(tries)
        for number, record in enumerate(tries, start=1):
            with self.subTest(try_number=number, query=record["query"]):
                self.assertEqual(listed_paths(self._similar(record["query"], number)), record["list"])

    def test_the_cross_type_pair_is_never_listed(self) -> None:
        [never] = self.ranks["fixture"]["never_listed"]
        first, second = never["pair"]
        for number, (query, partner) in enumerate(((first, second), (second, first)), start=100):
            with self.subTest(query=query):
                self.assertNotIn(partner, listed_paths(self._similar(query, number)))


# ── The behaviour on small wikis ────────────────────────────────


def add_pages(paths: WikiPaths, pages: dict[str, str], *, link: bool = True) -> None:
    """Write ``pages`` into the wiki and, with ``link``, link each from ``index.md``."""
    lines: list[str] = []
    for path, text in pages.items():
        target = paths.wiki_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        lines.append(index_line(path, stem(path)))
    if link:
        with (paths.wiki_dir / INDEX_MD).open("a", encoding="utf-8") as index:
            index.write("\n" + "\n".join(lines) + "\n")


def init_wiki(root: Path) -> WikiPaths:
    """``root`` with ``notes.md`` (the pages' source) and an initialised wiki holding ``BASE_PAGES``, all linked."""
    (root / NOTES).write_text("# notes\n", encoding="utf-8")
    paths = WikiPaths.for_root(root)
    api.init(paths)
    add_pages(paths, BASE_PAGES)
    return paths


class _WikiCase(unittest.TestCase):
    """A root made by :func:`init_wiki`."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-similar-")
        self.root = Path(self._tmp.name).resolve()
        self.paths = init_wiki(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def propose(self, edits: list[PageEdit], name: str, paths: WikiPaths | None = None) -> list[dict[str, Any]]:
        written = api.propose(edits, self.paths if paths is None else paths, name=name)
        plan = load_json(written / PLAN_JSON)
        entries: list[dict[str, Any]] = plan["edits"]
        return entries

    def entry(self, entries: list[dict[str, Any]], path: str) -> dict[str, Any]:
        [found] = [entry for entry in entries if entry["path"] == path]
        return found


def jitter_edits() -> list[PageEdit]:
    return [
        PageEdit(JITTER, CREATE, JITTER_PAGE, "new"),
        PageEdit(INDEX_MD, APPEND_INDEX, index_line(JITTER, "Retry backoff jitter"), "link"),
    ]


@unittest.skipUnless(FTS5.available, NO_FTS5)
class PlanJsonTest(_WikiCase):
    """Creates only, each with its own list of live pages of its type, never a page of the same proposal (FR-020)."""

    def test_a_create_lists_its_similar_pages_best_first_with_titles(self) -> None:
        entries = self.propose(jitter_edits(), "one")
        create = self.entry(entries, JITTER)
        self.assertNotIn(SIMILAR_PAGES_ERROR_KEY, create)
        listed = create[SIMILAR_PAGES_KEY]
        self.assertEqual(listed[0], {"path": BACKOFF, "title": "Retry backoff"})
        self.assertLessEqual(len(listed), SIMILAR_PAGES_K)
        expected, _notes = similar_pages(self.paths, JITTER_PAGE, exclude=frozenset({JITTER, INDEX_MD}))
        self.assertEqual(listed, [{"path": page.path, "title": page.title} for page in expected.pages])

    def test_append_and_update_edits_get_no_key(self) -> None:
        updated = BASE_PAGES[BUDGET].replace("per minute", "per hour")
        edits = [*jitter_edits(), PageEdit(BUDGET, UPDATE, updated, "tighten")]
        entries = self.propose(edits, "mixed")
        for path in (INDEX_MD, BUDGET):
            with self.subTest(path=path):
                self.assertNotIn(SIMILAR_PAGES_KEY, self.entry(entries, path))
                self.assertNotIn(SIMILAR_PAGES_ERROR_KEY, self.entry(entries, path))

    def test_a_page_of_the_same_proposal_is_never_listed(self) -> None:
        updated = BASE_PAGES[BUDGET].replace("per minute", "per hour")
        edits = [*jitter_edits(), PageEdit(BUDGET, UPDATE, updated, "tighten")]
        listed = [page["path"] for page in self.entry(self.propose(edits, "same"), JITTER)[SIMILAR_PAGES_KEY]]
        self.assertNotIn(BUDGET, listed)
        self.assertIn(BACKOFF, listed)

    def test_two_creates_each_get_their_own_list(self) -> None:
        edits = [*jitter_edits(), PageEdit(WARMUP, CREATE, WARMUP_PAGE, "new")]
        entries = self.propose(edits, "two")
        jitter = [page["path"] for page in self.entry(entries, JITTER)[SIMILAR_PAGES_KEY]]
        warmup = [page["path"] for page in self.entry(entries, WARMUP)[SIMILAR_PAGES_KEY]]
        self.assertEqual(jitter[0], BACKOFF)
        self.assertEqual(warmup[0], EVICTION)
        for listed in (jitter, warmup):
            self.assertNotIn(JITTER, listed)
            self.assertNotIn(WARMUP, listed)


@unittest.skipUnless(FTS5.available, NO_FTS5)
class NeverListedTest(_WikiCase):
    """Superseded, other-type and unlinked pages are never listed, however alike they are (FR-019)."""

    def setUp(self) -> None:
        super().setUp()
        add_pages(
            self.paths,
            {
                SUPERSEDED: decision(
                    SUPERSEDED, "Retry backoff jitter old", JITTER_BODY, extra=f"superseded_by: {BACKOFF}\n"
                ),
                CONCEPT: concept(CONCEPT, "Retry backoff jitter concept", JITTER_BODY),
            },
        )
        add_pages(self.paths, {UNLINKED: decision(UNLINKED, "Retry backoff jitter unlinked", JITTER_BODY)}, link=False)

    def test_only_live_linked_pages_of_the_same_type_are_listed(self) -> None:
        result, notes = similar_pages(self.paths, JITTER_PAGE, exclude=frozenset({JITTER}))
        self.assertIsNone(result.error)
        self.assertEqual(notes, ())
        listed = listed_paths(result)
        for path in (SUPERSEDED, CONCEPT, UNLINKED):
            with self.subTest(path=path):
                self.assertNotIn(path, listed)
        self.assertEqual(sorted(listed), sorted(BASE_PAGES))

    def test_the_proposal_writes_the_same_list(self) -> None:
        listed = [
            page["path"] for page in self.entry(self.propose(jitter_edits(), "filters"), JITTER)[SIMILAR_PAGES_KEY]
        ]
        self.assertEqual(sorted(listed), sorted(BASE_PAGES))


class SwitchTest(unittest.TestCase):
    """``WIKI_STUDIO_SIMILAR_PAGES``: unset or empty on, ``on``/``off`` in any case, else ``ValueError`` (FR-021)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-similar-switch-")
        self.root = Path(self._tmp.name).resolve()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def resolved(self, env: dict[str, str], **kwargs: Any) -> bool:
        return WikiPaths.resolve(root=self.root, env=env, **kwargs).similar_pages

    def test_the_values(self) -> None:
        cases = {
            None: True,
            "": True,
            "on": True,
            "ON": True,
            " on ": True,
            "off": False,
            "OFF": False,
            " Off\n": False,
        }
        for value, expected in cases.items():
            env = {} if value is None else {ENV_SIMILAR_PAGES: value}
            with self.subTest(value=value):
                self.assertIs(self.resolved(env), expected)

    def test_an_invalid_value_raises_naming_the_variable_and_the_value(self) -> None:
        for value in ("yes", "0", "of", "   "):
            with self.subTest(value=value), self.assertRaises(ValueError) as caught:
                self.resolved({ENV_SIMILAR_PAGES: value})
            self.assertIn(ENV_SIMILAR_PAGES, str(caught.exception))
            self.assertIn(repr(value), str(caught.exception))

    def test_the_argument_wins_over_the_variable(self) -> None:
        self.assertIs(self.resolved({ENV_SIMILAR_PAGES: "on"}, similar_pages=False), False)
        self.assertIs(self.resolved({ENV_SIMILAR_PAGES: "nonsense"}, similar_pages=True), True)

    def test_for_root(self) -> None:
        self.assertIs(WikiPaths.for_root(self.root).similar_pages, True)
        self.assertIs(WikiPaths.for_root(self.root, similar_pages=False).similar_pages, False)

    def test_an_invalid_value_exits_1(self) -> None:
        with mock.patch.dict(os.environ, {ENV_SIMILAR_PAGES: "maybe"}):
            result = run_cli("propose", "--from", str(self.root / "drafts"), cwd=self.root)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn(ENV_SIMILAR_PAGES, result.stderr)


class SwitchOffTest(_WikiCase):
    """With the switch off neither key is written and ``similar_pages`` is never called (FR-020, FR-021)."""

    def test_off_writes_no_key_and_never_ranks(self) -> None:
        off = WikiPaths.for_root(self.root, similar_pages=False)
        with mock.patch.object(api, "similar_pages") as spy:
            entries = self.propose(jitter_edits(), "off", paths=off)
        spy.assert_not_called()
        for entry in entries:
            with self.subTest(path=entry["path"]):
                self.assertNotIn(SIMILAR_PAGES_KEY, entry)
                self.assertNotIn(SIMILAR_PAGES_ERROR_KEY, entry)


class Fts5MissingTest(_WikiCase):
    """Without FTS5 a create records why, and the proposal is otherwise the same (FR-019, FR-020)."""

    def test_the_error_is_recorded_and_nothing_else_changes(self) -> None:
        probe = Fts5Probe(available=False, sqlite_version="3.0.0", reason=NO_FTS5_REASON)
        with mock.patch.object(discovery, "fts5_available", return_value=probe):
            missing = api.propose(jitter_edits(), self.paths, name="no-fts5")
        off = api.propose(jitter_edits(), WikiPaths.for_root(self.root, similar_pages=False), name="off")
        entries = load_json(missing / PLAN_JSON)["edits"]
        create = self.entry(entries, JITTER)
        self.assertEqual(create[SIMILAR_PAGES_ERROR_KEY], f"{SIMILAR_ERROR_NO_FTS5}: {NO_FTS5_REASON}")
        self.assertTrue(create[SIMILAR_PAGES_ERROR_KEY].startswith("FTS5 not available"))
        self.assertNotIn(SIMILAR_PAGES_KEY, create)
        del create[SIMILAR_PAGES_ERROR_KEY]
        self.assertEqual(entries, load_json(off / PLAN_JSON)["edits"])
        for entry in entries:
            with self.subTest(preview=entry["preview"]):
                self.assertEqual((missing / entry["preview"]).read_bytes(), (off / entry["preview"]).read_bytes())


@unittest.skipUnless(FTS5.available, NO_FTS5)
class CacheAndErrorsTest(_WikiCase):
    """An unusable cache ranks in memory with a warning; the caught errors become ``similar_pages_error`` (FR-019)."""

    def test_an_unusable_cache_gives_the_same_list_and_a_warning(self) -> None:
        usable = self.entry(self.propose(jitter_edits(), "usable"), JITTER)[SIMILAR_PAGES_KEY]
        cache = self.root / "no-such-directory" / "search.sqlite"
        unusable = WikiPaths.for_root(self.root, search_cache=cache)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            written = api.propose(jitter_edits(), unusable, name="unusable")
        messages = [str(w.message) for w in caught if issubclass(w.category, DiscoveryWarning)]
        self.assertEqual(len(messages), 1, messages)
        self.assertIn(str(cache), messages[0])
        plan_text = (written / PLAN_JSON).read_text(encoding="utf-8")
        self.assertEqual(self.entry(json.loads(plan_text)["edits"], JITTER)[SIMILAR_PAGES_KEY], usable)
        self.assertNotIn(str(self.root), plan_text)
        self.assertNotIn(str(cache), plan_text)

    def test_caught_errors_are_recorded_and_the_proposal_is_written(self) -> None:
        for number, error in enumerate((ContractViolationError("cache inside"), sqlite3.OperationalError("locked"))):
            name = f"error-{number}"
            with (
                self.subTest(error=type(error).__name__),
                mock.patch.object(discovery, "rank_cached", side_effect=error),
            ):
                written = api.propose(jitter_edits(), self.paths, name=name)
                create = self.entry(load_json(written / PLAN_JSON)["edits"], JITTER)
                self.assertEqual(create[SIMILAR_PAGES_ERROR_KEY], f"{NOT_COMPUTED}: {type(error).__name__}")
                self.assertNotIn(SIMILAR_PAGES_KEY, create)
                self.assertEqual((written / create["preview"]).read_text(encoding="utf-8"), JITTER_PAGE)

    def test_the_ranking_runs_before_the_lock_is_entered(self) -> None:
        order: list[str] = []
        real_enter = WikiLock.__enter__
        real_similar = discovery.similar_pages

        def entering(lock: WikiLock) -> WikiLock:
            order.append("lock")
            return real_enter(lock)

        def ranking(*args: Any, **kwargs: Any) -> tuple[SimilarList, tuple[str, ...]]:
            order.append("similar")
            return real_similar(*args, **kwargs)

        with mock.patch.object(WikiLock, "__enter__", entering), mock.patch.object(api, "similar_pages", ranking):
            api.propose(jitter_edits(), self.paths, name="order")
        self.assertIn("lock", order)
        self.assertEqual(order[: order.index("lock")], ["similar"])


class IngestUnchangedTest(unittest.TestCase):
    """``ingest`` passes nothing: its ``plan.json`` carries neither key (FR-020)."""

    def test_ingest_writes_no_key(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wiki_studio-similar-ingest-") as tmp:
            root = make_repo_layout(Path(tmp), with_schema=True)
            paths = WikiPaths.for_root(root)
            result = api.ingest(root / "sample-incident.md", paths, backend="test")
            assert result.written is not None
            for entry in load_json(result.written / PLAN_JSON)["edits"]:
                with self.subTest(path=entry["path"]):
                    self.assertNotIn(SIMILAR_PAGES_KEY, entry)
                    self.assertNotIn(SIMILAR_PAGES_ERROR_KEY, entry)


class CliExitAndPromoteTest(_WikiCase):
    """``wiki-studio propose`` exits 0 and ``--promote`` applies the same files whatever the hint did (FR-022)."""

    NAME = "jitter"

    def write_draft(self, root: Path) -> Path:
        draft = root / "draft"
        (draft / "decisions").mkdir(parents=True)
        (draft / JITTER).write_text(JITTER_PAGE, encoding="utf-8")
        (draft / INDEX_MD).write_text(index_line(JITTER, "Retry backoff jitter") + "\n", encoding="utf-8")
        return draft

    def promote_case(self, root: Path) -> tuple[str, dict[str, Any]]:
        """On a fresh wiki under ``root``: propose and promote the jitter page.

        Returns the applied page without the ``page_id`` line propose assigns, and the archived create entry.
        """
        root.mkdir()
        paths = init_wiki(root)
        result = run_cli("propose", "--from", str(self.write_draft(root)), "--name", self.NAME, "--promote", cwd=root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.splitlines()[0]).name, self.NAME)
        applied = (paths.wiki_dir / JITTER).read_text(encoding="utf-8")
        page = "".join(line for line in applied.splitlines(keepends=True) if not line.startswith("page_id: "))
        archived = load_json(paths.applied_dir / self.NAME / PLAN_JSON)
        return page, self.entry(archived["edits"], JITTER)

    def test_every_case_exits_0_and_applies_the_page(self) -> None:
        no_fts5 = Fts5Probe(available=False, sqlite_version="3.0.0", reason=NO_FTS5_REASON)
        cases: list[tuple[str, contextlib.AbstractContextManager[Any], set[str]]] = [
            ("off", mock.patch.dict(os.environ, {ENV_SIMILAR_PAGES: "off"}), set()),
            (
                "no-fts5",
                mock.patch.object(discovery, "fts5_available", return_value=no_fts5),
                {SIMILAR_PAGES_ERROR_KEY},
            ),
            (
                "error",
                mock.patch.object(discovery, "rank_cached", side_effect=sqlite3.OperationalError("locked")),
                {SIMILAR_PAGES_ERROR_KEY},
            ),
        ]
        if FTS5.available:
            cases.insert(0, ("on", contextlib.nullcontext(), {SIMILAR_PAGES_KEY}))
        for label, case, keys in cases:
            with self.subTest(case=label), case:
                page, create = self.promote_case(self.root / label)
                self.assertEqual(page, JITTER_PAGE)
                self.assertEqual(set(create) & {SIMILAR_PAGES_KEY, SIMILAR_PAGES_ERROR_KEY}, keys)

    def test_a_propose_without_promote_leaves_the_wiki_unchanged(self) -> None:
        before = snapshot(self.paths.wiki_dir)
        result = run_cli("propose", "--from", str(self.write_draft(self.root)), "--name", "kept", cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(snapshot(self.paths.wiki_dir), before)
        plan = load_json(self.paths.proposals_dir / "kept" / PLAN_JSON)
        create = self.entry(plan["edits"], JITTER)
        self.assertTrue(SIMILAR_PAGES_KEY in create or SIMILAR_PAGES_ERROR_KEY in create)


# ── The 500-page bound (FR-022) ─────────────────────────────────

WORDS = [
    "alpha",
    "bravo",
    "charlie",
    "delta",
    "echo",
    "foxtrot",
    "golf",
    "hotel",
    "india",
    "juliet",
    "kilo",
    "lima",
    "mike",
    "november",
    "oscar",
    "papa",
    "quebec",
    "romeo",
    "sierra",
    "tango",
    "uniform",
    "victor",
    "whiskey",
    "xray",
    "yankee",
    "zulu",
    "amber",
    "basalt",
    "cobalt",
    "dune",
    "ember",
    "fjord",
    "granite",
]


def synthetic_body(number: int) -> str:
    return " ".join(WORDS[(number * step) % len(WORDS)] for step in (1, 3, 7, 11, 13, 17))


@unittest.skipUnless(FTS5.available, NO_FTS5)
class FiveHundredPagesTest(unittest.TestCase):
    """One create's list on a 500-page wiki of decision pages within the bound from ``timing.json`` (FR-022)."""

    def test_one_list_within_the_bound(self) -> None:
        bound = bound_seconds(load_json(RESULTS_DIR / rank.TIMING_NAME))
        with tempfile.TemporaryDirectory(prefix="wiki_studio-similar-500-") as tmp:
            root = Path(tmp).resolve()
            wiki = root / "wiki"
            (wiki / "decisions").mkdir(parents=True)
            links: list[str] = []
            for number in range(BOUND_PAGES):
                path = f"decisions/page-{number}.md"
                (wiki / path).write_text(decision(path, f"Page {number}", synthetic_body(number)), encoding="utf-8")
                links.append(index_line(path, path))
            (wiki / INDEX_MD).write_text("# Index\n\n" + "\n".join(links) + "\n", encoding="utf-8")
            (wiki / LOG_MD).write_text("# Log\n", encoding="utf-8")
            paths = WikiPaths.for_root(root, wiki_dir=wiki)
            new_page = decision("decisions/new.md", "New page", synthetic_body(BOUND_PAGES))
            start = time.perf_counter()
            result, _notes = similar_pages(paths, new_page, exclude=frozenset({"decisions/new.md"}))
            elapsed = time.perf_counter() - start
        self.assertIsNone(result.error)
        self.assertEqual(len(result.pages), SIMILAR_PAGES_K)
        self.assertLessEqual(elapsed, bound)

    def test_the_bound_is_recomputed_from_timing_json(self) -> None:
        timing = load_json(RESULTS_DIR / rank.TIMING_NAME)
        per_try = timing["seconds"][rank.BINDING] / timing["tries"]
        self.assertEqual(bound_seconds(timing), max(10, math.ceil(10 * per_try * 500 / 298)))


if __name__ == "__main__":
    unittest.main()
