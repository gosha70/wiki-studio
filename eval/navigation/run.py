# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Navigation evidence, layer 1 (``specs/wiki-studio-0-3-0``): deterministic numbers over a frozen fixture.

For every preregistered question this runs the querier's model-free page
selection over the frozen wiki and reports ingest coverage, navigation hit
rate at 1 and at ``max_pages``, and the words ``query`` would load against a
written-down grep rule over the raw corpus. No backend is invoked.

    python -m eval.navigation.run            # prints the JSON that results.json holds

Every count is ``count_words``: whitespace-separated words, not model tokens.
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any

from wiki_studio.paths import WikiPaths
from wiki_studio.querier import DEFAULT_MAX_QUERY_PAGES, _extract_index_links, _select_query_candidates
from wiki_studio.wiki_state import _TOKEN_RE

FIXTURE_DIR = Path(__file__).resolve().parent

# Fixed by the spec (FR-005, FR-006).
MAX_PAGES = DEFAULT_MAX_QUERY_PAGES
MIN_WORD_LENGTH = 3
CONTEXT_LINES = 2
INDEX_NAME = "index.md"
KIND_ABSENT = "absent"
KIND_COMPETING = "competing"
DECIMALS = 4
UNIT = "whitespace-separated words (len(text.split())), not model tokens"


def count_words(text: str) -> int:
    """The one unit for every count in this evaluation."""
    return len(text.split())


def load_stopwords(path: Path) -> frozenset[str]:
    """One word per line; ``#`` lines are the provenance header."""
    words = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return frozenset(w for w in words if w and not w.startswith("#"))


def question_words(question: str, stopwords: frozenset[str]) -> list[str]:
    """The grep rule's words: the querier's token pattern minus the stop list and short words, first occurrence kept."""
    found = [w for w in _TOKEN_RE.findall(question.lower()) if w not in stopwords and len(w) >= MIN_WORD_LENGTH]
    return list(dict.fromkeys(found))


def _merge_ranges(hits: list[int], last_line: int) -> list[tuple[int, int]]:
    """Context windows around each matching line, merged where they overlap or touch."""
    merged: list[tuple[int, int]] = []
    for line_no in hits:
        start, end = max(0, line_no - CONTEXT_LINES), min(last_line, line_no + CONTEXT_LINES)
        if merged and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def grep_words(words: list[str], corpus_dir: Path) -> int:
    """Words an agent with grep would read: every line matching any word, whole-word and case-insensitive,
    with ``CONTEXT_LINES`` lines before and after, overlapping windows merged per file, over every corpus file.

    "Whole word" is ``\\b…\\b`` with ``re.escape``, the same word constituents as ``grep -w``
    (letters, digits, underscore); a hyphenated word such as ``page-type`` therefore also
    matches inside ``page-type-export``, exactly as ``grep -w`` would.
    """
    if not words:
        return 0
    patterns = [re.compile(r"\b" + re.escape(w) + r"\b", re.IGNORECASE) for w in words]
    total = 0
    for file in sorted(corpus_dir.rglob("*.md")):
        lines = file.read_text(encoding="utf-8").splitlines()
        hits = [i for i, line in enumerate(lines) if any(p.search(line) for p in patterns)]
        for start, end in _merge_ranges(hits, len(lines) - 1):
            total += count_words("\n".join(lines[start : end + 1]))
    return total


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, DECIMALS) if denominator else None


def _shared_file(fixture_dir: Path, shared_dir: Path | None, name: str) -> Path:
    """A fixture's own copy wins; otherwise the shared one (run 2 uses run 1's corpus, questions and stop list)."""
    own = fixture_dir / name
    present = own.is_file() or (own.is_dir() and any(own.iterdir()))  # an empty directory does not shadow
    if present or shared_dir is None:
        return own
    return shared_dir / name


