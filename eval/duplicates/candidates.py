# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The near-duplicate study's scorer: B0 and B1 over every pair of the frozen corpus (issue 121, FR-020, FR-021).

``python -m eval.duplicates.candidates [--out-dir DIR]`` refuses to run, writing nothing and naming both values,
unless ``corpus.json`` and ``labels.json`` hash to ``protocol.json``'s ``corpus_sha256`` and ``labels_sha256``. It
then scores the two candidates as ``protocol.json`` defines them, reading their rules from it: B0 is
``wiki_state._tokenise(title + " " + paragraph)``, the title and the paragraph read by ``_title`` and
``_first_paragraph``, imported read-only from ``eval/patterns/duplicates.py``; B1 is B0 with the protocol's text rules
and token rules. Every unordered pair of pages is compared, and a pair is a candidate when
``4 * shared >= union`` with a non-empty union, in integers.

Three files are written under ``--out-dir`` (default ``eval/duplicates/results/``):

* ``candidates.json`` (deterministic): the three input hashes; the page and pair counts by scope; the true pairs by
  disposition and by scope; per candidate the true and false candidates, the true pairs found out of n, the false
  candidates by disposition, the true and false candidates by scope and by repository, the false candidates per 100
  pages, the verdict on each bar condition and overall, and ``candidate_pairs``, one string per pair; then
  ``true_pair_scores``, one string per true pair with both candidates' scores; the verdict and the winner;
* ``secondary.json`` (deterministic, not binding): B0 and B1 on the issue 54 fixture, read as recorded and with the
  disputed pair read as the protocol's second reading, counts only, no verdict;
* ``timing.json``: the wall time of each candidate's scoring pass, with the page and pair counts.

The script runs no git, calls no model, reads nothing outside the repository and writes only ``--out-dir``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from itertools import combinations
from pathlib import Path
from typing import TYPE_CHECKING, Any

from eval.duplicates.extract import CORPUS_DIR_NAME, CORPUS_JSON_NAME, DUPLICATES_DIR
from eval.duplicates.sample import LABELS_NAME
from eval.patterns.duplicates import (
    FIXTURE_NAME,
    MANIFEST_NAME,
    PATTERNS_DIR,
    TRUE_DISPOSITIONS,
    _first_paragraph,
    _title,
)
from wiki_studio.review import superseded_by
from wiki_studio.wiki_state import _tokenise

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

PROTOCOL_NAME = "protocol.json"
RESULTS_DIR_NAME = "results"
CANDIDATES_NAME = "candidates.json"
SECONDARY_NAME = "secondary.json"
TIMING_NAME = "timing.json"
DEFAULT_OUT_DIR = DUPLICATES_DIR / RESULTS_DIR_NAME
CORPUS_SHA256_KEY = "corpus_sha256"
LABELS_SHA256_KEY = "labels_sha256"

STUDY = "issue 121 near-duplicate study: the candidates scored"
SECONDARY_STUDY = "issue 121 near-duplicate study: the issue 54 fixture re-scored (not binding)"
TIMING_STUDY = "issue 121 near-duplicate study: the wall time of each candidate's scoring pass"
CLOCK = "time.perf_counter"
SECONDS_DIGITS = 6

PASS = "pass"
FAIL = "fail"
NOT_TESTABLE = "not testable"
WINNER_NONE = "none"
TRUE_KEY = "true"
FALSE_KEY = "false"
FOUND = "found"
MISSED = "missed"
RECORDED_READING = "as recorded"
SECOND_READING_PREFIX = "disputed pair as"
PER_PAGES = 100
HUNDREDTHS = Decimal("0.01")

REFUSED = 1


@dataclass(frozen=True)
class Candidate:
    """One candidate as ``protocol.json`` defines it: text rules, ``_tokenise``, then token rules and words."""

    name: str
    separator: str
    text_rules: tuple[tuple[re.Pattern[str], str], ...]
    token_rules: tuple[re.Pattern[str], ...]
    words: frozenset[str]

    def tokens(self, title: str, paragraph: str) -> set[str]:
        """The token set of ``title + separator + paragraph`` under this candidate's rules."""
        text = f"{title}{self.separator}{paragraph}"
        for pattern, replacement in self.text_rules:
            text = pattern.sub(replacement, text)
        kept = {token for token in _tokenise(text) if token not in self.words}
        return {token for token in kept if not any(rule.fullmatch(token) for rule in self.token_rules)}


