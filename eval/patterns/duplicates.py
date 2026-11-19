# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Duplicate candidates on the frozen labels (FR-022, FR-023, FR-024).

``python -m eval.patterns.duplicates [--out PATH]`` refuses to run unless ``labels.json`` still
hashes to ``protocol.json``'s ``labels_sha256``, then computes the signals the frozen protocol
fixes over the fixture's eligible pages, read in place:

* (a) ``health_lint._candidate_pairs``' rule — a shared cited ``sources[].path`` or a direct link
  either way — recording which part fired;
* (a-path) the shared-path part on its own, with its own verdict and counts;
* (b) the Jaccard similarity of ``wiki_state._tokenise(title + " " + the first paragraph of
  ``## Decision``)`` at the protocol's threshold (for a background page without ``## Decision``,
  its title and its first body paragraph);
* (c) shared entity mentions, counted as ``missing-cross-link`` counts them, at the protocol's
  threshold;
* ``combined``, the union of (a), (b) and (c).

Each signal reports its candidates (category, label or ``background, unlisted``, true or false,
the part of (a) that fired, and — for a true pair — the ``annotation_linked`` mark), the counts
behind the pass bar, its verdict, the secondary 91-pair table, the pairs the superseded exclusion
removed and the hashes of the two frozen files it read. The fixture is read in place: the script
writes only ``--out`` and never writes ``labels.json``, ``questions.json`` or ``protocol.json``.
No backend is called and nothing is merged, pruned or edited.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from itertools import combinations
from pathlib import Path
from typing import TYPE_CHECKING, Any

from wiki_studio import api
from wiki_studio.findings import KIND_OPEN_CONFLICT
from wiki_studio.health_lint import _candidate_pairs, _entity_mentions, _intra_wiki_links_from
from wiki_studio.paths import WikiPaths
from wiki_studio.prose_lint import load_avoid_map
from wiki_studio.review import superseded_by
from wiki_studio.wiki_state import _tokenise
from wiki_studio.yaml_lite import parse_frontmatter

if TYPE_CHECKING:
    from collections.abc import Sequence

PATTERNS_DIR = Path(__file__).resolve().parent
LABELS_NAME = "labels.json"
PROTOCOL_NAME = "protocol.json"
MANIFEST_NAME = "manifest.json"
FIXTURE_NAME = "wiki"
DEFAULT_OUT = PATTERNS_DIR / "results" / "duplicates.json"
STUDY = "issue 54 duplicate candidates"
BACKGROUND_UNLISTED = "background, unlisted"
TRUE_DISPOSITIONS = frozenset({"redundant", "conflicting"})
FALSE_REASONS = ("distinct-by-precondition", "unrelated", BACKGROUND_UNLISTED)
NON_ENTITIES = frozenset({"index", "log", "overview"})
SHARED_PATH = "shared-path"
DIRECT_LINK = "direct-link"
_NUMBERED_ITEM_RE = re.compile(r"^\d+[.)]\s")
_SKIPPED_BLOCK_PREFIXES = ("#", ">", "|", "```", "- ", "* ", "+ ")


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_frozen(patterns_dir: Path) -> int:
    """0 when ``labels.json`` hashes to the protocol's frozen value; 1, naming both values, when not."""
    actual = _sha256_of(patterns_dir / LABELS_NAME)
    protocol = json.loads((patterns_dir / PROTOCOL_NAME).read_text(encoding="utf-8"))
    expected = str(protocol["labels_sha256"])
    if actual == expected:
        return 0
    sys.stderr.write(
        f"{LABELS_NAME} sha256 {actual} does not match {PROTOCOL_NAME} labels_sha256 {expected}; "
        "the labels are not the frozen labels, so nothing was computed and nothing was written\n"
    )
    return 1


def _body(text: str) -> str:
    """The page text after its frontmatter, as the health checks read it."""
    if text.startswith("---"):
        close = text.find("\n---", 3)
        if close != -1:
            return text[close + 4 :]
    return text


def _title(text: str) -> str:
    try:
        value = parse_frontmatter(text).get("title")
    except Exception:
        return ""
    return str(value) if value is not None else ""


