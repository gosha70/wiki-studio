# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The retrieval measurement of the reusable-patterns study (FR-018).

``python -m eval.patterns.retrieval [--out PATH]`` copies ``eval/patterns/wiki`` into a
temporary root and calls ``api.find(question, paths, max_pages=5, ranker=r)`` for each question
in ``questions.json`` and each ranker in ``discovery.RANKERS``. Per question and ranker it
records the selected pages in rank order, the ranker that ran, hit at 1, hit at 5, whether the
trap outranks the reuse target, and — for a question that names a superseded page — whether
that page is listed ineligible and never selected; then the per-ranker totals, the questions'
sha256 and the Python and SQLite versions of the run. The discovery runner under
``eval/navigation`` is neither used nor edited.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from wiki_studio import api, discovery
from wiki_studio.paths import WikiPaths

if TYPE_CHECKING:
    from collections.abc import Sequence

PATTERNS_DIR = Path(__file__).resolve().parent
FIXTURE = PATTERNS_DIR / "wiki"
QUESTIONS = PATTERNS_DIR / "questions.json"
DEFAULT_OUT = PATTERNS_DIR / "results" / "retrieval.json"
MAX_PAGES = 5
STUDY = "issue 54 retrieval"


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _trap_outranks(selected: list[str], trap: str | None, target: str | None) -> bool | None:
    """True when the trap is above the reuse target, or present while the target is absent."""
    if trap is None:
        return None
    if trap not in selected:
        return False
    return target is None or target not in selected or selected.index(trap) < selected.index(target)


def _superseded_view(result: api.FindResult, page: str | None) -> dict[str, Any] | None:
    """Whether a question's superseded page is listed ineligible and absent from the selection."""
    if page is None:
        return None
    return {
        "page": page,
        "listed_ineligible": any(entry.path == page and entry.reason == "superseded" for entry in result.ineligible),
        "selected": page in [found.path for found in result.pages],
    }


def _totals(entries: list[dict[str, Any]]) -> dict[str, int]:
    superseded = [entry["superseded"] for entry in entries if entry["superseded"] is not None]
    return {
        "questions": len(entries),
        "hit_at_1": sum(1 for entry in entries if entry["hit_at_1"]),
        "hit_at_5": sum(1 for entry in entries if entry["hit_at_5"]),
        "trap_outranks": sum(1 for entry in entries if entry["trap_outranks"]),
        "superseded_checked": len(superseded),
        "superseded_violations": sum(
            1 for view in superseded if not (view["listed_ineligible"] and not view["selected"])
        ),
    }


def run_retrieval(root: Path) -> dict[str, Any]:
    """Copy the fixture into ``root`` and measure ``find`` for every question and ranker."""
    root = root.absolute()
    wiki = root / "wiki"
    shutil.copytree(FIXTURE, wiki)
    paths = WikiPaths.for_root(root, wiki_dir=wiki)
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))["questions"]
    rankers: dict[str, Any] = {}
    for ranker in discovery.RANKERS:
        entries: list[dict[str, Any]] = []
        for question in questions:
            result = api.find(question["question"], paths, max_pages=MAX_PAGES, ranker=ranker)
            selected = [found.path for found in result.pages]
            gold = set(question["gold"])
            entries.append(
                {
                    "id": question["id"],
                    "selected": selected,
                    "ran_as": result.ranker,
                    "hit_at_1": bool(selected) and selected[0] in gold,
                    "hit_at_5": all(page in selected for page in gold),
                    "trap_outranks": _trap_outranks(selected, question.get("trap"), question.get("reuse_target")),
                    "superseded": _superseded_view(result, question.get("superseded")),
                }
            )
        rankers[ranker] = {"questions": entries, "totals": _totals(entries)}
    return {
        "study": STUDY,
        "questions_sha256": _sha256_of(QUESTIONS),
        "max_pages": MAX_PAGES,
        "environment": {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version},
        "rankers": rankers,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m eval.patterns.retrieval",
        description="The issue 54 retrieval measurement: api.find over each question and ranker.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        metavar="PATH",
        help=f"Write the JSON to PATH (parents created); without it the JSON is printed. Result: {DEFAULT_OUT}.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the measurement; return the exit code (``--help`` exits 0 like any argparse program)."""
    parser = _build_arg_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    with tempfile.TemporaryDirectory(prefix="patterns-retrieval-") as tmp:
        result = run_retrieval(Path(tmp))
    text = json.dumps(result, indent=2) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