@dataclass(frozen=True)
class Page:
    """One corpus page: its path under ``corpus/``, repository, family, title and the paragraph the scorer reads."""

    path: str
    repository: str
    family: str
    title: str
    paragraph: str


@dataclass(frozen=True)
class Pair:
    """One unordered pair of corpus pages in sorted order, with its label, scope and repository split."""

    left: str
    right: str
    label: str
    scope: str
    repository: str


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pair_key(left: str, right: str) -> tuple[str, str]:
    return (left, right) if left <= right else (right, left)


def check_frozen(directory: Path, protocol: Mapping[str, Any]) -> list[str]:
    """One message per input that does not hash to the protocol's value, naming both values; empty when frozen."""
    problems: list[str] = []
    for name, key in ((CORPUS_JSON_NAME, CORPUS_SHA256_KEY), (LABELS_NAME, LABELS_SHA256_KEY)):
        actual = sha256_of(directory / name)
        expected = str(protocol[key])
        if actual != expected:
            problems.append(f"{name} sha256 {actual} does not match {PROTOCOL_NAME} {key} {expected}")
    return problems


def candidates_from_protocol(protocol: Mapping[str, Any]) -> list[Candidate]:
    """The candidates in the protocol's order, each built from its fields, a ``base`` candidate's rules first."""
    specs = protocol["candidates"]
    built: dict[str, Candidate] = {}
    for name in specs["order"]:
        spec = specs[name]
        base = built[str(spec["base"])] if "base" in spec else None
        text_rules = tuple(
            (re.compile(rule["pattern"]), str(rule["replacement"])) for rule in spec.get("text_rules", [])
        )
        token_specs = spec.get("token_rules", [])
        token_rules = tuple(re.compile(rule["fullmatch"]) for rule in token_specs if "fullmatch" in rule)
        words = frozenset(str(word) for rule in token_specs for word in rule.get("words", []))
        if base is None:
            built[name] = Candidate(str(name), str(spec["separator"]), text_rules, token_rules, words)
        else:
            built[name] = Candidate(
                str(name),
                base.separator,
                base.text_rules + text_rules,
                base.token_rules + token_rules,
                base.words | words,
            )
    return [built[name] for name in specs["order"]]


def threshold_of(protocol: Mapping[str, Any]) -> tuple[int, int]:
    """The threshold as the integers ``(numerator, denominator)``: Jaccard at least numerator / denominator."""
    threshold = protocol["threshold"]
    return int(threshold["numerator"]), int(threshold["denominator"])


def is_candidate(shared: int, union: int, threshold: tuple[int, int]) -> bool:
    """``denominator * shared >= numerator * union`` with a non-empty union: exact, no rounding."""
    numerator, denominator = threshold
    return union > 0 and denominator * shared >= numerator * union


def score_pairs(candidate: Candidate, texts: Sequence[tuple[str, str]]) -> list[tuple[int, int]]:
    """``(shared, union)`` for every pair of ``(title, paragraph)`` texts, in ``combinations`` order."""
    token_sets = [candidate.tokens(title, paragraph) for title, paragraph in texts]
    return [(len(left & right), len(left | right)) for left, right in combinations(token_sets, 2)]


def bar_verdict(
    found: int, true_pairs: int, true_candidates: int, false_candidates: int, bar: Mapping[str, Any]
) -> dict[str, Any]:
    """Each of the bar's three conditions and the overall verdict: pass, fail, or not testable (too few true pairs)."""
    enough, recall, _ratio = bar["conditions"]
    result: dict[str, Any] = {
        "enough_true_pairs": true_pairs >= int(enough["minimum_true_pairs"]),
        "recall": int(recall["denominator"]) * found >= int(recall["numerator"]) * true_pairs,
        "false_not_above_true": false_candidates <= true_candidates,
    }
    if not result["enough_true_pairs"]:
        result["overall"] = NOT_TESTABLE
    elif result["recall"] and result["false_not_above_true"]:
        result["overall"] = PASS
    else:
        result["overall"] = FAIL
    return result


