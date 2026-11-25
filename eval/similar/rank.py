# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The similar-pages study's ranking script: every try of the frozen protocol, ranked once (issue 121, FR-011, FR-012).

``python -m eval.similar.rank [--out-dir DIR]`` first checks every ``inputs`` hash of ``protocol.json`` and every
corpus page against its ``corpus.json`` entry; on any difference it names the file and both values, writes nothing
and exits 1. It then ranks as ``protocol.json`` says, reading its fields rather than restating them: each corpus page
is indexed under its title-slug path (:func:`slug_paths`), each try's index holds every corpus page but the query page
in ``corpus.json`` order, the query is :func:`query_text`, the ranking is ``search_index.SearchIndex.rank`` under
``discovery.DEFAULT_RANKER_CONFIG``, the ranked pages are kept when of the query page's page type, and the list is
the first k of them. The tries are built from ``eval/duplicates/labels.json`` (the later page of each ``supersedes``
pair as ``protocol.json`` names it) and must equal ``protocol.json``'s ``tries``.

Reported beside the verdict and never part of it: the partner's rank in every try, the noise by label, two other
query readings (the whole page as written, the body only) and the issue 54 fixture ranked as the hint would rank it.

Two files are written under ``--out-dir`` (default ``eval/similar/results/``): ``ranks.json``, the same bytes on
every run, and ``timing.json``, the wall seconds of each pass. The script runs no git, calls no model, opens no
network connection, reads only files under the repository and writes only ``--out-dir``.
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import posixpath
import re
import sqlite3
import stat
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from wiki_studio.discovery import DEFAULT_RANKER_CONFIG, ranker_config_hash
from wiki_studio.querier import _extract_index_links
from wiki_studio.review import frontmatter_value, superseded_by
from wiki_studio.search_index import build_document, build_in_memory

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "eval" / "similar" / "results"

# The inputs, relative to the repository root (their hashes are protocol.json's ``inputs``).
PROTOCOL_PATH = "eval/similar/protocol.json"
CORPUS_JSON_PATH = "eval/duplicates/corpus.json"
LABELS_PATH = "eval/duplicates/labels.json"
FIXTURE_LABELS_PATH = "eval/patterns/labels.json"
RANKS_NAME = "ranks.json"
TIMING_NAME = "timing.json"

STUDY = "issue 121 similar-pages study: every try ranked"
TIMING_STUDY = "issue 121 similar-pages study: the wall seconds of each pass"
CLOCK = "time.perf_counter"
SECONDS_DIGITS = 6

# corpus.json and labels.json keys.
PAGES_KEY = "pages"
PAGE_KEY = "page"
TITLE_KEY = "title"
SHA256_KEY = "sha256"
PATH_KEY = "path"
PAIR_KEY = "pair"
DISPOSITION_KEY = "disposition"
PAIRS_KEY = "pairs"
CROSS_PAIRS_KEY = "cross_pairs"
PATTERN_PAIRS_KEY = "pattern_pairs"
BACKGROUND_PAIRS_KEY = "background_pairs"
PAGE_TYPE_KEY = "page_type"

# Dispositions: a pair of these is tried both ways; a supersedes pair once, the later ruling as the query.
REDUNDANT = "redundant"
CONFLICTING = "conflicting"
SUPERSEDES = "supersedes"
BOTH_WAYS = frozenset({REDUNDANT, CONFLICTING})
# The issue 54 fixture's true pairs as recorded (FR-007 (c)).
FIXTURE_TRUE_DISPOSITIONS = frozenset({REDUNDANT, CONFLICTING})
# The label of a pair labels.json does not list (its ``defaults``).
UNRELATED = "unrelated"

# The title-slug path (FR-003).
SLUG_PLACEHOLDER = "<slug>"
PATH_TEMPLATE = "decisions/<slug>.md"
UNTITLED = "untitled"
_NON_SLUG_RUN = re.compile(r"[^a-z0-9]+")
SLUG_SEPARATOR = "-"
FIRST_SUFFIX = 2

# A page's title and body do not depend on the path build_document is given.
_ANY_PATH = ""

