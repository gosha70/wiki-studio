---
feature_id: wiki-studio-0-3-0
date: 2026-10-16
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/eval-run-2
rounds_completed: 2
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-3-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 2
**Verdict**: PASS

## Summary

Round 2 review of the run 2 navigation evaluation. The builder's fixes for the Round 1 findings are largely present and correct: exit-0-without-proposal is now labeled, lint_clean is recorded, colliding stems are refused, `_shared_file` treats empty dirs as absent, RUNS always includes run 2, the checkpoint names `4d224df`, and the README/CHANGELOG caveats are in place. A few correctness issues remain in the protocol script and the results/README consistency.

## Findings

- [warning] f-51150da7: `_proposal_dir_for` uses `datetime.date.today().isoformat()` at call time, but the manifest's `ingest_date` is also `today()`. If the ingest crosses midnight (the run took ~9 minutes here, but a slow run could), the proposal directory name and the recorded `ingest_date` can disagree, and the `proposal_dir` recorded in the manifest would not match the on-disk directory. Pin the date once at the start of `ingest` and pass it through. (eval/navigation/run2_protocol.py)
- [warning] f-ebca6602: The retry condition is `if code in RETRY_EXIT_CODES and not written and attempt == 1`. If the first attempt exits 2/3 and writes a proposal directory (partial write), the loop falls through to the `else` branch and records `ingest_error (exit {code})` with `proposal_dir` set — but the directory is left on disk and the next document's ingest may see it. The spec's one-attempt rule is preserved, but the leftover directory is not cleaned or flagged. Either remove the partial directory or record it explicitly as a partial write. (eval/navigation/run2_protocol.py)
- [warning] f-4cc35be7: `_commit_run` runs `git add -- <run_dir>` and commits, but the manifest is written by `ingest` before `_commit_run` is called and `_commit_run` does not re-read or re-write the manifest. If `ingest` returns 0 but the final `_save_manifest` failed silently (e.g. disk full), the commit would still succeed with a stale manifest. The builder disputed this in Round 1, but the dispute only addresses the "commit only run_dir" half; the "manifest written before commit" half is still true. Add a `check=True` read-back of the manifest before committing, or re-write it inside `_commit_run`. (eval/navigation/run2_protocol.py)
- [warning] f-975d7630: The ancestor walk starts at `pid` and checks `if ancestor == probe_pid` before advancing, but the probe's own PID is the `claude` process, not the shell that spawned it. A pytest started by a hook inside the `claude` subprocess will have `claude`'s PID as an ancestor only if the hook is a direct child; if the hook spawns via a shell, the walk still reaches `claude`'s PID, so this is fine — but the loop condition `while ancestor in parent` will silently stop if any intermediate process has already exited (common for short-lived shells), causing a hook-spawned pytest to be misclassified as `unrelated`. The docstring now states this limitation, but the byte comparison is the only decisive check; consider also comparing the probe's `pytest_unrelated` list against a baseline taken before the probe. (eval/navigation/run2_protocol.py)
- [warning] f-1728b058: The lint command is `[sys.executable, "-m", "wiki_studio", "lint", "--root", str(run_dir), "--wiki-dir", str(run_dir / "wiki")]`, but the manifest's `lint` record only stores `exit_code`, `stdout`, `stderr`. If lint fails, `ingest` still returns 0 and the summary reports success. The spec (FR-016, checkpoint US5) treats lint as part of the gate. The builder added `lint_clean` to the summary, which is good, but `ingest` still returns 0 on a lint failure. Either return non-zero on lint failure or make the checkpoint explicitly require `lint_clean` true. (eval/navigation/run2_protocol.py)
- [warning] f-ca26e500: `_fresh_wiki` creates `index.md` and `log.md` only if they do not exist. On a re-run after a partial failure (e.g. probe passed, ingest crashed mid-way), the wiki already has content and `_fresh_wiki` will not reset it, so the second ingest would append to a partially-populated wiki. The `if manifest.get("ingest")` guard prevents a full re-run, but a crash before `manifest["ingest"]` is written leaves the run in a state where `ingest` can be re-invoked and will not start clean. The builder disputed this in Round 1, but the dispute only addresses the window before `manifest["ingest"]` is saved; a crash between `_fresh_wiki` and the first `_save_manifest` still leaves a dirty wiki. (eval/navigation/run2_protocol.py)
- [warning] f-c0aa499d: `_shared_record` reads `run1["corpus_files"]` and copies it verbatim into run 2's manifest, but does not re-verify the sha256 of the actual corpus files on disk. If a corpus file were modified between run 1 and run 2, the manifest would still record run 1's hashes. The spec (FR-013) requires run 2's manifest to record the shared files' sha256 and a test to assert they equal run 1's manifest values — the test does this, but the protocol script itself does not. (eval/navigation/run2_protocol.py)
- [warning] f-9967c4dd: `_commit_run` commits only `run_dir`, so any changes to `README.md`, `CHANGELOG.md`, `tests/`, or `specs/` made by the build are not included, contradicting the commit message "run 2 one-time ingest under the US5 protocol". The builder disputed this in Round 1, arguing the build's write-up is a separate commit by design. That is defensible, but the commit message should say so explicitly to avoid confusion. (eval/navigation/run2_protocol.py)
- [warning] f-3c26f370: The README says "the three that did not (ADR-009, licensing, sibling-projects) failed on a different contract gap than run 1: the model returned `index.md` as a full page edit instead of an `append-index` line". The ingest logs show the error is a validator rejection (`page_type 'index' is not promotable for create/update`), not a prompt gap per se — the model did produce an `index.md` edit, and the validator correctly rejected it. The CHANGELOG now pairs the gap with the validator messages, but the README does not. Add the validator message to the README paragraph. (README.md)
- [warning] f-f38f538b: The README's run 2 column says "Documents promoted, of the 10 in the corpus  (README.md)
- [note] f-9c45e182: The parser accepts `--shared` anywhere in the argument list and treats any other `-`-prefixed token as a usage error via `any(p.startswith("-") for p in positionals)`. This means `run.py --shared` (missing value) is silently treated as a positional `--shared` and then rejected by the `startswith("-")` check, producing the usage message — acceptable, but the error message does not distinguish "missing value for --shared" from "unknown flag". (eval/navigation/run.py)
- [note] f-0cf349e6: `_shared_file` returns `own` if `own.exists()` or `shared_dir is None`, else `shared_dir / name`. For `corpus`, `own` is a directory; `Path.exists()` returns True for directories, so a fixture with an empty `corpus/` directory would shadow the shared corpus. The builder fixed this by checking `own.is_dir() and any(own.iterdir())`, which is correct, but the fix is not covered by a test. (eval/navigation/run.py)
- [note] f-defcc96f: The `RUNS` list is now always `[("run1", FIXTURE, FIXTURE), ("run2", RUN2, FIXTURE)]`, which is correct per FR-016. But the test does not assert that run 2's `manifest.json` records the shared files' sha256 equal to run 1's, which FR-013 requires. Add that assertion. (tests/test_navigation_eval.py)
- [note] f-8985bfbe: The checkpoint says `git diff --stat 4d224df..HEAD -- eval/navigation/corpus ...` is empty, but the actual commit before run 2 is `4d224df` (the #11 merge), which is recorded in `FIX_MERGE_COMMIT`. The checkpoint now names `4d224df`, which is correct, but the `isolation_probe.passed` and `determinism test green` checkboxes are still unchecked (`[ ]`), even though the run is complete. Mark them `[x]` or explain why they remain open. (specs/wiki-studio-0-3-0/tasks.md)
- [note] f-c6f63002: The record notes that run 2's model is `claude-opus-5-5` while run 1 recorded `opus`, and that "the protocol asked for a concrete identifier when the CLI accepts one". This is a real difference between the two runs that affects comparability, and it is recorded as a mismatch but not as a caveat in the README. The README's run 2 paragraph does mention the model-name difference, so this is covered, but the origin-alignment record should cross-reference the README caveat. The builder fixed this in Round 1, but the fix is not visible in the diff. (specs/wiki-studio-0-3-0/origin-alignment-2026-10-16-2300.md)