def compute(fixture_dir: Path = FIXTURE_DIR, shared_dir: Path | None = None) -> dict[str, Any]:
    """The evaluation over ``fixture_dir`` (gold, frozen wiki) with its own or ``shared_dir``'s questions,
    stop list and corpus."""
    questions_path = _shared_file(fixture_dir, shared_dir, "questions.json")
    questions: list[dict[str, Any]] = json.loads(questions_path.read_text(encoding="utf-8"))
    gold_by_id = {g["id"]: g for g in json.loads((fixture_dir / "gold.json").read_text(encoding="utf-8"))}
    missing = [q["id"] for q in questions if q["id"] not in gold_by_id]
    if missing:
        raise ValueError(f"gold.json has no entry for question(s): {', '.join(missing)}")
    stopwords = load_stopwords(_shared_file(fixture_dir, shared_dir, "stopwords.txt"))
    corpus_dir = _shared_file(fixture_dir, shared_dir, "corpus")
    wiki_dir = fixture_dir / "wiki"
    paths = WikiPaths.for_root(fixture_dir, wiki_dir=wiki_dir, proposals_dir=fixture_dir / "proposals")
    index_links = set(_extract_index_links((wiki_dir / INDEX_NAME).read_text(encoding="utf-8")))

    per_question: list[dict[str, Any]] = []
    for q in questions:
        gold_entry = gold_by_id[q["id"]]
        gold = gold_entry.get("gold")
        index_md, selected, contents = _select_query_candidates(paths, q["question"], MAX_PAGES)
        entry: dict[str, Any] = {
            "id": q["id"],
            "kind": q["kind"],
            "gold": gold,
            "distractors": list(gold_entry.get("distractors") or []),
            "selected": list(selected),
            # Why a question carries no hit numbers: "absent" (no answer in the corpus), "no_gold"
            # (ingest wrote no page with the answer), "answered_by_index" (the index is always
            # loaded, FR-004). Word counts (FR-006) are computed for every question with gold,
            # index-only answers included.
            "excluded_reason": (
                KIND_ABSENT
                if q["kind"] == KIND_ABSENT
                else "no_gold"
                if gold is None
                else "answered_by_index"
                if gold == INDEX_NAME
                else None
            ),
            "hit_at_1": None,
            "hit_at_max": None,
            "gold_unreachable": None,
            "wiki_words": None,
            "grep_words": None,
        }
        has_gold = q["kind"] != KIND_ABSENT and gold is not None
        if has_gold:
            entry["wiki_words"] = count_words(index_md) + sum(count_words(contents[p]) for p in selected)
            entry["grep_words"] = grep_words(question_words(q["question"], stopwords), corpus_dir)
        if has_gold and gold != INDEX_NAME:
            entry["hit_at_1"] = bool(selected) and selected[0] == gold
            entry["hit_at_max"] = gold in selected
            entry["gold_unreachable"] = gold not in index_links
        per_question.append(entry)

    non_absent = [e for e in per_question if e["kind"] != KIND_ABSENT]
    with_gold = [e for e in non_absent if e["gold"] is not None]
    answered_by_index = [e["id"] for e in with_gold if e["gold"] == INDEX_NAME]
    evaluated = [e for e in with_gold if e["gold"] != INDEX_NAME]
    absent = [e for e in per_question if e["kind"] == KIND_ABSENT]
    competing = [e for e in evaluated if e["kind"] == KIND_COMPETING]

    def outranked(e: dict[str, Any]) -> bool:
        # FR-005: "any distractor is ranked above gold". A gold page outside the
        # selection ranks below every selected page, so a selected distractor
        # outranks it then too; that case is also visible as a miss at max.
        sel: list[str] = e["selected"]
        gold_pos = sel.index(e["gold"]) if e["gold"] in sel else len(sel)
        return any(d in sel and sel.index(d) < gold_pos for d in e["distractors"])

    # Word metrics are over every question with gold (FR-006); only the hit rates drop index-only answers.
    ratio_set = [e for e in with_gold if e["grep_words"]]
    ratios = [e["wiki_words"] / e["grep_words"] for e in ratio_set]

    return {
        "unit": UNIT,
        "parameters": {"max_pages": MAX_PAGES, "min_word_length": MIN_WORD_LENGTH, "context_lines": CONTEXT_LINES},
        "counts": {
            "questions": len(per_question),
            "single": sum(e["kind"] == "single" for e in per_question),
            "competing": sum(e["kind"] == KIND_COMPETING for e in per_question),
            "absent": len(absent),
            "with_gold": len(with_gold),
        },
        "ingest_coverage": _ratio(len(with_gold), len(non_absent)),
        "navigation": {
            "evaluated": len(evaluated),
            "hit_at_1": _ratio(sum(bool(e["hit_at_1"]) for e in evaluated), len(evaluated)),
            "hit_at_max": _ratio(sum(bool(e["hit_at_max"]) for e in evaluated), len(evaluated)),
            "gold_unreachable": [e["id"] for e in evaluated if e["gold_unreachable"]],
            "answered_by_index": answered_by_index,
            "competing_evaluated": len(competing),
            "distractor_outranks": _ratio(sum(outranked(e) for e in competing), len(competing)),
            "empty_selection": [e["id"] for e in evaluated if not e["selected"]],
            "mean_pages_selected": round(statistics.fmean(len(e["selected"]) for e in evaluated), DECIMALS)
            if evaluated
            else None,
            "index_linked_pages": len(index_links),
            # Derived baseline, not a measurement: the same number of pages per question drawn
            # at random from the index-linked pages. At 1: 1/N when anything was selected.
            "random_hit_at_1": round(
                statistics.fmean((1 / len(index_links) if e["selected"] else 0.0) for e in evaluated), DECIMALS
            )
            if evaluated and index_links
            else None,
            "random_hit_at_max": round(
                statistics.fmean(len(e["selected"]) / len(index_links) for e in evaluated), DECIMALS
            )
            if evaluated and index_links
            else None,
        },
        "absent": {
            "evaluated": len(absent),
            "absent_empty": _ratio(sum(not e["selected"] for e in absent), len(absent)),
            "absent_pages_loaded": round(statistics.fmean(len(e["selected"]) for e in absent), DECIMALS)
            if absent
            else None,
        },
        "words": {
            "evaluated": len(ratio_set),
            "grep_empty": [e["id"] for e in with_gold if not e["grep_words"]],
            "wiki_words_total": sum(e["wiki_words"] for e in ratio_set),
            "grep_words_total": sum(e["grep_words"] for e in ratio_set),
            "ratio_median": round(statistics.median(ratios), DECIMALS) if ratios else None,
            "ratio_mean": round(statistics.fmean(ratios), DECIMALS) if ratios else None,
        },
        "per_question": per_question,
    }


def main(argv: list[str] | None = None) -> int:
    """``run.py [fixture-dir] [--shared DIR]``: print the evaluation as JSON."""
    args = list(argv) if argv is not None else []
    positionals: list[str] = []
    shared: Path | None = None
    i = 0
    while i < len(args):
        if args[i] == "--shared" and i + 1 < len(args):
            shared = Path(args[i + 1])
            i += 2
            continue
        positionals.append(args[i])
        i += 1
    if len(positionals) > 1 or any(p.startswith("-") for p in positionals):
        sys.stderr.write("usage: python -m eval.navigation.run [fixture-dir] [--shared DIR]\n")
        return 2
    fixture = Path(positionals[0]) if positionals else FIXTURE_DIR
    sys.stdout.write(json.dumps(compute(fixture, shared_dir=shared), indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
