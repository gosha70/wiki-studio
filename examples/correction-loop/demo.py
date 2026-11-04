# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# mypy: disable-error-code="import-not-found"
"""The correction loop, one scripted run: a wrong decision, a reviewed correction, the next session.

``python demo.py --workdir DIR [--summary PATH]`` runs three processes in order,
each with ``DIR`` as its working directory and one persisted memkernel store and
one wiki beneath it:

``session-1``
    Initialise the wiki, retain a wrong decision, recall it (the wrong rule is
    the current answer), and export it through wiki-studio's gate as one draft.
``curator``
    Read the draft with the wiki-studio CLI, write the corrected page into a
    draft directory outside the wiki, propose it with ``.base.json`` and
    promote it, approve it, and read the receipt and the approval record back.
``session-2``
    Import through memkernel's governed importer, recall again (the right rule
    is the current answer and the page's ``page_sha:`` is the approved
    revision), and show the old memory kept as superseded.

Every step runs the Python calls memkernel's MCP tools make; no model backend
is on any path, and the only model is memkernel's local embedding model.
The orchestrator stops at the first failing step: exit 0 when every check
passes, 1 when a check fails (one line names it), 2 when the script cannot run.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

# The decision under test: a neutral first line names the topic, because memkernel
# takes the page title from the first line and the slug from the title.
TOPIC = "Deploy window"
WRONG = "Deploy on Fridays after 17:00 UTC."
RIGHT = "Deploy on Tuesdays before noon; never on Fridays."
QUESTION = "When may we deploy?"

PROJECT_ID = "wiki-studio-correction-loop-demo"
CURATOR = "curator"
STATE_DIR_NAME = ".demo"
STATE_FILE_NAME = "state.json"
DRAFT_DIR_NAME = "correction"
STEPS = ("session-1", "curator", "session-2")


class CannotRunError(Exception):
    """The script cannot run: a missing package, the model, or a bad argument (exit 2)."""


class CheckFailedError(Exception):
    """A named check failed (exit 1)."""

    def __init__(self, name: str, detail: str = "") -> None:
        super().__init__(name)
        self.name = name
        self.detail = detail


def _check(checks: list[dict[str, Any]], name: str, ok: bool, detail: str = "") -> None:
    """Record one check and stop the step, naming it, when it is false."""
    checks.append({"name": name, "ok": bool(ok), "detail": detail})
    if not ok:
        raise CheckFailedError(name, detail)
    print(f"ok: {name}")


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tail(text: str, limit: int = 300) -> str:
    return " ".join(text.split())[-limit:]


def _state_path(workdir: Path) -> Path:
    return workdir / STATE_DIR_NAME / STATE_FILE_NAME


def _load_state(workdir: Path) -> dict[str, Any]:
    path = _state_path(workdir)
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(workdir: Path, step: str, values: dict[str, Any], checks: list[dict[str, Any]]) -> None:
    state = _load_state(workdir)
    state[step] = {"values": values, "checks": checks}
    path = _state_path(workdir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _wiki_studio_cli() -> str | None:
    """The ``wiki-studio`` console script beside the interpreter running this demo (FR-011)."""
    return shutil.which("wiki-studio", path=str(Path(sys.executable).parent))


def _step_env(workdir: Path) -> dict[str, str]:
    """The environment every step runs with: memkernel's settings point at ``workdir``."""
    env = os.environ.copy()
    for name in (
        "WIKI_STUDIO_WIKI_DIR",
        "WIKI_STUDIO_PROPOSALS_DIR",
        "WIKI_STUDIO_SEARCH_CACHE",
        "WIKI_STUDIO_SOURCE_ROOTS",
        "WIKI_STUDIO_ACTOR",
    ):
        env.pop(name, None)
    env["WIKI_STUDIO_ROOT"] = str(workdir)
    env["MEMKERNEL_PROJECT_ROOT"] = str(workdir)
    env["MEMKERNEL_PROJECT_ID"] = PROJECT_ID
    env["MEMKERNEL_CHROMA_PERSIST_PATH"] = str(workdir / ".memkernel" / "chroma")
    env["MEMKERNEL_WIKI_DIR"] = str(workdir / "knowledge" / "wiki")
    env["MEMKERNEL_WIKI_PROPOSALS_DIR"] = str(workdir / "doc_internal" / "proposals")
    return env


