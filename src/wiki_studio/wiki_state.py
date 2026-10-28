# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# wiki-studio.wiki_state — load existing wiki state for the multi-page ingest prompt.
#
# Phase 1 of the rescoped wiki-ingest-pipeline. The Karpathy-pattern
# maintainer prompt is wiki-aware: it includes index.md, log.md, and a
# bounded candidate set of relevant existing pages so the LLM can produce
# a multi-page write plan that integrates with current state instead of
# generating an isolated proposal.
#
# Candidate selection is a deliberately simple lexical heuristic: token
# overlap between the source content and each wiki page's title +
# frontmatter slug. It runs in O(pages × source_tokens) Python and needs
# no embeddings or external dependencies. Trade-off: it will miss
# semantic matches with no shared vocabulary; the curator is the
# backstop. Phase N may add a smarter selector if dogfooding shows the
# heuristic is too narrow.

from __future__ import annotations

import hashlib
import os
import re
import stat
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .errors import ContractViolationError
from .paths import ContainmentError, contain

if TYPE_CHECKING:
    from pathlib import Path

    from .paths import WikiPaths

# Maximum candidate pages to load into the prompt by default. The prompt
# size budget is the 32 KiB AGENTS-style limit; ten typical wiki pages
# (~1–2 KiB each) plus index.md + log.md + the source comfortably fit.
DEFAULT_MAX_CANDIDATES = 10

# Token regex: alphanumerics + hyphens, case-folded. Stop at any other
# character. This matches slug shapes and most identifier-like words.
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9-]*")

# Words too common to be useful for relevance scoring. The list is
# deliberately small — a real stopword list is overkill for the
# wiki-page corpus, which is technical prose with repeating jargon.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "were",
        "which",
        "with",
    }
)


@dataclass(frozen=True)
class PageContent:
    """One page as read once: the exact bytes, their UTF-8 text and the sha256 of those bytes.

    The three always come from a single read, so a hash recorded as an
    edit's ``base_sha256`` identifies the very bytes whose text the author
    (or the model's prompt) saw.
    """

    data: bytes
    text: str
    sha256: str


def read_page_content(path: Path) -> PageContent:
    """Read ``path`` once and return its bytes, decoded text and sha256.

    ``OSError`` and ``UnicodeDecodeError`` propagate; the caller decides what
    an unreadable or non-UTF-8 page means on its surface.
    """
    data = path.read_bytes()
    return PageContent(data=data, text=data.decode("utf-8"), sha256=hashlib.sha256(data).hexdigest())


@dataclass(frozen=True)
class WikiState:
    """Snapshot of the existing wiki passed into the multi-page ingest prompt.

    Attributes
    ----------
    index_md : str
        Verbatim contents of the wiki's ``index.md``. Empty string
        if the wiki has no index (a fresh-repo edge case).
    log_md : str
        Verbatim contents of the wiki's ``log.md``. Empty string
        if absent.
    candidates : dict[str, PageContent]
        Map from wiki-relative path (e.g. ``concepts/origin-alignment.md``)
        to the page as read once (bytes, text, sha256). Selected by
        relevance against the ingest source. Order is not significant;
        the dict type is preserved for stable JSON serialisation in the
        BackendPrompt. ``candidate_pages`` (the text placed in the
        prompt) and ``candidate_hashes`` (the ``base_sha256`` attached
        to an ``update`` of that page) are views of the same reads.
    """

    index_md: str
    log_md: str
    candidates: dict[str, PageContent] = field(default_factory=dict)

    @property
    def candidate_pages(self) -> dict[str, str]:
        """Wiki-relative path to the page text the prompt shows."""
        return {rel: page.text for rel, page in self.candidates.items()}

    @property
    def candidate_hashes(self) -> dict[str, str]:
        """Wiki-relative path to the sha256 of the bytes that text was decoded from."""
        return {rel: page.sha256 for rel, page in self.candidates.items()}


def _tokenise(text: str) -> set[str]:
    """Return a lowercase token-set for relevance scoring."""
    if not text:
        return set()
    return {tok for tok in _TOKEN_RE.findall(text.lower()) if tok not in _STOPWORDS}


_O_NONBLOCK = getattr(os, "O_NONBLOCK", 0)


def _read_text_or_empty(path: Path) -> str:
    """Return the file contents, or '' if the file is missing, unreadable, not a regular file or not valid UTF-8.

    A non-UTF-8 page reads as empty here, so no caller selects, checks or crashes on it;
    the structural linter reports it (0.8.0, FR-003). The open is non-blocking and
    the kind is judged on the descriptor, so a FIFO at a page path reads as empty
    instead of hanging every reader (the 0.7.0 selector, the health and prose checks).
    """
    try:
        fd = os.open(path, os.O_RDONLY | _O_NONBLOCK)
    except OSError:
        return ""
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return ""
        with os.fdopen(fd, "rb") as handle:
            fd = -1
            return handle.read().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    finally:
        if fd >= 0:
            os.close(fd)


