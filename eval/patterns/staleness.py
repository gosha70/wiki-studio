# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Revisit signals: every cited source against a code-copilot-team checkout (FR-026).

``python -m eval.patterns.staleness --checkout PATH [--out PATH]`` reads every ``path:`` +
``sha:`` source of the 14 pattern pages and the code-copilot-team pin from ``manifest.json``,
then, for each source, runs two read-only git commands with an argument list and no shell, in
the checkout given:

* ``git -C <checkout> cat-file -e <pin>:<path>`` — present at the pin or missing;
* when the ``sha:`` is known to the checkout, ``git -C <checkout> diff --quiet <sha> <pin>
  -- <path>`` — changed or unchanged since ``sha``; ``null`` with a reason when the ``sha:``
  is unknown to the checkout.

Per source it records ``stale_claim`` — what ``stale-claim`` would report with the wiki inside
that checkout at the pin, flagged exactly when the path is missing (health_lint.py 141) — and
``revision_check``; per page, its ``Revisit when:`` line. It reads nothing over the network,
writes only ``--out`` (the committed run is ``results/staleness.json``), calls no backend and
edits nothing in the checkout. A checkout or pin that cannot be read exits 2 and writes
nothing.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from wiki_studio.yaml_lite import parse_frontmatter

if TYPE_CHECKING:
    from collections.abc import Sequence

PATTERNS_DIR = Path(__file__).resolve().parent
MANIFEST_NAME = "manifest.json"
FIXTURE_NAME = "wiki"
DEFAULT_OUT = PATTERNS_DIR / "results" / "staleness.json"
STUDY = "issue 54 revisit signals"
FLAGGED = "flagged"
NOT_FLAGGED = "not flagged"
CHANGED = "changed"
UNCHANGED = "unchanged"
REVISIT_PREFIX = "Revisit when:"
CHECKOUT_UNREADABLE = 2


class CheckoutError(RuntimeError):
    """The checkout cannot be read at the pin, so nothing was computed."""


def _git(checkout: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run one git command read-only, with an argument list and no shell."""
    return subprocess.run(
        ["git", "-C", str(checkout), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _revision(checkout: Path, pin: str, path: str, sha: str) -> tuple[str | None, str | None]:
    """``changed`` or ``unchanged`` from ``git diff --quiet``, or ``None`` with a reason."""
    if _git(checkout, "cat-file", "-e", f"{sha}^{{commit}}").returncode != 0:
        return None, f"sha {sha} is not a commit in the checkout"
    result = _git(checkout, "diff", "--quiet", sha, pin, "--", path)
    if result.returncode == 0:
        return UNCHANGED, None
    if result.returncode == 1:
        return CHANGED, None
    return None, f"git diff --quiet exited {result.returncode}"


def check_sources(checkout: Path, pin: str, sources: Sequence[dict[str, str]]) -> list[dict[str, Any]]:
    """Present at the pin and changed since its ``sha``, one entry per source, in input order.

    ``stale_claim`` is flagged exactly when the path is missing at the pin, which is all
    ``stale-claim`` reports (health_lint.py 110-155). ``revision_check`` is ``changed``,
    ``unchanged``, or ``None`` with ``revision_reason`` when the ``sha`` is unknown to the
    checkout or the diff command itself failed.
    """
    results: list[dict[str, Any]] = []
    for source in sources:
        path, sha = source["path"], source["sha"]
        present = _git(checkout, "cat-file", "-e", f"{pin}:{path}").returncode == 0
        revision, reason = _revision(checkout, pin, path, sha)
        results.append(
            {
                "path": path,
                "sha": sha,
                "stale_claim": NOT_FLAGGED if present else FLAGGED,
                "revision_check": revision,
                "revision_reason": reason,
            }
        )
    return results


def _body(text: str) -> str:
    """The page text after its frontmatter."""
    if text.startswith("---"):
        close = text.find("\n---", 3)
        if close != -1:
            return text[close + 4 :]
    return text


def _revisit_when(text: str) -> str | None:
    """The page's ``Revisit when:`` line, without the prefix, or None when it has none."""
    for line in _body(text).splitlines():
        if line.startswith(REVISIT_PREFIX):
            return line[len(REVISIT_PREFIX) :].strip()
    return None


def _page_sources(text: str) -> list[dict[str, str]]:
    """Every ``path:`` + ``sha:`` entry of the page's ``sources:``, in frontmatter order."""
    parsed = parse_frontmatter(text)
    return [
        {"path": str(source["path"]), "sha": str(source["sha"])}
        for source in parsed.get("sources") or []
        if isinstance(source, dict) and "path" in source and "sha" in source
    ]


def _totals(pages: list[dict[str, Any]]) -> dict[str, int]:
    """The counts the README restates: sources, flags, changed/unchanged/unknown, pages."""
    sources = [source for page in pages for source in page["sources"]]
    return {
        "pages": len(pages),
        "sources": len(sources),
        "stale_claim_flagged": sum(1 for source in sources if source["stale_claim"] == FLAGGED),
        "revision_changed": sum(1 for source in sources if source["revision_check"] == CHANGED),
        "revision_unchanged": sum(1 for source in sources if source["revision_check"] == UNCHANGED),
        "revision_unknown": sum(1 for source in sources if source["revision_check"] is None),
        "pages_with_a_changed_source": sum(
            1 for page in pages if any(source["revision_check"] == CHANGED for source in page["sources"])
        ),
    }


def run_staleness(checkout: Path, patterns_dir: Path = PATTERNS_DIR) -> dict[str, Any]:
    """Check every pattern page's sources against ``checkout`` at the manifest's pin."""
    manifest = json.loads((patterns_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    pin = str(manifest["pins"]["code_copilot_team"]["commit"])
    if _git(checkout, "cat-file", "-e", f"{pin}^{{commit}}").returncode != 0:
        raise CheckoutError(f"cannot read the pin {pin} in the checkout {checkout}")
    fixture = patterns_dir / FIXTURE_NAME
    pages: list[dict[str, Any]] = []
    for entry in manifest["pages"]:
        text = (fixture / entry["path"]).read_text(encoding="utf-8")
        pages.append(
            {
                "page": entry["path"],
                "revisit_when": _revisit_when(text),
                "sources": check_sources(checkout, pin, _page_sources(text)),
            }
        )
    return {"study": STUDY, "pin": pin, "pages": pages, "totals": _totals(pages)}


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m eval.patterns.staleness",
        description="The issue 54 revisit signals: every cited source against a code-copilot-team checkout.",
    )
    parser.add_argument(
        "--checkout",
        type=Path,
        required=True,
        metavar="PATH",
        help="The local code-copilot-team checkout to read (read-only; nothing is written there).",
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
    """Run the checks and return the exit code: 0 ok, 2 when the checkout or pin is unreadable."""
    parser = _build_arg_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    try:
        result = run_staleness(args.checkout)
    except CheckoutError as exc:
        sys.stderr.write(f"{exc}; nothing was computed and nothing was written\n")
        return CHECKOUT_UNREADABLE
    text = json.dumps(result, indent=2) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
