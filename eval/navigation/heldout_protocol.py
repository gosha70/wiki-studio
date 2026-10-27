# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The held-out set of the discovery evaluation, as ``heldout/protocol.md`` states (0.8.0, FR-022..FR-030).

``heldout/manifest.json`` carries ``state`` through ``sources`` → ``questions``
→ ``pinned`` → ``ingested`` → ``wiki-frozen`` → ``frozen`` → ``run`` with a
timestamp per transition. Each subcommand runs in one state only and refuses
any other (exit 1, naming the expected state), so the preregistered order is
enforced by the tool, not only by the document:

    python -m eval.navigation.heldout_protocol questions --commit SHA   # sources → questions
    python -m eval.navigation.heldout_protocol pin --model FULL-NAME    # questions → pinned
    python -m eval.navigation.heldout_protocol probe                    # pinned (must pass; may be re-run)
    python -m eval.navigation.heldout_protocol ingest                   # pinned → ingested (once, no retries)
    python -m eval.navigation.heldout_protocol freeze-wiki              # ingested → wiki-frozen
    python -m eval.navigation.heldout_protocol freeze                   # wiki-frozen → frozen

The last transition, ``frozen`` → ``run``, belongs to the one held-out run of
``eval.navigation.discovery``. Nothing here commits; the owner commits after
each step. Run 2's helpers are reused and ``run2_protocol.py`` is not edited.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from eval.navigation.run2_protocol import (
    BACKEND_TIMEOUT_SECONDS,
    ENV_KEYS,
    PROBE_PROMPT,
    REPO_ROOT,
    _env_record,
    _git,
    _now,
    _pytest_processes,
    _run_env,
    _sha256,
    _tree_hash,
    _version,
)
from wiki_studio.discovery import _NEVER_CANDIDATES, LoadedPage, _read_eligible
from wiki_studio.querier import _extract_index_links

HELDOUT_DIR = Path(__file__).resolve().parent / "heldout"
MANIFEST_NAME = "manifest.json"
QUESTIONS_NAME = "questions.json"
GOLD_NAME = "gold.json"
CORPUS_DIR = "corpus"
WIKI_DIR = "wiki"
PROPOSALS_DIR = "proposals"
LOGS_DIR = "ingest-logs"
APPLIED_DIR = ".applied"
INDEX_NAME = "index.md"
SET_HELDOUT = "heldout"

STATE_SOURCES = "sources"
STATE_QUESTIONS = "questions"
STATE_PINNED = "pinned"
STATE_INGESTED = "ingested"
STATE_WIKI_FROZEN = "wiki-frozen"
STATE_FROZEN = "frozen"
STATE_RUN = "run"
STATES: tuple[str, ...] = (
    STATE_SOURCES,
    STATE_QUESTIONS,
    STATE_PINNED,
    STATE_INGESTED,
    STATE_WIKI_FROZEN,
    STATE_FROZEN,
    STATE_RUN,
)

# The question set's floor (FR-023).
KIND_SINGLE = "single"
KIND_COMPETING = "competing"
KIND_ABSENT = "absent"
KINDS: tuple[str, ...] = (KIND_SINGLE, KIND_COMPETING, KIND_ABSENT)
MIN_ANSWERABLE = 35
MIN_COMPETING = 6
MIN_ABSENT = 6

BACKEND = "claude"
ENV_MODEL = "ANTHROPIC_MODEL"
ENV_ISOLATION_HOOK_SKIP = "HOOK_SKIP"
ENV_ISOLATION_CONFIG_DIR = "CLAUDE_CONFIG_DIR"

# One ingest attempt per document; how it ended (FR-025).
DISPOSITION_PROMOTED = "promoted"
DISPOSITION_REJECTED = "rejected"
DISPOSITION_BACKEND_ERROR = "backend_error"
DISPOSITION_TIMEOUT = "timeout"
EXIT_BACKEND_NOT_FOUND = 2
EXIT_BACKEND_FAILED = 3
TIMEOUT_MARKER = "timed out"
GATE_REJECTED_MARKER = "gate rejected"


class ProtocolError(Exception):
    """A step refused: out of order, or an input differs from what the manifest recorded."""


# ── The manifest and its states ───────────────────────────────


def load_manifest(heldout_dir: Path = HELDOUT_DIR) -> dict[str, Any]:
    path = heldout_dir / MANIFEST_NAME
    if not path.is_file():
        raise ProtocolError(f"{path} not found; the held-out set starts from its sources manifest (FR-022)")
    manifest: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return manifest