def _probe_embedding() -> None:
    """Load memkernel's embedding model once; an unavailable model is "cannot run", never a failed check."""
    model = os.environ.get("MEMKERNEL_EMBEDDING_MODEL", "")
    if model and (os.path.isabs(model) or os.sep in model) and not Path(model).is_dir():
        raise CannotRunError(f"the embedding model {model} is not a snapshot directory")
    try:
        from memkernel.config import MemKernelSettings
        from memkernel.retrieval.embeddings import SentenceTransformerEmbedding

        SentenceTransformerEmbedding(MemKernelSettings())
    except Exception as exc:  # the model may be absent, offline or at another revision
        raise CannotRunError(f"the embedding model could not be loaded: {exc}") from exc


def _probe() -> None:
    """Everything the three steps need before the first byte is written."""
    try:
        importlib.import_module("memkernel.wiki.sync")
        importlib.import_module("wiki_studio.api")
    except Exception as exc:
        raise CannotRunError(f"memkernel or wiki-studio is not importable: {exc}") from exc
    cli = _wiki_studio_cli()
    if cli is None:
        raise CannotRunError(f"the wiki-studio CLI is not beside the interpreter ({Path(sys.executable).parent})")
    _probe_embedding()


def _run_cli(arguments: list[str], workdir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(arguments, cwd=str(workdir), capture_output=True, text=True, check=False)


def _find_curator_receipt(workdir: Path) -> Path | None:
    """The newest committed receipt under ``.applied/`` that names the curator as its actor."""
    applied = workdir / "doc_internal" / "proposals" / ".applied"
    candidates: list[tuple[str, str, Path]] = []
    for path in applied.glob("*/receipt.json"):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        actor = receipt.get("actor")
        if receipt.get("state") == "committed" and isinstance(actor, dict) and actor.get("name") == CURATOR:
            candidates.append((str(receipt.get("committed_at") or ""), path.parent.name, path))
    return max(candidates)[2] if candidates else None


def _keyed(text: str, key: str) -> str:
    """The one frontmatter value for ``key``; empty when the page carries none or several."""
    values = [line.split(":", 1)[1].strip() for line in text.splitlines() if line.startswith(f"{key}:")]
    return values[0] if len(values) == 1 else ""


def _replace_line(lines: list[str], old: str, new: str) -> None:
    """Replace the one line equal to ``old``; anything but exactly one is a failed correction check."""
    hits = [index for index, line in enumerate(lines) if line == old]
    if len(hits) != 1:
        raise CheckFailedError("correction-drafted", f"expected one line {old!r}, found {len(hits)}")
    lines[hits[0]] = new


def _corrected_page(text: str, wrong_ref: str) -> str:
    """The curator's replacement: the rule in the title, the heading and the body, and ``corrects:``."""
    lines = text.splitlines()
    status = [index for index, line in enumerate(lines) if line == "status: draft"]
    if len(status) != 1:
        raise CheckFailedError("correction-drafted", f"expected one status line, found {len(status)}")
    lines[status[0] : status[0] + 1] = ["status: stable", f"corrects: {wrong_ref}"]
    _replace_line(lines, f"title: {TOPIC}", f"title: {RIGHT}")
    _replace_line(lines, f"# {TOPIC}", f"# {RIGHT}")
    _replace_line(lines, TOPIC, RIGHT)  # the Decision section repeats the memory's first line
    _replace_line(lines, WRONG, RIGHT)
    return "\n".join(lines) + "\n"


def _session_1(workdir: Path, checks: list[dict[str, Any]], values: dict[str, Any]) -> None:
    """Initialise the wiki, retain the wrong decision and export it as one draft through the gate."""
    from memkernel.core.models import MemoryType
    from memkernel.factory import build_service
    from memkernel.wiki.sync import WikiExporter

    from wiki_studio import api
    from wiki_studio.paths import WikiPaths

    paths = WikiPaths.resolve()
    api.init(paths)
    _check(
        checks,
        "wiki-initialised",
        (paths.wiki_dir / "index.md").is_file() and (paths.wiki_dir / "log.md").is_file(),
        str(paths.wiki_dir),
    )
    service = build_service()
    ref_id = service.retain(f"{TOPIC}\n\n{WRONG}", MemoryType.DECISION)
    _check(checks, "wrong-decision-retained", bool(ref_id), str(ref_id))
    recalled = [service.get(result.ref_id, touch=False) for result in service.recall(QUESTION)]
    _check(checks, "wrong-rule-current", any(m is not None and WRONG in m.content for m in recalled))
    report = WikiExporter(
        service,
        paths.wiki_dir,
        project_root=paths.root,
        proposals_dir=paths.proposals_dir,
    ).export()
    _check(checks, "export-gated", report.gated and report.gate_error is None, report.gate_error or "")
    _check(checks, "one-draft-page", len(report.written) == 1, ", ".join(report.written))
    _check(checks, "submission-digest-recorded", bool(report.submission_digest), str(report.submission_digest))
    page = report.written[0]
    page_text = api.read_page(page, paths).text
    _check(checks, "page-is-a-draft", "status: draft" in page_text.splitlines())
    _check(checks, "page-names-the-wrong-memory", f"memkernel_ref: {ref_id}" in page_text.splitlines(), ref_id)
    values.update({"page": page, "ref_id": ref_id, "submission_digest": report.submission_digest})
    print(f"ref_id: {ref_id}")
    print(f"page: {page}")
    print(f"submission_digest: {report.submission_digest}")


def _curator(workdir: Path, checks: list[dict[str, Any]], values: dict[str, Any]) -> None:
    """Read the draft, correct it, propose and promote it, approve it, and read the records back."""
    from wiki_studio import api
    from wiki_studio.paths import WikiPaths

    state = _load_state(workdir)
    if "session-1" not in state:
        raise CannotRunError("session-1 has not run in this --workdir")
    page = state["session-1"]["values"]["page"]
    cli = _wiki_studio_cli()
    if cli is None:
        raise CannotRunError(f"the wiki-studio CLI is not beside the interpreter ({Path(sys.executable).parent})")

    read = _run_cli([cli, "read", "--json", page], workdir)
    _check(checks, "read-json-exit-0", read.returncode == 0, _tail(read.stderr))
    payload = json.loads(read.stdout)
    wrong_ref = _keyed(payload["content"], "memkernel_ref")
    _check(checks, "page-names-the-wrong-memory", bool(wrong_ref), wrong_ref)
    _check(
        checks,
        "page-names-the-session-1-memory",
        wrong_ref == state["session-1"]["values"].get("ref_id"),
        wrong_ref,
    )
    corrected = _corrected_page(payload["content"], wrong_ref)
    lines = corrected.splitlines()
    _check(
        checks,
        "correction-drafted",
        "status: stable" in lines
        and f"corrects: {wrong_ref}" in lines
        and WRONG not in corrected
        and TOPIC not in corrected,
        wrong_ref,
    )
    _check(
        checks,
        "rule-replaced-in-title-heading-body",
        f"title: {RIGHT}" in lines and f"# {RIGHT}" in lines and lines.count(RIGHT) >= 2,
    )
    draft_dir = workdir / "drafts" / DRAFT_DIR_NAME
    draft = draft_dir / page
    draft.parent.mkdir(parents=True, exist_ok=True)
    draft.write_text(corrected, encoding="utf-8")
    (draft_dir / ".base.json").write_text(json.dumps({page: payload["sha256"]}), encoding="utf-8")

    propose = _run_cli(
        [cli, "propose", "--from", str(draft_dir.relative_to(workdir)), "--promote", "--by", CURATOR], workdir
    )
    _check(checks, "propose-and-promote-exit-0", propose.returncode == 0, _tail(propose.stderr or propose.stdout))
    approve = _run_cli([cli, "approve", page, "--by", CURATOR], workdir)
    _check(checks, "approve-exit-0", approve.returncode == 0, _tail(approve.stderr or approve.stdout))

    receipt_path = _find_curator_receipt(workdir)
    _check(checks, "receipt-archived", receipt_path is not None, str(workdir / "doc_internal" / "proposals"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path else {}
    actor = receipt.get("actor")
    _check(checks, "receipt-is-committed", receipt.get("state") == "committed", str(receipt.get("state")))
    _check(
        checks,
        "receipt-names-the-curator",
        isinstance(actor, dict) and actor.get("name") == CURATOR,
        str(actor),
    )
    _check(
        checks,
        "receipt-has-its-values",
        all(receipt.get(key) for key in ("proposal", "submission_digest", "started_at", "committed_at")),
    )

    paths = WikiPaths.resolve()
    review = api.review_state(paths, pages=[page])[0]
    _check(checks, "page-approved", review.state == "approved", f"{review.state}: {review.reason}")
    _check(checks, "approval-record-found", review.record_path is not None, str(review.record_path))
    record = json.loads((paths.wiki_dir / review.record_path).read_text(encoding="utf-8")) if review.record_path else {}
    approver = record.get("approver")
    _check(
        checks,
        "approval-record-names-the-curator",
        isinstance(approver, dict) and approver.get("name") == CURATOR,
        str(approver),
    )
    _check(checks, "approval-record-has-a-timestamp", bool(record.get("timestamp")), str(record.get("timestamp")))
    _check(
        checks,
        "approval-bound-to-the-page",
        record.get("sha256") == review.live_sha256 == review.approved_sha256,
    )

    print(
        "receipt: "
        f"proposal={receipt.get('proposal')} "
        f"submission_digest={receipt.get('submission_digest')} "
        f"actor={actor.get('name') if isinstance(actor, dict) else actor} "
        f"started_at={receipt.get('started_at')} "
        f"committed_at={receipt.get('committed_at')}"
    )
    print(
        f"approval: approver={approver.get('name') if isinstance(approver, dict) else approver} "
        f"timestamp={record.get('timestamp')}"
    )
    values.update(
        {
            "proposal": receipt.get("proposal"),
            "submission_digest": receipt.get("submission_digest"),
            "started_at": receipt.get("started_at"),
            "committed_at": receipt.get("committed_at"),
            "actor": actor.get("name") if isinstance(actor, dict) else actor,
            "approver": approver.get("name") if isinstance(approver, dict) else approver,
            "timestamp": record.get("timestamp"),
            "approved_sha256": review.approved_sha256,
        }
    )


def _session_2(workdir: Path, checks: list[dict[str, Any]], values: dict[str, Any]) -> None:
    """A new process on the same store: import the approved revision and recall the correction."""
    from memkernel.config import MemKernelSettings
    from memkernel.factory import build_service
    from memkernel.wiki.sync import WikiImporter

    from wiki_studio import api
    from wiki_studio.paths import WikiPaths

    settings = MemKernelSettings()
    service = build_service(settings)
    report = WikiImporter(
        service,
        Path(settings.wiki_dir),
        project_root=Path(settings.project_root),
    ).import_pages()
    _check(checks, "import-governed", report.governed, report.import_error or "")
    _check(checks, "one-page-imported", len(report.imported) == 1, ", ".join(report.imported))
    page = report.imported[0]
    corrections = [entry for entry in report.corrections if entry.get("page") == page]
    _check(checks, "correction-recorded", len(corrections) == 1, str(report.corrections))
    wrong_ref = corrections[0]["ref_id"] if corrections else ""

    recalled = [service.get(result.ref_id, touch=False) for result in service.recall(QUESTION)]
    corrected_recall_at = _utc_now()
    answers = [memory for memory in recalled if memory is not None and RIGHT in memory.content]
    _check(checks, "right-answer-current", bool(answers))
    answer = answers[0]  # check() has already stopped the step when the list is empty
    _check(checks, "answer-is-the-page", answer.source == page, answer.source)

    paths = WikiPaths.resolve()
    review = api.review_state(paths, pages=[page])[0]
    _check(checks, "page-approved", review.state == "approved", f"{review.state}: {review.reason}")
    _check(
        checks,
        "page-sha-beside-the-approved-sha",
        review.approved_sha256 is not None
        and f"page_sha:{review.approved_sha256}" in answer.tags
        and review.approved_sha256 == review.live_sha256,
        str(review.approved_sha256),
    )
    current = service.list_memories()
    _check(
        checks,
        "wrong-rule-not-current",
        not any(memory is not None and WRONG in memory.content for memory in recalled)
        and not any(WRONG in memory.content for memory in current),
    )
    old = [memory for memory in service.list_memories(include_superseded=True) if memory.ref_id == wrong_ref]
    _check(checks, "old-record-kept", len(old) == 1, str([memory.ref_id for memory in old]))
    superseded_by = old[0].superseded_by if old else None
    _check(
        checks,
        "old-record-superseded-by-the-page",
        bool(superseded_by) and superseded_by == answer.ref_id,
        str(superseded_by),
    )

    receipt_path = _find_curator_receipt(workdir)
    _check(checks, "receipt-archived", receipt_path is not None, str(workdir / "doc_internal" / "proposals"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path else {}
    _check(
        checks,
        "receipt-values-visible",
        bool(receipt.get("submission_digest")) and bool(receipt.get("committed_at")),
        str(receipt.get("proposal")),
    )
    _check(checks, "approval-record-found", review.record_path is not None, str(review.record_path))
    record = json.loads((paths.wiki_dir / review.record_path).read_text(encoding="utf-8")) if review.record_path else {}
    approver = record.get("approver")
    _check(
        checks,
        "approver-and-timestamp-visible",
        isinstance(approver, dict) and bool(approver.get("name")) and bool(record.get("timestamp")),
        str(approver),
    )

    print(f"answer: {answer.content}")
    print(f"page: {page}")
    print(f"page_sha: {review.approved_sha256}")
    print(f"approved_sha256: {review.approved_sha256} (equal)")
    print(f"submission_digest: {receipt.get('submission_digest')}")
    print(f"committed_at: {receipt.get('committed_at')}")
    print(f"approver: {approver.get('name') if isinstance(approver, dict) else approver}")
    print(f"timestamp: {record.get('timestamp')}")
    print(f"old record: {wrong_ref} superseded_by {superseded_by}")
    values.update(
        {
            "page": page,
            "page_sha": review.approved_sha256,
            "approved_sha256": review.approved_sha256,
            "submission_digest": receipt.get("submission_digest"),
            "committed_at": receipt.get("committed_at"),
            "approver": approver.get("name") if isinstance(approver, dict) else approver,
            "timestamp": record.get("timestamp"),
            "approval_completed_at": record.get("timestamp"),
            "corrected_recall_at": corrected_recall_at,
            "answer": answer.content,
            "wrong_ref_id": wrong_ref,
            "superseded_by": superseded_by,
        }
    )


_STEP_FUNCTIONS = {"session-1": _session_1, "curator": _curator, "session-2": _session_2}


def _run_step(step: str, workdir: Path) -> int:
    """Run one step: 0 on success, 1 with the failed check named, 2 when the script cannot run."""
    if not workdir.is_dir():
        raise CannotRunError(f"--workdir {workdir} does not exist")
    checks: list[dict[str, Any]] = []
    values: dict[str, Any] = {}
    try:
        _STEP_FUNCTIONS[step](workdir, checks, values)
    except CheckFailedError as exc:
        print(f"FAILED: {step}: {exc.name}" + (f" ({exc.detail})" if exc.detail else ""))
        return 1
    except CannotRunError:
        raise
    except Exception as exc:  # an unexpected failure is "cannot run", never a named check
        print(f"cannot run: {step} raised {type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 2
    _save_state(workdir, step, values, checks)
    return 0


def _version(module_name: str) -> str:
    module = importlib.import_module(module_name)
    return str(getattr(module, "__version__", "unknown"))


def _write_summary(workdir: Path, summary: Path) -> None:
    state = _load_state(workdir)
    values = state.get("session-2", {}).get("values", {})
    checks = [{"step": step, **item} for step in STEPS for item in state.get(step, {}).get("checks", [])]
    document = {
        "demo": "correction-loop",
        "wiki_studio_version": _version("wiki_studio"),
        "memkernel_version": _version("memkernel"),
        "python_version": platform.python_version(),
        "page": values.get("page"),
        "page_sha": values.get("page_sha"),
        "approved_sha256": values.get("approved_sha256"),
        "submission_digest": values.get("submission_digest"),
        "committed_at": values.get("committed_at"),
        "approver": values.get("approver"),
        "timestamp": values.get("timestamp"),
        "approval_completed_at": values.get("approval_completed_at"),
        "corrected_recall_at": values.get("corrected_recall_at"),
        "checks": checks,
    }
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def _orchestrate(workdir: Path, summary: Path | None) -> int:
    """Run session-1, curator and session-2 in order and stop at the first failing step."""
    if workdir.exists() and not workdir.is_dir():
        raise CannotRunError(f"--workdir {workdir} is not a directory")
    if workdir.is_dir() and any(workdir.iterdir()):
        raise CannotRunError(f"--workdir {workdir} is not empty; a run starts in an empty directory")
    _probe()
    workdir.mkdir(parents=True, exist_ok=True)
    env = _step_env(workdir)
    script = Path(__file__).resolve()
    for step in STEPS:
        print(f"demo: running {step}", flush=True)
        completed = subprocess.run(
            [sys.executable, str(script), step, "--workdir", str(workdir)],
            cwd=str(workdir),
            env=env,
            check=False,
        )
        if completed.returncode != 0:
            if completed.returncode == 2:
                print(f"demo: {step} could not run", file=sys.stderr)
                return 2
            print(f"demo: {step} failed (exit {completed.returncode})", file=sys.stderr)
            return 1
    if summary is not None:
        _write_summary(workdir, summary)
    print("demo: every check passed")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="demo.py", description=__doc__.splitlines()[0])
    parser.add_argument("step", nargs="?", choices=STEPS, help="one step; omit to run all three")
    parser.add_argument("--workdir", type=Path, required=True, help="the project directory the run writes into")
    parser.add_argument("--summary", type=Path, help="the orchestrator writes one JSON summary here")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    workdir = args.workdir.expanduser().absolute()
    try:
        if args.step is None:
            return _orchestrate(workdir, args.summary)
        if args.summary is not None:
            raise CannotRunError("--summary belongs to the orchestrator, not to one step")
        return _run_step(args.step, workdir)
    except CannotRunError as exc:
        print(f"cannot run: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
