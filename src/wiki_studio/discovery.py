# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wiki_studio.discovery — which pages ``find`` and ``query`` put in front of a model (0.8.0, FR-001..FR-007).

``index.md`` is always read first. The candidates are the pages it links
inside the wiki; a candidate is eligible when it is a regular file, valid
UTF-8 and carries no ``superseded_by``. Two rankers order the eligible pages:
``index-first`` (the 0.7.0 word-overlap selector,
:func:`wiki_studio.querier._select_query_candidates`, wrapped and never
edited) and ``fts5`` (bm25 over :mod:`wiki_studio.search_index`). The byte
budget then takes pages in rank order, skipping a page that does not fit, up
to the page cap. Without FTS5 in this Python's SQLite the ``fts5`` ranker
falls back to ``index-first`` and says why; it never fails.

Each eligible page is read once per call, as bytes: that read is hashed, and
its decoded text is what the prompt carries and what citations are checked
against.
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
import posixpath
import sqlite3
import stat
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .contract import DiscoveryInfo
from .querier import DEFAULT_MAX_QUERY_PAGES, _extract_index_links, _select_query_candidates
from .review import superseded_by
from .search_index import IN_MEMORY_DATABASE, build_document, build_in_memory, create_table

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from .paths import WikiPaths

# The two rankers and the default (index-first until the held-out measurement decides, FR-029).
RANKER_FTS5 = "fts5"
RANKER_INDEX_FIRST = "index-first"
RANKERS: tuple[str, ...] = (RANKER_FTS5, RANKER_INDEX_FIRST)
DEFAULT_RANKER = RANKER_INDEX_FIRST
ENV_RANKER = "WIKI_STUDIO_RANKER"

# Where the resolved ranker came from (``resolve_ranker``).
RANKER_SOURCE_FLAG = "flag"
RANKER_SOURCE_ENV = "env"
RANKER_SOURCE_DEFAULT = "default"

# The byte budget over index.md plus the selected pages (FR-007).
DEFAULT_MAX_CONTEXT_BYTES = 65536

# The untuned FTS5 configuration (FR-005, FR-006); FR-021 replaces it with the tuned one.
FTS5_TOKENIZER = "porter unicode61"
WEIGHT_PATH = 4.0
WEIGHT_TITLE = 4.0
WEIGHT_HEADINGS = 2.0
WEIGHT_BODY = 1.0
MIN_MATCH_TOKENS = 1

# Why a page linked from index.md is not a candidate (FR-004).
INELIGIBLE_MISSING = "missing"
INELIGIBLE_NOT_REGULAR_FILE = "not-regular-file"
INELIGIBLE_NOT_UTF8 = "not-utf8"
INELIGIBLE_SUPERSEDED = "superseded"

INDEX_NAME = "index.md"
LOG_NAME = "log.md"
# index.md and log.md are read as navigation and history, never ranked as pages.
_NEVER_CANDIDATES = frozenset({INDEX_NAME, LOG_NAME})


@dataclass(frozen=True)
class RankerConfig:
    """The FTS5 ranker's configuration; :func:`ranker_config_hash` identifies it (FR-006)."""

    tokenizer: str
    weights: tuple[float, float, float, float]
    min_match_tokens: int
    max_pages: int


DEFAULT_RANKER_CONFIG = RankerConfig(
    tokenizer=FTS5_TOKENIZER,
    weights=(WEIGHT_PATH, WEIGHT_TITLE, WEIGHT_HEADINGS, WEIGHT_BODY),
    min_match_tokens=MIN_MATCH_TOKENS,
    max_pages=DEFAULT_MAX_QUERY_PAGES,
)


def ranker_config_hash(config: RankerConfig = DEFAULT_RANKER_CONFIG) -> str:
    """Lowercase hex sha256 of the configuration's canonical JSON (sorted keys, no spaces, UTF-8)."""
    document = {
        "ranker": RANKER_FTS5,
        "tokenizer": config.tokenizer,
        "weights": [float(w) for w in config.weights],
        "min_match_tokens": config.min_match_tokens,
        "max_pages": config.max_pages,
    }
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def resolve_ranker(flag: str | None = None, *, env: Mapping[str, str] | None = None) -> tuple[str, str]:
    """``(ranker, source)``: a non-empty flag, else a non-empty ``WIKI_STUDIO_RANKER``, else the default.

    Raises ``ValueError`` naming the value and the accepted names when the
    chosen value is not a ranker.
    """
    if flag is not None and flag.strip():
        value, source = flag.strip(), RANKER_SOURCE_FLAG
    else:
        environ: Mapping[str, str] = os.environ if env is None else env
        value, source = environ.get(ENV_RANKER, "").strip(), RANKER_SOURCE_ENV
        if not value:
            return DEFAULT_RANKER, RANKER_SOURCE_DEFAULT
    if value not in RANKERS:
        origin = "--ranker" if source == RANKER_SOURCE_FLAG else ENV_RANKER
        raise ValueError(f"unknown ranker {value!r} ({origin}); expected one of: {', '.join(RANKERS)}")
    return value, source


