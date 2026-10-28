# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Discovery evidence, run 3 and the held-out set (specs/wiki-studio-0-8-0, US3, FR-019..FR-030).

Runs ``wiki_studio.api.find`` with both rankers (``fts5`` and ``index-first``)
over a frozen fixture and reports, per question and per ranker, the pages
selected, hit at 1 and at 5, whether a distractor outranks gold, the bytes and
words loaded and the pages omitted or ineligible, beside the grep negative
control of run 1. Every hit rate carries the eligible page count and the
random baseline. No backend is invoked.

    python -m eval.navigation.discovery run --fixture eval/navigation/run2 --shared eval/navigation \\
        --config eval/navigation/run3/ranker-config-untuned.json        # prints the JSON results-untuned.json holds
    python -m eval.navigation.discovery tune                             # only after the held-out freeze
    python -m eval.navigation.discovery run --fixture eval/navigation/heldout --shared eval/navigation  # once
    python -m eval.navigation.discovery decide                           # FR-029's rule and its basis

The search cache always lives in a temporary directory (or ``--search-cache``,
never inside the fixture), so no evaluation writes into a frozen directory.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import platform
import re
import sqlite3
import statistics
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from eval.navigation.heldout_protocol import (
    HELDOUT_DIR,
    MANIFEST_NAME,
    RUN_ATTEMPT_NAME,
    SET_HELDOUT,
    STATE_FROZEN,
    STATE_RUN,
    STATE_RUN_STARTED,
    ProtocolError,
    advance,
    load_manifest,
    read_eligible_pages,
    save_manifest,
    verify_frozen,
)
from eval.navigation.run import (
    DECIMALS,
    FIXTURE_DIR,
    INDEX_NAME,
    KIND_ABSENT,
    KIND_COMPETING,
    UNIT,
    _ratio,
    _shared_file,
    count_words,
    grep_words,
    load_stopwords,
    question_words,
)
from eval.navigation.run2_protocol import _git, _now
from wiki_studio import __version__, api
from wiki_studio import discovery as wiki_discovery
from wiki_studio.discovery import (
    DEFAULT_MAX_CONTEXT_BYTES,
    RANKER_FTS5,
    RANKER_INDEX_FIRST,
    RANKERS,
    RankerConfig,
    fts5_available,
    ranker_config_hash,
)
from wiki_studio.paths import WikiPaths
from wiki_studio.querier import DEFAULT_MAX_QUERY_PAGES
from wiki_studio.search_index import build_document, build_in_memory

SHARED_DIR = FIXTURE_DIR  # eval/navigation: run 1's corpus, questions and stop list
REPO_ROOT = SHARED_DIR.parents[1]
DEV_FIXTURE = SHARED_DIR / "run2"  # the development set: run 2's frozen wiki, read in place (FR-021)
RUN3_DIR = SHARED_DIR / "run3"
UNTUNED_CONFIG_NAME = "ranker-config-untuned.json"
UNTUNED_RESULTS_NAME = "results-untuned.json"
TUNED_CONFIG_NAME = "ranker-config.json"
TUNING_NAME = "tuning.json"
RESULTS_NAME = "results.json"
POST_HOC_PREFIX = "results-post-hoc-"
CACHE_FILE_NAME = "search-cache.sqlite"
WIKI_DIR = "wiki"
PROPOSALS_DIR = "proposals"

# Not compared when a results file is reproduced (FR-020): where and when it ran, not what it measured.
LATENCY_KEY = "latency"
ATTEMPT_KEY = "run_attempt"  # the one held-out attempt (its marker's record), in results.json and the manifest
ENVIRONMENT_PARAMETERS: tuple[str, ...] = ("sqlite_version", "wiki_studio_version")

LATENCY_REPETITIONS = 5
P95 = 0.95
MILLISECONDS = 1000.0

# The closed tuning grid (FR-021): 2 tokenizers x 3^3 weights x 2 minimum matches = 108 configurations.
GRID_TOKENIZERS: tuple[str, ...] = ("porter unicode61", "unicode61")
GRID_WEIGHTS: tuple[float, ...] = (1.0, 2.0, 4.0)
GRID_BODY_WEIGHT = 1.0
GRID_MIN_MATCH: tuple[int, ...] = (1, 2)
WEIGHT_COUNT = 4  # bm25 weights: path, title, headings, body

# The default decision's floors (FR-029: D8b, D8c).
MIN_GOLD_QUESTIONS = 15
MIN_ELIGIBLE_PAGES = 10

if TYPE_CHECKING:
    from collections.abc import Callable

POST_HOC_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class RunnerError(Exception):
    """A refused step (out of order, a stale or missing record, a path inside a frozen directory)."""


# ── Ranker configuration files ────────────────────────────────


def config_document(config: RankerConfig) -> dict[str, Any]:
    """A configuration as ``run3/ranker-config*.json`` holds it, with its hash (FR-006)."""
    return {
        "ranker": RANKER_FTS5,
        "tokenizer": config.tokenizer,
        "weights": [float(w) for w in config.weights],
        "min_match_tokens": config.min_match_tokens,
        "max_pages": config.max_pages,
        "ranker_config_hash": ranker_config_hash(config),
    }


