# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The owner's review sample of false pairs, drawn once from the labelling commit's labels (issue 121, FR-008).

``python -m eval.duplicates.sample [--out PATH]`` reads ``labels.json`` and ``corpus.json`` and draws 20 pairs
from the population of every within-family pair of the three base families (``routing``, ``pi``, ``memkernel``;
extension families are not sampled) whose label is false: an in-group ``companion`` or
``distinct-by-precondition`` disposition, or ``unrelated`` (stated or by default). The 20 are split across the
families in proportion to their within-family pair counts by the largest-remainder method, ties to the family
order; within each family the draw is ``random.Random(SAMPLE_SEED).sample(sorted(population), k)``.

Output: ``review-sample.json`` with the seed, the split, the sha256 of the ``labels.json`` it was drawn from and
the 20 pairs with their family and label. The script reads the two files and writes only ``--out``; it computes
no similarity. It is run once, before the owner changes any label, and never re-drawn.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from itertools import combinations
from pathlib import Path
from typing import TYPE_CHECKING, Any

from eval.duplicates.extract import BASE_FAMILIES, CORPUS_JSON_NAME, DUPLICATES_DIR, MEMKERNEL_FAMILY

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

LABELS_NAME = "labels.json"
SAMPLE_NAME = "review-sample.json"
DEFAULT_OUT = DUPLICATES_DIR / SAMPLE_NAME
SAMPLE_SEED = 121
SAMPLE_SIZE = 20
SAMPLED_FAMILIES = (*BASE_FAMILIES, MEMKERNEL_FAMILY)
TRUE_DISPOSITIONS = frozenset({"redundant", "conflicting", "supersedes"})
DEFAULT_LABEL = "unrelated"

SAMPLE_FAILED = 1


class SampleError(RuntimeError):
    """The inputs cannot give the sample (a missing file, or a family with too few false pairs)."""


def within_family_pairs(entries: Iterable[Mapping[str, Any]]) -> dict[str, list[tuple[str, str]]]:
    """Every unordered pair of pages inside each sampled family, each pair in sorted order."""
    pages: dict[str, list[str]] = {}
    for entry in entries:
        family = str(entry["family"])
        if family in SAMPLED_FAMILIES:
            pages.setdefault(family, []).append(str(entry["page"]))
    return {family: list(combinations(sorted(pages[family]), 2)) for family in SAMPLED_FAMILIES if family in pages}


def largest_remainder(counts: Mapping[str, int], size: int = SAMPLE_SIZE) -> dict[str, int]:
    """``size`` split in proportion to ``counts`` by the largest-remainder method, ties to the family order."""
    families = [family for family in SAMPLED_FAMILIES if family in counts]
    whole = sum(counts[family] for family in families)
    if whole == 0:
        raise SampleError("no within-family pairs in the base families")
    split = {family: size * counts[family] // whole for family in families}
    remainders = {family: size * counts[family] % whole for family in families}
    order = sorted(families, key=lambda family: (-remainders[family], families.index(family)))
    for family in order[: size - sum(split.values())]:
        split[family] += 1
    return split


def draw(labels: Mapping[str, Any], corpus: Mapping[str, Any]) -> tuple[dict[str, int], list[dict[str, Any]]]:
    """The split and the drawn pairs, in family order and, within a family, in draw order."""
    stated: dict[tuple[str, ...], str] = {
        tuple(sorted((str(row["pair"][0]), str(row["pair"][1])))): str(row["disposition"]) for row in labels["pairs"]
    }
    pairs = within_family_pairs(corpus["pages"])
    split = largest_remainder({family: len(family_pairs) for family, family_pairs in pairs.items()})
    drawn: list[dict[str, Any]] = []
    for family, k in split.items():
        population = [pair for pair in pairs[family] if stated.get(pair, DEFAULT_LABEL) not in TRUE_DISPOSITIONS]
        if k > len(population):
            raise SampleError(f"{family} has {len(population)} false pairs, fewer than the {k} to draw")
        for pair in random.Random(SAMPLE_SEED).sample(sorted(population), k):
            drawn.append({"pair": list(pair), "family": family, "label": stated.get(pair, DEFAULT_LABEL)})
    return split, drawn


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m eval.duplicates.sample",
        description="Draw the issue 121 review sample: 20 false within-family pairs of the base families, seeded.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        metavar="PATH",
        help=f"Write the sample to PATH (parents created; default: {DEFAULT_OUT.name} beside the labels).",
    )
    return parser


def main(argv: Sequence[str] | None = None, *, duplicates_dir: Path | None = None) -> int:
    """Draw and write the sample; return 0, or 1 when the inputs cannot give it (nothing is written)."""
    parser = _build_arg_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    directory = DUPLICATES_DIR if duplicates_dir is None else duplicates_dir
    try:
        labels_bytes = (directory / LABELS_NAME).read_bytes()
        corpus = json.loads((directory / CORPUS_JSON_NAME).read_text(encoding="utf-8"))
        split, drawn = draw(json.loads(labels_bytes.decode("utf-8")), corpus)
    except (OSError, ValueError, SampleError) as exc:
        sys.stderr.write(f"{exc}; nothing was written\n")
        return SAMPLE_FAILED
    document = {
        "seed": SAMPLE_SEED,
        "split": split,
        "labels_sha256": hashlib.sha256(labels_bytes).hexdigest(),
        "pairs": drawn,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes((json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    sys.stdout.write(f"{len(drawn)} pairs drawn ({split}), written to {args.out}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
