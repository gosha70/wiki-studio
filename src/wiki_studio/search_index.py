# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wiki_studio.search_index — the FTS5 table the ``fts5`` ranker scores pages with (FR-005, FR-006, FR-012..FR-015).

One row per eligible page: its path (unindexed, the join key), the path as
words, the frontmatter title, the heading lines and the body without its
frontmatter. A question becomes a MATCH expression only through
:func:`build_query`: the querier's tokens, each double-quoted, joined with
``OR``, so raw question text never reaches FTS5's query syntax. Ranking is
``bm25`` with one weight per indexed column, ascending (SQLite returns a lower
value for a better match), ties broken by the page's position in ``index.md``.

The on-disk cache is this module's alone: it is the only code in the package
that opens an SQLite connection. It lives beside the wiki's lock file, never
inside the wiki, and holds three tables: ``manifest`` (path, sha256, bytes of
every indexed page), the FTS5 ``pages`` table and ``meta`` (what the cache was
built for). Every call refreshes it under one ``BEGIN IMMEDIATE`` transaction
by diffing the caller's freshly read hashes against ``manifest`` (no mtime,
size or stat shortcut) and ranks in the same transaction over the current
paths only. The text stored there serves ranking and is never read back for a
prompt. A cache that does not match is rebuilt; a corrupt one is removed and
rebuilt; one that cannot be used safely (a symlink, an unwritable or
read-only directory, a lock held past the busy timeout, an existing file
wider than owner-only that cannot be tightened) makes that call rank in
memory with one warning. Cache state never fails a call.
"""

from __future__ import annotations

import contextlib
import errno
import os
import sqlite3
import stat
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import __version__
from .errors import ContractViolationError
from .paths import path_inside_dir
from .review import frontmatter_value
from .wiki_state import _tokenise

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

IN_MEMORY_DATABASE = ":memory:"
TABLE_NAME = "pages"
TITLE_KEY = "title"
FRONTMATTER_MARKER = "---"
HEADING_PREFIX = "#"
PAGE_SUFFIX = ".md"
QUERY_JOINER = " OR "
# The indexed columns, in table order; ``path`` is unindexed and is the join key.
INDEXED_COLUMNS: tuple[str, ...] = ("path_words", "title", "headings", "body")
# bm25 takes a weight for every column; the unindexed ``path`` never matches, so its weight is inert.
_PATH_COLUMN_WEIGHT = 0.0

# The on-disk cache (FR-013): its format, carried by ``PRAGMA user_version`` and ``meta``.
CACHE_FORMAT = 1
MANIFEST_TABLE = "manifest"
META_TABLE = "meta"
META_CACHE_FORMAT = "cache_format"
META_RANKER_CONFIG_HASH = "ranker_config_hash"
META_WIKI_PATH = "wiki_path"
META_WIKI_ID = "wiki_id"
META_SQLITE_VERSION = "sqlite_version"
META_PACKAGE_VERSION = "package_version"
# The meta keys that must equal the current values, else the cache is dropped and rebuilt (FR-015).
IDENTITY_KEYS: tuple[str, ...] = (META_CACHE_FORMAT, META_RANKER_CONFIG_HASH, META_WIKI_PATH, META_WIKI_ID)
# How long a refresh waits for another process's transaction before ranking in memory (FR-014).
SEARCH_CACHE_BUSY_TIMEOUT_SECONDS = 5
_MILLISECONDS_PER_SECOND = 1000
# The cache file is readable by its owner only: it holds a copy of every eligible page's text.
CACHE_FILE_MODE = 0o600
# POSIX only; with O_EXCL a final symlink is refused anyway.
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
# File modes are tightened on POSIX only; on Windows the directory's default ACL applies.
_POSIX = os.name == "posix"
# SQLite's rollback journal beside the database (removed with a corrupt cache so it is never replayed).
JOURNAL_SUFFIX = "-journal"
_URI_READ_WRITE = "?mode=rw"
_URI_READ_ONLY = "?mode=ro"
# SQLite primary result codes that say the file cannot be used right now (permissions, a lock, the disk),
# not that it is broken: rank in memory and leave it. Every other database error removes and rebuilds it.
_SQLITE_PERM = 3
_SQLITE_BUSY = 5
_SQLITE_LOCKED = 6
_SQLITE_NOMEM = 7
_SQLITE_READONLY = 8
_SQLITE_INTERRUPT = 9
_SQLITE_IOERR = 10
_SQLITE_FULL = 13
_SQLITE_CANTOPEN = 14
_SQLITE_PROTOCOL = 15
_SQLITE_NOLFS = 22
_SQLITE_AUTH = 23
_ENVIRONMENT_CODES = frozenset(
    {
        _SQLITE_PERM,
        _SQLITE_BUSY,
        _SQLITE_LOCKED,
        _SQLITE_NOMEM,
        _SQLITE_READONLY,
        _SQLITE_INTERRUPT,
        _SQLITE_IOERR,
        _SQLITE_FULL,
        _SQLITE_CANTOPEN,
        _SQLITE_PROTOCOL,
        _SQLITE_NOLFS,
        _SQLITE_AUTH,
    }
)
_PRIMARY_CODE_MASK = 0xFF

# ``info.discovery.cache.state`` (FR-018).
CACHE_STATE_PRESENT = "present"
CACHE_STATE_MISSING = "missing"
CACHE_STATE_UNUSABLE = "unusable"


@dataclass(frozen=True)
class SearchDocument:
    """One page as the FTS5 table holds it."""

    path: str
    path_words: str
    title: str
    headings: str
    body: str


def _split_frontmatter(text: str) -> list[str]:
    """The page's lines after its frontmatter (all lines when it has none or the block is unclosed)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_MARKER:
        return lines
    for i in range(1, len(lines)):
        if lines[i].strip() == FRONTMATTER_MARKER:
            return lines[i + 1 :]
    return lines


