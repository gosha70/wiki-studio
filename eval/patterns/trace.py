# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The lifecycle trace of the reusable-patterns study (FR-017).

``python -m eval.patterns.trace [--out PATH]`` copies ``eval/patterns/wiki`` into a temporary
root, removes the native-feature example page and its index line from the copy, and drives the
real verbs in-process through :func:`wiki_studio.cli.main` with ``--root``, ``--wiki-dir`` and
``--proposals-dir`` pointing into that root and ``--by trace-agent`` on propose, promote and
approve. Every step records its argv (the temporary root written ``<root>``, the reviewed
revision ``<sha256>``), its exit code and a deterministic observation computed from the step's
JSON or the wiki. No model is called, nothing outside the temporary root is written, and no
timestamp, page id, sha256 value or generated proposal path is recorded.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from wiki_studio import api
from wiki_studio.cli import main as cli_main
from wiki_studio.findings import KIND_APPROVAL_POLICY_CHANGED, KIND_APPROVAL_STALE, KIND_UNAPPROVED
from wiki_studio.paths import MANIFEST_NAME, WikiPaths
from wiki_studio.yaml_lite import parse_frontmatter

if TYPE_CHECKING:
    from collections.abc import Sequence

PATTERNS_DIR = Path(__file__).resolve().parent
FIXTURE = PATTERNS_DIR / "wiki"
QUESTIONS = PATTERNS_DIR / "questions.json"
DEFAULT_OUT = PATTERNS_DIR / "results" / "trace.json"

# The page removed from the copy: the native-feature example, which no other fixture page links to.
PAGE = "decisions/swe-bench-fetch-uses-the-stdlib-rows-api-not-parquet.md"
# The successor the supersession step writes (a trace-only page, never fixture content).
SUCCESSOR = "decisions/swe-bench-fetch-pins-the-task-cache.md"
# The date the trace's own log line carries, fixed so the prose is the same on every run.
TRACE_DATE = "2026-11-18"
AGENT = "trace-agent"

ROOT_MARK = "<root>"
SHA_MARK = "<sha256>"
STUDY = "issue 54 lifecycle trace"
REVIEW_KINDS = frozenset({KIND_UNAPPROVED, KIND_APPROVAL_STALE, KIND_APPROVAL_POLICY_CHANGED})

_STALE_RE = re.compile(r"page cites missing source path: '([^']+)'")
_LINT_RE = re.compile(r"linted (\d+) pages, (\d+) violations")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")

# The first body paragraph of the broken draft names a page that is not in the wiki, so the
# staged-tree structural linter refuses the promotion and nothing broken reaches the wiki.
_BROKEN_PAGE = "decisions/trace-broken-link.md"
_BROKEN_TEXT = (
    "---\n"
    "page_type: decision\n"
    "slug: trace-broken-link\n"
    "title: Trace broken link\n"
    "status: stable\n"
    f"last_reviewed: {TRACE_DATE}\n"
    "sources:\n"
    "  - path: specs/benchmark-adapters-backends/spec.md\n"
    "    sha: 13eb704\n"
    "---\n"
    "\n"
    "## Decision\n"
    "\n"
    "In the context of a refused draft, we chose a link to a missing page. We chose it over a "
    "valid page link. The reason: the trace needs a draft the linter refuses.\n"
    "\n"
    "Chosen: [a page that is not in the wiki](decisions/trace-missing-page.md).\n"
    "\n"
    "## Context\n"
    "\n"
    "Requirement: be refused by the staged-tree linter.\n"
    "\n"
    "Applies when: never.\n"
    "\n"
    "Does not apply when: always.\n"
    "\n"
    "## Alternatives considered\n"
    "\n"
    "- A valid link: it would be promoted.\n"
    "\n"
    "## Consequences\n"
    "\n"
    "Revisit when: never.\n"
    "\n"
    "Tests: none.\n"
    "\n"
    "Confidence: high: the target does not exist.\n"
)

_CITED_FILE_TEXT = "# A cited spec\n\nThe trace writes this file after the promotion.\n"
_CITED_FILE_CHANGED = "# A cited spec\n\nThe trace rewrites this file after the supersession.\n"


