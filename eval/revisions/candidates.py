# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The revision-check study's scoring: C0-C4 against the frozen bar, from the record (FR-013).

``python -m eval.revisions.candidates [--out PATH]`` reads ``protocol.json``, the
recorded hunks (``results/hunks.json`` and each keyword-quoting case's own
``hunks.json``), the issue 54 fixture pages in place under
``eval/patterns/wiki/``, the pre-successor copy and the case pages. It imports
``wiki_studio.fact_diff`` and ``wiki_studio.wiki_state._tokenise`` read-only,
runs no git and reads no checkout, so CI reruns it. Per candidate it gives the
figures and bar verdicts of FR-013, then the winner by the frozen selection
rule, and the process counts the shipped call cap and timeout are derived
from. Without ``--out`` the JSON is printed; the committed run is
``results/candidates.json``. The output names keyword-quoting cases by id only
and carries no recorded text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import posixpath
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from wiki_studio import fact_diff
from wiki_studio.wiki_state import _tokenise

if TYPE_CHECKING:
    from collections.abc import Sequence

REVISIONS_DIR = Path(__file__).resolve().parent
REPO_ROOT = REVISIONS_DIR.parents[1]
PROTOCOL = REVISIONS_DIR / "protocol.json"
HUNKS = REVISIONS_DIR / "results" / "hunks.json"
DEFAULT_OUT = REVISIONS_DIR / "results" / "candidates.json"
STUDY = "issue 120 revision check: the candidates scored"

RUN_STUDY = "study"
RUN_PRE_SUCCESSOR = "pre-successor"
RECORDED_IN = "recorded_in"
CHANGED_STATUSES = frozenset({"M", "T"})
STATE_CHECKED = "checked"
EXACT_KIND_STEPS = ("p1", "p2", "p3", "p4")
STEP_C1 = "p5"
STEP_HUNKS = "p6"
STEP_HEADINGS = "p7"
SECONDS_DIGITS = 6

PASS = "pass"
FAIL = "fail"
NOT_TESTABLE = "not testable"
KEPT = "kept"
LOST = "lost"
WINNER_NONE = "none"

REVISIT_PREFIX = "Revisit when:"
LIST_MARKER_RE = re.compile(r"^(?:[-*+]|\d+[.)])[ \t]+")
NOT_RECORDED = "not recorded"
# Post hoc, not binding (found after the freeze, external review of the evidence PR): the anchor-based
# candidates re-scored without fragment anchors. It never changes a verdict, the bar or the winner.
POST_HOC_CANDIDATES = ("C2", "C4")
POST_HOC_MIN_ANCHOR_LENGTH = 4
POST_HOC_RULE = (
    "anchors shorter than 4 characters, anchors with no letter, and the last dotted component of a"
    " backticked path (an identifier containing '/') are ignored"
)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def page_body(text: str) -> str:
    """The page text after its frontmatter, as ``fact_diff`` splits it."""
    return fact_diff._split_frontmatter(text)[1]


def anchors(text: str, *, fragments: bool = True) -> set[str]:
    """C2's anchors: backticked identifiers (also by their last dotted component) and ``file:line`` references.

    Taken over the body with fenced code blanked, with ``fact_diff``'s regexes
    and normalisation unchanged. An empty string is no anchor. With
    ``fragments=False`` (post hoc only), the anchors ``POST_HOC_RULE`` names are
    left out.
    """
    prose = fact_diff._without_fences(page_body(text))
    found = {f"{m.group(1)}:{m.group(2)}" for m in fact_diff._PATH_LINE_RE.finditer(prose)}
    for match in fact_diff._BACKTICK_RE.finditer(prose):
        identifier = fact_diff._normalize_identifier(match.group(1))
        found.add(identifier)
        if fragments or "/" not in identifier:
            found.add(identifier.rsplit(".", 1)[-1])
    if not fragments:
        found = {anchor for anchor in found if _not_a_fragment(anchor)}
    return {anchor for anchor in found if anchor}


def _not_a_fragment(anchor: str) -> bool:
    return len(anchor) >= POST_HOC_MIN_ANCHOR_LENGTH and any(char.isalpha() for char in anchor)


def revisit_when(text: str) -> str | None:
    """The text after ``Revisit when:`` on the first such body line outside fenced code, or None."""
    for line in fact_diff._without_fences(page_body(text)).splitlines():
        stripped = LIST_MARKER_RE.sub("", line.lstrip(), count=1)
        if stripped.startswith(REVISIT_PREFIX):
            return stripped[len(REVISIT_PREFIX) :]
    return None


def revisit_tokens(text: str) -> set[str]:
    """C3's tokens; empty when the page has no ``Revisit when:`` line or the line says it is not recorded."""
    line = revisit_when(text)
    if line is None or NOT_RECORDED in line.lower():
        return set()
    return _tokenise(line)


