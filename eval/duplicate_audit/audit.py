# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The duplicate-audit study's script: mutual rank at k = 1, 3, 5 on one set (issue 121, FR-015, FR-016).

``python -m eval.duplicate_audit.audit --set {development,held-out} [--out-dir DIR]`` first checks the set's frozen
inputs and writes nothing, exiting 1 with the file and both values, on any difference. ``development``: every
``development.inputs`` hash of ``protocol.json`` and every page of cycle 10's corpus against its ``corpus.json``
entry. ``held-out``: ``held-out/freeze.json`` must exist, ``protocol.json``, ``corpus.json``, ``labels.json`` and
``review-sample.json`` must hash to its values, and every page to its ``corpus.json`` entry, so no candidate runs on
the held-out set before the freeze.

It then ranks as ``protocol.json`` says (FR-003): every page under its title-slug path
(``eval.similar.rank.slug_paths``), one in-memory FTS5 index over every page of the set in ``corpus.json`` order on
this script's own connection, and for each page its own row deleted, the rest ranked with
``discovery.similar_query`` under ``DEFAULT_RANKER_CONFIG``, pages of another page type dropped, and the row inserted
back. :func:`page_lists` gives every page's list once; :func:`flagged` reads each k from them (FR-004);
:func:`is_restatement` names the restatement rule a pair meets (FR-005). Per candidate the counts, and on the
held-out set the bar, the verdict and the winner (FR-006); on the development set the stop rule (FR-007).

Two files are written under ``--out-dir`` (default ``eval/duplicate_audit/results/``): ``<set>.json``, the same bytes
on every run, and ``<set>-timing.json``, the wall seconds of the pass and, for the held-out set, of the same pass over
the synthetic wiki of the time bound (FR-010). The script runs no git, calls no model, opens no network connection,
reads only files under the repository and writes only ``--out-dir``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import sqlite3
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from eval.similar.rank import slug_paths
from wiki_studio.discovery import DEFAULT_RANKER_CONFIG, ranker_config_hash, similar_query
from wiki_studio.review import frontmatter_value
from wiki_studio.search_index import INDEXED_COLUMNS, TABLE_NAME, SearchIndex, build_document, create_table

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "eval" / "duplicate_audit" / "results"

# The study's files, relative to the repository root.
PROTOCOL_PATH = "eval/duplicate_audit/protocol.json"
HELD_OUT_DIR = "eval/duplicate_audit/held-out"
FREEZE_PATH = f"{HELD_OUT_DIR}/freeze.json"
CORPUS_JSON_NAME = "corpus.json"
CORPUS_DIR_NAME = "corpus"
LABELS_NAME = "labels.json"
REVIEW_SAMPLE_NAME = "review-sample.json"

DEVELOPMENT = "development"
HELD_OUT = "held-out"
SETS = (DEVELOPMENT, HELD_OUT)
RESULTS_SUFFIX = ".json"
TIMING_SUFFIX = "-timing.json"

STUDY = "issue 121 duplicate-audit study: mutual rank on one set"
TIMING_STUDY = "issue 121 duplicate-audit study: the wall seconds of each pass"
CLOCK = "time.perf_counter"
SECONDS_DIGITS = 6
PER_100_DIGITS = 2
PER_100 = 100

# freeze.json keys and the file each pins.
FREEZE_PINS = (
    ("protocol_sha256", PROTOCOL_PATH),
    ("corpus_sha256", f"{HELD_OUT_DIR}/{CORPUS_JSON_NAME}"),
    ("labels_sha256", f"{HELD_OUT_DIR}/{LABELS_NAME}"),
    ("review_sample_sha256", f"{HELD_OUT_DIR}/{REVIEW_SAMPLE_NAME}"),
)

# corpus.json and labels.json keys.
PAGES_KEY = "pages"
PAGE_KEY = "page"
SHA256_KEY = "sha256"
PATH_KEY = "path"
REPOSITORY_KEY = "repository"
SPEC_PATH_KEY = "spec_path"
ORIGIN_ISSUE_KEY = "origin_issue"
PAIR_KEY = "pair"
DISPOSITION_KEY = "disposition"
PAIRS_KEY = "pairs"
CROSS_PAIRS_KEY = "cross_pairs"
GROUPS_KEY = "groups"
GROUP_ID_KEY = "id"
PAGE_TYPE_KEY = "page_type"

