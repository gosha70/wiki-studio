# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wiki_studio.search_index — the FTS5 table the ``fts5`` ranker scores pages with (FR-005, FR-006).

One row per eligible page: its path (unindexed, the join key), the path as
words, the frontmatter title, the heading lines and the body without its
frontmatter. A question becomes a MATCH expression only through
:func:`build_query`: the querier's tokens, each double-quoted, joined with
``OR``, so raw question text never reaches FTS5's query syntax. Ranking is
``bm25`` with one weight per indexed column, ascending (SQLite returns a lower
value for a better match), ties broken by the page's position in ``index.md``.

In 0.8.0 US1 the table lives in memory for one call; the on-disk cache beside
the wiki's lock file is this module's too, and this module stays its only
writer.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .review import frontmatter_value
from .wiki_state import _tokenise

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

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


def build_in_memory(documents: Iterable[SearchDocument], *, tokenizer: str) -> SearchIndex:
    """A fresh in-memory index over ``documents`` (no file is opened or written)."""
    connection = sqlite3.connect(IN_MEMORY_DATABASE)
    try:
        create_table(connection, tokenizer)
        connection.executemany(
            f"INSERT INTO {TABLE_NAME} (path, {', '.join(INDEXED_COLUMNS)}) VALUES (?, ?, ?, ?, ?)",
            [(d.path, d.path_words, d.title, d.headings, d.body) for d in documents],
        )
    except BaseException:
        connection.close()
        raise
    return SearchIndex(connection)