def build_document(path: str, text: str) -> SearchDocument:
    """The FTS5 row for page ``path`` whose text is ``text`` (FR-005)."""
    stem = path[: -len(PAGE_SUFFIX)] if path.endswith(PAGE_SUFFIX) else path
    path_words = stem.replace("/", " ").replace("-", " ")
    body_lines = _split_frontmatter(text)
    headings = [line.lstrip(HEADING_PREFIX).strip() for line in body_lines if line.startswith(HEADING_PREFIX)]
    return SearchDocument(
        path=path,
        path_words=path_words,
        title=frontmatter_value(text, TITLE_KEY) or "",
        headings="\n".join(headings),
        body="\n".join(body_lines),
    )


def _quote(token: str) -> str:
    """One FTS5 string: the token double-quoted with every ``"`` doubled."""
    return '"' + token.replace('"', '""') + '"'


def _sql_string(value: str) -> str:
    """``value`` as an SQL string literal (single-quoted, every ``'`` doubled)."""
    return "'" + value.replace("'", "''") + "'"


def question_tokens(question: str) -> list[str]:
    """The question's tokens under the querier's pattern and stop list, sorted for a stable query."""
    return sorted(_tokenise(question))


def build_query(question: str) -> str | None:
    """The MATCH expression for ``question``, or None when it has no token (then nothing is selected)."""
    tokens = question_tokens(question)
    if not tokens:
        return None
    return QUERY_JOINER.join(_quote(token) for token in tokens)