# The label of a pair labels.json does not list.
UNRELATED = "unrelated"

# The restatement rules (FR-005), named in protocol.json's order; a pair meeting none is written NOT_RESTATEMENT.
RULE_SAME_DIRECTORY = "a"
RULE_PITCH_AND_BUNDLE = "b"
RULE_TWO_PITCHES = "c"
RESTATEMENT_RULES = (RULE_SAME_DIRECTORY, RULE_PITCH_AND_BUNDLE, RULE_TWO_PITCHES)
NOT_RESTATEMENT = "-"
_PITCH_PATH = re.compile(r"specs/pitches/(?P<id>[^/]+)/pitch\.md")
_BUNDLE_PATH = re.compile(r"specs/[^/]+/(?:plan|spec)\.md")
_LEADING_NUMBER = re.compile(r"\d+")

# The pair scopes (reported, not binding).
ONE_FEATURE = "one-feature"
WITHIN_REPOSITORY = "within-repository"
CROSS_REPOSITORY = "cross-repository"
PAIR_SCOPES = (ONE_FEATURE, WITHIN_REPOSITORY, CROSS_REPOSITORY)

# The held-out bundles with no origin_issue (plan, O3): their found true pairs that are not restatements are listed.
WIKI_STUDIO = "wiki-studio"
NO_ORIGIN_ISSUE_DIRECTORIES = ("specs/wiki-studio-0-1-0", "specs/wiki-studio-0-6-0")

# The synthetic wiki of the time bound (FR-010): copy c >= 1 of a page gets this suffix on its stem.
COPY_SUFFIX = "-c"
PAGE_SUFFIX = ".md"

# The row this script inserts into its own index, column for column.
ROW_COLUMNS = (PATH_KEY, *INDEXED_COLUMNS)
INSERT_ROW = f"INSERT INTO {TABLE_NAME} ({', '.join(ROW_COLUMNS)}) VALUES ({', '.join('?' for _ in ROW_COLUMNS)})"
DELETE_ROW = f"DELETE FROM {TABLE_NAME} WHERE {PATH_KEY} = ?"
IN_MEMORY = ":memory:"

MISSING = "missing"
NONE = "none"
REFUSED = 1


@dataclass(frozen=True)
class Page:
    """One page of a set: its key (the corpus path), its title-slug index path, its text and its page type."""

    key: str
    path: str
    text: str
    page_type: str | None


@dataclass(frozen=True)
class StudySet:
    """Where a set's corpus, pages and labels live, relative to the repository root."""

    name: str
    corpus_json: str
    corpus_root: str
    labels: str


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


def study_set(name: str, protocol: Mapping[str, Any]) -> StudySet:
    """The set's paths: cycle 10's corpus for ``development`` (from ``protocol.json``), ``held-out/`` otherwise."""
    if name == DEVELOPMENT:
        development = protocol[DEVELOPMENT]
        corpus_root = str(development["corpus_pages"]["root"])
        corpus_json = posixpath.join(posixpath.dirname(corpus_root), CORPUS_JSON_NAME)
        return StudySet(name, corpus_json, corpus_root, str(development["labels"]))
    return StudySet(
        name,
        f"{HELD_OUT_DIR}/{CORPUS_JSON_NAME}",
        f"{HELD_OUT_DIR}/{CORPUS_DIR_NAME}",
        f"{HELD_OUT_DIR}/{LABELS_NAME}",
    )


def _mismatch(rel: str, actual: str, source: str, expected: str) -> str:
    return f"{rel} sha256 {actual} does not match {source} {expected}"


def check_pages(root: Path, chosen: StudySet) -> list[str]:
    """One message per corpus page whose sha256 differs from its ``corpus.json`` entry."""
    problems: list[str] = []
    for entry in load_json(root / chosen.corpus_json)[PAGES_KEY]:
        rel, expected = f"{chosen.corpus_root}/{entry[PAGE_KEY]}", str(entry[SHA256_KEY])
        actual = _sha256_or_missing(root / rel)
        if actual != expected:
            problems.append(_mismatch(rel, actual, chosen.corpus_json, expected))
    return problems