def _contained_read_or_empty(wiki_dir: Path, rel: str) -> str:
    """``rel`` read inside the wiki boundary (FR-012); a symlinked or escaping file is refused, not read."""
    try:
        real = contain(rel, wiki_dir)
    except ContainmentError as exc:
        raise ContractViolationError(f"{rel} in {wiki_dir} is outside the wiki boundary ({exc})") from exc
    return _read_text_or_empty(real)


def _inside_wiki(page: Path, wiki_dir: Path) -> bool:
    """True when ``page`` (under ``wiki_dir``) reaches no symlink and stays inside the wiki."""
    try:
        contain(page.relative_to(wiki_dir), wiki_dir)
    except (ContainmentError, ValueError):
        return False
    return True


def _list_wiki_pages(wiki_dir: Path) -> list[Path]:
    """Return all candidate wiki .md files (excludes schema/, scripts/, .audit/, index, log, overview)."""
    if not wiki_dir.is_dir():
        return []
    excluded_dirs = {"schema", "scripts", ".audit"}
    excluded_stems = {"index", "log", "overview"}
    pages: list[Path] = []
    for p in sorted(wiki_dir.rglob("*.md")):
        rel_parts = p.relative_to(wiki_dir).parts
        if rel_parts and rel_parts[0] in excluded_dirs:
            continue
        if p.stem in excluded_stems and p.parent == wiki_dir:
            continue
        # The wiki boundary (FR-012): a symlinked page, or one under a symlinked
        # directory, is never a candidate, so no file outside the wiki reaches
        # the prompt.
        if not _inside_wiki(p, wiki_dir):
            continue
        pages.append(p)
    return pages


def _read_page_or_none(path: Path) -> PageContent | None:
    """The page as read once, or None when it is missing, unreadable or not UTF-8 (then it is no candidate)."""
    try:
        return read_page_content(path)
    except (OSError, UnicodeDecodeError):
        return None


def _score_page_against_source(page_path: Path, content: str, source_tokens: set[str]) -> int:
    """Score a wiki page by token overlap with the source.

    Score = |source_tokens ∩ page_signal_tokens|, where page_signal_tokens
    is the union of the page's slug, the slugified path, and the first
    400 characters of body (typically title + lead paragraph).
    ``content`` is the page text already read, so scoring never reads
    the page a second time.
    """
    if not source_tokens or not content:
        return 0
    # Slug: filename stem.
    signal = {page_path.stem.lower()}
    # Path tokens (e.g., concepts/origin-alignment → "concepts", "origin", "alignment").
    signal |= _tokenise(str(page_path).replace("/", " ").replace("-", " "))
    # First 400 chars usually cover title + lead paragraph.
    signal |= _tokenise(content[:400])
    return len(source_tokens & signal)


def load_wiki_state(
    paths: WikiPaths,
    source_path: Path,
    source_content: str,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> WikiState:
    """Load index/log + a relevance-ranked candidate page set.

    Parameters
    ----------
    paths : WikiPaths
        The resolved layout; pages are read from ``paths.wiki_dir``.
    source_path : Path
        The source file being ingested. Path tokens are added to the
        relevance signal so a source under ``docs/wiki-ingest/``
        will rank wiki pages with "wiki" in their slug higher.
    source_content : str
        The full source content; tokens drive the relevance scoring.
    max_candidates : int
        Cap on candidate pages. Pages tied at the boundary score are
        cut deterministically by sorted path order.

    Returns
    -------
    WikiState
        index_md, log_md verbatim; candidates keyed by wiki-relative
        path, each read exactly once: the text the prompt shows and the
        sha256 an ``update`` of that page carries come from the same
        bytes (FR-007). Returns empty state for missing wiki.
    """
    wiki_dir = paths.wiki_dir
    if not wiki_dir.is_dir():
        return WikiState(index_md="", log_md="", candidates={})
    index_md = _contained_read_or_empty(wiki_dir, "index.md")
    log_md = _contained_read_or_empty(wiki_dir, "log.md")

    source_tokens = _tokenise(source_content) | _tokenise(str(source_path))

    # One read per page: the bytes scored here are the bytes a selected page
    # contributes to the prompt and to its hash; nothing is reread later.
    scored: list[tuple[int, Path, PageContent]] = []
    for page in _list_wiki_pages(wiki_dir):
        content = _read_page_or_none(page)
        if content is None:
            continue
        score = _score_page_against_source(page, content.text, source_tokens)
        if score > 0:
            scored.append((score, page, content))

    # Sort by descending score, then by path for stability.
    scored.sort(key=lambda item: (-item[0], str(item[1])))
    selected = scored[:max_candidates]

    candidates = {str(page.relative_to(wiki_dir)): content for _score, page, content in selected}
    return WikiState(index_md=index_md, log_md=log_md, candidates=candidates)