# ── The FTS5 probe ────────────────────────────────────────────


@dataclass(frozen=True)
class Fts5Probe:
    """Whether this Python's SQLite has FTS5 with the configured tokenizer (FR-002)."""

    available: bool
    sqlite_version: str
    reason: str | None = None


@functools.cache
def fts5_available() -> Fts5Probe:
    """Create an FTS5 table with the tokenizer in a ``:memory:`` database, once per process."""
    connection = sqlite3.connect(IN_MEMORY_DATABASE)
    try:
        create_table(connection, FTS5_TOKENIZER)
    except sqlite3.OperationalError as exc:
        return Fts5Probe(available=False, sqlite_version=sqlite3.sqlite_version, reason=str(exc))
    finally:
        connection.close()
    return Fts5Probe(available=True, sqlite_version=sqlite3.sqlite_version)


def describe_discovery(*, env: Mapping[str, str] | None = None) -> DiscoveryInfo:
    """``info``'s ``discovery`` (FR-010): the probe, the default ranker and its source, the live configuration hash.

    Raises ``ValueError`` when ``WIKI_STUDIO_RANKER`` names no ranker.
    """
    probe = fts5_available()
    ranker, source = resolve_ranker(None, env=env)
    return DiscoveryInfo(
        fts5=probe.available,
        sqlite_version=probe.sqlite_version,
        fts5_reason=probe.reason,
        default_ranker=ranker,
        default_ranker_source=source,
        ranker_config_hash=ranker_config_hash(),
    )


# ── Eligibility ───────────────────────────────────────────────


@dataclass(frozen=True)
class IneligiblePage:
    """A page linked from index.md that no ranker may select, and why."""

    path: str
    reason: str


@dataclass(frozen=True)
class OmittedPage:
    """A ranked page skipped because it did not fit in the byte budget."""

    path: str
    bytes: int


@dataclass(frozen=True)
class LoadedPage:
    """An eligible page as read once in this call: its text, the sha256 and length of its bytes."""

    path: str
    text: str
    sha256: str
    bytes: int


def _read_eligible(wiki_dir: Path, rel: str) -> LoadedPage | IneligiblePage:
    """Read one index-linked page once and classify it (FR-004)."""
    page = wiki_dir / rel
    try:
        mode = page.lstat().st_mode
    except OSError:
        return IneligiblePage(rel, INELIGIBLE_MISSING)
    if not stat.S_ISREG(mode):
        return IneligiblePage(rel, INELIGIBLE_NOT_REGULAR_FILE)
    try:
        data = page.read_bytes()
    except OSError:
        return IneligiblePage(rel, INELIGIBLE_MISSING)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return IneligiblePage(rel, INELIGIBLE_NOT_UTF8)
    if superseded_by(text) is not None:
        return IneligiblePage(rel, INELIGIBLE_SUPERSEDED)
    return LoadedPage(rel, text, hashlib.sha256(data).hexdigest(), len(data))


def _read_index(wiki_dir: Path) -> tuple[str, int]:
    """``index.md``'s text and byte count; ``("", 0)`` when it is missing, unreadable or not UTF-8."""
    try:
        data = (wiki_dir / INDEX_NAME).read_bytes()
        return data.decode("utf-8"), len(data)
    except (OSError, UnicodeDecodeError):
        return "", 0


# ── Selection ─────────────────────────────────────────────────