def config_from_document(document: dict[str, Any]) -> RankerConfig:
    """The configuration a document describes; refuses one whose recorded hash does not match."""
    weights = tuple(float(w) for w in document["weights"])
    if len(weights) != WEIGHT_COUNT:
        raise RunnerError(f"a ranker configuration has {WEIGHT_COUNT} weights, got {len(weights)}")
    config = RankerConfig(
        tokenizer=str(document["tokenizer"]),
        weights=(weights[0], weights[1], weights[2], weights[3]),
        min_match_tokens=int(document["min_match_tokens"]),
        max_pages=int(document["max_pages"]),
    )
    recorded = document.get("ranker_config_hash")
    if recorded is not None and recorded != ranker_config_hash(config):
        raise RunnerError(f"the recorded ranker_config_hash {recorded} does not match the configuration")
    return config


def load_config(path: Path) -> RankerConfig:
    if not path.is_file():
        raise RunnerError(f"{path} not found")
    return config_from_document(json.loads(path.read_text(encoding="utf-8")))


def _write_json(path: Path, document: Any) -> None:
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# ── One evaluation ────────────────────────────────────────────


@dataclass(frozen=True)
class _Inputs:
    questions: list[dict[str, Any]]
    gold_by_id: dict[str, dict[str, Any]]
    stopwords: frozenset[str]
    corpus_dir: Path
    paths: WikiPaths
    eligible: int


def _inside(path: Path, directory: Path) -> bool:
    return path.resolve().is_relative_to(directory.resolve())


def _load_inputs(fixture_dir: Path, shared_dir: Path | None, search_cache: Path) -> _Inputs:
    if _inside(search_cache, fixture_dir) or (shared_dir is not None and _inside(search_cache, shared_dir)):
        raise RunnerError(f"the search cache {search_cache} is inside a frozen evaluation directory (FR-019)")
    questions: list[dict[str, Any]] = json.loads(
        _shared_file(fixture_dir, shared_dir, "questions.json").read_text(encoding="utf-8")
    )
    gold_by_id = {g["id"]: g for g in json.loads((fixture_dir / "gold.json").read_text(encoding="utf-8"))}
    missing = [q["id"] for q in questions if q["id"] not in gold_by_id]
    if missing:
        raise ValueError(f"gold.json has no entry for question(s): {', '.join(missing)}")
    wiki_dir = fixture_dir / WIKI_DIR
    paths = WikiPaths.for_root(
        fixture_dir, wiki_dir=wiki_dir, proposals_dir=fixture_dir / PROPOSALS_DIR, search_cache=search_cache
    )
    if is_heldout(fixture_dir):
        # The held-out set's corpus is an evaluation input of its own (D8a): it is
        # never borrowed from the shared development corpus.
        corpus_dir = fixture_dir / "corpus"
        if not corpus_dir.is_dir() or not any(p.is_file() for p in corpus_dir.iterdir()):
            raise RunnerError(f"the held-out corpus {corpus_dir} is missing or empty; the run never falls back")
    else:
        corpus_dir = _shared_file(fixture_dir, shared_dir, "corpus")
    return _Inputs(
        questions=questions,
        gold_by_id=gold_by_id,
        stopwords=load_stopwords(_shared_file(fixture_dir, shared_dir, "stopwords.txt")),
        corpus_dir=corpus_dir,
        paths=paths,
        eligible=len(read_eligible_pages(wiki_dir)),
    )


def _excluded_reason(kind: str, gold: str | None) -> str | None:
    """As run.py: ``absent``, ``no_gold`` or ``answered_by_index`` carry no hit numbers."""
    if kind == KIND_ABSENT:
        return KIND_ABSENT
    if gold is None:
        return "no_gold"
    if gold == INDEX_NAME:
        return "answered_by_index"
    return None


def _outranked(selected: list[str], gold: str, distractors: list[str]) -> bool:
    """run.py's rule: a distractor ranked above gold (gold outside the selection ranks below every page)."""
    gold_pos = selected.index(gold) if gold in selected else len(selected)
    return any(d in selected and selected.index(d) < gold_pos for d in distractors)


def _ranker_entry(
    paths: WikiPaths, question: dict[str, Any], meta: dict[str, Any], ranker: str, config: RankerConfig
) -> dict[str, Any]:
    result = api.find(
        question["question"],
        paths,
        max_pages=config.max_pages,
        max_bytes=DEFAULT_MAX_CONTEXT_BYTES,
        ranker=ranker,
        ranker_config=config,
    )
    selected = [page.path for page in result.pages]
    words = count_words(result.index.read_text(encoding="utf-8")) + sum(
        count_words(page.file.read_text(encoding="utf-8")) for page in result.pages
    )
    evaluated = meta["excluded_reason"] is None
    gold = meta["gold"]
    return {
        "ran_as": result.ranker,
        "fallback_reason": result.fallback_reason,
        "selected": selected,
        "hit_at_1": (bool(selected) and selected[0] == gold) if evaluated else None,
        "hit_at_5": (gold in selected) if evaluated else None,
        "distractor_outranks": _outranked(selected, gold, meta["distractors"])
        if evaluated and meta["kind"] == KIND_COMPETING
        else None,
        "bytes_loaded": result.bytes_loaded,
        "words_loaded": words,
        "omitted": [{"path": o.path, "bytes": o.bytes} for o in result.omitted],
        "ineligible": [{"path": i.path, "reason": i.reason} for i in result.ineligible],
        "warnings": list(result.warnings),
    }


def _mean(values: list[float]) -> float | None:
    return round(statistics.fmean(values), DECIMALS) if values else None