def check_development(root: Path, protocol: Mapping[str, Any], chosen: StudySet) -> list[str]:
    """Every ``development.inputs`` hash and every page; empty when frozen."""
    problems: list[str] = []
    for entry in protocol[DEVELOPMENT]["inputs"]:
        rel, expected = str(entry[PATH_KEY]), str(entry[SHA256_KEY])
        actual = _sha256_or_missing(root / rel)
        if actual != expected:
            problems.append(_mismatch(rel, actual, PROTOCOL_PATH, expected))
    return problems + check_pages(root, chosen)


def check_held_out(root: Path, chosen: StudySet) -> list[str]:
    """``freeze.json`` present, every file it pins at its value, every page at its entry; empty when frozen."""
    freeze_file = root / FREEZE_PATH
    if not freeze_file.is_file():
        return [f"{FREEZE_PATH} does not exist: no candidate runs on the held-out set before the freeze"]
    freeze = load_json(freeze_file)
    problems: list[str] = []
    for key, rel in FREEZE_PINS:
        expected, actual = str(freeze[key]), _sha256_or_missing(root / rel)
        if actual != expected:
            problems.append(_mismatch(rel, actual, f"{FREEZE_PATH} {key}", expected))
    if (root / chosen.corpus_json).is_file():
        problems += check_pages(root, chosen)
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


def check_inputs(root: Path, protocol: Mapping[str, Any], chosen: StudySet) -> list[str]:
    """Every check of the chosen set and the ranker; empty when the run may go ahead."""
    if chosen.name == DEVELOPMENT:
        return check_development(root, protocol, chosen) + check_ranker(protocol)
    return check_held_out(root, chosen) + check_ranker(protocol)


def checked_hashes(root: Path, protocol: Mapping[str, Any], chosen: StudySet) -> dict[str, str]:
    """The hashes the run was checked against, and ``protocol.json``'s and ``freeze.json``'s own."""
    if chosen.name == DEVELOPMENT:
        inputs = {str(entry[PATH_KEY]): str(entry[SHA256_KEY]) for entry in protocol[DEVELOPMENT]["inputs"]}
    else:
        inputs = {rel: sha256_of(root / rel) for _, rel in FREEZE_PINS}
        inputs[FREEZE_PATH] = sha256_of(root / FREEZE_PATH)
    inputs[PROTOCOL_PATH] = sha256_of(root / PROTOCOL_PATH)
    return inputs


# ── The pages and their lists (FR-003, FR-004) ────────────────


def load_pages(root: Path, chosen: StudySet, entries: Sequence[Mapping[str, Any]], template: str) -> list[Page]:
    """Every page in ``corpus.json`` order, keyed by its corpus path, indexed under its title-slug path."""
    paths = slug_paths(entries, template=template)
    pages: list[Page] = []
    for entry in entries:
        key = str(entry[PAGE_KEY])
        text = (root / chosen.corpus_root / key).read_text(encoding="utf-8")
        pages.append(Page(key, paths[key], text, frontmatter_value(text, PAGE_TYPE_KEY)))
    return pages


def _row(page: Page) -> tuple[str, ...]:
    document = build_document(page.path, page.text)
    return (page.path, *(str(getattr(document, column)) for column in INDEXED_COLUMNS))


def page_lists(pages: Sequence[Page]) -> dict[str, list[str]]:
    """Each page's list: the pages of its page type its query ranks, best first, with its own row removed (FR-003).

    One in-memory index holds every page in ``pages`` order. For each page its
    row is deleted, ``SearchIndex.rank`` ranks ``similar_query`` of its text over
    every other page's path in order, pages of another page type are dropped,
    and the row is inserted back before the next page.
    """
    by_path = {page.path: page for page in pages}
    rows = {page.key: _row(page) for page in pages}
    connection = sqlite3.connect(IN_MEMORY)
    with SearchIndex(connection) as index:
        create_table(connection, DEFAULT_RANKER_CONFIG.tokenizer)
        connection.executemany(INSERT_ROW, [rows[page.key] for page in pages])
        lists: dict[str, list[str]] = {}
        for page in pages:
            connection.execute(DELETE_ROW, (page.path,))
            ranked = index.rank(
                similar_query(page.text),
                order=[other.path for other in pages if other.key != page.key],
                weights=DEFAULT_RANKER_CONFIG.weights,
                min_match_tokens=DEFAULT_RANKER_CONFIG.min_match_tokens,
            )
            connection.execute(INSERT_ROW, rows[page.key])
            lists[page.key] = [by_path[path].key for path in ranked if by_path[path].page_type == page.page_type]
    return lists