@dataclass(frozen=True)
class Selection:
    """What one call loads: ``index.md``, then ``pages`` in rank order within the cap and the budget."""

    index_md: str
    pages: tuple[LoadedPage, ...]
    ranker: str
    fallback_reason: str | None
    bytes_loaded: int
    max_bytes: int
    omitted: tuple[OmittedPage, ...]
    ineligible: tuple[IneligiblePage, ...]
    ranker_config_hash: str | None
    warnings: tuple[str, ...]

    @property
    def pages_loaded(self) -> list[str]:
        return [page.path for page in self.pages]

    @property
    def pages_content(self) -> dict[str, str]:
        return {page.path: page.text for page in self.pages}


def _validate_max_bytes(max_bytes: int) -> None:
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ValueError(f"max_bytes must be a positive integer, got {max_bytes!r}")


def _rank_fts5(question: str, eligible: dict[str, LoadedPage], config: RankerConfig) -> list[str]:
    order = list(eligible)
    documents = (build_document(rel, eligible[rel].text) for rel in order)
    with build_in_memory(documents, tokenizer=config.tokenizer) as index:
        return index.rank(question, order=order, weights=config.weights, min_match_tokens=config.min_match_tokens)


def _rank_index_first(
    paths: WikiPaths, question: str, candidate_count: int, eligible: dict[str, LoadedPage]
) -> list[str]:
    # The whole ranked list from the 0.7.0 selector; its own reads serve ranking only.
    _index, ranked, _contents = _select_query_candidates(paths, question, max_pages=candidate_count)
    return [rel for rel in ranked if rel in eligible]


def select(
    paths: WikiPaths,
    question: str,
    *,
    max_pages: int = DEFAULT_MAX_QUERY_PAGES,
    max_bytes: int = DEFAULT_MAX_CONTEXT_BYTES,
    ranker: str = DEFAULT_RANKER,
    config: RankerConfig | None = None,
) -> Selection:
    """Select the pages for ``question`` with ``ranker`` under the cap and the byte budget (FR-004, FR-007).

    An empty ``index_md`` means the wiki has no readable ``index.md``; the
    caller decides what that means on its surface. Raises ``ValueError`` for
    an unknown ranker or a ``max_bytes`` that is not a positive integer.
    Writes nothing.
    """
    _validate_max_bytes(max_bytes)
    if ranker not in RANKERS:
        raise ValueError(f"unknown ranker {ranker!r}; expected one of: {', '.join(RANKERS)}")
    config = DEFAULT_RANKER_CONFIG if config is None else config
    fallback_reason: str | None = None
    if ranker == RANKER_FTS5:
        probe = fts5_available()
        if not probe.available:
            ranker = RANKER_INDEX_FIRST
            fallback_reason = probe.reason or "FTS5 is not available"
    config_hash = ranker_config_hash(config) if ranker == RANKER_FTS5 else None

    wiki_dir = paths.wiki_dir
    index_md, index_bytes = _read_index(wiki_dir)
    if not index_md:
        return Selection("", (), ranker, fallback_reason, 0, max_bytes, (), (), config_hash, ())

    links = _extract_index_links(index_md, wiki_dir)
    eligible: dict[str, LoadedPage] = {}
    ineligible: list[IneligiblePage] = []
    for rel in links:
        if posixpath.normpath(rel) in _NEVER_CANDIDATES:
            continue
        read = _read_eligible(wiki_dir, rel)
        if isinstance(read, LoadedPage):
            eligible[rel] = read
        else:
            ineligible.append(read)

    if ranker == RANKER_FTS5:
        ranked = _rank_fts5(question, eligible, config)
    else:
        ranked = _rank_index_first(paths, question, len(links), eligible)

    warnings: list[str] = []
    selected: list[LoadedPage] = []
    omitted: list[OmittedPage] = []
    loaded = index_bytes
    if index_bytes > max_bytes:
        warnings.append(
            f"{INDEX_NAME} alone is {index_bytes} bytes, over the {max_bytes}-byte budget; no page was loaded"
        )
    else:
        for rel in ranked:
            if len(selected) >= max_pages:
                break
            page = eligible[rel]
            if loaded + page.bytes > max_bytes:
                omitted.append(OmittedPage(rel, page.bytes))
                continue
            selected.append(page)
            loaded += page.bytes
    return Selection(
        index_md=index_md,
        pages=tuple(selected),
        ranker=ranker,
        fallback_reason=fallback_reason,
        bytes_loaded=loaded,
        max_bytes=max_bytes,
        omitted=tuple(omitted),
        ineligible=tuple(ineligible),
        ranker_config_hash=config_hash,
        warnings=tuple(warnings),
    )