def _median(values: list[int]) -> float | None:
    return round(float(statistics.median(values)), DECIMALS) if values else None


def _navigation(per_question: list[dict[str, Any]], ranker: str, eligible: int) -> dict[str, Any]:
    evaluated = [e for e in per_question if e["excluded_reason"] is None]
    entries = [e[ranker] for e in evaluated]
    competing = [e[ranker] for e in evaluated if e["kind"] == KIND_COMPETING]
    return {
        "ran_as": sorted({e[ranker]["ran_as"] for e in per_question}),
        "evaluated": len(evaluated),
        "hits_at_1": sum(bool(r["hit_at_1"]) for r in entries),
        "hits_at_5": sum(bool(r["hit_at_5"]) for r in entries),
        "hit_at_1": _ratio(sum(bool(r["hit_at_1"]) for r in entries), len(entries)),
        "hit_at_5": _ratio(sum(bool(r["hit_at_5"]) for r in entries), len(entries)),
        # Beside every hit rate: the pages a ranker could pick from, and the derived random baseline
        # (run.py's rule over the eligible pages: the same number of pages drawn at random).
        "eligible_pages": eligible,
        "random_hit_at_1": _mean([(1 / eligible if r["selected"] else 0.0) for r in entries]) if eligible else None,
        "random_hit_at_5": _mean([min(len(r["selected"]), eligible) / eligible for r in entries]) if eligible else None,
        "competing_evaluated": len(competing),
        "distractor_outranks": _ratio(sum(bool(r["distractor_outranks"]) for r in competing), len(competing)),
        "empty_selection": [e["id"] for e in evaluated if not e[ranker]["selected"]],
        "mean_pages_selected": _mean([len(r["selected"]) for r in entries]),
    }


def _absent(per_question: list[dict[str, Any]], ranker: str) -> dict[str, Any]:
    entries = [e[ranker] for e in per_question if e["kind"] == KIND_ABSENT]
    return {
        "evaluated": len(entries),
        "absent_empty": _ratio(sum(not r["selected"] for r in entries), len(entries)),
        "absent_pages_loaded": _mean([len(r["selected"]) for r in entries]),
        "absent_bytes_loaded": _mean([r["bytes_loaded"] for r in entries]),
    }


def _context(per_question: list[dict[str, Any]], ranker: str) -> dict[str, Any]:
    entries = [e[ranker] for e in per_question]
    return {
        "questions": len(entries),
        "bytes_total": sum(r["bytes_loaded"] for r in entries),
        "bytes_median": _median([r["bytes_loaded"] for r in entries]),
        "words_total": sum(r["words_loaded"] for r in entries),
        "words_median": _median([r["words_loaded"] for r in entries]),
    }


def _discordant(per_question: list[dict[str, Any]]) -> dict[str, Any]:
    """Questions where the rankers disagree, at 1 and at 5 (the discordant pairs of a paired comparison)."""
    evaluated = [e for e in per_question if e["excluded_reason"] is None]

    def split(key: str) -> dict[str, list[str]]:
        return {
            "fts5_only": [e["id"] for e in evaluated if e[RANKER_FTS5][key] and not e[RANKER_INDEX_FIRST][key]],
            "index_first_only": [e["id"] for e in evaluated if e[RANKER_INDEX_FIRST][key] and not e[RANKER_FTS5][key]],
        }

    return {"at_1": split("hit_at_1"), "at_5": split("hit_at_5")}


def is_heldout(fixture_dir: Path) -> bool:
    """The held-out set: its manifest says so, or it is ``heldout/`` itself."""
    manifest = fixture_dir / MANIFEST_NAME
    if manifest.is_file() and json.loads(manifest.read_text(encoding="utf-8")).get("set") == SET_HELDOUT:
        return True
    return fixture_dir.resolve() == HELDOUT_DIR.resolve()


def _ingest_coverage(fixture_dir: Path, answer_in_a_page: int, answerable: int) -> dict[str, Any]:
    """Measured for the held-out wiki; inherited from the fixture's own results for the development wiki (FR-020)."""
    if is_heldout(fixture_dir):
        summary = (load_manifest(fixture_dir).get("ingest") or {}).get("summary") or {}
        return {
            "basis": "measured",
            "documents_ingested": summary.get("documents_ingested"),
            "documents_promoted": summary.get("promoted"),
            "answer_in_a_page": answer_in_a_page,
            "answerable": answerable,
            "rate": _ratio(answer_in_a_page, answerable),
        }
    own = fixture_dir / RESULTS_NAME
    if not own.is_file():
        raise RunnerError(f"{_label(own)} not found; the development wiki's ingest coverage is inherited from it")
    counts = json.loads(own.read_text(encoding="utf-8"))["counts"]
    answer_in_a_page, answerable = counts["with_gold"], counts["questions"] - counts["absent"]
    return {
        "basis": "inherited, not re-measured",
        "source": _label(own),
        "answer_in_a_page": answer_in_a_page,
        "answerable": answerable,
        "rate": _ratio(answer_in_a_page, answerable),
    }


def _label(path: Path) -> str:
    resolved = path.resolve()
    return resolved.relative_to(REPO_ROOT).as_posix() if resolved.is_relative_to(REPO_ROOT) else path.name