def changed_lines(path_record: dict[str, Any]) -> list[str]:
    """The ``+`` and ``-`` lines of the recorded hunks, without their marker."""
    return [line[1:] for hunk in path_record["hunks"] for line in hunk["lines"]]


class PageView:
    """What the candidates read from one page: its body, anchors and Revisit-when tokens."""

    def __init__(self, text: str, *, fragments: bool = True) -> None:
        self.body_lower = page_body(text).lower()
        self.anchors = anchors(text, fragments=fragments)
        self.tokens = revisit_tokens(text)


def _c2_fires(view: PageView, path_record: dict[str, Any]) -> bool:
    lines = changed_lines(path_record)
    if any(anchor in line for line in lines for anchor in view.anchors):
        return True
    if path_record["markdown"]:
        for hunk in path_record["hunks"]:
            heading = hunk["heading"]
            if heading and heading.lower() in view.body_lower:
                return True
    return False


def _c3_fires(view: PageView, path_record: dict[str, Any]) -> bool:
    return any(_tokenise(line) & view.tokens for line in changed_lines(path_record))


def decide(candidate: str, view: PageView, path_record: dict[str, Any]) -> tuple[bool, set[str]]:
    """Whether ``candidate`` flags one changed source, and which of p5-p7 it needed to decide."""
    p5 = bool(path_record["p5_differs"])
    hunk_steps = {STEP_HUNKS, STEP_HEADINGS} if path_record["markdown"] else {STEP_HUNKS}

    def c2() -> tuple[bool, set[str]]:
        if not view.anchors:
            return p5, {STEP_C1}
        return _c2_fires(view, path_record), set(hunk_steps)

    def c3() -> tuple[bool, set[str]]:
        if not view.tokens:
            return p5, {STEP_C1}
        return _c3_fires(view, path_record), {STEP_HUNKS}

    if candidate == "C0":
        return True, set()
    if candidate == "C1":
        return p5, {STEP_C1}
    if candidate == "C2":
        return c2()
    if candidate == "C3":
        return c3()
    if candidate == "C4":
        flag2, steps2 = c2()
        flag3, steps3 = c3()
        return flag2 and flag3, steps2 | steps3
    raise ValueError(f"unknown candidate {candidate}")