def flagged(lists: Mapping[str, Sequence[str]], k: int) -> list[tuple[str, str, int, int]]:
    """Every pair each in the other's first ``k``, sorted: (a, b, b's rank in a's list, a's rank in b's), a < b."""
    pairs: list[tuple[str, str, int, int]] = []
    for page, listed in lists.items():
        for other in listed[:k]:
            if page < other and page in lists.get(other, [])[:k]:
                pairs.append((page, other, list(listed).index(other) + 1, list(lists[other]).index(page) + 1))
    return sorted(pairs)


# ── Labels, restatements and pair scope (FR-005) ──────────────


def pair_labels(labels: Mapping[str, Any]) -> dict[frozenset[str], str]:
    """Every labelled pair of ``pairs`` and ``cross_pairs`` mapped to its disposition."""
    entries = [*labels[PAIRS_KEY], *labels[CROSS_PAIRS_KEY]]
    return {frozenset(str(page) for page in entry[PAIR_KEY]): str(entry[DISPOSITION_KEY]) for entry in entries}


def _pitch_number(entry: Mapping[str, Any]) -> int | None:
    """The leading number of the pitch id when the entry comes from a pitch with one, else None."""
    match = _PITCH_PATH.fullmatch(str(entry.get(SPEC_PATH_KEY, "")))
    if match is None:
        return None
    number = _LEADING_NUMBER.match(match.group("id"))
    return None if number is None else int(number.group())


def _is_pitch(entry: Mapping[str, Any]) -> bool:
    return _PITCH_PATH.fullmatch(str(entry.get(SPEC_PATH_KEY, ""))) is not None


def _origin_issue(entry: Mapping[str, Any]) -> int | None:
    """The entry's ``origin_issue`` when it is an integer (a bool or a string is not), else None."""
    value = entry.get(ORIGIN_ISSUE_KEY)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _restates_pitch(pitch: Mapping[str, Any], bundle: Mapping[str, Any]) -> bool:
    """Rule (b) with ``pitch`` the pitch page: a bundle of the same repository whose origin issue is the pitch's."""
    number = _pitch_number(pitch)
    return (
        number is not None
        and _BUNDLE_PATH.fullmatch(str(bundle.get(SPEC_PATH_KEY, ""))) is not None
        and pitch.get(REPOSITORY_KEY) == bundle.get(REPOSITORY_KEY)
        and _origin_issue(bundle) == number
    )


def is_restatement(a: Mapping[str, Any], b: Mapping[str, Any]) -> str | None:
    """The first restatement rule the two pages' ``corpus.json`` entries meet, in the order a, b, c, or None."""
    same_repository = a.get(REPOSITORY_KEY) == b.get(REPOSITORY_KEY)
    if same_repository and posixpath.dirname(str(a[SPEC_PATH_KEY])) == posixpath.dirname(str(b[SPEC_PATH_KEY])):
        return RULE_SAME_DIRECTORY
    if _restates_pitch(a, b) or _restates_pitch(b, a):
        return RULE_PITCH_AND_BUNDLE
    if _is_pitch(a) and _is_pitch(b):
        return RULE_TWO_PITCHES
    return None


def pair_scope(a: Mapping[str, Any], b: Mapping[str, Any], rule: str | None) -> str:
    """``one-feature`` under rule a or b, else ``within-repository`` for one repository, else ``cross-repository``."""
    if rule in (RULE_SAME_DIRECTORY, RULE_PITCH_AND_BUNDLE):
        return ONE_FEATURE
    if a.get(REPOSITORY_KEY) == b.get(REPOSITORY_KEY):
        return WITHIN_REPOSITORY
    return CROSS_REPOSITORY


# ── Counting, the bar, selection and the stop rule (FR-006, FR-007) ──