def parameters(config: RankerConfig) -> dict[str, Any]:
    document = config_document(config)
    return {
        "ranker_config": {k: v for k, v in document.items() if k != "ranker_config_hash"},
        "ranker_config_hash": document["ranker_config_hash"],
        "max_pages": config.max_pages,
        "max_bytes": DEFAULT_MAX_CONTEXT_BYTES,
        "tokenizer": config.tokenizer,
        "weights": document["weights"],
        "min_match_tokens": config.min_match_tokens,
        "sqlite_version": sqlite3.sqlite_version,
        "wiki_studio_version": __version__,
    }


def _evaluate(inputs: _Inputs, config: RankerConfig, rankers: tuple[str, ...]) -> list[dict[str, Any]]:
    per_question: list[dict[str, Any]] = []
    for q in inputs.questions:
        gold_entry = inputs.gold_by_id[q["id"]]
        gold = gold_entry.get("gold")
        meta: dict[str, Any] = {
            "id": q["id"],
            "kind": q["kind"],
            "gold": gold,
            "distractors": list(gold_entry.get("distractors") or []),
            "excluded_reason": _excluded_reason(q["kind"], gold),
        }
        has_gold = q["kind"] != KIND_ABSENT and gold is not None
        meta["grep_words"] = (
            grep_words(question_words(q["question"], inputs.stopwords), inputs.corpus_dir) if has_gold else None
        )
        for ranker in rankers:
            meta[ranker] = _ranker_entry(inputs.paths, q, meta, ranker, config)
        per_question.append(meta)
    return per_question


def compute(
    fixture_dir: Path,
    shared_dir: Path | None = None,
    *,
    config: RankerConfig,
    search_cache: Path,
    latency: bool = True,
    inputs: _Inputs | None = None,
) -> dict[str, Any]:
    """The evaluation of both rankers over ``fixture_dir`` under ``config``, the cache at ``search_cache``.

    ``inputs`` are loaded here unless the caller loaded them already (the
    held-out run checks every input before it records its one attempt).
    """
    if inputs is None:
        inputs = _load_inputs(fixture_dir, shared_dir, search_cache)
    per_question = _evaluate(inputs, config, RANKERS)
    non_absent = [e for e in per_question if e["kind"] != KIND_ABSENT]
    with_gold = [e for e in non_absent if e["gold"] is not None]
    return {
        "unit": UNIT,
        "fixture": _label(fixture_dir),
        "parameters": parameters(config),
        "counts": {
            "questions": len(per_question),
            "single": sum(e["kind"] == "single" for e in per_question),
            "competing": sum(e["kind"] == KIND_COMPETING for e in per_question),
            "absent": sum(e["kind"] == KIND_ABSENT for e in per_question),
            "with_gold": len(with_gold),
            "evaluated": sum(e["excluded_reason"] is None for e in per_question),
        },
        "eligible_pages": inputs.eligible,
        "navigation": {ranker: _navigation(per_question, ranker, inputs.eligible) for ranker in RANKERS},
        "discordant": _discordant(per_question),
        "absent": {ranker: _absent(per_question, ranker) for ranker in RANKERS},
        "context": {ranker: _context(per_question, ranker) for ranker in RANKERS},
        "ingest_coverage": _ingest_coverage(fixture_dir, len(with_gold), len(non_absent)),
        LATENCY_KEY: measure_latency(inputs, config) if latency else None,
        "per_question": per_question,
    }


# ── Latency ───────────────────────────────────────────────────


def _rank_in_memory(wiki_dir: Path, question: str, config: RankerConfig) -> list[str]:
    """``find``'s fts5 ranking with a fresh in-memory index and no cache (the cache's comparison point).

    Ranking only: it does not apply ``find``'s byte budget or load the selected pages.
    """
    pages = read_eligible_pages(wiki_dir)
    documents = [build_document(rel, page.text) for rel, page in pages.items()]
    with build_in_memory(documents, tokenizer=config.tokenizer) as index:
        ranked = index.rank(
            question, order=list(pages), weights=config.weights, min_match_tokens=config.min_match_tokens
        )
    return ranked[: config.max_pages]


def _timed_ms(action: Callable[[], object]) -> float:
    start = time.perf_counter()
    action()
    return (time.perf_counter() - start) * MILLISECONDS


def _stats(samples: list[float]) -> dict[str, float]:
    """Median and nearest-rank p95, in milliseconds."""
    ordered = sorted(samples)
    p95 = ordered[max(0, math.ceil(P95 * len(ordered)) - 1)]
    return {"median_ms": round(statistics.median(ordered), 3), "p95_ms": round(p95, 3)}


def measure_latency(inputs: _Inputs, config: RankerConfig) -> dict[str, Any]:
    """Cold and warm ``find`` through the on-disk cache, and a fresh in-memory index (FR-018, FR-020).

    Each repetition times, for every question, a ``find`` against a cache
    file that does not exist yet (cold), the same call again (warm), and the
    in-memory selection. The cache files live in a temporary directory removed
    afterwards. Machine-dependent: never compared on reproduction.
    """
    with tempfile.TemporaryDirectory() as tmp:
        return _measure_latency(inputs, config, Path(tmp))


