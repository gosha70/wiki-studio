# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Run 2 of the navigation evaluation, as the protocol in specs/wiki-studio-0-3-0 (US5, FR-013..FR-016) states.

Two steps, run from the repository root by the owner, in this order:

    python -m eval.navigation.run2_protocol probe     # verifies hook isolation; consumes no attempt
    python -m eval.navigation.run2_protocol ingest    # pinned one-time ingest, one attempt per document

``probe`` requires an isolation method in the environment (``HOOK_SKIP=1``
honoured by the user's Stop hook, or ``CLAUDE_CONFIG_DIR``) and records the
probe in ``run2/manifest.json``. ``ingest`` refuses to run without a passed
probe, pins commit, versions, model and settings before the first attempt,
runs every corpus document once in run 1's order (one retry only when the
backend returned nothing), promotes each proposal once, writes per-document
logs, lints the frozen wiki and records everything. Nothing is edited by hand
and nothing is regenerated: a second ``ingest`` on a recorded run is refused.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SHARED_DIR = Path(__file__).resolve().parent  # eval/navigation (run 1: corpus, questions, stop list)
REPO_ROOT = SHARED_DIR.parents[1]
DEFAULT_RUN_DIR = SHARED_DIR / "run2"
FIX_MERGE_COMMIT = "4d224df"  # the issue #11 fix; run 2 must run from a descendant
BACKEND_TIMEOUT_SECONDS = 120
PROBE_PROMPT = "Reply with the single word OK."
RETRY_EXIT_CODES = (2, 3)  # backend not found / backend failed: a retry is allowed only if nothing was written
ENV_KEYS = (
    "HOOK_SKIP",
    "CLAUDE_CONFIG_DIR",
    "ANTHROPIC_MODEL",
    "WIKI_STUDIO_ROOT",
    "WIKI_STUDIO_WIKI_DIR",
    "WIKI_STUDIO_PROPOSALS_DIR",
)

INDEX_MD = (
    "---\npage_type: index\nslug: index\ntitle: Navigation evaluation index\nstatus: stable\n"
    "last_reviewed: {date}\n---\n\n# Navigation evaluation index\n"
)
LOG_MD = (
    "---\npage_type: log\nslug: log\ntitle: Navigation evaluation log\nstatus: stable\n"
    "last_reviewed: {date}\n---\n\n# Navigation evaluation log\n"
)


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_hash(root: Path) -> str:
    """One hash over every file (path and bytes) below ``root``; '' when absent."""
    if not root.exists():
        return ""
    digest = hashlib.sha256()
    for file in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(file.relative_to(root).as_posix().encode())
        digest.update(file.read_bytes())
    return digest.hexdigest()