# The fixture's index and the two files it never ranks, as discovery.select reads them.
INDEX_NAME = "index.md"
NEVER_RANKED = frozenset({INDEX_NAME, "log.md"})

PASS = "pass"
FAIL = "fail"
WHOLE_PAGE = "whole_page"
BODY_ONLY = "body_only"
BINDING = "binding"
FIXTURE = "fixture"
MISSING = "missing"

REFUSED = 1


@dataclass(frozen=True)
class Page:
    """One rankable page: its key in the study (corpus path or fixture path), its index path, text and page type."""

    key: str
    path: str
    text: str
    page_type: str | None


@dataclass(frozen=True)
class Try:
    """One try: the page proposed (``query``), the page it should find (``partner``) and the pair's disposition."""

    query: str
    partner: str
    disposition: str


# ── Reading and checking the inputs ───────────────────────────


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_or_missing(path: Path) -> str:
    try:
        return sha256_of(path)
    except OSError:
        return MISSING


def check_frozen(root: Path, protocol: Mapping[str, Any]) -> list[str]:
    """One message per input or corpus page whose sha256 differs from its pin, naming both values; empty when frozen."""
    problems: list[str] = []
    for entry in protocol["inputs"]:
        rel, expected = str(entry[PATH_KEY]), str(entry[SHA256_KEY])
        actual = _sha256_or_missing(root / rel)
        if actual != expected:
            problems.append(f"{rel} sha256 {actual} does not match {PROTOCOL_PATH} {expected}")
    corpus_root = str(protocol["corpus_pages"]["root"])
    for entry in load_json(root / CORPUS_JSON_PATH)[PAGES_KEY]:
        rel, expected = f"{corpus_root}/{entry[PAGE_KEY]}", str(entry[SHA256_KEY])
        actual = _sha256_or_missing(root / rel)
        if actual != expected:
            problems.append(f"{rel} sha256 {actual} does not match {CORPUS_JSON_PATH} {expected}")
    return problems


def check_ranker(protocol: Mapping[str, Any]) -> list[str]:
    """A message when protocol.json's ranker fields are not ``DEFAULT_RANKER_CONFIG``'s; empty when they are."""
    recorded = protocol["ranker"]
    expected = (
        DEFAULT_RANKER_CONFIG.tokenizer,
        list(DEFAULT_RANKER_CONFIG.weights),
        DEFAULT_RANKER_CONFIG.min_match_tokens,
    )
    actual = (recorded["tokenizer"], [float(w) for w in recorded["weights"]], recorded["min_match_tokens"])
    if actual != expected:
        return [f"{PROTOCOL_PATH} ranker {actual} is not DEFAULT_RANKER_CONFIG's {expected}"]
    return []


# ── The title-slug paths (FR-003) ─────────────────────────────


def slug_of(title: str) -> str:
    """The title lowercased, every run outside ``[a-z0-9]`` one ``-``, the ends stripped; ``untitled`` when empty."""
    return _NON_SLUG_RUN.sub(SLUG_SEPARATOR, title.lower()).strip(SLUG_SEPARATOR) or UNTITLED


def slug_paths(entries: Sequence[Mapping[str, Any]], *, template: str = PATH_TEMPLATE) -> dict[str, str]:
    """Each corpus page's title-slug path, pages taken in ``entries`` order.

    The first page with a slug keeps it. A later page with the same slug gets
    ``<slug>-2``, then ``-3``, skipping any value another page holds: one a
    page keeps as its own slug or one already given to an earlier page.
    """
    bases = [(str(entry[PAGE_KEY]), slug_of(str(entry[TITLE_KEY]))) for entry in entries]
    keeper: dict[str, str] = {}
    for page, base in bases:
        keeper.setdefault(base, page)
    taken = set(keeper)
    slugs: dict[str, str] = {}
    for page, base in bases:
        if keeper[base] == page:
            slugs[page] = base
            continue
        number = FIRST_SUFFIX
        while f"{base}{SLUG_SEPARATOR}{number}" in taken:
            number += 1
        slug = f"{base}{SLUG_SEPARATOR}{number}"
        taken.add(slug)
        slugs[page] = slug
    return {page: template.replace(SLUG_PLACEHOLDER, slug) for page, slug in slugs.items()}


