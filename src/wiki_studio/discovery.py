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
against. The ``fts5`` ranker keeps its table in a rebuildable cache beside the
wiki's lock file (:mod:`wiki_studio.search_index`), refreshed from those hashes
on every call; the cache only ranks and never supplies text.
"""

from __future__ import annotations

import errno
import functools
import hashlib
import json
import os
import posixpath
import sqlite3
import stat
import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .contract import DiscoveryInfo, read_manifest
from .errors import ContractViolationError
from .querier import DEFAULT_MAX_QUERY_PAGES, _extract_index_links, _select_query_candidates
from .review import superseded_by
from .search_index import CacheIdentity, IndexedPage, build_document, describe_cache, probe_fts5, rank_cached

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

# The page cap every public surface accepts: ``MIN_FIND_PAGES..DEFAULT_MAX_QUERY_PAGES`` inclusive (FR-006, FR-035).
MIN_FIND_PAGES = 1

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

_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
# What ``open(O_NOFOLLOW)`` raises for a symlink: ELOOP on Linux and macOS, EMLINK on the BSDs.
_SYMLINK_ERRNOS = frozenset({errno.ELOOP, errno.EMLINK})


class DiscoveryWarning(UserWarning):
    """A selection warning ``query`` passes on (the index over the budget, a search cache that could not be used)."""


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
    reason = probe_fts5(FTS5_TOKENIZER)
    return Fts5Probe(available=reason is None, sqlite_version=sqlite3.sqlite_version, reason=reason)


def _wiki_id(paths: WikiPaths) -> str:
    """The manifest's ``wiki_id``, or the empty string for a legacy wiki or one whose manifest does not parse."""
    try:
        manifest = read_manifest(paths)
    except ContractViolationError:
        return ""
    return "" if manifest is None else manifest.wiki_id


def cache_identity(paths: WikiPaths, config: RankerConfig = DEFAULT_RANKER_CONFIG) -> CacheIdentity:
    """What the search cache for ``paths`` under ``config`` must have been built for (FR-013)."""
    return CacheIdentity(
        wiki_path=str(paths.wiki_dir.resolve()),
        wiki_id=_wiki_id(paths),
        ranker_config_hash=ranker_config_hash(config),
        tokenizer=config.tokenizer,
    )


def describe_discovery(paths: WikiPaths | None = None, *, env: Mapping[str, str] | None = None) -> DiscoveryInfo:
    """``info``'s ``discovery`` (FR-010): the probe, the default ranker and its source, the live configuration hash.

    With ``paths``, ``cache`` is the search cache's path and state (FR-018),
    judged without writing anything. Raises ``ValueError`` when
    ``WIKI_STUDIO_RANKER`` names no ranker.
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
        cache=None
        if paths is None
        else describe_cache(paths.search_cache_file(), paths.wiki_dir, cache_identity(paths)).as_dict(),
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


def _read_regular(path: Path) -> bytes | None:
    """The bytes of the regular file at ``path``; ``None`` for a symlink or any other non-regular entry.

    The file is opened with ``O_NOFOLLOW`` and its kind judged on the open
    descriptor (as ``review._read_nofollow`` does), so an entry swapped for a
    symlink after any earlier check is never read. Raises ``OSError`` when the
    entry is missing or unreadable. Where ``O_NOFOLLOW`` is unavailable
    (Windows) the open follows a symlink, so the ``lstat`` before it is the
    weaker, non-atomic check.
    """
    if not _O_NOFOLLOW and not stat.S_ISREG(os.lstat(path).st_mode):
        return None
    try:
        fd = os.open(path, os.O_RDONLY | _O_NOFOLLOW)
    except OSError as exc:
        if exc.errno in _SYMLINK_ERRNOS:
            return None
        raise
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None
        with os.fdopen(fd, "rb") as handle:
            fd = -1
            return handle.read()
    finally:
        if fd >= 0:
            os.close(fd)


def _read_eligible(wiki_dir: Path, rel: str) -> LoadedPage | IneligiblePage:
    """Read one index-linked page once and classify it (FR-004)."""
    try:
        data = _read_regular(wiki_dir / rel)
    except OSError:
        return IneligiblePage(rel, INELIGIBLE_MISSING)
    if data is None:
        return IneligiblePage(rel, INELIGIBLE_NOT_REGULAR_FILE)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return IneligiblePage(rel, INELIGIBLE_NOT_UTF8)
    if superseded_by(text) is not None:
        return IneligiblePage(rel, INELIGIBLE_SUPERSEDED)
    return LoadedPage(rel, text, hashlib.sha256(data).hexdigest(), len(data))


def _read_index(wiki_dir: Path) -> tuple[str, int]:
    """``index.md``'s text and byte count; ``("", 0)`` when it is missing, a symlink, unreadable or not UTF-8."""
    try:
        data = _read_regular(wiki_dir / INDEX_NAME)
    except OSError:
        return "", 0
    if data is None:
        return "", 0
    try:
        return data.decode("utf-8"), len(data)
    except UnicodeDecodeError:
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