def save_manifest(heldout_dir: Path, manifest: dict[str, Any]) -> None:
    (heldout_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def require_state(manifest: dict[str, Any], expected: str, step: str) -> None:
    """Refuse ``step`` unless the manifest is in ``expected`` (FR-030)."""
    actual = manifest.get("state")
    if actual != expected:
        raise ProtocolError(
            f"{step}: refusing to run out of order; expected state {expected!r}, the manifest is in {actual!r}"
        )


def advance(manifest: dict[str, Any], state: str) -> None:
    """Move to ``state`` and timestamp the transition."""
    manifest["state"] = state
    manifest.setdefault("history", []).append({"state": state, "at": _now()})


def _verify_corpus(heldout_dir: Path, manifest: dict[str, Any]) -> None:
    drifted = [
        entry["path"]
        for entry in manifest["corpus_files"]
        if _sha256(heldout_dir / CORPUS_DIR / entry["corpus_file"]) != entry["sha256"]
    ]
    if drifted:
        raise ProtocolError(f"corpus files differ from the manifest: {', '.join(drifted)}")


def _verify_file(heldout_dir: Path, manifest: dict[str, Any], name: str, key: str) -> None:
    path = heldout_dir / name
    if not path.is_file():
        raise ProtocolError(f"{path} not found")
    if _sha256(path) != manifest.get(key):
        raise ProtocolError(f"{name}'s sha256 differs from the manifest's {key}; it was edited after it was recorded")


def verify_frozen(heldout_dir: Path, manifest: dict[str, Any]) -> None:
    """The questions, the gold and the wiki tree still hash to what ``freeze`` recorded (FR-027)."""
    _verify_file(heldout_dir, manifest, QUESTIONS_NAME, "questions_sha256")
    _verify_file(heldout_dir, manifest, GOLD_NAME, "gold_sha256")
    if _tree_hash(heldout_dir / WIKI_DIR) != manifest.get("wiki_tree_sha256"):
        raise ProtocolError("the held-out wiki differs from the tree hash frozen in the manifest")


def read_eligible_pages(wiki_dir: Path) -> dict[str, LoadedPage]:
    """The pages either ranker may select, in index order: index-linked, regular, UTF-8, not superseded (FR-004)."""
    index_md = (wiki_dir / INDEX_NAME).read_text(encoding="utf-8")
    pages: dict[str, LoadedPage] = {}
    for rel in _extract_index_links(index_md, wiki_dir):
        if posixpath.normpath(rel) in _NEVER_CANDIDATES:
            continue
        read = _read_eligible(wiki_dir, rel)
        if isinstance(read, LoadedPage):
            pages[rel] = read
    return pages


# ── questions ─────────────────────────────────────────────────


def validate_questions(questions: Any) -> None:
    """``questions.json``'s shape and FR-023's floor: ≥35 answerable (≥6 competing) and ≥6 absent."""
    if not isinstance(questions, list) or not all(isinstance(q, dict) for q in questions):
        raise ProtocolError("questions.json must be a list of objects")
    ids = [q.get("id") for q in questions]
    if len(set(ids)) != len(ids) or not all(isinstance(i, str) and i for i in ids):
        raise ProtocolError("every question needs a unique, non-empty id")
    bad = [q["id"] for q in questions if q.get("kind") not in KINDS or not str(q.get("question", "")).strip()]
    if bad:
        raise ProtocolError(f"questions with an unknown kind or no text: {', '.join(bad)}")
    kinds = [q["kind"] for q in questions]
    answerable = kinds.count(KIND_SINGLE) + kinds.count(KIND_COMPETING)
    if (
        answerable < MIN_ANSWERABLE
        or kinds.count(KIND_COMPETING) < MIN_COMPETING
        or kinds.count(KIND_ABSENT) < MIN_ABSENT
    ):
        raise ProtocolError(
            f"the set needs at least {MIN_ANSWERABLE} answerable questions ({MIN_COMPETING} competing) and "
            f"{MIN_ABSENT} absent; it has {answerable} ({kinds.count(KIND_COMPETING)} competing) and "
            f"{kinds.count(KIND_ABSENT)} absent"
        )


def _committed_bytes(commit: str, path: Path) -> bytes:
    """The file's bytes at ``commit`` (``git show``); raises ``ProtocolError`` when it is not committed there."""
    rel = path.resolve().relative_to(REPO_ROOT).as_posix()
    proc = subprocess.run(["git", "show", f"{commit}:{rel}"], cwd=REPO_ROOT, capture_output=True)
    if proc.returncode != 0:
        raise ProtocolError(f"{rel} is not committed at {commit}: {proc.stderr.decode(errors='replace').strip()}")
    return proc.stdout


def step_questions(heldout_dir: Path, commit: str) -> str:
    """Record the committed questions before the ingest (FR-023): ``sources`` → ``questions``."""
    manifest = load_manifest(heldout_dir)
    require_state(manifest, STATE_SOURCES, "questions")
    path = heldout_dir / QUESTIONS_NAME
    if not path.is_file():
        raise ProtocolError(f"{path} not found; the questions are written and committed first")
    validate_questions(json.loads(path.read_text(encoding="utf-8")))
    sha = _git("rev-parse", commit)  # resolved once: the bytes checked are the commit recorded
    committed = hashlib.sha256(_committed_bytes(sha, path)).hexdigest()
    on_disk = _sha256(path)
    if committed != on_disk:
        raise ProtocolError(f"questions.json differs from its committed version at {commit}; commit it first")
    manifest["questions_sha256"] = on_disk
    manifest["questions_commit"] = sha
    advance(manifest, STATE_QUESTIONS)
    save_manifest(heldout_dir, manifest)
    return f"questions: recorded {on_disk[:12]} at {manifest['questions_commit'][:12]}"


# ── pin ───────────────────────────────────────────────────────


def _heldout_env(heldout_dir: Path, model: str | None) -> dict[str, str]:
    env = _run_env(heldout_dir)
    if model:
        env[ENV_MODEL] = model
    return env


def step_pin(heldout_dir: Path, model: str | None, claude_binary: str) -> str:
    """Pin versions, backend, model, timeout and environment before the first attempt (FR-024)."""
    manifest = load_manifest(heldout_dir)
    require_state(manifest, STATE_QUESTIONS, "pin")
    _verify_corpus(heldout_dir, manifest)
    _verify_file(heldout_dir, manifest, QUESTIONS_NAME, "questions_sha256")
    model = model or os.environ.get(ENV_MODEL)
    if not model:
        raise ProtocolError(f"pin: name the model by its full name (--model or {ENV_MODEL})")
    env = _heldout_env(heldout_dir, model)
    manifest["pins"] = {
        "wiki_studio_commit": _git("rev-parse", "HEAD"),
        "wiki_studio_version": _version([sys.executable, "-m", "wiki_studio", "--version"]),
        "backend": BACKEND,
        "model": model,
        "claude_code_version": _version([claude_binary, "--version"]),
        "backend_timeout_seconds": BACKEND_TIMEOUT_SECONDS,
        "env": _env_record(env),
        "env_keys": list(ENV_KEYS),
    }
    advance(manifest, STATE_PINNED)
    save_manifest(heldout_dir, manifest)
    return f"pin: {BACKEND} / {model}"


# ── probe ─────────────────────────────────────────────────────


def step_probe(heldout_dir: Path, claude_binary: str) -> bool:
    """Run 2's isolation probe: one trivial call that must change nothing under the held-out set (FR-024)."""
    manifest = load_manifest(heldout_dir)
    require_state(manifest, STATE_PINNED, "probe")
    if manifest.get("ingest"):
        raise ProtocolError("probe: the ingest has started; nothing is re-run after the first attempt (FR-024)")
    env = _heldout_env(heldout_dir, manifest["pins"]["model"])
    if env.get(ENV_ISOLATION_HOOK_SKIP) != "1" and not env.get(ENV_ISOLATION_CONFIG_DIR):
        raise ProtocolError(f"probe: set {ENV_ISOLATION_HOOK_SKIP}=1 or {ENV_ISOLATION_CONFIG_DIR} first")
    watched = {
        "audit_log": heldout_dir / WIKI_DIR / ".audit",
        "query_log": heldout_dir / "doc_internal",
        "proposals": heldout_dir / PROPOSALS_DIR,
        "wiki": heldout_dir / WIKI_DIR,
        "corpus": heldout_dir / CORPUS_DIR,
        "heldout_set": heldout_dir,  # everything else beside them: questions.json, gold.json, the manifest
    }
    before = {name: _tree_hash(path) for name, path in watched.items()}
    command = [claude_binary, "-p", PROBE_PROMPT]
    started = _now()
    proc = subprocess.Popen(
        command, env=env, cwd=heldout_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    hook_pytest: list[str] = []
    unrelated_pytest: list[str] = []
    while proc.poll() is None:
        for pid, cmd, under_probe in _pytest_processes(proc.pid):
            line = f"{pid} {cmd}"
            target = hook_pytest if under_probe else unrelated_pytest
            if line not in target:
                target.append(line)
        time.sleep(0.5)
    stdout, stderr = proc.communicate()
    after = {name: _tree_hash(path) for name, path in watched.items()}
    unchanged = before == after
    passed = unchanged and not hook_pytest and proc.returncode == 0
    record = {
        "started_at": started,
        "finished_at": _now(),
        "command": command,
        "env": _env_record(env),
        "exit_code": proc.returncode,
        "stdout": stdout.strip()[:500],
        "stderr": stderr.strip()[:500],
        "hashes_before": before,
        "hashes_after": after,
        "unchanged": unchanged,
        "pytest_seen": bool(hook_pytest),
        "pytest_under_probe": hook_pytest,
        "pytest_unrelated": unrelated_pytest,
        "passed": passed,
    }
    manifest.setdefault("probes", []).append(record)
    manifest["isolation_probe"] = record
    save_manifest(heldout_dir, manifest)
    return passed


# ── ingest ────────────────────────────────────────────────────


def _run_logged(cmd: list[str], env: dict[str, str], log_prefix: Path) -> tuple[int, float, str, str]:
    start = time.monotonic()
    proc = subprocess.run(cmd, env=env, cwd=REPO_ROOT, capture_output=True, text=True)
    wall = round(time.monotonic() - start, 3)
    log_prefix.with_name(log_prefix.name + ".stdout.txt").write_text(proc.stdout, encoding="utf-8")
    log_prefix.with_name(log_prefix.name + ".stderr.txt").write_text(proc.stderr, encoding="utf-8")
    return proc.returncode, wall, proc.stdout, proc.stderr


def _proposal_dirs(proposals: Path) -> set[str]:
    if not proposals.is_dir():
        return set()
    return {p.name for p in proposals.iterdir() if p.is_dir() and p.name != APPLIED_DIR}


def _ingest_one(heldout_dir: Path, number: int, entry: dict[str, Any], env: dict[str, str]) -> dict[str, Any]:
    """One attempt, then ``promote`` when the gate accepted it; never a retry (FR-025)."""
    proposals = heldout_dir / PROPOSALS_DIR
    logs = heldout_dir / LOGS_DIR
    source = heldout_dir / CORPUS_DIR / entry["corpus_file"]
    before = _proposal_dirs(proposals)
    code, wall, out, err = _run_logged(
        [sys.executable, "-m", "wiki_studio", "ingest", str(source), "--backend", BACKEND],
        env,
        logs / f"{number:02d}-ingest",
    )
    written = sorted(_proposal_dirs(proposals) - before)
    doc: dict[str, Any] = {
        "path": entry["path"],
        "attempts": 1,
        "ingest_exit_code": code,
        # Not a measurement: one per attempt that reached the backend, whether or not it made a call.
        "model_calls_upper_bound": 0 if code == EXIT_BACKEND_NOT_FOUND else 1,
        "proposal_dir": written[0] if written else None,
        "promote_exit_code": None,
        "pages_written": [],
        "wall_seconds": wall,
    }
    if code == EXIT_BACKEND_FAILED and TIMEOUT_MARKER in err:
        doc["disposition"] = DISPOSITION_TIMEOUT
    elif code in (EXIT_BACKEND_NOT_FOUND, EXIT_BACKEND_FAILED):
        doc["disposition"] = DISPOSITION_BACKEND_ERROR
    elif code != 0 or not written or GATE_REJECTED_MARKER in out:
        doc["disposition"] = DISPOSITION_REJECTED
    else:
        pcode, pwall, _out, _err = _run_logged(
            [sys.executable, "-m", "wiki_studio", "promote", str(proposals / written[0])],
            env,
            logs / f"{number:02d}-promote",
        )
        doc["wall_seconds"] = round(wall + pwall, 3)
        doc["promote_exit_code"] = pcode
        if pcode == 0:
            plan = json.loads((proposals / APPLIED_DIR / written[0] / "plan.json").read_text(encoding="utf-8"))
            doc["pages_written"] = [e["path"] for e in plan["edits"]]
            doc["disposition"] = DISPOSITION_PROMOTED
        else:
            doc["disposition"] = DISPOSITION_REJECTED
    return doc


def step_ingest(heldout_dir: Path) -> str:
    """``init`` a fresh wiki and ingest every document once, in manifest order (FR-025): ``pinned`` → ``ingested``."""
    manifest = load_manifest(heldout_dir)
    require_state(manifest, STATE_PINNED, "ingest")
    if not (manifest.get("isolation_probe") or {}).get("passed"):
        raise ProtocolError("ingest: no passed isolation probe in the manifest; run `probe` first")
    if manifest.get("ingest"):
        raise ProtocolError("ingest: an ingest is already recorded; it is never repeated (FR-025)")
    if (heldout_dir / WIKI_DIR).exists():
        raise ProtocolError("ingest: heldout/wiki/ already exists; the ingest starts from a fresh `init`")
    _verify_corpus(heldout_dir, manifest)
    _verify_file(heldout_dir, manifest, QUESTIONS_NAME, "questions_sha256")
    env = _heldout_env(heldout_dir, manifest["pins"]["model"])
    (heldout_dir / LOGS_DIR).mkdir(exist_ok=True)
    init_code, _wall, _out, init_err = _run_logged(
        [sys.executable, "-m", "wiki_studio", "init"], env, heldout_dir / LOGS_DIR / "00-init"
    )
    if init_code != 0:
        raise ProtocolError(f"ingest: `init` failed (exit {init_code}): {init_err.strip()[-300:]}")
    record: dict[str, Any] = {"started_at": _now(), "documents": []}
    manifest["ingest"] = record
    save_manifest(heldout_dir, manifest)  # recorded before the first attempt: from here nothing is re-run
    for number, entry in enumerate(manifest["corpus_files"], start=1):
        doc = _ingest_one(heldout_dir, number, entry, env)
        record["documents"].append(doc)
        save_manifest(heldout_dir, manifest)
        print(f"{number:02d} {entry['path']}: {doc['disposition']} ({doc['wall_seconds']}s)")
    lcode, _wall, lout, lerr = _run_logged(
        [sys.executable, "-m", "wiki_studio", "lint"], env, heldout_dir / LOGS_DIR / "lint"
    )
    documents = record["documents"]
    record["lint"] = {"exit_code": lcode, "stdout": lout, "stderr": lerr}
    record["completed_at"] = _now()
    record["summary"] = {
        "documents_ingested": len(documents),
        "promoted": sum(d["disposition"] == DISPOSITION_PROMOTED for d in documents),
        "rejected": sum(d["disposition"] == DISPOSITION_REJECTED for d in documents),
        "backend_error": sum(d["disposition"] == DISPOSITION_BACKEND_ERROR for d in documents),
        "timeout": sum(d["disposition"] == DISPOSITION_TIMEOUT for d in documents),
        "model_calls_upper_bound": sum(d["model_calls_upper_bound"] for d in documents),
        "total_wall_seconds": round(sum(d["wall_seconds"] for d in documents), 3),
        "lint_clean": lcode == 0,
    }
    advance(manifest, STATE_INGESTED)
    save_manifest(heldout_dir, manifest)
    return f"ingest: done; {record['summary']}"


# ── freeze-wiki and freeze ────────────────────────────────────


def step_freeze_wiki(heldout_dir: Path) -> str:
    """Record the wiki's and the archived proposals' tree hashes (FR-026): ``ingested`` → ``wiki-frozen``."""
    manifest = load_manifest(heldout_dir)
    require_state(manifest, STATE_INGESTED, "freeze-wiki")
    manifest["wiki_tree_sha256"] = _tree_hash(heldout_dir / WIKI_DIR)
    manifest["proposals_tree_sha256"] = _tree_hash(heldout_dir / PROPOSALS_DIR)
    manifest["ingest_summary"] = manifest["ingest"]["summary"]
    advance(manifest, STATE_WIKI_FROZEN)
    save_manifest(heldout_dir, manifest)
    return f"freeze-wiki: {manifest['wiki_tree_sha256'][:12]}"


def validate_gold(questions: list[dict[str, Any]], gold: Any, wiki_dir: Path) -> None:
    """One entry per question with a reason; absent questions have no gold; every gold page exists (FR-027)."""
    if not isinstance(gold, list) or not all(isinstance(g, dict) for g in gold):
        raise ProtocolError("gold.json must be a list of objects")
    by_id = {g.get("id"): g for g in gold}
    if set(by_id) != {q["id"] for q in questions} or len(by_id) != len(gold):
        raise ProtocolError("gold.json needs exactly one entry per question")
    for q in questions:
        entry = by_id[q["id"]]
        target = entry.get("gold")
        if not str(entry.get("reason", "")).strip():
            raise ProtocolError(f"gold for {q['id']} has no reason")
        if not isinstance(entry.get("distractors", []), list):
            raise ProtocolError(f"gold for {q['id']}: distractors must be a list")
        if q["kind"] == KIND_ABSENT and target is not None:
            raise ProtocolError(f"{q['id']} is absent; its gold must be null")
        if target is not None and not (
            isinstance(target, str)
            and (wiki_dir / target).resolve().is_relative_to(wiki_dir.resolve())
            and (wiki_dir / target).is_file()
        ):
            raise ProtocolError(f"gold for {q['id']} names no page of the frozen wiki: {target!r}")


def step_freeze(heldout_dir: Path) -> str:
    """Freeze questions, gold and wiki before tuning starts (FR-027): ``wiki-frozen`` → ``frozen``."""
    manifest = load_manifest(heldout_dir)
    require_state(manifest, STATE_WIKI_FROZEN, "freeze")
    _verify_file(heldout_dir, manifest, QUESTIONS_NAME, "questions_sha256")
    wiki_dir = heldout_dir / WIKI_DIR
    if _tree_hash(wiki_dir) != manifest.get("wiki_tree_sha256"):
        raise ProtocolError("freeze: the wiki changed after freeze-wiki; it is never edited")
    gold_path = heldout_dir / GOLD_NAME
    if not gold_path.is_file():
        raise ProtocolError(f"{gold_path} not found; assign gold from the frozen wiki first")
    questions = json.loads((heldout_dir / QUESTIONS_NAME).read_text(encoding="utf-8"))
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    validate_gold(questions, gold, wiki_dir)
    manifest["gold_sha256"] = _sha256(gold_path)
    manifest["gold_questions"] = sum(g["gold"] not in (None, INDEX_NAME) for g in gold)
    manifest["eligible_pages"] = len(read_eligible_pages(wiki_dir))
    advance(manifest, STATE_FROZEN)
    save_manifest(heldout_dir, manifest)
    return f"freeze: gold_questions={manifest['gold_questions']} eligible_pages={manifest['eligible_pages']}"


# ── CLI ───────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.navigation.heldout_protocol", description=__doc__)
    parser.add_argument("--heldout-dir", type=Path, default=HELDOUT_DIR, help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="step", required=True)
    p_questions = sub.add_parser("questions", help="Record the committed questions (sources → questions).")
    p_questions.add_argument("--commit", default="HEAD", help="The commit that holds questions.json.")
    p_pin = sub.add_parser("pin", help="Pin versions, backend and model (questions → pinned).")
    p_pin.add_argument("--model", default=None, help=f"The model by its full name (default: ${ENV_MODEL}).")
    p_pin.add_argument("--claude", default=BACKEND, help="The Claude Code binary.")
    p_probe = sub.add_parser("probe", help="The isolation probe (in pinned; must pass).")
    p_probe.add_argument("--claude", default=BACKEND, help="The Claude Code binary.")
    sub.add_parser("ingest", help="The one ingest (pinned → ingested).")
    sub.add_parser("freeze-wiki", help="Hash the ingested wiki (ingested → wiki-frozen).")
    sub.add_parser("freeze", help="Freeze questions, gold and wiki (wiki-frozen → frozen).")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    heldout_dir: Path = args.heldout_dir
    try:
        if args.step == "questions":
            message = step_questions(heldout_dir, args.commit)
        elif args.step == "pin":
            message = step_pin(heldout_dir, args.model, args.claude)
        elif args.step == "probe":
            passed = step_probe(heldout_dir, args.claude)
            print(f"probe: {'PASSED' if passed else 'FAILED'}")
            if not passed:
                print("probe: fix the isolation and run the probe again; no attempt was consumed", file=sys.stderr)
            return 0 if passed else 1
        elif args.step == "ingest":
            message = step_ingest(heldout_dir)
        elif args.step == "freeze-wiki":
            message = step_freeze_wiki(heldout_dir)
        else:
            message = step_freeze(heldout_dir)
    except ProtocolError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