class SearchIndex:
    """An FTS5 ``pages`` table over one SQLite connection; :meth:`rank` orders pages for a question."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> SearchIndex:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _matching(self, expression: str, weights: Sequence[float]) -> dict[str, float]:
        rows = self._connection.execute(
            f"SELECT path, bm25({TABLE_NAME}, ?, ?, ?, ?, ?) FROM {TABLE_NAME} WHERE {TABLE_NAME} MATCH ?",
            (_PATH_COLUMN_WEIGHT, *weights, expression),
        ).fetchall()
        return {str(path): float(score) for path, score in rows}

    def rank(
        self,
        question: str,
        *,
        order: Sequence[str],
        weights: Sequence[float],
        min_match_tokens: int,
    ) -> list[str]:
        """Paths of ``order`` that match ``question``, best bm25 first, ties by position in ``order``.

        ``order`` is the eligible pages in ``index.md`` order; a row whose path
        is not in it is never returned. A page matching fewer than
        ``min_match_tokens`` distinct question tokens is dropped.
        """
        expression = build_query(question)
        if expression is None:
            return []
        scores = self._matching(expression, weights)
        position = {path: i for i, path in enumerate(order)}
        ranked = [path for path in scores if path in position]
        if min_match_tokens > 1:
            matched: dict[str, int] = dict.fromkeys(ranked, 0)
            for token in question_tokens(question):
                for path in self._matching(_quote(token), weights):
                    if path in matched:
                        matched[path] += 1
            ranked = [path for path in ranked if matched[path] >= min_match_tokens]
        ranked.sort(key=lambda path: (scores[path], position[path]))
        return ranked


def create_table(connection: sqlite3.Connection, tokenizer: str) -> None:
    """Create the ``pages`` FTS5 table with ``tokenizer``; raises ``sqlite3.OperationalError`` without FTS5."""
    columns = ", ".join(INDEXED_COLUMNS)
    connection.execute(
        f"CREATE VIRTUAL TABLE {TABLE_NAME} USING fts5(path UNINDEXED, {columns}, tokenize={_sql_string(tokenizer)})"
    )


def probe_fts5(tokenizer: str) -> str | None:
    """None when this Python's SQLite can create an FTS5 table with ``tokenizer``, else the error text (FR-002)."""
    connection = sqlite3.connect(IN_MEMORY_DATABASE)
    try:
        create_table(connection, tokenizer)
    except sqlite3.OperationalError as exc:
        return str(exc)
    finally:
        connection.close()
    return None


_INSERT_PAGE = f"INSERT INTO {TABLE_NAME} (path, {', '.join(INDEXED_COLUMNS)}) VALUES (?, ?, ?, ?, ?)"


def _insert_documents(connection: sqlite3.Connection, documents: Iterable[SearchDocument]) -> None:
    connection.executemany(_INSERT_PAGE, [(d.path, d.path_words, d.title, d.headings, d.body) for d in documents])


def build_in_memory(documents: Iterable[SearchDocument], *, tokenizer: str) -> SearchIndex:
    """A fresh in-memory index over ``documents`` (no file is opened or written)."""
    connection = sqlite3.connect(IN_MEMORY_DATABASE)
    try:
        create_table(connection, tokenizer)
        _insert_documents(connection, documents)
    except BaseException:
        connection.close()
        raise
    return SearchIndex(connection)


# ── The on-disk cache ─────────────────────────────────────────


@dataclass(frozen=True)
class IndexedPage:
    """One eligible page as this call read it: its FTS5 row and the sha256 and length of its bytes."""

    document: SearchDocument
    sha256: str
    bytes: int


@dataclass(frozen=True)
class CacheIdentity:
    """What a cache file is built for; a file whose ``meta`` differs on :data:`IDENTITY_KEYS` is rebuilt."""

    wiki_path: str
    wiki_id: str
    ranker_config_hash: str
    tokenizer: str

    def meta(self) -> dict[str, str]:
        return {
            META_CACHE_FORMAT: str(CACHE_FORMAT),
            META_RANKER_CONFIG_HASH: self.ranker_config_hash,
            META_WIKI_PATH: self.wiki_path,
            META_WIKI_ID: self.wiki_id,
            META_SQLITE_VERSION: sqlite3.sqlite_version,
            META_PACKAGE_VERSION: __version__,
        }


@dataclass(frozen=True)
class CachedRanking:
    """The ranked paths and, when the cache could not be used, the one warning saying so."""

    ranked: list[str]
    warning: str | None = None


class CacheUnusableError(Exception):
    """The cache cannot be used safely in this call; rank in memory (the message is the reason)."""


class CacheCorruptError(Exception):
    """The cache file is not a usable database; remove it and rebuild."""


def check_cache_location(cache_path: Path, wiki_dir: Path) -> None:
    """Raise ``ContractViolationError`` (exit 4) when ``cache_path`` lies inside the wiki (FR-012).

    ``WikiPaths`` refuses such a path with ``ValueError``; this re-check
    covers a ``WikiPaths`` built directly, at every open.
    """
    if path_inside_dir(cache_path, wiki_dir):
        raise ContractViolationError(
            f"search cache {cache_path} is inside the wiki directory {wiki_dir}; the cache must lie outside it"
        )


def _lstat(path: Path) -> os.stat_result | None:
    try:
        return path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise CacheUnusableError(f"cannot inspect {path}: {exc.strerror or exc}") from exc