def _measure_latency(inputs: _Inputs, config: RankerConfig, cache_dir: Path) -> dict[str, Any]:
    environment = {
        "machine": platform.platform(),
        "processor": platform.machine(),
        "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version,
    }
    if not fts5_available().available:
        return {"fts5": False, **environment}
    cold: list[float] = []
    warm: list[float] = []
    in_memory: list[float] = []
    root = inputs.paths.root
    for repetition in range(LATENCY_REPETITIONS):
        for number, q in enumerate(inputs.questions):
            cache = cache_dir / f"latency-{repetition}-{number}.sqlite"
            for previous in cache_dir.iterdir():  # one cold cache on disk at a time
                previous.unlink()
            paths = WikiPaths.for_root(
                root, wiki_dir=inputs.paths.wiki_dir, proposals_dir=inputs.paths.proposals_dir, search_cache=cache
            )

            text: str = q["question"]

            def cached(p: WikiPaths = paths, question: str = text) -> None:
                api.find(question, p, max_pages=config.max_pages, ranker=RANKER_FTS5, ranker_config=config)

            def fresh(question: str = text) -> None:
                _rank_in_memory(inputs.paths.wiki_dir, question, config)

            cold.append(_timed_ms(cached))
            warm.append(_timed_ms(cached))
            in_memory.append(_timed_ms(fresh))
    return {
        "fts5": True,
        "repetitions": LATENCY_REPETITIONS,
        "samples_per_path": len(cold),
        "unit": "milliseconds per call",
        "cold_cache": _stats(cold),
        "warm_cache": _stats(warm),
        "in_memory_no_cache": _stats(in_memory),
        **environment,
    }


# ── Reproduction ──────────────────────────────────────────────


def comparable(results: dict[str, Any]) -> dict[str, Any]:
    """A results document without ``latency`` and the environment parameters (FR-020)."""
    document = {k: v for k, v in results.items() if k not in (LATENCY_KEY, ATTEMPT_KEY)}
    document["parameters"] = {k: v for k, v in results["parameters"].items() if k not in ENVIRONMENT_PARAMETERS}
    return document


def reproduce(results_file: Path, fixture_dir: Path, shared_dir: Path | None = None) -> bool:
    """Recompute ``results_file`` under its own ``parameters.ranker_config``; True when it matches.

    The cache lives in a temporary directory removed afterwards, so nothing
    is written beside the frozen fixture; this is not a run in FR-028's sense.
    """
    committed = json.loads(results_file.read_text(encoding="utf-8"))
    document = dict(committed["parameters"]["ranker_config"])
    document["ranker_config_hash"] = committed["parameters"]["ranker_config_hash"]
    config = config_from_document(document)
    with tempfile.TemporaryDirectory() as tmp:
        fresh = compute(fixture_dir, shared_dir, config=config, search_cache=Path(tmp) / CACHE_FILE_NAME, latency=False)
    return comparable(fresh) == comparable(committed)


# ── tune ──────────────────────────────────────────────────────


def grid() -> list[RankerConfig]:
    """The closed grid of FR-021, in its fixed enumeration order."""
    return [
        RankerConfig(
            tokenizer=tokenizer,
            weights=(w_path, w_title, w_headings, GRID_BODY_WEIGHT),
            min_match_tokens=min_match,
            max_pages=DEFAULT_MAX_QUERY_PAGES,
        )
        for tokenizer in GRID_TOKENIZERS
        for w_path, w_title, w_headings in itertools.product(GRID_WEIGHTS, repeat=3)
        for min_match in GRID_MIN_MATCH
    ]


def _require_frozen(heldout_dir: Path, step: str) -> dict[str, Any]:
    """The held-out set is frozen (and unchanged since), or ``step`` refuses (FR-021, FR-028)."""
    try:
        manifest = load_manifest(heldout_dir)
    except ProtocolError as exc:
        raise RunnerError(f"{step}: {exc}") from exc
    if manifest.get("state") != STATE_FROZEN:
        raise RunnerError(
            f"{step}: refusing; the held-out set is not frozen (state {manifest.get('state')!r}, expected "
            f"{STATE_FROZEN!r}); follow eval/navigation/heldout/protocol.md first"
        )
    try:
        verify_frozen(heldout_dir, manifest)
    except ProtocolError as exc:
        raise RunnerError(f"{step}: {exc}") from exc
    return manifest