def _cited_paths(text: str) -> set[str]:
    """The page's ``sources[].path`` values, the set ``_candidate_pairs`` compares."""
    try:
        frontmatter = parse_frontmatter(text)
    except Exception:
        return set()
    return {
        str(source["path"])
        for source in frontmatter.get("sources") or []
        if isinstance(source, dict) and source.get("path")
    }


def _decision_section(body: str) -> str | None:
    """The text of ``## Decision`` up to the next H2, or None when the page has no such section."""
    match = re.search(r"(?m)^## Decision[ \t]*$", body)
    if match is None:
        return None
    rest = body[match.end() :]
    following = re.search(r"(?m)^## ", rest)
    return rest if following is None else rest[: following.start()]


def _first_paragraph(text: str) -> str:
    """The first prose paragraph of ``## Decision``, else of the body (headings, quotes, lists skipped)."""
    body = _body(text)
    section = _decision_section(body)
    source = body if section is None else section
    for block in re.split(r"\n[ \t]*\n", source):
        stripped = block.strip()
        if not stripped or stripped.startswith(_SKIPPED_BLOCK_PREFIXES) or _NUMBERED_ITEM_RE.match(stripped):
            continue
        if stripped.strip("-") == "":
            continue
        return " ".join(stripped.split())
    return ""


def _entity_vocabulary(fixture: Path) -> tuple[list[str], dict[str, list[str]]]:
    """The entity slugs (every page except index, log and overview) and the glossary aliases."""
    slugs: list[str] = []
    for page in sorted(fixture.rglob("*.md")):
        slug = page.stem
        if slug in NON_ENTITIES:
            continue
        slugs.append(slug)
    avoid_map, _problems = load_avoid_map(fixture)
    aliases = {entry.canonical: list(entry.terms) for entry in avoid_map.values() if entry.anchor is None}
    return slugs, aliases


def _page_info(fixture: Path, rels: list[str]) -> dict[str, dict[str, Any]]:
    """Read each page once: eligibility, title, (b) tokens, (c) mentions, cited paths and links."""
    vocabulary, aliases = _entity_vocabulary(fixture)
    info: dict[str, dict[str, Any]] = {}
    for rel in sorted(set(rels)):
        text = (fixture / rel).read_text(encoding="utf-8")
        info[rel] = {
            "eligible": superseded_by(text) is None,
            "tokens": _tokenise(f"{_title(text)} {_first_paragraph(text)}"),
            "mentions": _entity_mentions(_body(text), vocabulary, aliases),
            "sources": _cited_paths(text),
            "links": set(_intra_wiki_links_from(fixture / rel, fixture)),
        }
    return info


def _pair(left: str, right: str) -> tuple[str, str]:
    return (left, right) if left < right else (right, left)


def _a_candidates(
    fixture: Path, eligible: list[str], info: dict[str, dict[str, Any]]
) -> dict[tuple[str, str], tuple[str, ...]]:
    """(a): the candidate pairs ``_candidate_pairs`` returns, each with the parts that fired."""
    candidates: dict[tuple[str, str], tuple[str, ...]] = {}
    for left, right in _candidate_pairs([fixture / rel for rel in eligible], fixture):
        left_rel = left.relative_to(fixture).as_posix()
        right_rel = right.relative_to(fixture).as_posix()
        key = _pair(left_rel, right_rel)
        parts: list[str] = []
        if info[left_rel]["sources"] & info[right_rel]["sources"]:
            parts.append(SHARED_PATH)
        if right_rel in info[left_rel]["links"] or left_rel in info[right_rel]["links"]:
            parts.append(DIRECT_LINK)
        candidates[key] = tuple(parts)
    return candidates


def _b_candidates(eligible: list[str], info: dict[str, dict[str, Any]], threshold: float) -> set[tuple[str, str]]:
    """(b): pairs whose title-plus-first-paragraph token sets have Jaccard similarity >= ``threshold``."""
    candidates: set[tuple[str, str]] = set()
    for left, right in combinations(eligible, 2):
        union = info[left]["tokens"] | info[right]["tokens"]
        if union and len(info[left]["tokens"] & info[right]["tokens"]) / len(union) >= threshold:
            candidates.add((left, right))
    return candidates