def _check_parent(cache_path: Path) -> None:
    parent = cache_path.parent
    info = _lstat(parent)
    if info is None:
        raise CacheUnusableError(f"its directory {parent} does not exist")
    if stat.S_ISLNK(info.st_mode):
        raise CacheUnusableError(f"its directory {parent} is a symlink")
    if not stat.S_ISDIR(info.st_mode):
        raise CacheUnusableError(f"{parent} is not a directory")
    if not os.access(parent, os.W_OK):
        raise CacheUnusableError(f"its directory {parent} is not writable")


def _tighten_mode(path: Path, info: os.stat_result, what: str) -> None:
    """Make the existing regular file ``path`` (as ``lstat`` saw it in ``info``) owner-only when it is wider.

    POSIX only. Bits outside :data:`CACHE_FILE_MODE` are cleared and the
    owner's own bits are kept (a read-only ``0o400`` stays read-only). The
    file is opened without following a symlink and ``fstat`` must show the
    same inode before ``fchmod``; a file that cannot be tightened (not owned
    by this user) is unusable, so no page text is ever written into a
    readable file.
    """
    mode = stat.S_IMODE(info.st_mode)
    if not _POSIX or not mode & ~CACHE_FILE_MODE:
        return
    try:
        fd = os.open(path, os.O_RDONLY | _O_NOFOLLOW)
    except OSError as exc:
        raise CacheUnusableError(f"cannot open {what} to tighten its mode: {exc.strerror or exc}") from exc
    try:
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino) or not stat.S_ISREG(opened.st_mode):
            raise CacheUnusableError(f"{what} changed while being inspected")
        try:
            os.fchmod(fd, mode & CACHE_FILE_MODE)
        except OSError as exc:
            raise CacheUnusableError(f"{what} is not owner-only and cannot be tightened") from exc
    finally:
        os.close(fd)


def _tighten_journal(cache_path: Path) -> None:
    """Tighten a journal left beside the cache (it holds page text too); a missing or non-regular one is left alone."""
    journal = cache_path.with_name(cache_path.name + JOURNAL_SUFFIX)
    info = _lstat(journal)
    if info is not None and stat.S_ISREG(info.st_mode):
        _tighten_mode(journal, info, "its journal")


def _ensure_regular_file(cache_path: Path) -> None:
    """``lstat`` the path and create it owner-only when missing; refuse a symlink or a non-regular file.

    An existing file wider than owner-only, and a journal beside it, are
    tightened to :data:`CACHE_FILE_MODE` first (FR-015).
    """
    _tighten_journal(cache_path)
    info = _lstat(cache_path)
    if info is None:
        try:
            fd = os.open(cache_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | _O_NOFOLLOW, CACHE_FILE_MODE)
        except FileExistsError:
            info = _lstat(cache_path)
        except OSError as exc:
            reason = "the file system is read-only" if exc.errno == errno.EROFS else exc.strerror or str(exc)
            raise CacheUnusableError(f"cannot create it: {reason}") from exc
        else:
            os.close(fd)
            return
    if info is None:
        raise CacheUnusableError("it vanished while being created")
    if stat.S_ISLNK(info.st_mode):
        raise CacheUnusableError("the path is a symlink (its target is never opened)")
    if not stat.S_ISREG(info.st_mode):
        raise CacheUnusableError("the path is not a regular file")
    _tighten_mode(cache_path, info, "the cache file")


def _remove_corrupt(cache_path: Path) -> None:
    """Remove a corrupt cache file and its stale journal: regular files only, never through a symlink."""
    for victim in (cache_path, cache_path.with_name(cache_path.name + JOURNAL_SUFFIX)):
        info = _lstat(victim)
        if info is None:
            continue
        if not stat.S_ISREG(info.st_mode):
            raise CacheUnusableError(f"{victim.name} is corrupt and not a regular file; it is left in place")
        try:
            victim.unlink()
        except OSError as exc:
            raise CacheUnusableError(f"cannot remove the corrupt {victim.name}: {exc.strerror or exc}") from exc