def _run_env(run_dir: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["WIKI_STUDIO_ROOT"] = str(run_dir)
    env["WIKI_STUDIO_WIKI_DIR"] = str(run_dir / "wiki")
    env["WIKI_STUDIO_PROPOSALS_DIR"] = str(run_dir / "proposals")
    return env


def _env_record(env: dict[str, str]) -> dict[str, str | None]:
    return {key: env.get(key) for key in ENV_KEYS}


def _load_manifest(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _save_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True).stdout.strip()


def _version(cmd: list[str]) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return (out.stdout or out.stderr).strip().splitlines()[-1] if (out.stdout or out.stderr).strip() else ""
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"unavailable: {exc}"


def _settings_model() -> str | None:
    """The model Claude Code's user settings pin, if any (what an unset ANTHROPIC_MODEL falls back to)."""
    settings = Path.home() / ".claude" / "settings.json"
    if not settings.is_file():
        return None
    try:
        value = json.loads(settings.read_text(encoding="utf-8")).get("model")
    except (OSError, json.JSONDecodeError):
        return None
    return str(value) if value else None


def _commit_run(run_dir: Path, message: str) -> str:
    """Commit everything under ``run_dir`` as produced; returns the short SHA."""
    subprocess.run(["git", "add", "--", str(run_dir)], cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=REPO_ROOT, check=True)
    return _git("rev-parse", "--short", "HEAD")


def _fresh_wiki(run_dir: Path) -> None:
    wiki = run_dir / "wiki"
    wiki.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    if not (wiki / "index.md").exists():
        (wiki / "index.md").write_text(INDEX_MD.format(date=today), encoding="utf-8")
    if not (wiki / "log.md").exists():
        (wiki / "log.md").write_text(LOG_MD.format(date=today), encoding="utf-8")
    (run_dir / "proposals").mkdir(exist_ok=True)
    (run_dir / "ingest-logs").mkdir(exist_ok=True)


def _shared_record() -> dict[str, Any]:
    run1 = json.loads((SHARED_DIR / "manifest.json").read_text(encoding="utf-8"))
    return {
        "shared_from": "eval/navigation (run 1's corpus, questions and stop list, used in place)",
        "corpus_repo": run1["corpus_repo"],
        "corpus_tag": run1["corpus_tag"],
        "corpus_commit": run1["corpus_commit"],
        "corpus_files": run1["corpus_files"],
        "questions_commit": run1["questions_commit"],
        "questions_sha256": _sha256(SHARED_DIR / "questions.json"),
        "stopwords_sha256": _sha256(SHARED_DIR / "stopwords.txt"),
    }


def _pytest_processes(probe_pid: int) -> list[tuple[int, str, bool]]:
    """Every running pytest as ``(pid, command, started under the probe call)``.

    A pytest whose parent chain reaches the probe's process was started by a hook
    inside that call; any other pytest (another session's hook, a developer's
    shell) is unrelated to this measurement and only recorded. The chain is read
    from one ``ps`` snapshot, so a hook child whose intermediate shell has already
    exited (and was reparented) can be misclassified as unrelated; the byte
    comparison of the fixture is the decisive check, this watch is the second.
    """
    ps = subprocess.run(["ps", "-axo", "pid=,ppid=,command="], capture_output=True, text=True)
    parent: dict[int, int] = {}
    commands: dict[int, str] = {}
    for line in ps.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 2:
            continue
        pid, ppid = int(parts[0]), int(parts[1])
        parent[pid] = ppid
        commands[pid] = parts[2] if len(parts) == 3 else ""
    found: list[tuple[int, str, bool]] = []
    for pid, cmd in commands.items():
        if "pytest" not in cmd:
            continue
        ancestor, hops, under = pid, 0, False
        while ancestor in parent and hops < 64:
            if ancestor == probe_pid:
                under = True
                break
            ancestor, hops = parent[ancestor], hops + 1
        found.append((pid, cmd, under))
    return found


# ── probe ─────────────────────────────────────────────────────


def probe(run_dir: Path, claude_binary: str) -> int:
    """One trivial backend call with the run's environment; pass only if nothing in run 2 changed."""
    env = _run_env(run_dir)
    if env.get("HOOK_SKIP") != "1" and not env.get("CLAUDE_CONFIG_DIR"):
        print("probe: set HOOK_SKIP=1 (honoured by the Stop hook) or CLAUDE_CONFIG_DIR first", file=sys.stderr)
        return 2
    _fresh_wiki(run_dir)
    watched = {
        "audit_log": run_dir / "wiki" / ".audit",
        "query_log": run_dir / "doc_internal",
        "proposals": run_dir / "proposals",
        "wiki": run_dir / "wiki",
    }
    before = {name: _tree_hash(path) for name, path in watched.items()}
    command = [claude_binary, "-p", PROBE_PROMPT]
    started = _now()
    proc = subprocess.Popen(command, env=env, cwd=run_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    hook_pytest: list[str] = []  # pytest processes descending from the probe call: the hook fired
    unrelated_pytest: list[str] = []  # pytest elsewhere on the machine (another session): informational
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
    pytest_seen = bool(hook_pytest)
    passed = unchanged and not pytest_seen and proc.returncode == 0
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
        "pytest_seen": pytest_seen,
        "pytest_under_probe": hook_pytest,
        "pytest_unrelated": unrelated_pytest,
        "passed": passed,
    }
    manifest = _load_manifest(run_dir)
    manifest.update(_shared_record())
    manifest.setdefault("probes", []).append(record)
    manifest["isolation_probe"] = record
    _save_manifest(run_dir, manifest)
    verdict = "PASSED" if passed else "FAILED"
    print(f"probe: {verdict} (exit {proc.returncode}, unchanged={unchanged}, pytest_seen={pytest_seen})")
    if not passed:
        print("probe: fix the isolation and run the probe again; no ingest attempt was consumed", file=sys.stderr)
    return 0 if passed else 1


# ── ingest ────────────────────────────────────────────────────


def _proposal_dir_for(run_dir: Path, source: Path) -> Path:
    return run_dir / "proposals" / f"{datetime.date.today().isoformat()}-{source.stem}"


def _run_logged(cmd: list[str], env: dict[str, str], log_prefix: Path) -> tuple[int, float, str, str]:
    start = time.monotonic()
    proc = subprocess.run(cmd, env=env, cwd=REPO_ROOT, capture_output=True, text=True)
    wall = round(time.monotonic() - start, 3)
    log_prefix.with_suffix(".stdout.txt").write_text(proc.stdout, encoding="utf-8")
    log_prefix.with_suffix(".stderr.txt").write_text(proc.stderr, encoding="utf-8")
    return proc.returncode, wall, proc.stdout, proc.stderr


def ingest(run_dir: Path, backend: str) -> int:
    manifest = _load_manifest(run_dir)
    probe_record = manifest.get("isolation_probe")
    if not probe_record or not probe_record.get("passed"):
        print("ingest: no passed isolation probe in run2/manifest.json; run `probe` first", file=sys.stderr)
        return 2
    if manifest.get("ingest"):
        print("ingest: this run is already recorded; a run is never regenerated (FR-003)", file=sys.stderr)
        return 2
    env = _run_env(run_dir)
    model_source = "env ANTHROPIC_MODEL"
    if backend == "claude" and not env.get("ANTHROPIC_MODEL"):
        # Not set: pin whatever Claude Code's own settings pin (run 1 ran on this alias) and say so.
        settings_model = _settings_model()
        if not settings_model:
            print("ingest: set ANTHROPIC_MODEL (no model in ~/.claude/settings.json to fall back on)", file=sys.stderr)
            return 2
        env["ANTHROPIC_MODEL"] = settings_model
        model_source = "~/.claude/settings.json model (ANTHROPIC_MODEL was unset)"
    head = _git("rev-parse", "HEAD")
    descends = (
        subprocess.run(["git", "merge-base", "--is-ancestor", FIX_MERGE_COMMIT, "HEAD"], cwd=REPO_ROOT).returncode == 0
    )
    if not descends:
        print(f"ingest: HEAD {head[:7]} does not descend from the #11 fix merge {FIX_MERGE_COMMIT}", file=sys.stderr)
        return 2
    if _git("status", "--porcelain", "--", "src", "eval/navigation/corpus", "eval/navigation/questions.json"):
        print(
            "ingest: uncommitted changes under src/ or the shared inputs; commit first so the run is pinned",
            file=sys.stderr,
        )
        return 2
    stems = [Path(e["path"]).stem for e in manifest["corpus_files"]]
    if len(set(stems)) != len(stems):
        print("ingest: two corpus files share a stem; their proposal directories would collide", file=sys.stderr)
        return 2
    _fresh_wiki(run_dir)

    pinned: dict[str, Any] = {
        "backend": backend,
        "model": env.get("ANTHROPIC_MODEL"),
        "model_source": model_source,
        "ingest_date": datetime.date.today().isoformat(),
        "started_at": _now(),
        "wiki_studio_commit": head,
        "wiki_studio_version": _version([sys.executable, "-m", "wiki_studio", "--version"]),
        "claude_version": _version(["claude", "--version"]) if backend == "claude" else None,
        "backend_timeout_seconds": BACKEND_TIMEOUT_SECONDS,
        "command": [
            "python",
            "-m",
            "wiki_studio",
            "ingest",
            "<corpus-file>",
            "--backend",
            backend,
            "--allow-out-of-repo",
        ],
        "locations": {k: env[k] for k in ("WIKI_STUDIO_ROOT", "WIKI_STUDIO_WIKI_DIR", "WIKI_STUDIO_PROPOSALS_DIR")},
        "env": _env_record(env),
        "tokens_note": "The text-mode copilot-CLI backends do not expose token usage; wall time only.",
        "documents": [],
    }
    manifest["ingest"] = pinned
    _save_manifest(run_dir, manifest)  # pinned before the first attempt

    logs = run_dir / "ingest-logs"
    for number, entry in enumerate(manifest["corpus_files"], start=1):
        source = SHARED_DIR / "corpus" / entry["path"]
        doc: dict[str, Any] = {
            "path": entry["path"],
            "attempts": 0,
            "transport_error": None,
            "proposal_dir": None,
            "disposition": None,
            "promote_error": None,
            "pages_written": [],
            "wall_seconds": 0.0,
            "tokens_in": None,
            "tokens_out": None,
        }
        for attempt in (1, 2):
            doc["attempts"] = attempt
            prefix = logs / f"{number:02d}-ingest" if attempt == 1 else logs / f"{number:02d}-ingest-retry"
            code, wall, out, err = _run_logged(
                [
                    sys.executable,
                    "-m",
                    "wiki_studio",
                    "ingest",
                    str(source),
                    "--backend",
                    backend,
                    "--allow-out-of-repo",
                ],
                env,
                prefix,
            )
            doc["wall_seconds"] = round(doc["wall_seconds"] + wall, 3)
            proposal_dir = _proposal_dir_for(run_dir, source)
            written = proposal_dir.is_dir()
            if code == 0 and written:
                # ingest exits 0 for both outcomes; a gate reject writes an empty patch-set and says so.
                doc["proposal_dir"] = proposal_dir.name
                doc["disposition"] = "reject" if "gate rejected" in out else "accept"
                break
            if code in RETRY_EXIT_CODES and not written and attempt == 1:
                # The backend returned nothing: the one permitted retry (FR-003).
                doc["transport_error"] = {"exit_code": code, "stderr": err.strip().splitlines()[-1:] or [""]}
                continue
            if code == 1:
                doc["disposition"] = "reject"
            elif code == 0:
                doc["disposition"] = "ingest_error (exit 0 but no proposal directory written)"
            else:
                doc["disposition"] = f"ingest_error (exit {code})"
            doc["proposal_dir"] = proposal_dir.name if written else None
            break

        if doc["disposition"] == "accept":
            proposal_dir = run_dir / "proposals" / str(doc["proposal_dir"])
            pcode, pwall, pout, perr = _run_logged(
                [sys.executable, "-m", "wiki_studio", "promote", str(proposal_dir)], env, logs / f"{number:02d}-promote"
            )
            doc["wall_seconds"] = round(doc["wall_seconds"] + pwall, 3)
            if pcode == 0:
                plan = json.loads(
                    (run_dir / "proposals" / ".applied" / str(doc["proposal_dir"]) / "plan.json").read_text()
                )
                doc["pages_written"] = [e["path"] for e in plan["edits"]]
            else:
                doc["promote_error"] = {"exit_code": pcode, "stderr": perr.strip()[-600:]}
        pinned["documents"].append(doc)
        _save_manifest(run_dir, manifest)
        print(
            f"{number:02d} {entry['path']}: {doc['disposition']} ({doc['attempts']} attempt(s), {doc['wall_seconds']}s)"
        )

    lcode, _, lout, lerr = _run_logged(
        [sys.executable, "-m", "wiki_studio", "lint", "--root", str(run_dir), "--wiki-dir", str(run_dir / "wiki")],
        env,
        logs / "lint",
    )
    pinned["lint"] = {"exit_code": lcode, "stdout": lout, "stderr": lerr}
    pinned["completed_at"] = _now()
    pinned["summary"] = {
        "documents_attempted": len(pinned["documents"]),
        "promoted": sum(d["disposition"] == "accept" and d["promote_error"] is None for d in pinned["documents"]),
        "retries": sum(d["attempts"] == 2 for d in pinned["documents"]),
        "total_wall_seconds": round(sum(d["wall_seconds"] for d in pinned["documents"]), 3),
        # A lint failure is recorded, never repaired (FR-003); the run still completes.
        "lint_clean": lcode == 0,
    }
    _save_manifest(run_dir, manifest)
    notes = run_dir / "ingest-notes.md"
    if not notes.exists():
        notes.write_text(
            "# Run 2 — one-time ingest record\n\nProduced by `eval/navigation/run2_protocol.py` under the protocol of\n"
            "`specs/wiki-studio-0-3-0/` (US5). Facts are in `manifest.json`; add observations below, never edits.\n",
            encoding="utf-8",
        )
    print(f"ingest: done; lint exit {lcode}; {pinned['summary']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in ("probe", "ingest", "all"):
        print("usage: python -m eval.navigation.run2_protocol probe|ingest|all")
        print("       [--run-dir DIR] [--backend NAME] [--claude BIN] [--commit]")
        print("  all: probe, then ingest if it passed; --commit commits run 2 as produced")
        return 2
    step, rest = args[0], args[1:]
    run_dir, backend, claude_binary, commit = DEFAULT_RUN_DIR, "claude", "claude", False
    while rest:
        flag = rest[0]
        if flag == "--commit":
            commit = True
            rest = rest[1:]
            continue
        value = rest[1] if len(rest) > 1 else None
        if flag == "--run-dir" and value:
            run_dir = Path(value).resolve()
        elif flag == "--backend" and value:
            backend = value
        elif flag == "--claude" and value:
            claude_binary = value
        else:
            print(f"unknown or incomplete option: {flag}", file=sys.stderr)
            return 2
        rest = rest[2:]
    if step == "probe":
        return probe(run_dir, claude_binary)
    if step == "all":
        if os.environ.get("HOOK_SKIP") != "1" and not os.environ.get("CLAUDE_CONFIG_DIR"):
            os.environ["HOOK_SKIP"] = "1"  # the Stop hook honours it; recorded in the probe's env
        if probe(run_dir, claude_binary) != 0:
            return 1
    code = ingest(run_dir, backend)
    if code == 0 and commit:
        sha = _commit_run(run_dir, "eval: run 2 one-time ingest under the US5 protocol (recorded by run2_protocol.py)")
        print(f"committed run 2 as {sha}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