def _c_candidates(eligible: list[str], info: dict[str, dict[str, Any]], threshold: int) -> set[tuple[str, str]]:
    """(c): pairs sharing at least ``threshold`` entity mentions beyond the two pages' own slugs."""
    candidates: set[tuple[str, str]] = set()
    for left, right in combinations(eligible, 2):
        shared = (info[left]["mentions"] & info[right]["mentions"]) - {Path(left).stem, Path(right).stem}
        if len(shared) >= threshold:
            candidates.add((left, right))
    return candidates


def _annotation_pairs(labels: dict[str, Any], info: dict[str, dict[str, Any]]) -> set[tuple[str, str]]:
    """The annotated label pairs joined by a direct link — the links FR-006 wrote from annotations."""
    joined: set[tuple[str, str]] = set()
    for entry in (*labels["pattern_pairs"], *labels["background_pairs"]):
        if entry.get("annotation") is None:
            continue
        left, right = entry["pair"]
        if left not in info or right not in info:
            continue
        if right in info[left]["links"] or left in info[right]["links"]:
            joined.add(_pair(left, right))
    return joined


def _open_conflict_pairs(fixture: Path) -> set[tuple[str, str]]:
    """The pairs ``api.findings`` already reports as ``open-conflict``; it reads only and takes no lock."""
    result = api.findings(WikiPaths.for_root(fixture.parent, wiki_dir=fixture))
    pairs: set[tuple[str, str]] = set()
    for finding in result.findings:
        if finding.kind == KIND_OPEN_CONFLICT and len(finding.pages) == 2:
            pairs.add(_pair(finding.pages[0], finding.pages[1]))
    return pairs


def _label_for(
    key: tuple[str, str],
    pattern_labels: dict[tuple[str, str], dict[str, Any]],
    background_labels: dict[tuple[str, str], dict[str, Any]],
) -> tuple[str, bool]:
    """The pair's disposition and truth: pattern labels, a listed background pair, else ``background, unlisted``."""
    entry = pattern_labels.get(key)
    if entry is None:
        entry = background_labels.get(key)
    if entry is None:
        return BACKGROUND_UNLISTED, False
    disposition = str(entry["disposition"])
    return disposition, disposition in TRUE_DISPOSITIONS


def _category(key: tuple[str, str], pattern_rels: set[str]) -> str:
    left_pattern = key[0] in pattern_rels
    right_pattern = key[1] in pattern_rels
    if left_pattern and right_pattern:
        return "pattern-pattern"
    if left_pattern or right_pattern:
        return "pattern-background"
    return "background-background"


def _annotation_mark(
    signal: str,
    key: tuple[str, str],
    parts: tuple[str, ...],
    b_fired: bool,
    c_fired: bool,
    annotation_pairs: set[tuple[str, str]],
    open_pairs: set[tuple[str, str]],
) -> bool:
    """The FR-014 mark: a link-only hit on an annotation link, or a pair ``findings`` reports as open-conflict."""
    if key in open_pairs:
        return True
    link_only = DIRECT_LINK in parts and SHARED_PATH not in parts and key in annotation_pairs
    if signal == "a":
        return link_only
    if signal == "combined":
        return link_only and not b_fired and not c_fired
    return False


