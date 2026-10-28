# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The rebuildable search cache (0.8.0 US2, FR-012..FR-018).

Every case runs through ``api.find`` and the CLI with the ``fts5`` ranker and
compares the cached ranking with a fresh in-memory ranking
(``search_index.build_in_memory``) over the pages as they are now; the wiki
tree is hashed before and after, so no case may write into the wiki or create
a file under it.
"""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
import random
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from tests.conftest import run_cli
from tests.helpers.search_cache_bootstrap import GO_MARKER, MODE_HOLD, MODE_KILL, MODE_PLAIN, STAGED_MARKER
from tests.test_discovery import DISCOVERY_WIKI, tree_hash
from wiki_studio import api, discovery, search_index
from wiki_studio.discovery import DEFAULT_RANKER_CONFIG, RANKER_FTS5, RankerConfig, ranker_config_hash
from wiki_studio.errors import ContractViolationError
from wiki_studio.paths import ENV_SEARCH_CACHE, SEARCH_CACHE_SUFFIX, WikiPaths, search_cache_path_for
from wiki_studio.querier import _extract_index_links
from wiki_studio.search_index import CACHE_FORMAT, build_document, build_in_memory
from wiki_studio.wikilock import lock_path_for

REPO_ROOT = Path(__file__).resolve().parents[1]
HAS_FTS5 = discovery.fts5_available().available
POSIX = os.name == "posix"
IS_ROOT = POSIX and os.geteuid() == 0
GIT = shutil.which("git")

QUESTIONS = (
    "retry backoff",
    "circuit breaker failing service",
    "twin page",
    "sqlite search cache",
    "release notes",
    "zebra quokka",
)
# A full ranking: no cap and a budget that never binds on these fixtures.
UNCAPPED = 1000
CHILD_TIMEOUT_SECONDS = 60
FALLBACK_TEXT = "ranked with an in-memory index for this call"
OTHER_CONFIG = RankerConfig(tokenizer="unicode61", weights=(1.0, 1.0, 1.0, 1.0), min_match_tokens=1, max_pages=5)


def fresh_ranking(paths: WikiPaths, question: str, config: RankerConfig = DEFAULT_RANKER_CONFIG) -> list[str]:
    """The ranking a fresh in-memory index gives over the eligible pages as they are on disk now."""
    index_md = (paths.wiki_dir / "index.md").read_text(encoding="utf-8")
    eligible: list[discovery.LoadedPage] = []
    for rel in _extract_index_links(index_md, paths.wiki_dir):
        if posixpath.normpath(rel) in ("index.md", "log.md"):
            continue
        read = discovery._read_eligible(paths.wiki_dir, rel)
        if isinstance(read, discovery.LoadedPage):
            eligible.append(read)
    documents = [build_document(page.path, page.text) for page in eligible]
    with build_in_memory(documents, tokenizer=config.tokenizer) as index:
        return index.rank(
            question,
            order=[page.path for page in eligible],
            weights=config.weights,
            min_match_tokens=config.min_match_tokens,
        )


def _page(slug: str, title: str, body: str, *, extra: str = "") -> str:
    return (
        f"---\npage_type: concept\nslug: {slug}\ntitle: {title}\nstatus: draft\nlast_reviewed: 2026-10-27\n"
        f'{extra}sources:\n  - url: "https://example.com/{slug}"\n    retrieved: 2026-10-27\n---\n\n'
        f"# {title}\n\n{body}\n"
    )


def _child_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("WIKI_STUDIO_")}
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(REPO_ROOT / "src"), str(REPO_ROOT), env.get("PYTHONPATH")) if p)
    return env


@unittest.skipUnless(HAS_FTS5, "this Python's SQLite has no FTS5")
class CacheCase(unittest.TestCase):
    """The discovery fixture under ``knowledge/wiki`` of a temporary root; the cache derived beside it."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-cache-")
        self.root = Path(self._tmp.name).resolve()
        shutil.copytree(DISCOVERY_WIKI, self.root / "knowledge" / "wiki")
        (self.root / "doc_internal" / "proposals").mkdir(parents=True)
        self.paths = WikiPaths.for_root(self.root)
        self.wiki = self.paths.wiki_dir
        self.cache = self.paths.search_cache_file()
        env = {k: v for k, v in os.environ.items() if not k.startswith("WIKI_STUDIO_")}
        environ = mock.patch.dict(os.environ, env, clear=True)
        environ.start()
        self.addCleanup(environ.stop)

    def tearDown(self) -> None:
        for base, dirnames, _files in os.walk(self.root):
            for name in dirnames:
                os.chmod(Path(base) / name, 0o755)  # undo a read-only directory before cleanup
        self._tmp.cleanup()

    # ── helpers ──

    def cli(self, *argv: str):  # noqa: ANN201 - test helper
        return run_cli(*argv, cwd=self.root)

    def find(self, question: str, paths: WikiPaths | None = None, **kwargs: object) -> api.FindResult:
        return api.find(question, paths or self.paths, ranker=RANKER_FTS5, **kwargs)  # type: ignore[arg-type]

    def cached_ranking(self, question: str, paths: WikiPaths | None = None, **kwargs: object) -> list[str]:
        selection = discovery.select(
            paths or self.paths,
            question,
            max_pages=UNCAPPED,
            ranker=RANKER_FTS5,
            **kwargs,  # type: ignore[arg-type]
        )
        self.assertEqual(selection.warnings, (), "the cache was usable")
        return selection.pages_loaded

    def assert_consistent(self, *, paths: WikiPaths | None = None, cli_args: tuple[str, ...] = ()) -> None:
        """Every question: the cached ranking equals a fresh in-memory one, through select, api.find and the CLI."""
        paths = paths or self.paths
        for question in QUESTIONS:
            expected = fresh_ranking(paths, question)
            self.assertEqual(self.cached_ranking(question, paths), expected, question)
            found = self.find(question, paths)
            self.assertEqual([p.path for p in found.pages], expected[:5], question)
            self.assertEqual(found.warnings, ())
            result = self.cli("find", question, "--ranker", "fts5", "--json", *cli_args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual([p["path"] for p in json.loads(result.stdout)["pages"]], expected[:5], question)
            self.assertNotIn("warning", result.stderr)

    def wiki_unchanged(self):  # noqa: ANN201 - context manager helper
        test = self

        class _Guard:
            def __enter__(self) -> None:
                self.before = tree_hash(test.wiki)

            def __exit__(self, *exc: object) -> None:
                if exc[0] is None:
                    test.assertEqual(tree_hash(test.wiki), self.before, "the wiki tree is byte-identical")

        return _Guard()

    def write_page(self, rel: str, text: str) -> None:
        (self.wiki / rel).write_text(text, encoding="utf-8")

    def edit_index(self, old: str, new: str) -> None:
        index = self.wiki / "index.md"
        text = index.read_text(encoding="utf-8")
        self.assertIn(old, text)
        index.write_text(text.replace(old, new), encoding="utf-8")

    def user_version(self) -> int:
        connection = sqlite3.connect(self.cache)
        try:
            return int(connection.execute("PRAGMA user_version").fetchone()[0])
        finally:
            connection.close()

    def meta(self) -> dict[str, str]:
        connection = sqlite3.connect(self.cache)
        try:
            return dict(connection.execute("SELECT key, value FROM meta").fetchall())
        finally:
            connection.close()

    def manifest_rows(self) -> dict[str, str]:
        connection = sqlite3.connect(self.cache)
        try:
            return dict(connection.execute("SELECT path, sha256 FROM manifest").fetchall())
        finally:
            connection.close()


class TestLocation(CacheCase):
    def test_the_derived_cache_is_beside_the_lock_file(self) -> None:
        self.assertEqual(self.cache, search_cache_path_for(self.wiki))
        self.assertEqual(self.cache.parent, lock_path_for(self.wiki).parent)
        self.assertEqual(self.cache.name, f".{self.wiki.name}{SEARCH_CACHE_SUFFIX}")
        self.assertIsNone(self.paths.search_cache)

    def test_only_the_cache_is_created_and_the_wiki_is_untouched(self) -> None:
        parent = self.wiki.parent
        before = set(os.listdir(parent))
        with self.wiki_unchanged():
            result = self.cli("find", "retry backoff", "--ranker", "fts5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(os.listdir(parent)) - before, {self.cache.name})
        self.assertTrue(self.cache.is_file())

    def test_flag_then_environment_then_default(self) -> None:
        env_cache = self.root / "env.sqlite"
        flag_cache = self.root / "flag.sqlite"
        resolved = WikiPaths.resolve(root=self.root, env={ENV_SEARCH_CACHE: str(env_cache)})
        self.assertEqual(resolved.search_cache_file(), env_cache)
        resolved = WikiPaths.resolve(root=self.root, search_cache=flag_cache, env={ENV_SEARCH_CACHE: str(env_cache)})
        self.assertEqual(resolved.search_cache_file(), flag_cache)
        self.assertEqual(WikiPaths.resolve(root=self.root, env={}).search_cache_file(), self.cache)
        with self.wiki_unchanged():
            result = self.cli("find", "retry", "--ranker", "fts5", "--search-cache", str(flag_cache))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(flag_cache.is_file())
        self.assertFalse(self.cache.exists())
        with mock.patch.dict(os.environ, {ENV_SEARCH_CACHE: str(env_cache)}):
            self.assertEqual(self.cli("find", "retry", "--ranker", "fts5").returncode, 0)
        self.assertTrue(env_cache.is_file())

    def test_an_explicit_cache_inside_the_wiki_is_refused(self) -> None:
        inside = self.wiki / "concepts" / "cache.sqlite"
        with self.assertRaisesRegex(ValueError, "inside the wiki"):
            WikiPaths.for_root(self.root, search_cache=inside)
        with self.assertRaisesRegex(ValueError, "inside the wiki"):
            WikiPaths.resolve(root=self.root, env={ENV_SEARCH_CACHE: str(self.wiki)})
        with self.wiki_unchanged():
            result = self.cli("find", "retry", "--ranker", "fts5", "--search-cache", str(inside))
            self.assertEqual(result.returncode, 1)
            self.assertIn("inside the wiki", result.stderr)
            with mock.patch.dict(os.environ, {ENV_SEARCH_CACHE: str(self.wiki / "x.sqlite")}):
                self.assertEqual(self.cli("find", "retry").returncode, 1)

    def test_a_directly_built_paths_inside_the_wiki_is_a_contract_violation(self) -> None:
        bad = replace(self.paths, search_cache=self.wiki / "cache.sqlite")
        with self.wiki_unchanged(), self.assertRaises(ContractViolationError):
            self.find("retry", bad)
        self.assertFalse((self.wiki / "cache.sqlite").exists())


class TestOnDiskCache(CacheCase):
    def test_manifest_meta_and_user_version(self) -> None:
        with self.wiki_unchanged():
            result = self.find("retry backoff")
        self.assertEqual(result.warnings, ())
        self.assertEqual(self.user_version(), CACHE_FORMAT)
        meta = self.meta()
        self.assertEqual(meta["cache_format"], str(CACHE_FORMAT))
        self.assertEqual(meta["ranker_config_hash"], ranker_config_hash())
        self.assertEqual(meta["wiki_path"], str(self.wiki.resolve()))
        self.assertEqual(meta["wiki_id"], "")
        self.assertEqual(meta["sqlite_version"], sqlite3.sqlite_version)
        self.assertIn("package_version", meta)
        rows = self.manifest_rows()
        self.assertIn("concepts/retry-backoff.md", rows)
        self.assertNotIn("index.md", rows)
        self.assertNotIn("log.md", rows)

    def test_the_wiki_id_comes_from_the_manifest(self) -> None:
        api.init(self.paths)
        manifest = json.loads((self.wiki / ".wiki-studio.json").read_text(encoding="utf-8"))
        with self.wiki_unchanged():
            self.find("retry")
        self.assertEqual(self.meta()["wiki_id"], manifest["wiki_id"])

    @unittest.skipUnless(POSIX, "POSIX file modes")
    def test_the_file_is_owner_only_after_creation_and_after_a_rebuild(self) -> None:
        self.find("retry")
        self.assertEqual(stat.S_IMODE(self.cache.stat().st_mode), 0o600)
        self.cache.write_bytes(os.urandom(4096))
        self.find("retry")
        self.assertEqual(stat.S_IMODE(self.cache.stat().st_mode), 0o600)

    @unittest.skipUnless(POSIX, "POSIX file modes")
    def test_a_pre_existing_wider_file_is_tightened_before_it_is_filled(self) -> None:
        self.cache.write_bytes(b"")
        os.chmod(self.cache, 0o644)
        journal = Path(str(self.cache) + "-journal")
        journal.write_bytes(b"")
        os.chmod(journal, 0o644)
        with self.wiki_unchanged():
            result = self.find("retry backoff")
        self.assertEqual(result.warnings, ())
        self.assertEqual(stat.S_IMODE(self.cache.stat().st_mode), 0o600)
        self.assertIn("concepts/retry-backoff.md", self.manifest_rows())
        if journal.exists():
            self.assertEqual(stat.S_IMODE(journal.lstat().st_mode), 0o600)

    @unittest.skipUnless(POSIX, "POSIX file modes")
    def test_a_wider_file_that_cannot_be_tightened_is_never_filled(self) -> None:
        self.cache.write_bytes(b"")
        os.chmod(self.cache, 0o644)
        with mock.patch.object(os, "fchmod", side_effect=PermissionError("not the owner")), self.wiki_unchanged():
            result = self.find("retry backoff")
        self.assertEqual([p.path for p in result.pages], fresh_ranking(self.paths, "retry backoff")[:5])
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("cannot be tightened", result.warnings[0])
        self.assertIn(FALLBACK_TEXT, result.warnings[0])
        self.assertEqual(self.cache.stat().st_size, 0, "no page text reached the readable file")
        self.assertEqual(stat.S_IMODE(self.cache.stat().st_mode), 0o644)

    def test_no_journal_is_left_behind(self) -> None:
        self.find("retry")
        self.assertFalse(Path(str(self.cache) + "-journal").exists())

    def test_the_cache_never_supplies_prompt_text(self) -> None:
        self.find("retry backoff")
        # Poison the cached copy of the page's body; the prompt text, bytes and hash still come from the wiki.
        connection = sqlite3.connect(self.cache)
        with connection:
            connection.execute("UPDATE pages SET body = 'POISONED' WHERE path = 'concepts/retry-backoff.md'")
        connection.close()
        selection = discovery.select(self.paths, "retry backoff", ranker=RANKER_FTS5)
        page = next(p for p in selection.pages if p.path == "concepts/retry-backoff.md")
        data = (self.wiki / page.path).read_bytes()
        self.assertEqual(page.text, data.decode("utf-8"))
        self.assertNotIn("POISONED", page.text)
        self.assertEqual((page.sha256, page.bytes), (hashlib.sha256(data).hexdigest(), len(data)))


class TestRefresh(CacheCase):
    def test_a_same_size_edit_with_a_restored_mtime(self) -> None:
        self.assert_consistent()
        page = self.wiki / "concepts" / "circuit-breaker.md"
        before = page.stat()
        text = page.read_text(encoding="utf-8")
        self.assertIn("Circuit", text)
        edited = text.replace("# Circuit Breaker", "# Quokkas Breaker", 1)
        self.assertNotEqual(edited, text)
        self.assertEqual(len(edited.encode()), len(text.encode()))
        page.write_text(edited, encoding="utf-8")
        os.utime(page, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual((page.stat().st_size, page.stat().st_mtime_ns), (before.st_size, before.st_mtime_ns))
        with self.wiki_unchanged():
            self.assert_consistent()
            self.assertIn("concepts/circuit-breaker.md", self.cached_ranking("quokkas"))

    @unittest.skipUnless(GIT, "git is not installed")
    def test_a_git_checkout_of_an_older_revision(self) -> None:
        def git(*argv: str) -> None:
            subprocess.run(
                [GIT or "git", "-c", "user.name=t", "-c", "user.email=t@example.com", *argv],
                cwd=self.root,
                check=True,
                capture_output=True,
            )

        git("init", "-q")
        git("add", "knowledge")
        git("commit", "-q", "-m", "one")
        self.assert_consistent()
        self.write_page("concepts/retry-backoff.md", _page("retry-backoff", "Retry Backoff", "zebra quokka jitter"))
        self.edit_index("- [Release notes](concepts/release-notes.md) — a long page.\n", "")
        git("commit", "-q", "-am", "two")
        self.assert_consistent()
        self.assertEqual(self.cached_ranking("zebra")[:1], ["concepts/retry-backoff.md"])
        git("checkout", "-q", "HEAD~1", "--", "knowledge")
        with self.wiki_unchanged():
            self.assert_consistent()
            self.assertEqual(self.cached_ranking("zebra"), [])

    def test_a_rename(self) -> None:
        self.assert_consistent()
        (self.wiki / "concepts" / "retry-backoff.md").rename(self.wiki / "concepts" / "backoff-retry.md")
        self.edit_index("concepts/retry-backoff.md", "concepts/backoff-retry.md")
        with self.wiki_unchanged():
            self.assert_consistent()
        ranking = self.cached_ranking("retry backoff")
        self.assertIn("concepts/backoff-retry.md", ranking)
        self.assertNotIn("concepts/retry-backoff.md", ranking)
        self.assertNotIn("concepts/retry-backoff.md", self.manifest_rows())

    def test_a_delete(self) -> None:
        self.assert_consistent()
        (self.wiki / "concepts" / "retry-backoff.md").unlink()
        with self.wiki_unchanged():
            self.assert_consistent()
            result = self.find("retry backoff")
        self.assertIn(("concepts/retry-backoff.md", "missing"), [(i.path, i.reason) for i in result.ineligible])
        self.assertNotIn("concepts/retry-backoff.md", self.manifest_rows())

    def test_a_page_unlinked_from_the_index(self) -> None:
        self.assert_consistent()
        self.edit_index("- [Retry backoff](concepts/retry-backoff.md) — how long to wait between attempts.\n", "")
        with self.wiki_unchanged():
            self.assert_consistent()
        self.assertNotIn("concepts/retry-backoff.md", self.cached_ranking("retry backoff"))
        self.assertNotIn("concepts/retry-backoff.md", self.manifest_rows())

    def test_an_index_reorder_moves_the_tie_order(self) -> None:
        self.assertEqual(self.cached_ranking("twin")[:2], ["concepts/twin-beta.md", "concepts/twin-alpha.md"])
        self.edit_index(
            "- [Twin beta](concepts/twin-beta.md) — one of two equal pages.\n"
            "- [Twin alpha](concepts/twin-alpha.md) — the other equal page.\n",
            "- [Twin alpha](concepts/twin-alpha.md) — the other equal page.\n"
            "- [Twin beta](concepts/twin-beta.md) — one of two equal pages.\n",
        )
        with self.wiki_unchanged():
            self.assert_consistent()
        self.assertEqual(self.cached_ranking("twin")[:2], ["concepts/twin-alpha.md", "concepts/twin-beta.md"])

    def test_a_page_gaining_superseded_by(self) -> None:
        self.assert_consistent()
        page = self.wiki / "concepts" / "retry-backoff.md"
        text = page.read_text(encoding="utf-8")
        page.write_text(text.replace("status: draft\n", "status: draft\nsuperseded_by: concepts/circuit-breaker.md\n"))
        with self.wiki_unchanged():
            self.assert_consistent()
            result = self.find("retry backoff")
        self.assertNotIn("concepts/retry-backoff.md", [p.path for p in result.pages])
        self.assertIn(("concepts/retry-backoff.md", "superseded"), [(i.path, i.reason) for i in result.ineligible])
        self.assertNotIn("concepts/retry-backoff.md", self.manifest_rows())


class TestRecovery(CacheCase):
    def test_a_truncated_cache(self) -> None:
        self.assert_consistent()
        data = self.cache.read_bytes()
        self.cache.write_bytes(data[: len(data) // 2])
        with self.wiki_unchanged():
            self.assert_consistent()
        self.assertEqual(self.user_version(), CACHE_FORMAT)

    def test_a_cache_of_random_bytes(self) -> None:
        self.cache.write_bytes(random.Random(7).randbytes(8192))
        with self.wiki_unchanged():
            self.assert_consistent()
        self.assertEqual(self.user_version(), CACHE_FORMAT)

    def test_an_empty_cache_file(self) -> None:
        self.cache.write_bytes(b"")
        with self.wiki_unchanged():
            self.assert_consistent()
        self.assertEqual(self.user_version(), CACHE_FORMAT)

    def test_a_wrong_user_version(self) -> None:
        self.find("retry")
        connection = sqlite3.connect(self.cache)
        connection.execute("PRAGMA user_version = 99")
        connection.execute("UPDATE manifest SET sha256 = 'stale'")
        connection.commit()
        connection.close()
        with self.wiki_unchanged():
            self.assert_consistent()
        self.assertEqual(self.user_version(), CACHE_FORMAT)
        self.assertNotIn("stale", self.manifest_rows().values())

    def test_a_changed_ranker_config_hash(self) -> None:
        self.assert_consistent()
        for question in QUESTIONS:
            self.assertEqual(
                self.cached_ranking(question, config=OTHER_CONFIG), fresh_ranking(self.paths, question, OTHER_CONFIG)
            )
        self.assertEqual(self.meta()["ranker_config_hash"], ranker_config_hash(OTHER_CONFIG))
        with self.wiki_unchanged():
            self.assert_consistent()
        self.assertEqual(self.meta()["ranker_config_hash"], ranker_config_hash())

    def test_a_cache_copied_from_another_wiki(self) -> None:
        other_root = self.root / "other"
        other_wiki = other_root / "knowledge" / "wiki"
        shutil.copytree(DISCOVERY_WIKI, other_wiki)
        (other_wiki / "concepts" / "zebra.md").write_text(_page("zebra", "Zebra", "zebra quokka"), encoding="utf-8")
        index = other_wiki / "index.md"
        index.write_text(
            index.read_text(encoding="utf-8") + "- [Zebra](concepts/zebra.md) — stripes.\n", encoding="utf-8"
        )
        other = WikiPaths.for_root(other_root)
        api.init(other)
        self.assertEqual(self.cached_ranking("zebra", other), ["concepts/zebra.md"])
        shutil.copyfile(other.search_cache_file(), self.cache)
        with self.wiki_unchanged():
            self.assert_consistent()
        self.assertEqual(self.cached_ranking("zebra"), [])
        self.assertEqual(self.meta()["wiki_path"], str(self.wiki.resolve()))
        self.assertEqual(self.meta()["wiki_id"], "")

    def test_a_symlink_at_the_cache_path_falls_back_and_never_touches_its_target(self) -> None:
        target = self.root / "target.bin"
        target.write_bytes(b"not a database, and must stay so")
        self.cache.symlink_to(target)
        with self.wiki_unchanged():
            result = self.find("retry backoff")
            self.assertEqual([p.path for p in result.pages], fresh_ranking(self.paths, "retry backoff")[:5])
            self.assertEqual(len(result.warnings), 1)
            self.assertIn("symlink", result.warnings[0])
            self.assertIn(FALLBACK_TEXT, result.warnings[0])
            cli = self.cli("find", "retry backoff", "--ranker", "fts5")
        self.assertEqual(cli.returncode, 0)
        self.assertEqual(cli.stderr.count(FALLBACK_TEXT), 1)
        self.assertTrue(self.cache.is_symlink())
        self.assertEqual(target.read_bytes(), b"not a database, and must stay so")

    def test_a_symlinked_parent_falls_back(self) -> None:
        real = self.root / "real-dir"
        real.mkdir()
        (self.root / "linked-dir").symlink_to(real)
        paths = WikiPaths.for_root(self.root, search_cache=self.root / "linked-dir" / "cache.sqlite")
        with self.wiki_unchanged():
            result = self.find("retry", paths)
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("symlink", result.warnings[0])
        self.assertEqual(os.listdir(real), [])

    @unittest.skipUnless(POSIX and not IS_ROOT, "POSIX permissions, not as root")
    def test_a_read_only_parent_falls_back(self) -> None:
        locked = self.root / "locked"
        locked.mkdir()
        os.chmod(locked, 0o555)
        cache = locked / "cache.sqlite"
        with self.wiki_unchanged():
            result = self.find("retry backoff", WikiPaths.for_root(self.root, search_cache=cache))
            self.assertEqual([p.path for p in result.pages], fresh_ranking(self.paths, "retry backoff")[:5])
            cli = self.cli("find", "retry backoff", "--ranker", "fts5", "--search-cache", str(cache))
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("not writable", result.warnings[0])
        self.assertEqual(cli.returncode, 0)
        self.assertIn(FALLBACK_TEXT, cli.stderr)
        self.assertFalse(cache.exists())

    @unittest.skipUnless(POSIX and not IS_ROOT, "POSIX permissions, not as root")
    def test_a_read_only_cache_file_ranks_when_current_and_falls_back_when_it_needs_a_write(self) -> None:
        self.find("retry")
        os.chmod(self.cache, 0o400)
        try:
            with self.wiki_unchanged():
                self.assertEqual(self.find("retry backoff").warnings, (), "nothing to refresh, nothing written")
            self.write_page("concepts/retry-backoff.md", _page("retry-backoff", "Retry Backoff", "zebra quokka"))
            with self.wiki_unchanged():
                result = self.find("zebra")
        finally:
            os.chmod(self.cache, 0o600)
        self.assertEqual([p.path for p in result.pages], fresh_ranking(self.paths, "zebra")[:5])
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("readonly", result.warnings[0])

    def test_a_lock_held_past_the_busy_timeout_falls_back(self) -> None:
        self.find("retry")
        holder = sqlite3.connect(self.cache, isolation_level=None)
        holder.execute("BEGIN IMMEDIATE")
        try:
            with mock.patch.object(search_index, "SEARCH_CACHE_BUSY_TIMEOUT_SECONDS", 0), self.wiki_unchanged():
                result = self.find("retry backoff")
        finally:
            holder.execute("ROLLBACK")
            holder.close()
        self.assertEqual([p.path for p in result.pages], fresh_ranking(self.paths, "retry backoff")[:5])
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("locked", result.warnings[0])

    def test_query_passes_the_fallback_warning_to_stderr_and_exits_0(self) -> None:
        self.cache.symlink_to(self.root / "nowhere")
        with self.wiki_unchanged():
            result = self.cli("query", "retry backoff", "--backend", "test", "--ranker", "fts5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr.count(FALLBACK_TEXT), 1)
        self.assertFalse((self.root / "nowhere").exists())

    def test_index_first_never_opens_the_cache(self) -> None:
        with self.wiki_unchanged():
            self.assertEqual(self.cli("find", "retry backoff", "--ranker", "index-first").returncode, 0)
        self.assertFalse(self.cache.exists())


class TestInfo(CacheCase):
    def cache_info(self) -> dict[str, object]:
        result = self.cli("info", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)["discovery"]["cache"]

    def test_the_states(self) -> None:
        with self.wiki_unchanged():
            info = self.cache_info()
            self.assertEqual((info["path"], info["state"]), (str(self.cache), "missing"))
            self.assertFalse(self.cache.exists(), "info writes nothing")
            self.find("retry")
            self.assertEqual(self.cache_info(), {"path": str(self.cache), "state": "present", "reason": None})
            self.find("retry", ranker_config=OTHER_CONFIG)
            stale = self.cache_info()
            self.assertEqual(stale["state"], "present")
            self.assertIn("rebuilds", str(stale["reason"]))
            self.cache.write_bytes(b"\x00garbage" * 512)
            broken = self.cache_info()
            self.assertEqual(broken["state"], "unusable")
            self.assertTrue(broken["reason"])
            self.cache.unlink()
            self.cache.symlink_to(self.root / "nowhere")
            linked = self.cache_info()
            self.assertEqual(linked["state"], "unusable")
            self.assertIn("symlink", str(linked["reason"]))
        text = self.cli("info").stdout
        self.assertIn(f"search-cache: {self.cache}  (unusable", text)


class TestProcesses(CacheCase):
    def spawn(self, mode: str, sync_dir: Path, *argv: str) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, "-m", "tests.helpers.search_cache_bootstrap", mode, str(sync_dir), *argv],
            cwd=self.root,
            env=_child_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def wait_for(self, marker: Path, child: subprocess.Popen[str]) -> None:
        deadline = time.monotonic() + CHILD_TIMEOUT_SECONDS
        while not marker.exists():
            if child.poll() is not None:
                self.fail(f"child exited early: {child.communicate()}")
            if time.monotonic() > deadline:
                child.kill()
                self.fail("child never reached the refresh")
            time.sleep(0.01)

    def find_argv(self, question: str) -> tuple[str, ...]:
        return ("--root", str(self.root), "find", question, "--ranker", "fts5", "--json")

    def test_two_processes_refreshing_at_once(self) -> None:
        self.find("retry")
        self.write_page("concepts/retry-backoff.md", _page("retry-backoff", "Retry Backoff", "zebra quokka"))
        sync = self.root / "sync"
        sync.mkdir()
        with self.wiki_unchanged():
            first = self.spawn(MODE_HOLD, sync, *self.find_argv("zebra retry"))
            self.wait_for(sync / STAGED_MARKER, first)
            second = self.spawn(MODE_PLAIN, sync, *self.find_argv("zebra retry"))
            time.sleep(0.3)
            (sync / GO_MARKER).write_text("go\n", encoding="utf-8")
            out_first, err_first = first.communicate(timeout=CHILD_TIMEOUT_SECONDS)
            out_second, err_second = second.communicate(timeout=CHILD_TIMEOUT_SECONDS)
        self.assertEqual(first.returncode, 0, err_first)
        self.assertEqual(second.returncode, 0, err_second)
        selected = [[p["path"] for p in json.loads(out)["pages"]] for out in (out_first, out_second)]
        self.assertEqual(selected[0], selected[1])
        self.assertEqual(selected[0], fresh_ranking(self.paths, "zebra retry")[:5])
        self.assertNotIn(FALLBACK_TEXT, err_first + err_second)
        self.assert_consistent()

    @unittest.skipUnless(POSIX, "SIGKILL")
    def test_a_process_killed_during_a_refresh(self) -> None:
        self.find("retry")
        self.write_page("concepts/retry-backoff.md", _page("retry-backoff", "Retry Backoff", "zebra quokka"))
        (self.wiki / "concepts" / "circuit-breaker.md").unlink()
        sync = self.root / "sync"
        sync.mkdir()
        with self.wiki_unchanged():
            child = self.spawn(MODE_KILL, sync, *self.find_argv("zebra"))
            child.communicate(timeout=CHILD_TIMEOUT_SECONDS)
        self.assertEqual(child.returncode, -9)
        self.assertTrue((sync / STAGED_MARKER).exists(), "the kill happened inside the refresh")
        with self.wiki_unchanged():
            self.assert_consistent()
        self.assertNotIn("concepts/circuit-breaker.md", self.manifest_rows())
        self.assertFalse(Path(str(self.cache) + "-journal").exists())


class TestProperty(CacheCase):
    STEPS = 200
    SEED = 20261027
    WORDS = ("retry", "backoff", "breaker", "zebra", "quokka", "sqlite", "cache", "twin", "release", "jitter")

    def test_random_operations_keep_the_cache_equal_to_a_fresh_index(self) -> None:
        rng = random.Random(self.SEED)
        created = 0
        for step in range(self.STEPS):
            index = self.wiki / "index.md"
            lines = index.read_text(encoding="utf-8").splitlines(keepends=True)
            links = [i for i, line in enumerate(lines) if line.startswith("- [")]
            present = sorted(p.relative_to(self.wiki).as_posix() for p in (self.wiki / "concepts").glob("*.md"))
            op = rng.choice(("edit", "edit", "add", "delete", "rename", "unlink", "reorder", "supersede", "cache"))
            if op == "edit" and present:
                rel = rng.choice(present)
                body = " ".join(rng.choice(self.WORDS) for _ in range(rng.randint(0, 12)))
                self.write_page(rel, _page(Path(rel).stem, Path(rel).stem.title(), body))
            elif op == "add":
                created += 1
                slug = f"page-{created}"
                body = " ".join(rng.choice(self.WORDS) for _ in range(rng.randint(1, 8)))
                self.write_page(f"concepts/{slug}.md", _page(slug, slug.title(), body))
                lines.append(f"- [{slug}](concepts/{slug}.md) — generated.\n")
                index.write_text("".join(lines), encoding="utf-8")
            elif op == "delete" and present:
                (self.wiki / rng.choice(present)).unlink()
            elif op == "rename" and present:
                rel = rng.choice(present)
                created += 1
                new = f"concepts/renamed-{created}.md"
                (self.wiki / rel).rename(self.wiki / new)
                index.write_text("".join(lines).replace(f"]({rel})", f"]({new})"), encoding="utf-8")
            elif op == "unlink" and links:
                del lines[rng.choice(links)]
                index.write_text("".join(lines), encoding="utf-8")
            elif op == "reorder" and len(links) > 1:
                shuffled = [lines[i] for i in links]
                rng.shuffle(shuffled)
                for i, line in zip(links, shuffled, strict=True):
                    lines[i] = line
                index.write_text("".join(lines), encoding="utf-8")
            elif op == "supersede" and present:
                page = self.wiki / rng.choice(present)
                text = page.read_text(encoding="utf-8")
                if "superseded_by:" in text:
                    text = "".join(line for line in text.splitlines(keepends=True) if "superseded_by:" not in line)
                else:
                    text = text.replace("status: draft\n", "status: draft\nsuperseded_by: concepts/x.md\n", 1)
                page.write_text(text, encoding="utf-8")
            elif op == "cache" and self.cache.exists():
                choice = rng.choice(("truncate", "garbage", "delete"))
                if choice == "delete":
                    self.cache.unlink()
                elif choice == "garbage":
                    self.cache.write_bytes(rng.randbytes(2048))
                else:
                    data = self.cache.read_bytes()
                    self.cache.write_bytes(data[: rng.randint(0, len(data))])
            before = tree_hash(self.wiki)
            question = " ".join(rng.sample(self.WORDS, rng.randint(1, 3)))
            self.assertEqual(
                self.cached_ranking(question), fresh_ranking(self.paths, question), f"step {step} after {op}"
            )
            self.assertEqual(tree_hash(self.wiki), before, f"step {step}: the wiki is untouched")


if __name__ == "__main__":
    unittest.main()