def tune(
    *,
    run3_dir: Path = RUN3_DIR,
    heldout_dir: Path = HELDOUT_DIR,
    dev_fixture: Path = DEV_FIXTURE,
    shared_dir: Path = SHARED_DIR,
    configurations: list[RankerConfig] | None = None,
) -> RankerConfig:
    """Evaluate the grid on the development set only and record the chosen configuration (FR-021)."""
    _require_frozen(heldout_dir, "tune")
    untuned_config_file = run3_dir / UNTUNED_CONFIG_NAME
    untuned_results = run3_dir / UNTUNED_RESULTS_NAME
    if not untuned_config_file.is_file() or not untuned_results.is_file():
        raise RunnerError(f"tune: refusing; {UNTUNED_CONFIG_NAME} and {UNTUNED_RESULTS_NAME} must be committed first")
    untuned = load_config(untuned_config_file)
    committed_untuned = json.loads(untuned_results.read_text(encoding="utf-8"))
    if committed_untuned["parameters"]["ranker_config_hash"] != ranker_config_hash(untuned):
        raise RunnerError(f"tune: refusing; {UNTUNED_RESULTS_NAME} was not produced under {UNTUNED_CONFIG_NAME}")
    if not reproduce(untuned_results, dev_fixture, shared_dir):
        raise RunnerError(f"tune: refusing; {UNTUNED_RESULTS_NAME} does not reproduce under {UNTUNED_CONFIG_NAME}")
    if (run3_dir / TUNED_CONFIG_NAME).exists():
        raise RunnerError(f"tune: refusing; {TUNED_CONFIG_NAME} exists; the tuned configuration is frozen")
    if not fts5_available().available:
        raise RunnerError(f"tune: FTS5 is not available in this Python's SQLite ({fts5_available().reason})")

    candidates = grid() if configurations is None else configurations
    if untuned not in candidates:
        raise RunnerError(f"tune: the candidates must include {UNTUNED_CONFIG_NAME}'s configuration (the tie-break)")
    records: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp:
        for number, config in enumerate(candidates):
            inputs = _load_inputs(dev_fixture, shared_dir, Path(tmp) / f"tune-{number}.sqlite")
            per_question = _evaluate(inputs, config, (RANKER_FTS5,))
            navigation = _navigation(per_question, RANKER_FTS5, inputs.eligible)
            records.append(
                {
                    "ranker_config": config_document(config),
                    "ranker_config_hash": ranker_config_hash(config),
                    "hit_at_1": navigation["hit_at_1"],
                    "hit_at_5": navigation["hit_at_5"],
                    "absent": _absent(per_question, RANKER_FTS5),
                }
            )
    untuned_hash = ranker_config_hash(untuned)

    def order(item: tuple[int, dict[str, Any]]) -> tuple[float, float, float, int]:
        position, record = item
        tie = -1 if record["ranker_config_hash"] == untuned_hash else position
        return (
            -(record["hit_at_1"] or 0.0),
            -(record["hit_at_5"] or 0.0),
            record["absent"]["absent_pages_loaded"] or 0.0,
            tie,
        )

    _position, chosen = min(enumerate(records), key=order)
    chosen_config = config_from_document(chosen["ranker_config"])
    _write_json(
        run3_dir / TUNING_NAME,
        {
            "development_set": _label(dev_fixture),
            "grid": {
                "tokenizer": list(GRID_TOKENIZERS),
                "w_path": list(GRID_WEIGHTS),
                "w_title": list(GRID_WEIGHTS),
                "w_headings": list(GRID_WEIGHTS),
                "w_body": GRID_BODY_WEIGHT,
                "min_match_tokens": list(GRID_MIN_MATCH),
            },
            "selection_rule": "highest hit at 1, then highest hit at 5, then fewer pages loaded for absent "
            "questions, then the untuned configuration, then grid order",
            "untuned_ranker_config_hash": untuned_hash,
            "configurations": records,
            "chosen": chosen,
        },
    )
    _write_json(run3_dir / TUNED_CONFIG_NAME, config_document(chosen_config))
    return chosen_config


# ── decide ────────────────────────────────────────────────────


@dataclass(frozen=True)
class Decision:
    """FR-029's outcome: the default ranker and the basis the CHANGELOG states."""

    default_ranker: str
    basis: str


RULE = (
    f"fts5 becomes the default only if, on the held-out set, its hit at 1 and its hit at 5 are each no lower "
    f"than index-first's, at least {MIN_GOLD_QUESTIONS} held-out questions have a gold page (D8b) and the "
    f"frozen held-out wiki has at least {MIN_ELIGIBLE_PAGES} eligible pages (D8c)"
)


def decide(results: dict[str, Any], manifest: dict[str, Any]) -> Decision:
    """Apply FR-029 to the one held-out result and the frozen manifest's floors."""
    fts5 = results["navigation"][RANKER_FTS5]
    index_first = results["navigation"][RANKER_INDEX_FIRST]
    gold_questions = int(manifest["gold_questions"])
    eligible = int(manifest["eligible_pages"])
    numbers = (
        f"fts5 hit at 1 {fts5['hit_at_1']} vs index-first {index_first['hit_at_1']}, hit at 5 {fts5['hit_at_5']} "
        f"vs {index_first['hit_at_5']}; {gold_questions} gold questions, {eligible} eligible pages"
    )
    floors = []
    if gold_questions < MIN_GOLD_QUESTIONS:
        floors.append(f"fewer than {MIN_GOLD_QUESTIONS} gold questions ({gold_questions}, D8b)")
    if eligible < MIN_ELIGIBLE_PAGES:
        floors.append(f"fewer than {MIN_ELIGIBLE_PAGES} eligible pages ({eligible}, D8c)")
    if floors:
        return Decision(
            RANKER_INDEX_FIRST,
            f"fts5 stays opt-in for want of evidence, not from a measured loss: {'; '.join(floors)} ({numbers})",
        )
    if fts5["ran_as"] != [RANKER_FTS5]:
        per_question = results.get("per_question") or []
        fallbacks = sum(e[RANKER_FTS5]["ran_as"] != RANKER_FTS5 for e in per_question)
        count = f"{fallbacks} of {len(per_question)} questions, " if per_question else ""
        return Decision(
            RANKER_INDEX_FIRST,
            f"fts5 fell back on at least one held-out question ({count}ran as {fts5['ran_as']})",
        )
    if (fts5["hit_at_1"] or 0.0) < (index_first["hit_at_1"] or 0.0):
        return Decision(RANKER_INDEX_FIRST, f"held-out measurement: fts5 is lower at hit at 1 ({numbers})")
    if (fts5["hit_at_5"] or 0.0) < (index_first["hit_at_5"] or 0.0):
        return Decision(RANKER_INDEX_FIRST, f"held-out measurement: fts5 is lower at hit at 5 ({numbers})")
    return Decision(RANKER_FTS5, f"held-out measurement: fts5 is no worse at hit at 1 and at 5 ({numbers})")