def validate_max_pages(max_pages: int) -> None:
    """``ValueError`` unless ``max_pages`` is an integer in ``MIN_FIND_PAGES..DEFAULT_MAX_QUERY_PAGES`` (FR-006).

    ``api.find``, ``api.query`` and the MCP ``find`` tool apply it, so no public
    surface loads more than the cap; ``select`` itself stays uncapped for the
    cache's full-ranking checks.
    """
    if isinstance(max_pages, bool) or not isinstance(max_pages, int):
        raise ValueError(
            f"max_pages must be an integer from {MIN_FIND_PAGES} to {DEFAULT_MAX_QUERY_PAGES}, got {max_pages!r}"
        )
    if not MIN_FIND_PAGES <= max_pages <= DEFAULT_MAX_QUERY_PAGES:
        raise ValueError(f"max_pages must be from {MIN_FIND_PAGES} to {DEFAULT_MAX_QUERY_PAGES}, got {max_pages}")


def _rank_fts5(
    paths: WikiPaths, question: str, eligible: dict[str, LoadedPage], config: RankerConfig
) -> tuple[list[str], str | None]:
    """Rank through the on-disk cache, refreshed from this call's reads; the warning when it fell back to memory."""
    pages = [IndexedPage(build_document(rel, page.text), page.sha256, page.bytes) for rel, page in eligible.items()]
    outcome = rank_cached(
        paths.search_cache_file(),
        paths.wiki_dir,
        cache_identity(paths, config),
        pages,
        question,
        weights=config.weights,
        min_match_tokens=config.min_match_tokens,
    )
    return outcome.ranked, outcome.warning


def _rank_index_first(
    paths: WikiPaths, question: str, candidate_count: int, eligible: dict[str, LoadedPage]
) -> list[str]:
    # The whole ranked list from the 0.7.0 selector; its own reads serve ranking only. The selector
    # keeps a link's spelling, so its paths are canonicalised (and deduplicated) to match ``eligible``.
    _index, ranked, _contents = _select_query_candidates(paths, question, max_pages=candidate_count)
    ordered: list[str] = []
    for rel in ranked:
        canonical = posixpath.normpath(rel)
        if canonical in eligible and canonical not in ordered:
            ordered.append(canonical)
    return ordered


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
    Writes nothing into the wiki; the ``fts5`` ranker refreshes its search
    cache beside it. Raises ``ContractViolationError`` when ``paths`` names a
    search cache inside the wiki.
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
    seen: set[str] = set()
    for link in links:
        # Two spellings of one page (``concepts/x.md``, ``./concepts/x.md``) are one candidate at its first position.
        rel = posixpath.normpath(link)
        if rel in _NEVER_CANDIDATES or rel in seen:
            continue
        seen.add(rel)
        read = _read_eligible(wiki_dir, rel)
        if isinstance(read, LoadedPage):
            eligible[rel] = read
        else:
            ineligible.append(read)

    notes: list[str] = []
    if ranker == RANKER_FTS5:
        ranked, cache_warning = _rank_fts5(paths, question, eligible, config)
        if cache_warning is not None:
            notes.append(cache_warning)
    else:
        ranked = _rank_index_first(paths, question, len(links), eligible)

    selected: list[LoadedPage] = []
    omitted: list[OmittedPage] = []
    loaded = index_bytes
    if index_bytes > max_bytes:
        notes.append(f"{INDEX_NAME} alone is {index_bytes} bytes, over the {max_bytes}-byte budget; no page was loaded")
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
        warnings=tuple(notes),
    )


def warn_selection(selection: Selection) -> None:
    """Pass a selection's warnings on as :class:`DiscoveryWarning` (``query`` has no result field for them)."""
    for message in selection.warnings:
        warnings.warn(message, DiscoveryWarning, stacklevel=2)