def _classify(exc: sqlite3.DatabaseError) -> Exception:
    """A file SQLite cannot use right now is a reason to rank in memory; any other error means it is broken."""
    code = getattr(exc, "sqlite_errorcode", None)
    primary = code & _PRIMARY_CODE_MASK if isinstance(code, int) else None
    if primary in _ENVIRONMENT_CODES:
        return CacheUnusableError(f"SQLite: {exc}")
    return CacheCorruptError(str(exc))


def _connect(cache_path: Path, mode: str) -> sqlite3.Connection:
    """Open the existing file (``mode=rw`` and ``mode=ro`` never create one) in autocommit mode."""
    connection = sqlite3.connect(
        cache_path.absolute().as_uri() + mode,
        uri=True,
        timeout=SEARCH_CACHE_BUSY_TIMEOUT_SECONDS,
        isolation_level=None,
    )
    connection.execute(f"PRAGMA busy_timeout = {SEARCH_CACHE_BUSY_TIMEOUT_SECONDS * _MILLISECONDS_PER_SECOND}")
    return connection


def _stored_meta(connection: sqlite3.Connection) -> dict[str, str] | None:
    exists = connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (META_TABLE,))
    if exists.fetchone() is None:
        return None
    return {str(key): str(value) for key, value in connection.execute(f"SELECT key, value FROM {META_TABLE}")}


def _matches(connection: sqlite3.Connection, identity: CacheIdentity) -> bool:
    (user_version,) = connection.execute("PRAGMA user_version").fetchone()
    if user_version != CACHE_FORMAT:
        return False
    stored = _stored_meta(connection)
    if stored is None:
        return False
    wanted = identity.meta()
    return all(stored.get(key) == wanted[key] for key in IDENTITY_KEYS)


def _rebuild_schema(connection: sqlite3.Connection, identity: CacheIdentity) -> None:
    """Drop the three tables and create them empty for ``identity`` (inside the caller's transaction)."""
    for table in (TABLE_NAME, MANIFEST_TABLE, META_TABLE):
        connection.execute(f"DROP TABLE IF EXISTS {table}")
    connection.execute(f"CREATE TABLE {MANIFEST_TABLE} (path TEXT PRIMARY KEY, sha256 TEXT, bytes INTEGER)")
    connection.execute(f"CREATE TABLE {META_TABLE} (key TEXT PRIMARY KEY, value TEXT)")
    create_table(connection, identity.tokenizer)
    connection.executemany(f"INSERT INTO {META_TABLE} (key, value) VALUES (?, ?)", identity.meta().items())
    connection.execute(f"PRAGMA user_version = {CACHE_FORMAT}")


def _apply_diff(connection: sqlite3.Connection, pages: Sequence[IndexedPage]) -> None:
    """Make ``manifest`` and ``pages`` hold exactly ``pages``: insert new, replace changed, delete gone (FR-014)."""
    stored = {str(path): str(sha) for path, sha in connection.execute(f"SELECT path, sha256 FROM {MANIFEST_TABLE}")}
    current = {page.document.path: page for page in pages}
    for path in sorted(stored.keys() - current.keys()):
        connection.execute(f"DELETE FROM {TABLE_NAME} WHERE path = ?", (path,))
        connection.execute(f"DELETE FROM {MANIFEST_TABLE} WHERE path = ?", (path,))
    for path, page in current.items():
        if stored.get(path) == page.sha256:
            continue
        if path in stored:
            connection.execute(f"DELETE FROM {TABLE_NAME} WHERE path = ?", (path,))
        _insert_documents(connection, [page.document])
        connection.execute(
            f"INSERT OR REPLACE INTO {MANIFEST_TABLE} (path, sha256, bytes) VALUES (?, ?, ?)",
            (path, page.sha256, page.bytes),
        )


@dataclass(frozen=True)
class _RankRequest:
    question: str
    pages: Sequence[IndexedPage]
    weights: Sequence[float]
    min_match_tokens: int

    @property
    def order(self) -> list[str]:
        return [page.document.path for page in self.pages]