def slug_collisions(entries: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    """Each slug given to more than one page by its title, with its pages in ``entries`` order."""
    groups: dict[str, list[str]] = {}
    for entry in entries:
        groups.setdefault(slug_of(str(entry[TITLE_KEY])), []).append(str(entry[PAGE_KEY]))
    return {slug: pages for slug, pages in groups.items() if len(pages) > 1}


# ── The query readings (FR-004, FR-007 (d)) ───────────────────


def query_text(text: str) -> str:
    """The query for a page whose text is ``text``: its frontmatter title, one space, its body (FR-004)."""
    document = build_document(_ANY_PATH, text)
    return f"{document.title} {document.body}"


def whole_page_text(text: str) -> str:
    """The reading that is not binding: the page as written, frontmatter included."""
    return text


def body_only_text(text: str) -> str:
    """The reading that is not binding: the body only, no title."""
    return build_document(_ANY_PATH, text).body


READINGS: dict[str, Callable[[str], str]] = {WHOLE_PAGE: whole_page_text, BODY_ONLY: body_only_text}


# ── The tries (FR-005, FR-007 (c)) ────────────────────────────


def pair_labels(labels: Mapping[str, Any]) -> dict[frozenset[str], str]:
    """Every labelled pair of ``pairs`` and ``cross_pairs`` mapped to its disposition."""
    entries = [*labels[PAIRS_KEY], *labels[CROSS_PAIRS_KEY]]
    return {frozenset(str(page) for page in entry[PAIR_KEY]): str(entry[DISPOSITION_KEY]) for entry in entries}


def later_pages(tries: Sequence[Mapping[str, Any]]) -> dict[frozenset[str], str]:
    """The later page of each ``supersedes`` pair, as protocol.json's tries name it (the query of that try)."""
    return {
        frozenset((str(entry["query"]), str(entry["partner"]))): str(entry["query"])
        for entry in tries
        if entry[DISPOSITION_KEY] == SUPERSEDES
    }


def build_tries(
    labels: Mapping[str, Any], later: Mapping[frozenset[str], str], true_dispositions: frozenset[str]
) -> list[Try]:
    """The tries in protocol order: each both-ways pair in labels order, sorted-first page first, then supersedes."""
    both_ways: list[Try] = []
    once: list[Try] = []
    for entry in [*labels[PAIRS_KEY], *labels[CROSS_PAIRS_KEY]]:
        disposition = str(entry[DISPOSITION_KEY])
        if disposition not in true_dispositions:
            continue
        first, second = sorted(str(page) for page in entry[PAIR_KEY])
        if disposition == SUPERSEDES:
            query = later.get(frozenset((first, second)))
            if query not in (first, second):
                raise ValueError(f"{PROTOCOL_PATH} names no later page for the supersedes pair {first}, {second}")
            once.append(Try(query, second if query == first else first, disposition))
        elif disposition in BOTH_WAYS:
            both_ways += [Try(first, second, disposition), Try(second, first, disposition)]
        else:
            raise ValueError(f"no direction rule for the disposition {disposition!r}")
    return both_ways + once


def build_fixture_tries(
    labels: Mapping[str, Any], page_types: Mapping[str, str | None], *, same_page_type: bool
) -> tuple[list[Try], list[dict[str, Any]]]:
    """The fixture's tries (pairs of one page type, both ways) and the true pairs the hint never lists."""
    tries: list[Try] = []
    never_listed: list[dict[str, Any]] = []
    for entry in [*labels[PATTERN_PAIRS_KEY], *labels[BACKGROUND_PAIRS_KEY]]:
        disposition = str(entry[DISPOSITION_KEY])
        if disposition not in FIXTURE_TRUE_DISPOSITIONS:
            continue
        first, second = sorted(str(page) for page in entry[PAIR_KEY])
        types = [page_types.get(first), page_types.get(second)]
        if types[0] is not None and types[1] is not None and (types[0] == types[1] or not same_page_type):
            tries += [Try(first, second, disposition), Try(second, first, disposition)]
        else:
            never_listed.append({PAIR_KEY: [first, second], DISPOSITION_KEY: disposition, "page_types": types})
    return tries, never_listed


def check_tries(name: str, built: Sequence[Try], recorded: Sequence[Mapping[str, Any]]) -> list[str]:
    """A message when the tries built from the labels are not protocol.json's ``name``, in order."""
    expected = [Try(str(entry["query"]), str(entry["partner"]), str(entry[DISPOSITION_KEY])) for entry in recorded]
    if list(built) != expected:
        return [f"the {name} built from the labels are not {PROTOCOL_PATH}'s {name}"]
    return []


# ── Reading the pages ─────────────────────────────────────────


def corpus_pages(root: Path, protocol: Mapping[str, Any], entries: Sequence[Mapping[str, Any]]) -> list[Page]:
    """Every corpus page in ``corpus.json`` order, keyed by its corpus path, indexed under its title-slug path."""
    corpus_root = root / str(protocol["corpus_pages"]["root"])
    paths = slug_paths(entries, template=str(protocol["index"]["path_template"]))
    pages: list[Page] = []
    for entry in entries:
        page = str(entry[PAGE_KEY])
        text = (corpus_root / page).read_text(encoding="utf-8")
        pages.append(Page(page, paths[page], text, frontmatter_value(text, PAGE_TYPE_KEY)))
    return pages


def _read_regular_text(path: Path) -> str | None:
    """The file's text when it is a regular file (not a symlink) and UTF-8, else None, as discovery.select skips it."""
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            return None
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def fixture_pages(wiki_dir: Path) -> tuple[list[Page], list[str]]:
    """The fixture pages the hint could list, in ``index.md`` link order, and the superseded pages left out."""
    index_md = (wiki_dir / INDEX_NAME).read_text(encoding="utf-8")
    eligible: list[Page] = []
    superseded: list[str] = []
    seen: set[str] = set()
    for link in _extract_index_links(index_md, wiki_dir):
        rel = posixpath.normpath(link)
        if rel in NEVER_RANKED or rel in seen:
            continue
        seen.add(rel)
        text = _read_regular_text(wiki_dir / rel)
        if text is None:
            continue
        if superseded_by(text) is not None:
            superseded.append(rel)
            continue
        eligible.append(Page(rel, rel, text, frontmatter_value(text, PAGE_TYPE_KEY)))
    return eligible, superseded


# ── Ranking and scoring (FR-003, FR-006) ──────────────────────


def compared_pages(
    pages: Sequence[Page], query_page: Page, query: str, *, same_page_type: bool, include_query_page: bool
) -> list[str]:
    """The keys of the pages compared for ``query``, best first: every match, then the page-type filter."""
    indexed = [page for page in pages if include_query_page or page.key != query_page.key]
    by_path = {page.path: page for page in indexed}
    with build_in_memory(
        [build_document(page.path, page.text) for page in indexed], tokenizer=DEFAULT_RANKER_CONFIG.tokenizer
    ) as index:
        ranked = index.rank(
            query,
            order=[page.path for page in indexed],
            weights=DEFAULT_RANKER_CONFIG.weights,
            min_match_tokens=DEFAULT_RANKER_CONFIG.min_match_tokens,
        )
    return [
        by_path[path].key for path in ranked if not same_page_type or by_path[path].page_type == query_page.page_type
    ]


def score_try(
    trial: Try, compared: Sequence[str], k: int, labels: Mapping[frozenset[str], str] | None = None
) -> dict[str, Any]:
    """The try's record: the first k compared pages, the partner's rank and found; with labels, the others."""
    listed = list(compared[:k])
    record: dict[str, Any] = {
        "query": trial.query,
        "partner": trial.partner,
        DISPOSITION_KEY: trial.disposition,
        "list": listed,
        "partner_rank": compared.index(trial.partner) + 1 if trial.partner in compared else None,
        "found": trial.partner in listed,
    }
    if labels is not None:
        record["others"] = [
            {PAGE_KEY: page, "label": labels.get(frozenset((trial.query, page)), UNRELATED)}
            for page in listed
            if page != trial.partner
        ]
    return record


def rank_tries(
    pages: Sequence[Page],
    tries: Sequence[Try],
    reading: Callable[[str], str],
    *,
    k: int,
    same_page_type: bool,
    include_query_page: bool,
    labels: Mapping[frozenset[str], str] | None = None,
) -> list[dict[str, Any]]:
    """Every try ranked with ``reading`` as the query rule, in order."""
    by_key = {page.key: page for page in pages}
    records: list[dict[str, Any]] = []
    for trial in tries:
        query_page = by_key[trial.query]
        compared = compared_pages(
            pages,
            query_page,
            reading(query_page.text),
            same_page_type=same_page_type,
            include_query_page=include_query_page,
        )
        records.append(score_try(trial, compared, k, labels))
    return records


def summarize(records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Found and tried, overall and for ``supersedes``, and the pairs with at least one found try."""
    pairs = {frozenset((record["query"], record["partner"])) for record in records}
    found_pairs = {frozenset((record["query"], record["partner"])) for record in records if record["found"]}
    supersedes = [record for record in records if record[DISPOSITION_KEY] == SUPERSEDES]
    return {
        "found": sum(1 for record in records if record["found"]),
        "tries": len(records),
        "supersedes_found": sum(1 for record in supersedes if record["found"]),
        "supersedes_tries": len(supersedes),
        "pairs_with_a_found_try": len(found_pairs),
        "pairs": len(pairs),
    }


def verdict(found: int, supersedes_found: int, bar: Mapping[str, Any]) -> str:
    """``pass`` when both conditions of the bar hold, else ``fail`` (FR-006)."""
    if found >= int(bar["min_found"]) and supersedes_found >= int(bar["min_supersedes_found"]):
        return PASS
    return FAIL


def noise(records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Every other listed page counted by its label against the query."""
    counts = Counter(str(other["label"]) for record in records for other in record["others"])
    return dict(sorted(counts.items()))


# ── The study ─────────────────────────────────────────────────


def _timed(action: Callable[[], list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], float]:
    start = time.perf_counter()
    records = action()
    return records, round(time.perf_counter() - start, SECONDS_DIGITS)


def rank_study(root: Path, protocol: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """``ranks.json`` and ``timing.json`` as documents; ``ValueError`` when the protocol does not match its inputs."""
    entries = load_json(root / CORPUS_JSON_PATH)[PAGES_KEY]
    labels = load_json(root / LABELS_PATH)
    fixture_spec = protocol["not_binding"][FIXTURE]
    k = int(protocol["k"])
    same_page_type = bool(protocol["same_page_type"])
    include_query_page = bool(protocol["index"]["query_page_in_index"])

    pages = corpus_pages(root, protocol, entries)
    tries = build_tries(labels, later_pages(protocol["tries"]), frozenset(protocol["true_dispositions"]))
    fixture_eligible, superseded = fixture_pages(root / str(fixture_spec["wiki"]))
    fixture_tries, never_listed = build_fixture_tries(
        load_json(root / FIXTURE_LABELS_PATH),
        {page.key: page.page_type for page in fixture_eligible},
        same_page_type=same_page_type,
    )
    problems = check_ranker(protocol)
    problems += check_tries("tries", tries, protocol["tries"])
    problems += check_tries("fixture tries", fixture_tries, fixture_spec["tries"])
    if [entry[PAIR_KEY] for entry in never_listed] != [list(fixture_spec["never_listed"][PAIR_KEY])]:
        problems.append(f"the fixture pairs never listed are not {PROTOCOL_PATH}'s never_listed pair")
    if superseded != list(fixture_spec["superseded_pages_left_out"]):
        problems.append(f"the fixture's superseded pages are not {PROTOCOL_PATH}'s superseded_pages_left_out")
    if problems:
        raise ValueError("; ".join(problems))

    ranked = functools.partial(rank_tries, k=k, same_page_type=same_page_type, include_query_page=include_query_page)
    binding, binding_seconds = _timed(functools.partial(ranked, pages, tries, query_text, labels=pair_labels(labels)))
    readings: dict[str, Any] = {}
    seconds: dict[str, float] = {BINDING: binding_seconds}
    for name, reading in READINGS.items():
        records, seconds[name] = _timed(functools.partial(ranked, pages, tries, reading))
        readings[name] = {BINDING: False, "tries": records, "summary": summarize(records)}
    fixture_records, seconds[FIXTURE] = _timed(functools.partial(ranked, fixture_eligible, fixture_tries, query_text))

    summary: dict[str, Any] = dict(summarize(binding))
    summary["verdict"] = verdict(summary["found"], summary["supersedes_found"], protocol["bar"])
    inputs = {str(entry[PATH_KEY]): str(entry[SHA256_KEY]) for entry in protocol["inputs"]}
    inputs[PROTOCOL_PATH] = sha256_of(root / PROTOCOL_PATH)
    ranks = {
        "study": STUDY,
        "inputs": inputs,
        "ranker": {
            "tokenizer": DEFAULT_RANKER_CONFIG.tokenizer,
            "weights": list(DEFAULT_RANKER_CONFIG.weights),
            "min_match_tokens": DEFAULT_RANKER_CONFIG.min_match_tokens,
            "ranker_config_hash": ranker_config_hash(),
        },
        "k": k,
        "paths": {page.key: page.path for page in pages},
        "collisions": slug_collisions(entries),
        "tries": binding,
        "summary": summary,
        "noise": noise(binding),
        "readings": readings,
        FIXTURE: {
            BINDING: False,
            "tries": fixture_records,
            "summary": summarize(fixture_records),
            "never_listed": never_listed,
            "superseded_left_out": superseded,
        },
    }
    timing = {
        "study": TIMING_STUDY,
        "clock": CLOCK,
        "pages": len(pages),
        "tries": len(tries),
        "fixture_pages": len(fixture_eligible),
        "fixture_tries": len(fixture_tries),
        "seconds": seconds,
    }
    return ranks, timing


def render(document: Mapping[str, Any]) -> bytes:
    """The document as written: ``indent=2``, sorted keys, UTF-8 as is, one final newline."""
    return (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def run(root: Path, out_dir: Path) -> int:
    """Check, rank and write both files; 1, writing nothing, when an input or the protocol does not match."""
    try:
        protocol = load_json(root / PROTOCOL_PATH)
        problems = check_frozen(root, protocol)
        if problems:
            sys.stderr.write("".join(f"{problem}\n" for problem in problems))
            sys.stderr.write("the inputs are not the frozen inputs, so nothing was ranked and nothing was written\n")
            return REFUSED
        ranks, timing = rank_study(root, protocol)
    except (OSError, ValueError, KeyError, sqlite3.Error) as exc:
        sys.stderr.write(f"{type(exc).__name__}: {exc}; nothing was written\n")
        return REFUSED
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / RANKS_NAME).write_bytes(render(ranks))
    (out_dir / TIMING_NAME).write_bytes(render(timing))
    summary = ranks["summary"]
    sys.stdout.write(
        f"found {summary['found']} of {summary['tries']}, supersedes {summary['supersedes_found']} of "
        f"{summary['supersedes_tries']}: {summary['verdict']}; written to {out_dir}\n"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m eval.similar.rank",
        description="Rank every try of the frozen similar-pages protocol once (issue 121).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"where ranks.json and timing.json are written (default: {DEFAULT_OUT_DIR.relative_to(REPO_ROOT)})",
    )
    return parser


def main(argv: Sequence[str] | None = None, *, root: Path | None = None) -> int:
    """Parse ``argv`` and run against ``root`` (default: this repository)."""
    try:
        args = build_parser().parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    return run(REPO_ROOT if root is None else root, args.out_dir)


if __name__ == "__main__":
    sys.exit(main())