def _path_index(run: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    return {(entry["repository"], entry["commit"], entry["path"]): entry for entry in run["paths"]}


def _source_key(source: dict[str, Any]) -> tuple[str, str, str]:
    """The recorded path entry of a matched source: the record keys paths by their normalised form."""
    return (source["repository"], source["commit"], posixpath.normpath(source["path"]))


def score_run(
    candidate: str, run: dict[str, Any], texts: dict[str, str], *, fragments: bool = True
) -> tuple[set[tuple[str, str, str]], set[tuple[tuple[str, str, str], str]]]:
    """The (page, path, sha) entries ``candidate`` flags in one run, and the (path key, step) calls it needs.

    Only a checked source whose path p4 marks changed (present at both
    commits) can be flagged: superseded pages are not examined, and a source
    missing at its ``sha:`` or at HEAD gets no revision kind.
    """
    paths = _path_index(run)
    flagged: set[tuple[str, str, str]] = set()
    needed: set[tuple[tuple[str, str, str], str]] = set()
    for page in run["pages"]:
        if page["superseded"]:
            continue
        view = PageView(texts[page["page"]], fragments=fragments)
        for source in page["sources"]:
            if source["state"] != STATE_CHECKED or source["status"] not in CHANGED_STATUSES:
                continue
            key = _source_key(source)
            flag, steps = decide(candidate, view, paths[key])
            needed |= {(key, step) for step in steps}
            if flag:
                flagged.add((page["page"], source["path"], source["sha"]))
    return flagged, needed


def cost(run: dict[str, Any], needed: set[tuple[tuple[str, str, str], str]]) -> tuple[int, float]:
    """Processes and wall time: every p1-p4 call of the run plus the p5-p7 calls in ``needed``."""
    processes, seconds = 0, 0.0
    for call in run["calls"]:
        if call["step"] in EXACT_KIND_STEPS or ((call["repository"], call["commit"], call["path"]), call["step"]) in (
            needed
        ):
            processes += 1
            seconds += call["seconds"]
    return processes, round(seconds, SECONDS_DIGITS)


def load_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """The protocol, the main record, each case's run by id and each case's ``case.json`` by id."""
    protocol = load_json(PROTOCOL)
    hunks = load_json(HUNKS)
    runs: dict[str, dict[str, Any]] = {}
    cases: dict[str, dict[str, Any]] = {}
    for directory in protocol["cases"]:
        case = load_json(REPO_ROOT / directory / "case.json")
        recorded = hunks["cases"][case["id"]]
        if RECORDED_IN in recorded:
            recorded = load_json(REPO_ROOT / recorded[RECORDED_IN])["run"]
        cases[case["id"]] = {**case, "directory": directory}
        runs[case["id"]] = recorded
    return protocol, hunks, runs, cases


def _page_texts(protocol: dict[str, Any], hunks: dict[str, Any]) -> dict[str, str]:
    wiki = REPO_ROOT / protocol["inputs"]["wiki"]
    texts = {
        page["page"]: (wiki / page["page"]).read_text(encoding="utf-8") for page in hunks["runs"][RUN_STUDY]["pages"]
    }
    for page in hunks["runs"][RUN_PRE_SUCCESSOR]["pages"]:
        texts[page["page"]] = (REVISIONS_DIR / page["page"]).read_text(encoding="utf-8")
    return texts


def _required(protocol: dict[str, Any], positives: int) -> int | None:
    recall = protocol["bar"]["recall"]
    if positives < recall["min_positives"]:
        return None
    return math.ceil(positives * recall["keep_numerator"] / recall["keep_denominator"])


def score() -> dict[str, Any]:
    """Score every candidate ``protocol.json`` lists and pick the winner by its selection rule."""
    protocol, hunks, case_runs, cases = load_inputs()
    texts = _page_texts(protocol, hunks)
    study_run = hunks["runs"][RUN_STUDY]
    pre_run = hunks["runs"][RUN_PRE_SUCCESSOR]
    false_pages = list(protocol["false_pages"])
    false_entries = {(entry["page"], entry["path"], entry["sha"]) for entry in protocol["false_entries"]}
    true_entry = protocol["true_entry"]
    true_key = (
        Path(true_entry["read_on"]).relative_to("eval/revisions").as_posix(),
        true_entry["path"],
        true_entry["sha"],
    )
    built = set(protocol["built_cases"])
    positives = [cid for cid, case in cases.items() if case["should_flag"] and not case["negative"]]
    negatives = [cid for cid, case in cases.items() if case["negative"]]
    reported_only = [cid for cid, case in cases.items() if not case["should_flag"] and not case["negative"]]
    required = _required(protocol, len(positives))
    max_false = protocol["bar"]["false_pages"]["max_flagged"]

    results: dict[str, Any] = {}
    for spec in protocol["candidates"]:
        cid = spec["id"]
        flagged, needed = score_run(cid, study_run, texts)
        pre_flagged, _ = score_run(cid, pre_run, texts)
        flagged_cases = _flagged_cases(cid, cases, case_runs)
        pages_flagged = [
            page["page"] for page in study_run["pages"] if any(entry[0] == page["page"] for entry in flagged)
        ]
        false_pages_flagged = [page for page in false_pages if page in pages_flagged]
        kept = [case_id for case_id in positives if case_id in flagged_cases]
        kept_without_built = [case_id for case_id in kept if case_id not in built]
        processes, seconds = cost(study_run, needed)
        true_kept = true_key in pre_flagged
        bar = {
            "false_pages": PASS if len(false_pages_flagged) <= max_false else FAIL,
            "true_entry": PASS if true_kept else FAIL,
            "recall": NOT_TESTABLE if required is None else (PASS if len(kept) >= required else FAIL),
        }
        bar["overall"] = PASS if all(value != FAIL for value in bar.values()) else FAIL
        results[cid] = {
            "name": spec["name"],
            "study": {
                "pages_flagged": pages_flagged,
                "entries_flagged": len(flagged),
                "false_pages_flagged": false_pages_flagged,
                "false_pages_flagged_count": len(false_pages_flagged),
                "false_pages_of": len(false_pages),
                "false_entries_flagged_count": len(flagged & false_entries),
                "false_entries_of": len(false_entries),
            },
            "true_entry": KEPT if true_kept else LOST,
            "supplementary": {
                "kept": len(kept),
                "of": len(positives),
                "required": required,
                "kept_cases": kept,
                "kept_without_built": len(kept_without_built),
                "of_without_built": len([case_id for case_id in positives if case_id not in built]),
            },
            "negatives": {"flagged": len([c for c in negatives if c in flagged_cases]), "of": len(negatives)},
            "reported_only": {case_id: case_id in flagged_cases for case_id in reported_only},
            "cost": {"study_processes": processes, "study_seconds": seconds},
            "bar": bar,
        }
    post_hoc: dict[str, Any] = {"binding": False, "rule": POST_HOC_RULE, "candidates": {}}
    for cid in POST_HOC_CANDIDATES:
        flagged, _ = score_run(cid, study_run, texts, fragments=False)
        pre_flagged, _ = score_run(cid, pre_run, texts, fragments=False)
        frozen_flagged, _ = score_run(cid, study_run, texts)
        flagged_cases = _flagged_cases(cid, cases, case_runs, fragments=False)
        frozen_cases = _flagged_cases(cid, cases, case_runs)
        pages_flagged = {entry[0] for entry in flagged}
        false_pages_flagged = [page for page in false_pages if page in pages_flagged]
        post_hoc["candidates"][cid] = {
            "false_pages_flagged_count": len(false_pages_flagged),
            "false_pages_of": len(false_pages),
            "false_entries_flagged_count": len(flagged & false_entries),
            "false_entries_of": len(false_entries),
            "true_entry": KEPT if true_key in pre_flagged else LOST,
            "supplementary_kept": len([case_id for case_id in positives if case_id in flagged_cases]),
            "supplementary_of": len(positives),
            "reported_only": {case_id: case_id in flagged_cases for case_id in reported_only},
            "flags_from_fragments_only": {
                "study_entries": [list(entry) for entry in sorted(frozen_flagged - flagged)],
                "cases": [case_id for case_id in frozen_cases if case_id not in flagged_cases],
            },
        }
    return {
        "study": STUDY,
        "inputs": _input_hashes(protocol, hunks),
        "candidates": results,
        "winner": select(protocol, results),
        "process_counts": process_counts(hunks, case_runs, results),
        "post_hoc": post_hoc,
    }


def _flagged_cases(
    cid: str, cases: dict[str, dict[str, Any]], case_runs: dict[str, dict[str, Any]], *, fragments: bool = True
) -> list[str]:
    """The cases whose own source ``cid`` flags, in the cases' order."""
    flagged: list[str] = []
    for case_id, case in cases.items():
        case_texts = {case_id: (REPO_ROOT / case["directory"] / "page.md").read_text(encoding="utf-8")}
        case_flags, _ = score_run(cid, case_runs[case_id], case_texts, fragments=fragments)
        if (case_id, case["path"], case["sha"]) in case_flags:
            flagged.append(case_id)
    return flagged


def select(protocol: dict[str, Any], results: dict[str, Any]) -> str:
    """The frozen rule: fewest false pages, then fewest study processes, then the lowest-numbered candidate."""
    order = [spec["id"] for spec in protocol["candidates"]]
    passing = [cid for cid in order if results[cid]["bar"]["overall"] == PASS]
    if not passing:
        return WINNER_NONE
    return min(
        passing,
        key=lambda cid: (
            results[cid]["study"]["false_pages_flagged_count"],
            results[cid]["cost"]["study_processes"],
            order.index(cid),
        ),
    )


def process_counts(
    hunks: dict[str, Any], case_runs: dict[str, dict[str, Any]], results: dict[str, Any]
) -> dict[str, Any]:
    """The study run's processes for the exact kind's plan and with each candidate, and the slowest call."""
    study_run = hunks["runs"][RUN_STUDY]
    processes, seconds = cost(study_run, set())
    runs = {RUN_STUDY: study_run, RUN_PRE_SUCCESSOR: hunks["runs"][RUN_PRE_SUCCESSOR], **case_runs}
    slowest: dict[str, Any] | None = None
    for name, run in runs.items():
        for call in run["calls"]:
            if slowest is None or call["seconds"] > slowest["seconds"]:
                slowest = {"run": name, "step": call["step"], "seconds": call["seconds"]}
    return {
        "exact_kind_plan": {"steps": list(EXACT_KIND_STEPS), "processes": processes, "seconds": seconds},
        "with_candidate": {
            cid: {"processes": result["cost"]["study_processes"], "seconds": result["cost"]["study_seconds"]}
            for cid, result in results.items()
        },
        "slowest_call": slowest,
    }


def _input_hashes(protocol: dict[str, Any], hunks: dict[str, Any]) -> dict[str, Any]:
    fenced = {
        case_id: sha256_of(REPO_ROOT / recorded[RECORDED_IN])
        for case_id, recorded in hunks["cases"].items()
        if RECORDED_IN in recorded
    }
    return {
        "protocol_sha256": sha256_of(PROTOCOL),
        "hunks_sha256": sha256_of(HUNKS),
        "case_hunks_sha256": dict(sorted(fenced.items())),
        "cases": list(protocol["cases"]),
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m eval.revisions.candidates",
        description="Score the revision-check candidates C0-C4 from the recorded hunks (no git, no checkout).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Write the JSON to PATH (parents created); without it the JSON is printed. "
            f"Committed run: {DEFAULT_OUT.relative_to(REPO_ROOT).as_posix()}."
        ),
    )
    return parser


def render(result: dict[str, Any]) -> str:
    return json.dumps(result, indent=2) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Score and print (or write) the result; 0 on success."""
    parser = _build_arg_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    text = render(score())
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