# ── run (the held-out guards) ─────────────────────────────────


def heldout_output(
    heldout_dir: Path,
    *,
    config_given: bool,
    post_hoc: str | None,
    live_config: RankerConfig,
    run3_dir: Path = RUN3_DIR,
) -> Path:
    """Where the held-out run under ``live_config`` may write, or a refusal (FR-028)."""
    if config_given:
        raise RunnerError("run: --config is refused for the held-out set; the one run uses the frozen configuration")
    manifest = load_manifest(heldout_dir)
    state = manifest.get("state")
    tuned = run3_dir / TUNED_CONFIG_NAME
    if state not in (STATE_FROZEN, STATE_RUN_STARTED, STATE_RUN):
        raise RunnerError(f"run: refusing; the held-out set is not frozen (state {state!r}, expected {STATE_FROZEN!r})")
    if not tuned.is_file():
        raise RunnerError(f"run: refusing; {_label(tuned)} does not exist (tune first, FR-021)")
    tuned_hash = ranker_config_hash(load_config(tuned))
    if tuned_hash != ranker_config_hash(live_config):
        raise RunnerError(
            f"run: refusing; {TUNED_CONFIG_NAME}'s hash differs from the live ranker_config_hash(); "
            "set DEFAULT_RANKER_CONFIG to the tuned configuration first"
        )
    try:
        verify_frozen(heldout_dir, manifest)
    except ProtocolError as exc:
        raise RunnerError(f"run: {exc}") from exc
    original = heldout_dir / RESULTS_NAME
    marker = heldout_dir / RUN_ATTEMPT_NAME
    attempt = _attempt_record(heldout_dir, manifest)
    if post_hoc is None:
        if attempt is not None or marker.exists() or original.exists() or state in (STATE_RUN_STARTED, STATE_RUN):
            started = attempt.get("started_at") if attempt else "an unrecorded time"
            raise RunnerError(
                f"run: refusing; the one held-out attempt was started at {started} ({_label(marker)}); "
                "any further run needs --post-hoc LABEL"
            )
        return original
    if not POST_HOC_LABEL_RE.match(post_hoc):
        raise RunnerError(f"run: --post-hoc label {post_hoc!r} must be letters, digits, '.', '_' or '-'")
    if attempt is None or not marker.exists():
        raise RunnerError("run: --post-hoc is for runs after the one held-out run, which has not happened")
    if original.exists():
        recorded_hash = json.loads(original.read_text(encoding="utf-8"))["parameters"]["ranker_config_hash"]
        produced = RESULTS_NAME
    elif _attempt_failed(heldout_dir, manifest, original):
        recorded_hash, produced = attempt.get("ranker_config_hash"), marker.name
    else:
        raise RunnerError(
            f"run: --post-hoc is for runs after the one held-out run; the attempt started at "
            f"{attempt.get('started_at')} has neither written {RESULTS_NAME} nor failed"
        )
    if recorded_hash != tuned_hash:
        raise RunnerError(f"run: refusing; {produced} was not produced under the current {TUNED_CONFIG_NAME}")
    labelled = heldout_dir / f"{POST_HOC_PREFIX}{post_hoc}.json"
    if labelled.exists():
        raise RunnerError(f"run: {labelled.name} exists; choose another label")
    return labelled


def _attempt_record(heldout_dir: Path, manifest: dict[str, Any]) -> dict[str, Any] | None:
    """The one attempt as its marker records it (the manifest's copy when the marker is unreadable), or None."""
    marker = heldout_dir / RUN_ATTEMPT_NAME
    if marker.is_file():
        try:
            record: dict[str, Any] = json.loads(marker.read_text(encoding="utf-8"))
            return record
        except (OSError, ValueError):
            pass
    recorded = manifest.get(ATTEMPT_KEY)
    return dict(recorded) if isinstance(recorded, dict) else None


def _attempt_failed(heldout_dir: Path, manifest: dict[str, Any], original: Path) -> bool:
    """The attempt ended without the original: a failure recorded in the manifest, or a marker with no results.

    The marker is written before the manifest moves to ``run-started``, so a
    crash between the two leaves the marker with the manifest still
    ``frozen``; that is an interrupted attempt too, recoverable only as
    ``--post-hoc``, never as the original.
    """
    recorded = manifest.get(ATTEMPT_KEY) or {}
    marker = heldout_dir / RUN_ATTEMPT_NAME
    return bool(recorded.get("failed_at")) or (marker.exists() and not original.exists())


def _write_attempt_marker(heldout_dir: Path, attempt: dict[str, Any]) -> None:
    """Create ``run-attempt.json`` exclusively: never overwritten, so a second attempt cannot pose as the first."""
    marker = heldout_dir / RUN_ATTEMPT_NAME
    try:
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as exc:
        raise RunnerError(f"run: refusing; {_label(marker)} exists; the one held-out attempt has started") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(attempt, indent=2, sort_keys=True) + "\n")