def _signal_view(
    name: str,
    keys: list[tuple[str, str]],
    a_candidates: dict[tuple[str, str], tuple[str, ...]],
    b_keys: set[tuple[str, str]],
    c_keys: set[tuple[str, str]],
    pattern_labels: dict[tuple[str, str], dict[str, Any]],
    background_labels: dict[tuple[str, str], dict[str, Any]],
    pattern_rels: set[str],
    true_pairs: set[tuple[str, str]],
    annotation_pairs: set[tuple[str, str]],
    open_pairs: set[tuple[str, str]],
) -> dict[str, Any]:
    """One signal's candidates, the counts behind its pass bar, its verdict and its mark summary."""
    candidates: list[dict[str, Any]] = []
    false_by_reason = dict.fromkeys(FALSE_REASONS, 0)
    found_true: set[tuple[str, str]] = set()
    linked_true = 0
    for key in keys:
        label, is_true = _label_for(key, pattern_labels, background_labels)
        parts = a_candidates.get(key, ())
        mark: bool | None = None
        if is_true:
            mark = _annotation_mark(name, key, parts, key in b_keys, key in c_keys, annotation_pairs, open_pairs)
            linked_true += int(mark)
            found_true.add(key)
        else:
            false_by_reason[label] += 1
        entry: dict[str, Any] = {
            "pair": [key[0], key[1]],
            "category": _category(key, pattern_rels),
            "label": label,
            "true": is_true,
            "annotation_linked": mark,
        }
        if name == "a":
            entry["parts"] = list(parts)
        candidates.append(entry)
    true_count = len(found_true)
    false_count = sum(false_by_reason.values())
    missed = sorted(true_pairs - found_true)
    if not true_pairs:
        verdict = "not testable"
    elif not missed and false_count <= true_count:
        verdict = "pass"
    else:
        verdict = "fail"
    return {
        "candidates": candidates,
        "counts": {
            "eligible_labelled_pairs": len(true_pairs),
            "found_labelled_pairs": true_count,
            "found_labelled_annotation_linked": linked_true,
            "true_candidates": true_count,
            "false_candidates": false_count,
            "false_by_reason": false_by_reason,
            "missed_labelled_pairs": [list(key) for key in missed],
        },
        "verdict": verdict,
        "rests_on_annotation_links": true_count > 0 and linked_true == true_count,
    }


def _labelled_pairs(
    pattern_labels: dict[tuple[str, str], dict[str, Any]],
    background_labels: dict[tuple[str, str], dict[str, Any]],
    eligible: set[str],
) -> set[tuple[str, str]]:
    """The eligible pairs labelled redundant or conflicting across the whole scope."""
    pairs: set[tuple[str, str]] = set()
    for labels in (pattern_labels, background_labels):
        for key, entry in labels.items():
            if entry["disposition"] in TRUE_DISPOSITIONS and key[0] in eligible and key[1] in eligible:
                pairs.add(key)
    return pairs