def _write_tree(directory: Path, files: dict[str, str]) -> None:
    """Write each wiki-relative file of a draft directory, creating parents."""
    for rel, text in files.items():
        target = directory / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _assert_unlinked(page: str) -> None:
    """Fail loudly when a fixture page other than ``index.md`` links the page the trace removes."""
    linked_by = []
    for candidate in sorted(FIXTURE.rglob("*.md")):
        rel = candidate.relative_to(FIXTURE).as_posix()
        if rel in ("index.md", page):
            continue
        if f"]({page})" in candidate.read_text(encoding="utf-8"):
            linked_by.append(rel)
    if linked_by:
        raise RuntimeError(f"{page} is linked from other fixture pages: {', '.join(linked_by)}")


def _first_cited_path(text: str) -> str:
    """The page's first ``sources:`` entry that carries a ``path:``."""
    for source in parse_frontmatter(text).get("sources") or []:
        if isinstance(source, dict) and source.get("path"):
            return str(source["path"])
    raise RuntimeError("the page cites no path source")


def _question_for(page: str) -> str:
    """The ``later-task`` question of the record the page is the reuse target of."""
    for entry in json.loads(QUESTIONS.read_text(encoding="utf-8"))["questions"]:
        if entry.get("reuse_target") == page:
            return str(entry["question"])
    raise RuntimeError(f"questions.json has no entry whose reuse_target is {page}")


def _with_superseded_by(text: str, successor: str) -> str:
    """The page text with ``superseded_by:`` added as the last frontmatter key before ``sources:``."""
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("sources:"):
            lines.insert(index, f"superseded_by: {successor}\n")
            return "".join(lines)
    raise RuntimeError("the page has no sources: key to insert superseded_by: before")


def _finding_view(payload: dict[str, Any], page: str) -> dict[str, Any]:
    """The findings ``findings --json`` reports for one page, without any hash or timestamp."""
    findings = [finding for finding in payload["findings"] if page in finding["pages"]]
    return {
        "page": page,
        "kinds": sorted({finding["kind"] for finding in findings}),
        "stale_claim_paths": sorted(
            match.group(1)
            for finding in findings
            if finding["kind"] == "stale-claim"
            for match in [_STALE_RE.search(finding["description"])]
            if match is not None
        ),
        "superseded_still_indexed": any(finding["kind"] == "superseded-still-indexed" for finding in findings),
    }


def _review_kinds(paths: WikiPaths, page: str) -> list[str]:
    """The review kinds ``findings`` reports for ``page`` (none when the page is approved or superseded)."""
    result = api.findings(paths)
    return sorted(
        {finding.kind for finding in result.findings if page in finding.pages and finding.kind in REVIEW_KINDS}
    )


def _review_state(paths: WikiPaths, page: str) -> str:
    (state,) = api.review_state(paths, pages=[page])
    return state.state


def _selected_paths(payload: dict[str, Any]) -> list[str]:
    return [entry["path"] for entry in payload["pages"]]


def _ineligible_reason(payload: dict[str, Any], page: str) -> str | None:
    for entry in payload["ineligible"]:
        if entry["path"] == page:
            return str(entry["reason"])
    return None


class _Trace:
    """The temporary root, the resolved layout and the steps recorded so far."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.wiki = root / "wiki"
        self.proposals = root / "proposals"
        self.paths = WikiPaths.for_root(root, wiki_dir=self.wiki, proposals_dir=self.proposals)
        self.steps: list[dict[str, Any]] = []

    def location(self) -> list[str]:
        """The three location flags every verb receives, pointing into the temporary root."""
        return ["--root", str(self.root), "--wiki-dir", str(self.wiki), "--proposals-dir", str(self.proposals)]

    def call(self, argv: list[str]) -> tuple[int, str]:
        """Run one verb in-process; its stdout is returned and its stderr is discarded."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = cli_main(list(argv))
            except SystemExit as exc:  # argparse exits on --help and usage errors
                code = exc.code if isinstance(exc.code, int) else 1
        return code, out.getvalue()

    def record(
        self, step: str, argv: list[str], code: int, observation: dict[str, Any], *, hidden: str | None = None
    ) -> None:
        """Append one step; ``hidden`` values (a revision) are written as ``<sha256>`` in the argv."""
        shown = []
        for token in argv:
            if hidden is not None and token == hidden:
                shown.append(SHA_MARK)
                continue
            shown.append(token.replace(str(self.root), ROOT_MARK))
        self.steps.append({"step": step, "argv": shown, "exit_code": code, "observation": observation})