def _official_attempt(
    heldout_dir: Path, shared_dir: Path | None, *, config: RankerConfig, search_cache: Path
) -> dict[str, Any]:
    """The one held-out run (FR-028): inputs checked, then marker and ``run-started``, then compute, write, ``run``.

    Every input (questions, gold, the frozen wiki, the cache placement) is
    loaded before the marker is written, so an input error is an ordinary
    refusal and never consumes the one attempt. A failure after the marker
    leaves the manifest in ``run-started`` with the failure recorded; the
    attempt is then recoverable only as ``--post-hoc``.
    """
    inputs = _load_inputs(heldout_dir, shared_dir, search_cache)
    attempt = {
        "started_at": _now(),
        "ranker_config_hash": ranker_config_hash(config),
        "wiki_studio_version": __version__,
        "wiki_studio_commit": _git("rev-parse", "HEAD"),
    }
    _write_attempt_marker(heldout_dir, attempt)
    manifest = load_manifest(heldout_dir)
    manifest[ATTEMPT_KEY] = dict(attempt)
    advance(manifest, STATE_RUN_STARTED)
    save_manifest(heldout_dir, manifest)
    try:
        results = compute(heldout_dir, shared_dir, config=config, search_cache=search_cache, inputs=inputs)
        results[ATTEMPT_KEY] = attempt
        _write_json(heldout_dir / RESULTS_NAME, results)
    except BaseException as exc:
        manifest[ATTEMPT_KEY]["failed_at"] = _now()
        manifest[ATTEMPT_KEY]["error"] = f"{type(exc).__name__}: {exc}"
        save_manifest(heldout_dir, manifest)
        raise
    advance(manifest, STATE_RUN)
    save_manifest(heldout_dir, manifest)
    return results


def _live_config() -> RankerConfig:
    """The live default, read at call time so the hash check sees what ``find`` would run."""
    return wiki_discovery.DEFAULT_RANKER_CONFIG


def run(
    fixture_dir: Path,
    shared_dir: Path | None,
    *,
    config_path: Path | None,
    search_cache: Path | None,
    post_hoc: str | None,
    run3_dir: Path = RUN3_DIR,
) -> tuple[dict[str, Any], Path | None]:
    """One evaluation; the held-out set's output path (written here, with its manifest) or None for stdout."""
    output: Path | None = None
    live = _live_config()  # read once: the config the held-out guard checks is the one that runs
    if is_heldout(fixture_dir):
        output = heldout_output(
            fixture_dir, config_given=config_path is not None, post_hoc=post_hoc, live_config=live, run3_dir=run3_dir
        )
    elif post_hoc is not None:
        raise RunnerError("run: --post-hoc applies to the held-out set only")
    config = load_config(config_path) if config_path is not None else live
    with tempfile.TemporaryDirectory() as tmp:
        cache = search_cache if search_cache is not None else Path(tmp) / CACHE_FILE_NAME
        if output is not None and output.name == RESULTS_NAME:
            results = _official_attempt(fixture_dir, shared_dir, config=config, search_cache=cache)
        else:
            results = compute(fixture_dir, shared_dir, config=config, search_cache=cache)
            if output is not None:
                _write_json(output, results)
    return results, output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.navigation.discovery", description=__doc__)
    sub = parser.add_subparsers(dest="step", required=True)
    p_run = sub.add_parser("run", help="Evaluate both rankers over a fixture.")
    p_run.add_argument("--fixture", type=Path, required=True, help="The fixture: gold.json and wiki/.")
    p_run.add_argument("--shared", type=Path, default=None, help="Questions, stop list and corpus if not its own.")
    p_run.add_argument("--config", type=Path, default=None, help="A ranker configuration file (default: live).")
    p_run.add_argument("--search-cache", type=Path, default=None, help="Cache file (default: a temporary one).")
    p_run.add_argument("--post-hoc", default=None, metavar="LABEL", help="A labelled held-out run after the one run.")
    sub.add_parser("tune", help="Tune on the development set (only after the held-out freeze).")
    sub.add_parser("decide", help="Print FR-029's rule, the decision and its basis.")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.step == "run":
            results, output = run(
                args.fixture,
                args.shared,
                config_path=args.config,
                search_cache=args.search_cache,
                post_hoc=args.post_hoc,
                run3_dir=RUN3_DIR,
            )
            if output is None:
                sys.stdout.write(json.dumps(results, indent=2, sort_keys=True) + "\n")
                return 0
            print(f"run: wrote {_label(output)}")
            return 0
        if args.step == "tune":
            chosen = tune(run3_dir=RUN3_DIR, heldout_dir=HELDOUT_DIR, dev_fixture=DEV_FIXTURE, shared_dir=SHARED_DIR)
            print(f"tune: chose {ranker_config_hash(chosen)}; wrote {TUNING_NAME} and {TUNED_CONFIG_NAME}")
            print("tune: next, set DEFAULT_RANKER_CONFIG in src/wiki_studio/discovery.py to it (FR-021)")
            return 0
        results_file = HELDOUT_DIR / RESULTS_NAME
        print(f"rule: {RULE}")
        if not results_file.is_file():
            raise RunnerError("decide: no held-out run yet; the default stays index-first and its basis is pending")
        decision = decide(json.loads(results_file.read_text(encoding="utf-8")), load_manifest(HELDOUT_DIR))
        print(f"default ranker: {decision.default_ranker}")
        print(f"basis: {decision.basis}")
        return 0
    except (RunnerError, ProtocolError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