@dataclass(frozen=True)
class FlaggedPair:
    """One flagged pair: the second page's rank in the first's list and the reverse, its label, scope and rule."""

    first: str
    second: str
    rank_in_first: int
    rank_in_second: int
    label: str
    scope: str
    rule: str | None

    def line(self) -> str:
        return (
            f"{self.first} {self.second} {self.rank_in_first}/{self.rank_in_second} {self.label} {self.scope} "
            f"{self.rule or NOT_RESTATEMENT}"
        )


def describe_pairs(
    pairs: Sequence[tuple[str, str, int, int]],
    labels: Mapping[frozenset[str], str],
    entries: Mapping[str, Mapping[str, Any]],
) -> list[FlaggedPair]:
    """Each flagged pair with its label (``unrelated`` when unlisted), its restatement rule and its scope."""
    described: list[FlaggedPair] = []
    for first, second, rank_in_first, rank_in_second in pairs:
        rule = is_restatement(entries[first], entries[second])
        scope = pair_scope(entries[first], entries[second], rule)
        label = labels.get(frozenset((first, second)), UNRELATED)
        described.append(FlaggedPair(first, second, rank_in_first, rank_in_second, label, scope, rule))
    return described


def _per_100(count: int, pages: int) -> float:
    return round(count * PER_100 / pages, PER_100_DIGITS) if pages else 0.0


def _by_rule(pairs: Sequence[FlaggedPair]) -> dict[str, int]:
    counts = Counter(pair.rule or NOT_RESTATEMENT for pair in pairs)
    return {rule: counts.get(rule, 0) for rule in (*RESTATEMENT_RULES, NOT_RESTATEMENT)}


def count_candidate(
    pairs: Sequence[FlaggedPair],
    *,
    true_dispositions: frozenset[str],
    false_dispositions: Sequence[str],
    groups: Sequence[Mapping[str, Any]],
    pages: int,
) -> dict[str, Any]:
    """One candidate's counts and pair lines; the readings that are not binding under ``not_binding``."""
    found = [pair for pair in pairs if pair.label in true_dispositions]
    false = [pair for pair in pairs if pair.label not in true_dispositions]
    false_labels = Counter(pair.label for pair in false)
    scopes = Counter(pair.scope for pair in pairs)
    found_groups = sorted(
        str(group[GROUP_ID_KEY])
        for group in groups
        if any(pair.first in group[PAGES_KEY] and pair.second in group[PAGES_KEY] for pair in found)
    )
    return {
        "flagged": len(pairs),
        "true": len(found),
        "false": len(false),
        "found": len(found),
        "non_restatement_found": sum(1 for pair in found if pair.rule is None),
        "pairs": sorted(pair.line() for pair in pairs),
        "not_binding": {
            "binding": False,
            "false_by_disposition": {label: false_labels.get(label, 0) for label in false_dispositions},
            "by_scope": {scope: scopes.get(scope, 0) for scope in PAIR_SCOPES},
            "flagged_by_restatement": _by_rule(pairs),
            "found_by_restatement": _by_rule(found),
            "per_100_pages": {
                "flagged": _per_100(len(pairs), pages),
                "true": _per_100(len(found), pages),
                "false": _per_100(len(false), pages),
            },
            "groups_with_a_flagged_true_pair": found_groups,
        },
    }


def bar_conditions(counts: Mapping[str, Any], n: int, bar: Mapping[str, Any]) -> dict[str, bool]:
    """FR-006's four conditions for one candidate's counts, and whether all hold."""
    conditions = {
        "testable": n >= int(bar["min_true_pairs"]),
        "recall": int(bar["recall_denominator"]) * int(counts["found"]) >= int(bar["recall_numerator"]) * n,
        "false_not_above_true": int(counts["false"]) <= int(counts["true"]),
        "non_restatement": int(counts["non_restatement_found"]) >= int(bar["min_non_restatement_found"]),
    }
    conditions["passes"] = all(conditions.values())
    return conditions


def select_winner(candidates: Sequence[tuple[str, int, Mapping[str, Any]]]) -> str | None:
    """Among (name, k, counts) whose bar passes, the fewest false per true; a tie to the smaller k; None if none."""
    best: tuple[str, int, Mapping[str, Any]] | None = None
    for name, k, counts in sorted(candidates, key=lambda candidate: candidate[1]):
        if not counts["bar"]["passes"]:
            continue
        if best is None or int(counts["false"]) * int(best[2]["true"]) < int(best[2]["false"]) * int(counts["true"]):
            best = (name, k, counts)
    return None if best is None else best[0]