def select(protocol: Mapping[str, Any], results: Mapping[str, Any]) -> tuple[str, str]:
    """The verdict and the winner: the passing candidate with the fewest false candidates, a tie to the protocol's."""
    verdict_winner, verdict_none, verdict_not_testable = protocol["verdicts"]
    order = list(protocol["candidates"]["order"])
    if any(results[name]["bar"]["overall"] == NOT_TESTABLE for name in order):
        return verdict_not_testable, WINNER_NONE
    passing = [name for name in order if results[name]["bar"]["overall"] == PASS]
    if not passing:
        return verdict_none, WINNER_NONE
    tie = protocol["selection"]["tie"]
    winner = min(passing, key=lambda name: (results[name]["false_candidates"], name != tie, order.index(name)))
    return verdict_winner, winner


def per_hundred_pages(false_candidates: int, pages: int) -> str:
    """``false * 100 / pages`` to two decimals, rounded half up, as a string so the two decimals stay written."""
    value = Decimal(false_candidates * PER_PAGES) / Decimal(pages)
    return str(value.quantize(HUNDREDTHS, rounding=ROUND_HALF_UP))


def pair_scope(left: Page, right: Page, scopes: Sequence[str]) -> str:
    within_family, cross_family, cross_repository = scopes
    if left.repository != right.repository:
        return cross_repository
    return within_family if left.family == right.family else cross_family


def corpus_pages(directory: Path, corpus: Mapping[str, Any]) -> list[Page]:
    """Every page of ``corpus.json`` in path order, read once: its title and the paragraph the scorer reads."""
    pages: list[Page] = []
    for entry in sorted(corpus["pages"], key=lambda row: str(row["page"])):
        text = (directory / CORPUS_DIR_NAME / str(entry["page"])).read_text(encoding="utf-8")
        path, repository, family = str(entry["page"]), str(entry["repository"]), str(entry["family"])
        pages.append(Page(path, repository, family, _title(text), _first_paragraph(text)))
    return pages


def corpus_pairs(pages: Sequence[Page], labels: Mapping[str, Any], protocol: Mapping[str, Any]) -> list[Pair]:
    """Every unordered pair of ``pages``, in ``combinations`` order, with its label, scope and repository split."""
    scopes = list(protocol["pairs"]["scope_order"])
    cross_repository = scopes[-1]
    default = str(protocol["labels"]["default"])
    stated = {pair_key(*row["pair"]): str(row["disposition"]) for row in (*labels["pairs"], *labels["cross_pairs"])}
    pairs: list[Pair] = []
    for left, right in combinations(pages, 2):
        scope = pair_scope(left, right, scopes)
        repository = cross_repository if scope == cross_repository else left.repository
        label = stated.get(pair_key(left.path, right.path), default)
        pairs.append(Pair(left.path, right.path, label, scope, repository))
    return pairs


def candidate_view(
    pairs: Sequence[Pair],
    scores: Sequence[tuple[int, int]],
    protocol: Mapping[str, Any],
    page_count: int,
    true_pairs: int,
) -> dict[str, Any]:
    """One candidate's figures (FR-020): counts, splits, per 100 pages, the bar and its candidate pairs."""
    threshold = threshold_of(protocol)
    true_labels = frozenset(protocol["labels"]["true"])
    splits = protocol["reporting_splits"]
    false_by_disposition = dict.fromkeys(splits["by_disposition"], 0)
    by_scope = {scope: {TRUE_KEY: 0, FALSE_KEY: 0} for scope in splits["by_scope"]}
    by_repository = {repository: {TRUE_KEY: 0, FALSE_KEY: 0} for repository in splits["by_repository"]}
    lines: list[str] = []
    true_candidates = 0
    false_candidates = 0
    for pair, (shared, union) in zip(pairs, scores, strict=True):
        if not is_candidate(shared, union, threshold):
            continue
        if pair.label in true_labels:
            side = TRUE_KEY
            true_candidates += 1
        else:
            side = FALSE_KEY
            false_candidates += 1
            false_by_disposition[pair.label] += 1
        by_scope[pair.scope][side] += 1
        by_repository[pair.repository][side] += 1
        lines.append(f"{pair.left} {pair.right} {shared}/{union} {pair.label} {pair.scope}")
    bar = bar_verdict(true_candidates, true_pairs, true_candidates, false_candidates, protocol["bar"])
    found = NOT_TESTABLE if bar["overall"] == NOT_TESTABLE else f"{true_candidates} of {true_pairs}"
    return {
        "true_candidates": true_candidates,
        "false_candidates": false_candidates,
        "true_pairs_found": true_candidates,
        "true_pairs": true_pairs,
        "found_out_of_n": found,
        "false_by_disposition": false_by_disposition,
        "by_scope": by_scope,
        "by_repository": by_repository,
        "false_per_100_pages": per_hundred_pages(false_candidates, page_count),
        "bar": bar,
        "candidate_pairs": sorted(lines),
    }


