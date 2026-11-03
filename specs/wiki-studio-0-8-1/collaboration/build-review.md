---
feature_id: wiki-studio-0-8-1
date: 2026-11-03
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-8-1
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-8-1 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The change adds a correction-loop demonstration (`demo.py`, `record.py`, docs, and a CI job) that exercises the memkernel↔wiki-studio governed loop end-to-end. The design is sound and the recorder's binding of a run to committed bytes, wheel sha256, PyPI-published memkernel sha256, and pinned embedding revision is a strong evidence story. The main correctness concerns are in the recorder's trust boundaries and a few fragile parsing/ordering assumptions in `demo.py`; none appear to break the happy path, but several could silently weaken the evidence or fail confusingly.

## Findings

- [warning] f-6ed8a681: The recorder is described as refusing unless the downloaded memkernel wheel's sha256 equals "the one PyPI publishes for that file", but the diff does not show how the PyPI-published digest is obtained or authenticated. If it is fetched over the network at record time without pinning (e.g., via the JSON API), a compromised or MITM'd response could make the check vacuous, and the manifest's `memkernel_pypi_sha256` would then be attacker-controlled evidence. (examples/correction-loop/record.py)
- [warning] f-bd0a3b3c: The protocol says the recorder refuses unless `git status --porcelain` is empty and builds the wheel from `git archive HEAD`. If the recorder runs `git archive HEAD` in the working tree rather than from a fresh clone, untracked-but-ignored files (e.g., a stale `dist/`) or a dirty submodule could still influence the build. The diff does not show the exact invocation, so this is a risk to verify. (examples/correction-loop/record.py)
- [warning] f-d02cf319: The receipt is chosen by `max((committed_at, dirname, path))`. If two receipts share a `committed_at` (same-second commits are plausible on a fast scripted run), the tiebreak is the directory name, which is not guaranteed to be monotonic. This could pick the wrong receipt and make the "curator receipt" check pass against an unrelated commit. (examples/correction-loop/demo.py)
- [warning] f-413b1d28: `_keyed` matches any line starting with `f"{key}:"`, including lines inside the body or inside a fenced code block that happen to start with the key. It returns `""` when there are zero or multiple matches, which is treated as a failed check — but a body line like `status: stable` inside an example would silently break the check with a confusing message. (examples/correction-loop/demo.py)
- [warning] f-2002ab2d: `_replace_line` requires exactly one line equal to `old`. The wrong rule `WRONG` appears in the title, the heading, and the body per the README, so the curator step must call `_replace_line` three times with three distinct `old` strings (title form, heading form, body form). If any of those forms is not byte-identical (e.g., trailing whitespace, or the heading is `## Deploy on Fridays after 17:00 UTC.` vs `### …`), the check fails with "expected one line … found 0", which is correct but brittle against formatting drift in the exported draft. (examples/correction-loop/demo.py)
- [warning] f-ed86fca7: The step env pops `WIKI_STUDIO_*` overrides but does not pop `MEMKERNEL_*` overrides other than the ones it sets. A developer's shell with `MEMKERNEL_EMBEDDING_MODEL` or `MEMKERNEL_CHROMA_PERSIST_PATH` set would leak into the demo, and the recorder's pinned-model guarantee (`HF_HUB_OFFLINE=1` + snapshot path) could be bypassed if the recorder sets `MEMKERNEL_EMBEDDING_MODEL` but the demo's `_step_env` copies `os.environ` and the recorder's value is what's expected — but any *other* `MEMKERNEL_*` var (e.g., a backend selector) would pass through unchecked. (examples/correction-loop/demo.py)
- [warning] f-495fb0a3: The check `os.path.isabs(model) or os.sep in model` treats a bare model name like `all-MiniLM-L6-v2` as "not a snapshot directory" and skips the directory check, then loads via `SentenceTransformerEmbedding`. That is fine for the default, but the recorder sets `MEMKERNEL_EMBEDDING_MODEL` to an absolute snapshot path and relies on `_probe_embedding` to reject a wrong revision. The probe only checks the directory exists, not that it is the pinned revision — the revision check is claimed to be in the recorder, but the demo's probe would happily load a different snapshot if the recorder's check were bypassed. (examples/correction-loop/demo.py)
- [warning] f-aa3bad47: `_run_cli` returns a `CompletedProcess` with `check=False`; the diff does not show callers asserting `returncode == 0` before parsing stdout. If a `wiki-studio read --json` or `propose` fails, the subsequent JSON parse would raise an uncaught exception (exit 1 via traceback) rather than a named check failure, violating the "one line names it" contract. (examples/correction-loop/demo.py)
- [warning] f-255898bf: State is written with `path.write_text(...)` directly. If the process is killed mid-write (e.g., CI timeout), the next step's `_load_state` will raise `json.JSONDecodeError` and the orchestrator will exit with a traceback rather than a clean "cannot run" or "check failed". (examples/correction-loop/demo.py)
- [note] f-21eac280: `_tail` collapses whitespace and takes the last 300 chars. For a multi-line stderr this loses the first line, which is often the actual error. Acceptable for a demo, but the detail field in `checks` will be less useful for debugging CI failures. (examples/correction-loop/demo.py)
- [note] f-427e4b89: The README says `--out` must not exist, and CI passes `$RUNNER_TEMP/demo-run`. On a self-hosted runner or a re-run in the same job, `$RUNNER_TEMP` may persist; the recorder should fail with exit 2 (cannot run) rather than exit 1 (check failed) in that case, and the CI job should `rm -rf` the path first or use a unique subdir. (examples/correction-loop/record.py)
- [note] f-c63e5f28: The job runs `record.py` but does not assert anything about the produced `manifest.json` beyond printing it. A recorder bug that produces a manifest with `exit_code: 0` but wrong `end_state_sha256` or a missing `memkernel_pypi_sha256` would pass CI silently. (.github/workflows/ci.yml)
- [note] f-3edc6880: The doc states the recorded run is pending and CI is the evidence "until then". That is honest, but the spec (FR-014/FR-015) may require a committed run; if so, this doc is a placeholder that will need a follow-up commit. Flagging so the reviewer of the evidence PR checks the spec's acceptance criteria rather than treating the doc as final. (docs/demo-correction-loop.md)
- [note] f-64fe4244: Disabling `import-not-found` for the whole module hides genuine import errors in the demo (e.g., a renamed memkernel symbol) behind a runtime `CannotRunError`. Acceptable for an example, but it weakens the typecheck signal for this file. (examples/correction-loop/demo.py)