def verdict_of(n: int, winner: str | None, protocol: Mapping[str, Any]) -> str:
    """``winner``, ``no candidate clears the bar`` or ``not testable``, as ``protocol.json`` spells them."""
    winner_verdict, no_candidate, not_testable = protocol["verdicts"]
    if n < int(protocol["bar"]["min_true_pairs"]):
        return str(not_testable)
    return str(winner_verdict if winner is not None else no_candidate)


def stop_rule(candidates: Mapping[str, Mapping[str, Any]], protocol: Mapping[str, Any]) -> dict[str, Any]:
    """Each candidate's ``false <= true`` on the development set; ``go`` when one holds, else ``stop`` (FR-007)."""
    holds = {name: int(counts["false"]) <= int(counts["true"]) for name, counts in candidates.items()}
    lines = protocol[DEVELOPMENT]["stage_lines"]
    outcome = "go" if any(holds.values()) else "stop"
    return {"false_not_above_true": holds, "outcome": outcome, "line": str(lines[outcome])}


# ── The audit ─────────────────────────────────────────────────


def _timed(action: Callable[[], dict[str, list[str]]]) -> tuple[dict[str, list[str]], float]:
    start = time.perf_counter()
    lists = action()
    return lists, round(time.perf_counter() - start, SECONDS_DIGITS)


def synthetic_pages(pages: Sequence[Page], count: int) -> list[Page]:
    """FR-010's synthetic wiki: page i is page ``i mod N``; copy ``c = i div N`` >= 1 gets ``-c<c>`` on its stem."""
    synthetic: list[Page] = []
    for i in range(count):
        page, copy = pages[i % len(pages)], i // len(pages)
        path = page.path if copy == 0 else f"{page.path[: -len(PAGE_SUFFIX)]}{COPY_SUFFIX}{copy}{PAGE_SUFFIX}"
        synthetic.append(Page(path, path, page.text, page.page_type))
    return synthetic


def _synthetic_pass(pages: Sequence[Page], ks: Sequence[int]) -> dict[str, list[str]]:
    lists = page_lists(pages)
    for k in ks:
        flagged(lists, k)
    return lists


def audit(root: Path, protocol: Mapping[str, Any], chosen: StudySet) -> tuple[dict[str, Any], dict[str, Any]]:
    """The results and timing documents for the chosen set, its inputs already checked."""
    entries = load_json(root / chosen.corpus_json)[PAGES_KEY]
    labels = load_json(root / chosen.labels)
    pages = load_pages(root, chosen, entries, str(protocol["index"]["path_template"]))
    by_key = {str(entry[PAGE_KEY]): entry for entry in entries}
    true_dispositions = frozenset(str(label) for label in protocol["true_dispositions"])
    labelled = pair_labels(labels)
    true_labels = Counter(label for label in labelled.values() if label in true_dispositions)
    n = sum(true_labels.values())
    candidates = [(str(candidate["name"]), int(candidate["k"])) for candidate in protocol["candidates"]]

    lists, seconds = _timed(lambda: page_lists(pages))
    results: dict[str, Any] = {}
    described: dict[str, list[FlaggedPair]] = {}
    for name, k in candidates:
        described[name] = describe_pairs(flagged(lists, k), labelled, by_key)
        counts = count_candidate(
            described[name],
            true_dispositions=true_dispositions,
            false_dispositions=[str(label) for label in protocol["false_dispositions"]],
            groups=labels.get(GROUPS_KEY, []),
            pages=len(pages),
        )
        results[name] = {"k": k, **counts}

    top = max(k for _, k in candidates)
    document: dict[str, Any] = {
        "study": STUDY,
        "set": chosen.name,
        "inputs": checked_hashes(root, protocol, chosen),
        "ranker": {
            "tokenizer": DEFAULT_RANKER_CONFIG.tokenizer,
            "weights": list(DEFAULT_RANKER_CONFIG.weights),
            "min_match_tokens": DEFAULT_RANKER_CONFIG.min_match_tokens,
            "ranker_config_hash": ranker_config_hash(),
        },
        "pages": len(pages),
        "paths": {page.key: page.path for page in pages},
        "lists": sorted(" ".join([key, "->", *listed[:top]]) for key, listed in lists.items()),
        "true_pairs": {
            "n": n,
            "by_disposition": {label: true_labels.get(label, 0) for label in sorted(true_dispositions)},
        },
        "candidates": results,
    }
    timing: dict[str, Any] = {
        "study": TIMING_STUDY,
        "set": chosen.name,
        "clock": CLOCK,
        "pages": len(pages),
        "seconds": seconds,
    }

    if chosen.name == DEVELOPMENT:
        document["stop_rule"] = stop_rule(results, protocol)
        return document, timing

    for name, _ in candidates:
        found = [pair for pair in described[name] if pair.label in true_dispositions]
        results[name]["bar"] = bar_conditions(results[name], n, protocol["bar"])
        results[name]["not_binding"]["no_origin_issue_found"] = no_origin_issue_found(found, by_key)
    winner = select_winner([(name, k, results[name]) for name, k in candidates])
    document["verdict"] = verdict_of(n, winner, protocol)
    document["winner"] = winner or NONE
    document["winner_line"] = str(protocol["winner_lines"][winner or NONE])

    count = int(protocol["time_bound"]["pages"])
    synthetic = synthetic_pages(pages, count)
    _, synthetic_seconds = _timed(lambda: _synthetic_pass(synthetic, [k for _, k in candidates]))
    timing["synthetic"] = {"pages": len(synthetic), "seconds": synthetic_seconds}
    return document, timing