def true_pair_scores(
    pairs: Sequence[Pair],
    scored: Mapping[str, Sequence[tuple[int, int]]],
    protocol: Mapping[str, Any],
) -> list[str]:
    """One string per true pair: the pair, its label and scope, then each candidate's score and found or missed."""
    threshold = threshold_of(protocol)
    true_labels = frozenset(protocol["labels"]["true"])
    lines: list[str] = []
    for index, pair in enumerate(pairs):
        if pair.label not in true_labels:
            continue
        parts = [pair.left, pair.right, pair.label, pair.scope]
        for name, scores in scored.items():
            shared, union = scores[index]
            parts.extend((name, f"{shared}/{union}", FOUND if is_candidate(shared, union, threshold) else MISSED))
        lines.append(" ".join(parts))
    return sorted(lines)


def score_corpus(directory: Path, protocol: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """``candidates.json`` and ``timing.json`` for the corpus under ``directory``."""
    corpus = load_json(directory / CORPUS_JSON_NAME)
    labels = load_json(directory / LABELS_NAME)
    pages = corpus_pages(directory, corpus)
    pairs = corpus_pairs(pages, labels, protocol)
    texts = [(page.title, page.paragraph) for page in pages]
    scored: dict[str, list[tuple[int, int]]] = {}
    seconds: dict[str, float] = {}
    for candidate in candidates_from_protocol(protocol):
        start = time.perf_counter()
        scored[candidate.name] = score_pairs(candidate, texts)
        seconds[candidate.name] = round(time.perf_counter() - start, SECONDS_DIGITS)

    true_labels = list(protocol["labels"]["true"])
    scopes = list(protocol["pairs"]["scope_order"])
    true_list = [pair for pair in pairs if pair.label in true_labels]
    results = {
        name: candidate_view(pairs, scores, protocol, len(pages), len(true_list)) for name, scores in scored.items()
    }
    verdict, winner = select(protocol, results)
    candidates_document = {
        "study": STUDY,
        "inputs": {
            "corpus_sha256": sha256_of(directory / CORPUS_JSON_NAME),
            "labels_sha256": sha256_of(directory / LABELS_NAME),
            "protocol_sha256": sha256_of(directory / PROTOCOL_NAME),
        },
        "pages": len(pages),
        "pairs": {
            "total": len(pairs),
            "by_scope": {scope: sum(pair.scope == scope for pair in pairs) for scope in scopes},
        },
        "true_pairs": {
            "total": len(true_list),
            "by_disposition": {label: sum(pair.label == label for pair in true_list) for label in true_labels},
            "by_scope": {scope: sum(pair.scope == scope for pair in true_list) for scope in scopes},
        },
        "candidates": results,
        "true_pair_scores": true_pair_scores(pairs, scored, protocol),
        "verdict": verdict,
        "winner": winner,
        "winner_line": protocol["winner_lines"][winner],
    }
    timing_document = {
        "study": TIMING_STUDY,
        "clock": CLOCK,
        "pages": len(pages),
        "pairs": len(pairs),
        "seconds": seconds,
    }
    return candidates_document, timing_document


def secondary(patterns_dir: Path, protocol: Mapping[str, Any]) -> dict[str, Any]:
    """B0 and B1 on the issue 54 fixture, read as recorded and with the disputed pair read again; counts only."""
    disputed = protocol["issue_54_disputed_pair"]
    fixture = patterns_dir / FIXTURE_NAME
    manifest = load_json(patterns_dir / MANIFEST_NAME)
    labels = load_json(patterns_dir / LABELS_NAME)
    rels = sorted({str(entry["path"]) for entry in (*manifest["pages"], *manifest["background"])})
    texts = {rel: (fixture / rel).read_text(encoding="utf-8") for rel in rels}
    eligible = [rel for rel in rels if superseded_by(texts[rel]) is None]
    pairs = list(combinations(eligible, 2))
    recorded = {pair_key(*row["pair"]): str(row["disposition"]) for row in labels["background_pairs"]}
    recorded.update({pair_key(*row["pair"]): str(row["disposition"]) for row in labels["pattern_pairs"]})
    second_reading = str(disputed["second_reading"])
    second = {**recorded, pair_key(*disputed["pair"]): second_reading}
    threshold = threshold_of(protocol)
    page_texts = [(_title(texts[rel]), _first_paragraph(texts[rel])) for rel in eligible]
    hits = {
        candidate.name: [is_candidate(shared, union, threshold) for shared, union in score_pairs(candidate, page_texts)]
        for candidate in candidates_from_protocol(protocol)
    }
    readings: dict[str, Any] = {}
    for reading, stated in ((RECORDED_READING, recorded), (f"{SECOND_READING_PREFIX} {second_reading}", second)):
        truth = [stated.get(pair) in TRUE_DISPOSITIONS for pair in pairs]
        view: dict[str, Any] = {"true_pairs": sum(truth)}
        for name, flags in hits.items():
            found = sum(flag and real for flag, real in zip(flags, truth, strict=True))
            false = sum(flag and not real for flag, real in zip(flags, truth, strict=True))
            view[name] = {"found": found, "false_candidates": false}
        readings[reading] = view
    return {
        "study": SECONDARY_STUDY,
        "binding": False,
        "inputs": {
            "labels_sha256": sha256_of(patterns_dir / LABELS_NAME),
            "manifest_sha256": sha256_of(patterns_dir / MANIFEST_NAME),
        },
        "true_dispositions": sorted(TRUE_DISPOSITIONS),
        "pages": len(rels),
        "eligible_pages": len(eligible),
        "pairs": len(pairs),
        "disputed_pair": [str(rel) for rel in disputed["pair"]],
        "readings": readings,
    }


def render(document: Mapping[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m eval.duplicates.candidates",
        description="Score the issue 121 candidates B0 and B1 over every pair of the frozen corpus (no git, no model).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        metavar="DIR",
        help=(
            f"Write {CANDIDATES_NAME}, {SECONDARY_NAME} and {TIMING_NAME} to DIR (created; "
            f"default: {RESULTS_DIR_NAME}/ beside the protocol)."
        ),
    )
    return parser


def main(
    argv: Sequence[str] | None = None, *, duplicates_dir: Path | None = None, patterns_dir: Path | None = None
) -> int:
    """Score and write the three files; 1, writing nothing, when the inputs are not the frozen inputs."""
    parser = _build_arg_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    directory = DUPLICATES_DIR if duplicates_dir is None else duplicates_dir
    fixture_dir = PATTERNS_DIR if patterns_dir is None else patterns_dir
    try:
        protocol = load_json(directory / PROTOCOL_NAME)
        problems = check_frozen(directory, protocol)
        if problems:
            sys.stderr.write("".join(f"{problem}\n" for problem in problems))
            sys.stderr.write("the inputs are not the frozen inputs, so nothing was computed and nothing was written\n")
            return REFUSED
        candidates_document, timing_document = score_corpus(directory, protocol)
        secondary_document = secondary(fixture_dir, protocol)
    except (OSError, ValueError, KeyError) as exc:
        sys.stderr.write(f"{exc!r}; nothing was written\n")
        return REFUSED
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / CANDIDATES_NAME).write_bytes(render(candidates_document))
    (out_dir / SECONDARY_NAME).write_bytes(render(secondary_document))
    (out_dir / TIMING_NAME).write_bytes(render(timing_document))
    sys.stdout.write(f"{candidates_document['verdict']}; {candidates_document['winner_line']}; written to {out_dir}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