def run_trace(root: Path) -> dict[str, Any]:
    """Build the temporary wiki, run the FR-017 steps in order and return the trace."""
    root = root.absolute()
    wiki = root / "wiki"
    proposals = root / "proposals"
    drafts = root / "drafts"
    _assert_unlinked(PAGE)
    page_text = (FIXTURE / PAGE).read_text(encoding="utf-8")
    first_path = _first_cited_path(page_text)
    question = _question_for(PAGE)

    shutil.copytree(FIXTURE, wiki)
    index_path = wiki / "index.md"
    index_lines = index_path.read_text(encoding="utf-8").splitlines()
    index_line = next(line for line in index_lines if f"]({PAGE})" in line)
    kept = [f"{line}\n" for line in index_lines if f"]({PAGE})" not in line]
    if len(kept) != len(index_lines) - 1:
        raise RuntimeError(f"expected exactly one index line for {PAGE}")
    index_path.write_text("".join(kept), encoding="utf-8")
    (wiki / PAGE).unlink()

    trace = _Trace(root)
    location = trace.location()

    # 1. init: the manifest records the policy; auto_approve_on_promote is false.
    argv = ["init", *location]
    code, _out = trace.call(argv)
    policy = json.loads((wiki / MANIFEST_NAME).read_text(encoding="utf-8"))["policy"]
    trace.record("init", argv, code, {"policy": dict(sorted(policy.items()))})

    # 2. propose the candidate: pending, so the page is absent from the wiki.
    _write_tree(
        drafts / "trace-candidate",
        {
            PAGE: page_text,
            "index.md": f"{index_line}\n",
            "log.md": f"- {TRACE_DATE} — add {Path(PAGE).stem} (decision): the native-feature pattern re-enters the "
            "wiki through the trace\n",
        },
    )
    argv = ["propose", "--from", str(drafts / "trace-candidate"), "--name", "trace-candidate", "--by", AGENT, *location]
    code, _out = trace.call(argv)
    trace.record(
        "propose-candidate",
        argv,
        code,
        {"page_in_wiki": (wiki / PAGE).is_file(), "proposal_written": (proposals / "trace-candidate").is_dir()},
    )

    # 3. propose a draft whose body links a missing page: propose does not resolve links.
    _write_tree(drafts / "trace-broken", {_BROKEN_PAGE: _BROKEN_TEXT})
    argv = ["propose", "--from", str(drafts / "trace-broken"), "--name", "trace-broken", "--by", AGENT, *location]
    code, _out = trace.call(argv)
    trace.record(
        "propose-broken",
        argv,
        code,
        {"page_in_wiki": (wiki / _BROKEN_PAGE).is_file(), "proposal_written": (proposals / "trace-broken").is_dir()},
    )

    # 4. promote the broken draft: the staged-tree linter refuses it and the wiki is unchanged.
    argv = ["promote", str(proposals / "trace-broken"), "--by", AGENT, *location]
    code, _out = trace.call(argv)
    trace.record("promote-broken-refused", argv, code, {"page_in_wiki": (wiki / _BROKEN_PAGE).is_file()})

    # 5. promote the candidate: the page enters the wiki unapproved.
    argv = ["promote", str(proposals / "trace-candidate"), "--by", AGENT, *location]
    code, _out = trace.call(argv)
    live = (wiki / PAGE).read_text(encoding="utf-8") if (wiki / PAGE).is_file() else ""
    trace.record(
        "promote-candidate",
        argv,
        code,
        {
            "page_in_wiki": (wiki / PAGE).is_file(),
            "review_state": _review_state(trace.paths, PAGE) if live else None,
            "page_id_present": "page_id" in parse_frontmatter(live) if live else False,
        },
    )

    # 6. lint: the promoted wiki is structurally clean.
    argv = ["lint", *location]
    code, out = trace.call(argv)
    match = _LINT_RE.search(out)
    trace.record(
        "lint",
        argv,
        code,
        {"pages": int(match.group(1)), "violations": int(match.group(2))}
        if match
        else {"pages": None, "violations": None},
    )

    # 7. write a file at the page's first cited path, inside the temporary root.
    cited = root / first_path
    cited.parent.mkdir(parents=True, exist_ok=True)
    cited.write_text(_CITED_FILE_TEXT, encoding="utf-8")
    trace.record("cited-file-written", ["write-file", str(cited)], 0, {"path": first_path, "exists": cited.is_file()})

    # 8. findings: the page is unapproved, and no stale-claim names the path just written.
    argv = ["findings", "--json", *location]
    code, out = trace.call(argv)
    findings_payload = json.loads(out)
    trace.record("findings-after-cited-file", argv, code, _finding_view(findings_payload, PAGE))

    # 9. read: the page's live bytes and the sha256 the approval must name.
    argv = ["read", PAGE, "--json", *location]
    code, out = trace.call(argv)
    read_payload = json.loads(out)
    trace.record(
        "read",
        argv,
        code,
        {
            "page": read_payload["path"],
            "sha256_is_hex64": _SHA256_RE.fullmatch(read_payload["sha256"]) is not None,
            "content_matches_wiki_file": read_payload["content"].encode("utf-8") == (wiki / PAGE).read_bytes(),
        },
    )

    # 10. approve exactly the revision that was read.
    argv = ["approve", PAGE, "--revision", read_payload["sha256"], "--by", AGENT, *location]
    code, _out = trace.call(argv)
    trace.record(
        "approve",
        argv,
        code,
        {"review_state": _review_state(trace.paths, PAGE), "review_kinds": _review_kinds(trace.paths, PAGE)},
        hidden=read_payload["sha256"],
    )

    # 11. find: the approved page answers its own later task.
    argv = ["find", question, "--ranker", "index-first", "--json", *location]
    code, out = trace.call(argv)
    find_payload = json.loads(out)
    trace.record(
        "find-approved",
        argv,
        code,
        {
            "page_selected": PAGE in _selected_paths(find_payload),
            "page_ineligible": _ineligible_reason(find_payload, PAGE),
        },
    )

    # 12. propose an update with the revision read from the live page: a guarded update.
    current = (wiki / PAGE).read_text(encoding="utf-8")
    updated = f"{current.rstrip()}\n\nTraced: this line was added to make the approval stale.\n"
    base = _sha256_text(current)
    _write_tree(drafts / "trace-update", {PAGE: updated, ".base.json": json.dumps({PAGE: base})})
    argv = ["propose", "--from", str(drafts / "trace-update"), "--name", "trace-update", "--by", AGENT, *location]
    code, _out = trace.call(argv)
    trace.record(
        "propose-update",
        argv,
        code,
        {
            "proposal_written": (proposals / "trace-update").is_dir(),
            "page_bytes_unchanged": _sha256_text((wiki / PAGE).read_text(encoding="utf-8")) == base,
        },
    )

    # 13. promote the update: the approval no longer matches the live bytes.
    argv = ["promote", str(proposals / "trace-update"), "--by", AGENT, *location]
    code, _out = trace.call(argv)
    trace.record(
        "promote-update",
        argv,
        code,
        {"review_state": _review_state(trace.paths, PAGE), "review_kinds": _review_kinds(trace.paths, PAGE)},
    )

    # 14. propose a successor and an update of the page that adds superseded_by, together.
    current = (wiki / PAGE).read_text(encoding="utf-8")
    base = _sha256_text(current)
    successor = (
        "---\n"
        "page_type: decision\n"
        "slug: swe-bench-fetch-pins-the-task-cache\n"
        "title: SWE-bench fetch pins the task cache through the stdlib rows API\n"
        "status: stable\n"
        f"last_reviewed: {TRACE_DATE}\n"
        "sources:\n"
        f"  - path: {first_path}\n"
        "    sha: 13eb704\n"
        "---\n"
        "\n"
        "## Decision\n"
        "\n"
        "In the context of fetching SWE-bench Verified tasks, we chose the stdlib rows API with a "
        "pinned task cache. We chose it over a Parquet dependency. The reason: no new dependency may "
        "be added, and a pinned cache answers the later task.\n"
        "\n"
        "Chosen: the stdlib rows API with a pinned, content-addressed task cache.\n"
        "\n"
        "## Context\n"
        "\n"
        "Requirement: fetch SWE-bench Verified tasks into a pinned cache.\n"
        "\n"
        "Applies when: a task fetch may cache its rows under the no-new-dependencies constraint.\n"
        "\n"
        "Does not apply when: not recorded in the source record.\n"
        "\n"
        "## Alternatives considered\n"
        "\n"
        "- A Parquet dependency: forbidden by the no-new-dependencies constraint.\n"
        "\n"
        "## Consequences\n"
        "\n"
        "Revisit when: the rows API changes.\n"
        "\n"
        "Tests: none in the trace.\n"
        "\n"
        "Confidence: high: the trace writes this page to replace the earlier one.\n"
    )
    _write_tree(
        drafts / "trace-supersede",
        {
            PAGE: _with_superseded_by(current, SUCCESSOR),
            SUCCESSOR: successor,
            "index.md": f"- [SWE-bench fetch pins the task cache]({SUCCESSOR})\n",
            ".base.json": json.dumps({PAGE: base}),
        },
    )
    argv = ["propose", "--from", str(drafts / "trace-supersede"), "--name", "trace-supersede", "--by", AGENT, *location]
    code, _out = trace.call(argv)
    trace.record(
        "propose-supersession",
        argv,
        code,
        {
            "proposal_written": (proposals / "trace-supersede").is_dir(),
            "successor_in_wiki": (wiki / SUCCESSOR).is_file(),
            "page_bytes_unchanged": _sha256_text((wiki / PAGE).read_text(encoding="utf-8")) == base,
        },
    )

    # 15. promote both edits at once: the successor exists when the superseded_by link is checked.
    argv = ["promote", str(proposals / "trace-supersede"), "--by", AGENT, *location]
    code, _out = trace.call(argv)
    trace.record(
        "promote-supersession",
        argv,
        code,
        {
            "successor_in_wiki": (wiki / SUCCESSOR).is_file(),
            "review_state": _review_state(trace.paths, PAGE),
        },
    )

    # 16. the same find: the superseded page is ineligible and the successor is selected.
    argv = ["find", question, "--ranker", "index-first", "--json", *location]
    code, out = trace.call(argv)
    find_payload = json.loads(out)
    trace.record(
        "find-after-supersession",
        argv,
        code,
        {
            "page_selected": PAGE in _selected_paths(find_payload),
            "page_ineligible": _ineligible_reason(find_payload, PAGE),
            "successor_selected": SUCCESSOR in _selected_paths(find_payload),
        },
    )

    # 17. findings: the superseded page is still indexed, and the review kind is gone.
    argv = ["findings", "--json", *location]
    code, out = trace.call(argv)
    superseded_findings = json.loads(out)
    trace.record("findings-after-supersession", argv, code, _finding_view(superseded_findings, PAGE))

    # 18. change the cited file's bytes: no check compares the recorded sha with the file.
    cited.write_text(_CITED_FILE_CHANGED, encoding="utf-8")
    trace.record("cited-file-changed", ["change-file", str(cited)], 0, {"path": first_path, "changed": True})

    # 19. findings again: exactly what the page reported before, so nothing reports a changed source.
    argv = ["findings", "--json", *location]
    code, out = trace.call(argv)
    changed_findings = json.loads(out)
    view = _finding_view(changed_findings, PAGE)
    before = [f for f in superseded_findings["findings"] if PAGE in f["pages"]]
    after = [f for f in changed_findings["findings"] if PAGE in f["pages"]]
    view["findings_unchanged"] = before == after
    trace.record("findings-after-source-change", argv, code, view)

    return {
        "study": STUDY,
        "page": PAGE,
        "page_removal": {"index_line_removed": True, "linked_from_other_pages": False},
        "steps": trace.steps,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m eval.patterns.trace",
        description="The issue 54 lifecycle trace: the real verbs over a temporary copy of the fixture.",
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
    """Run the trace; return the exit code (``--help`` exits 0 like any argparse program)."""
    parser = _build_arg_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    with tempfile.TemporaryDirectory(prefix="patterns-trace-") as tmp:
        result = run_trace(Path(tmp))
    text = json.dumps(result, indent=2) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