def no_origin_issue_found(found: Sequence[FlaggedPair], entries: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """The lines of the true pairs found that are not restatements and involve a bundle with no origin issue."""
    return sorted(
        pair.line()
        for pair in found
        if pair.rule is None and any(_in_no_origin_bundle(entries[page]) for page in (pair.first, pair.second))
    )


def _in_no_origin_bundle(entry: Mapping[str, Any]) -> bool:
    directory = posixpath.dirname(str(entry[SPEC_PATH_KEY]))
    return entry.get(REPOSITORY_KEY) == WIKI_STUDIO and directory in NO_ORIGIN_ISSUE_DIRECTORIES


def render(document: Mapping[str, Any]) -> bytes:
    """The document as written: ``indent=2``, sorted keys, UTF-8 as is, one final newline."""
    return (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def run(root: Path, name: str, out_dir: Path) -> int:
    """Check, audit and write both files; 1, writing nothing, when an input does not match its pin."""
    try:
        protocol = load_json(root / PROTOCOL_PATH)
        chosen = study_set(name, protocol)
        problems = check_inputs(root, protocol, chosen)
        if problems:
            sys.stderr.write("".join(f"{problem}\n" for problem in problems))
            sys.stderr.write("the inputs are not the frozen inputs, so nothing was ranked and nothing was written\n")
            return REFUSED
        document, timing = audit(root, protocol, chosen)
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        sys.stderr.write(f"{type(exc).__name__}: {exc}; nothing was written\n")
        return REFUSED
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{name}{RESULTS_SUFFIX}").write_bytes(render(document))
    (out_dir / f"{name}{TIMING_SUFFIX}").write_bytes(render(timing))
    line = document["stop_rule"]["line"] if name == DEVELOPMENT else document["winner_line"]
    sys.stdout.write(f"{line}; written to {out_dir}\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m eval.duplicate_audit.audit",
        description="Run the frozen duplicate-audit protocol once on one set (issue 121).",
    )
    parser.add_argument(
        "--set",
        dest="study_set",
        choices=SETS,
        required=True,
        help="the development set (cycle 10's frozen corpus) or the held-out set (only after its freeze)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"where both result files are written (default: {DEFAULT_OUT_DIR.relative_to(REPO_ROOT)})",
    )
    return parser


def main(argv: Sequence[str] | None = None, *, root: Path | None = None) -> int:
    """Parse ``argv`` and run against ``root`` (default: this repository)."""
    try:
        args = build_parser().parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    return run(REPO_ROOT if root is None else root, args.study_set, args.out_dir)


if __name__ == "__main__":
    sys.exit(main())
