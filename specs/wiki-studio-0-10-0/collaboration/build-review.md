---
feature_id: wiki-studio-0-10-0
date: 2026-11-17
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-10-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-10-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The `nightly` verb wiring in `cli.py` is small and mostly correct, but the `--json` + `--report` interaction has a real bug: when `--report` is given and `--json` is not, the markdown is written to the file (good); when `--json` is given with `--report`, the file is written and JSON printed (good); but when `--json` is given *without* `--report`, the markdown is suppressed and JSON printed (good). The problem is the `elif not args.json` branch: when `--report` is `None` and `--json` is set, nothing is written to stdout except the JSON — that's intended. However, the `--report` path check happens before `api.nightly` runs, but the `--json` output is emitted even when the report write fails, which the tests confirm is intended. The bigger concern is that `_do_nightly` does not handle the case where `api.nightly` itself raises (e.g., `PathOutsideRootError` or other contract errors) — those would propagate as uncaught exceptions rather than mapping to the documented exit codes. Also, the `--report` path is resolved/checked via `nightly.check_report_path`, but the error message in the test asserts `str(target.resolve())` appears in stderr — this depends on `check_report_path` raising an error whose message includes the resolved path, which is not visible in this diff and should be verified.

## Findings

- [warning] f-3c627c21: `api.nightly(paths)` is called without a try/except; if it raises (e.g., `PathOutsideRootError`, `ContractViolationError`, or any other `WikiStudioError` subclass), the exception propagates out of `_do_nightly` and `main`'s dispatcher, producing a traceback instead of the documented exit codes (0/1/6). Other verbs in this file appear to rely on `main`'s top-level handler, but the nightly help text promises specific exit codes for specific conditions, and an uncaught exception would violate that contract. (src/wiki_studio/cli.py)
- [warning] f-4fcf9319: When `--report` is provided and `--json` is not, the markdown goes to the file and stdout is empty (correct). When `--report` is provided and `--json` is set, the file is written and JSON printed (correct). But when `--report` is *not* provided and `--json` is *not* set, markdown goes to stdout (correct). The `elif not args.json` structure means: if `report is None` and `args.json` is True, neither branch writes markdown — correct. However, if `report is not None` and the write fails, `result` is replaced with exit_code 6, but the `elif not args.json` branch is skipped (since `report is not None`), so no markdown is emitted — correct. The logic is sound but fragile: a future refactor that changes the `if/elif` to `if/if` would silently double-emit. Consider making the intent explicit with a comment or restructuring. (src/wiki_studio/cli.py)
- [note] f-55e4163f: The `check_report_path` call is guarded by `if args.report is not None`, but the help text says a refused path "exits 1 before anything runs." The test `test_a_report_path_inside_the_wiki_exits_one_before_anything_runs` patches `api.nightly` to raise and asserts it is not called — good. But the test also asserts `str(target.resolve())` appears in stderr, which requires `check_report_path` to raise an error whose message includes the resolved path. This is not visible in the diff; if `check_report_path` raises a `PathOutsideRootError` whose message uses the *unresolved* path, the test would fail. Verify the error message format matches the test's expectation, or relax the test to check for the path in either form. (src/wiki_studio/cli.py)
- [note] f-8a93a751: The test patches `wiki_studio.api.promote`, `wiki_studio.api.approve`, `wiki_studio.api._promote`, `wiki_studio.api._approve`, and every public function in `promoter`. It does not patch `wiki_studio.promoter.promote` / `wiki_studio.promoter.approve` directly if those are re-exported from `api` — but the `patch.object(promoter, name, ...)` loop covers them. However, the test does not patch `wiki_studio.cli`'s references to promote/approve (if any), nor does it patch `wiki_studio.api`'s internal call sites if `api.nightly` calls `promoter.promote` via a local alias. The static AST scan of `nightly.py` is the stronger guarantee; the runtime test is a belt-and-suspenders check. Consider also asserting that `nightly.py` does not import `api` in a way that could reach promote/approve transitively (e.g., `from . import api` then `api.promote(...)`). (tests/test_nightly_cli.py)
- [note] f-527aca8a: The help text says "Exit codes at this phase: 0 a completed run, whatever it found; 1 structural lint failed (the report is still written) or the --report path lies inside the wiki (nothing runs); 6 the report could not be written." This is clear, but it does not mention what happens if `api.nightly` raises an unexpected error (see first finding). If the outer handler maps such errors to a code, document it; if not, the help text is incomplete. (src/wiki_studio/cli.py)