def run_duplicates(patterns_dir: Path = PATTERNS_DIR) -> dict[str, Any]:
    """Compute every signal over the fixture in place and return the JSON-ready result."""
    fixture = patterns_dir / FIXTURE_NAME
    labels = json.loads((patterns_dir / LABELS_NAME).read_text(encoding="utf-8"))
    protocol = json.loads((patterns_dir / PROTOCOL_NAME).read_text(encoding="utf-8"))
    manifest = json.loads((patterns_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    pattern_rels = [entry["path"] for entry in manifest["pages"]]
    background_rels = [entry["path"] for entry in manifest["background"]]
    info = _page_info(fixture, [*pattern_rels, *background_rels])
    eligible = sorted(rel for rel, page in info.items() if page["eligible"])
    eligible_set = set(eligible)

    a_candidates = _a_candidates(fixture, eligible, info)
    a_path_keys = {key for key, parts in a_candidates.items() if SHARED_PATH in parts}
    threshold_b = float(protocol["signals"]["b"]["threshold"]["value"])
    threshold_c = int(protocol["signals"]["c"]["threshold"]["value"])
    b_keys = _b_candidates(eligible, info, threshold_b)
    c_keys = _c_candidates(eligible, info, threshold_c)
    combined_keys = set(a_candidates) | b_keys | c_keys

    pattern_labels = {_pair(*entry["pair"]): entry for entry in labels["pattern_pairs"]}
    background_labels = {_pair(*entry["pair"]): entry for entry in labels["background_pairs"]}
    pattern_rels_set = set(pattern_rels)
    true_pairs = _labelled_pairs(pattern_labels, background_labels, eligible_set)
    annotation_pairs = _annotation_pairs(labels, info)
    open_pairs = _open_conflict_pairs(fixture)

    signals = {
        "a": _signal_view(
            "a",
            sorted(a_candidates),
            a_candidates,
            b_keys,
            c_keys,
            pattern_labels,
            background_labels,
            pattern_rels_set,
            true_pairs,
            annotation_pairs,
            open_pairs,
        ),
        "a-path": _signal_view(
            "a-path",
            sorted(a_path_keys),
            a_candidates,
            b_keys,
            c_keys,
            pattern_labels,
            background_labels,
            pattern_rels_set,
            true_pairs,
            annotation_pairs,
            open_pairs,
        ),
        "b": _signal_view(
            "b",
            sorted(b_keys),
            a_candidates,
            b_keys,
            c_keys,
            pattern_labels,
            background_labels,
            pattern_rels_set,
            true_pairs,
            annotation_pairs,
            open_pairs,
        ),
        "c": _signal_view(
            "c",
            sorted(c_keys),
            a_candidates,
            b_keys,
            c_keys,
            pattern_labels,
            background_labels,
            pattern_rels_set,
            true_pairs,
            annotation_pairs,
            open_pairs,
        ),
        "combined": _signal_view(
            "combined",
            sorted(combined_keys),
            a_candidates,
            b_keys,
            c_keys,
            pattern_labels,
            background_labels,
            pattern_rels_set,
            true_pairs,
            annotation_pairs,
            open_pairs,
        ),
    }

    pattern_table = [
        {
            "pair": list(entry["pair"]),
            "disposition": entry["disposition"],
            "annotation": entry.get("annotation"),
            "eligible": entry["pair"][0] in eligible_set and entry["pair"][1] in eligible_set,
        }
        for entry in labels["pattern_pairs"]
    ]
    eligible_patterns = [rel for rel in pattern_rels if rel in eligible_set]
    eligible_background = [rel for rel in background_rels if rel in eligible_set]
    background_pairs_total = len(background_rels) * (len(background_rels) - 1) // 2
    background_pairs_eligible = len(eligible_background) * (len(eligible_background) - 1) // 2
    pattern_pairs_total = len(pattern_rels) * (len(pattern_rels) - 1) // 2
    pass_bar: dict[str, Any] = {
        "rule": (
            "a signal passes when it finds every eligible pair labelled redundant or conflicting "
            "and its false candidates do not outnumber its true ones across the whole scope"
        ),
        "meaning": (
            "a pass is grounds to draft an issue for a findings kind, "
            "not evidence that such a kind would work in general"
        ),
        "eligible_labelled_pairs": len(true_pairs),
    }
    if len(true_pairs) <= 2:
        pass_bar["rests_on"] = f"the bar rests on {len(true_pairs)} pairs"
    return {
        "study": STUDY,
        "labels_sha256": _sha256_of(patterns_dir / LABELS_NAME),
        "protocol_sha256": _sha256_of(patterns_dir / PROTOCOL_NAME),
        "scope": {
            "eligible_pages": len(eligible),
            "eligible_pattern_pairs": len(eligible_patterns) * (len(eligible_patterns) - 1) // 2,
            "eligible_pattern_background_pairs": len(eligible_patterns) * len(eligible_background),
            "eligible_background_background_pairs": background_pairs_eligible,
        },
        "pass_bar": pass_bar,
        "signals": signals,
        "pattern_pairs": pattern_table,
        "superseded_exclusion": {
            "reason": str(protocol["eligibility"]["reason"]),
            "pattern_pairs_total": pattern_pairs_total,
            "pattern_pairs_removed": pattern_pairs_total - len(eligible_patterns) * (len(eligible_patterns) - 1) // 2,
            "background_pages_ineligible": len(background_rels) - len(eligible_background),
            "background_pairs_removed": background_pairs_total - background_pairs_eligible,
        },
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m eval.patterns.duplicates",
        description="The issue 54 duplicate candidates: FR-014's signals on the frozen labels.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        metavar="PATH",
        help=f"Write the JSON to PATH (parents created); without it the JSON is printed. Result: {DEFAULT_OUT}.",
    )
    return parser


def main(argv: Sequence[str] | None = None, *, patterns_dir: Path | None = None) -> int:
    """Run the signals and return the exit code; a frozen-label mismatch returns 1 and writes nothing."""
    parser = _build_arg_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    directory = PATTERNS_DIR if patterns_dir is None else patterns_dir
    if check_frozen(directory) != 0:
        return 1
    result = run_duplicates(directory)
    text = json.dumps(result, indent=2) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