def _refresh_and_rank(cache_path: Path, identity: CacheIdentity, request: _RankRequest) -> list[str]:
    """One transaction: check ``meta``, rebuild if it differs, apply the diff, rank, commit."""
    try:
        connection = _connect(cache_path, _URI_READ_WRITE)
    except sqlite3.DatabaseError as exc:
        raise _classify(exc) from exc
    try:
        connection.execute("BEGIN IMMEDIATE")
        if not _matches(connection, identity):
            _rebuild_schema(connection, identity)
        _apply_diff(connection, request.pages)
        ranked = SearchIndex(connection).rank(
            request.question,
            order=request.order,
            weights=request.weights,
            min_match_tokens=request.min_match_tokens,
        )
        connection.execute("COMMIT")
        return ranked
    except sqlite3.DatabaseError as exc:
        raise _classify(exc) from exc
    finally:
        if connection.in_transaction:
            # Closing the connection rolls back whatever a failed ROLLBACK leaves.
            with contextlib.suppress(sqlite3.Error):
                connection.execute("ROLLBACK")
        connection.close()


def _rank_on_disk(cache_path: Path, identity: CacheIdentity, request: _RankRequest) -> list[str]:
    _check_parent(cache_path)
    _ensure_regular_file(cache_path)
    try:
        return _refresh_and_rank(cache_path, identity, request)
    except CacheCorruptError:
        _remove_corrupt(cache_path)
    _ensure_regular_file(cache_path)
    try:
        return _refresh_and_rank(cache_path, identity, request)
    except CacheCorruptError as exc:
        raise CacheUnusableError(f"still not a database after a rebuild: {exc}") from exc


def rank_cached(
    cache_path: Path,
    wiki_dir: Path,
    identity: CacheIdentity,
    pages: Sequence[IndexedPage],
    question: str,
    *,
    weights: Sequence[float],
    min_match_tokens: int,
) -> CachedRanking:
    """Refresh the cache at ``cache_path`` against ``pages`` and rank ``question`` over them (FR-014, FR-015).

    ``pages`` is the eligible set in ``index.md`` order, read and hashed by the
    caller in this call. Raises ``ContractViolationError`` when the path lies
    inside the wiki; every other cache problem ends in an in-memory ranking
    and a warning.
    """
    check_cache_location(cache_path, wiki_dir)
    request = _RankRequest(question, pages, weights, min_match_tokens)
    try:
        return CachedRanking(_rank_on_disk(cache_path, identity, request))
    except CacheUnusableError as exc:
        warning = f"search cache {cache_path}: {exc}; ranked with an in-memory index for this call"
    with build_in_memory((page.document for page in pages), tokenizer=identity.tokenizer) as index:
        ranked = index.rank(question, order=request.order, weights=weights, min_match_tokens=min_match_tokens)
    return CachedRanking(ranked, warning)


@dataclass(frozen=True)
class CacheState:
    """``info.discovery.cache`` (FR-018): where the cache is, whether it is usable, and why not."""

    path: str
    state: str
    reason: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {"path": self.path, "state": self.state, "reason": self.reason}


def describe_cache(cache_path: Path, wiki_dir: Path, identity: CacheIdentity) -> CacheState:
    """The cache's state without writing anything: the file is opened read-only, if at all."""
    shown = str(cache_path)
    if path_inside_dir(cache_path, wiki_dir):
        return CacheState(shown, CACHE_STATE_UNUSABLE, "inside the wiki directory")
    try:
        _check_parent(cache_path)
        info = _lstat(cache_path)
    except CacheUnusableError as exc:
        return CacheState(shown, CACHE_STATE_UNUSABLE, str(exc))
    if info is None:
        return CacheState(shown, CACHE_STATE_MISSING, "created on the first fts5 call")
    if stat.S_ISLNK(info.st_mode):
        return CacheState(shown, CACHE_STATE_UNUSABLE, "the path is a symlink")
    if not stat.S_ISREG(info.st_mode):
        return CacheState(shown, CACHE_STATE_UNUSABLE, "the path is not a regular file")
    try:
        connection = _connect(cache_path, _URI_READ_ONLY)
        try:
            matches = _matches(connection, identity)
        finally:
            connection.close()
    except sqlite3.DatabaseError as exc:
        return CacheState(shown, CACHE_STATE_UNUSABLE, f"{exc}; the next fts5 call removes and rebuilds it")
    if not matches:
        reason = "built for another wiki, format or ranker configuration; the next fts5 call rebuilds it"
        return CacheState(shown, CACHE_STATE_PRESENT, reason)
    return CacheState(shown, CACHE_STATE_PRESENT, None)
