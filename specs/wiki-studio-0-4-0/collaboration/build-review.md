---
feature_id: wiki-studio-0-4-0
date: 2026-10-17
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: fix/21-promote-rollback
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-4-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The fix correctly addresses the three defects in issue #21: the in-flight file is now recorded before its write so it gets rolled back, rollback restores exact original bytes (preserving CRLF), and rollback runs on any `BaseException` with `KeyboardInterrupt`/`SystemExit` re-raised after restoration. The test coverage is solid, exercising half-writes, multiple exception types, CRLF preservation, and the new-page removal path. I found no blocking issues; a few notes on edge cases and test robustness.

## Findings

- [note] f-0d51e11a: If a target was newly created and the write failed before any bytes landed, `target.exists()` is False and unlink is skipped — correct. But if the write partially created the file and then raised, `exists()` is True and unlink removes it — also correct. However, if `mkdir(parents=True)` succeeded but the write failed, empty parent dirs created by this commit are left behind. This is pre-existing behavior and not a regression, but worth noting for the "exact pre-commit state" claim in the docstring. (src/wiki_studio/promoter.py)
- [note] f-646976cd: `applied` is guaranteed non-empty here because the append happens before the write that raised, so `applied[-1]` is the failing target. This is correct, but it relies on the invariant that the exception can only originate from inside the loop body after the append. If a future refactor moves the append or adds code before it that can raise, this would IndexError. A brief comment or an explicit `assert applied` would harden it. (src/wiki_studio/promoter.py)
- [note] f-86b259d6: Catching `Exception` (not `BaseException`) during rollback is the right call — a `KeyboardInterrupt` during rollback should propagate rather than be swallowed into `rollback_errors`. But note that if rollback itself is interrupted by `KeyboardInterrupt`, the original exception's `add_note` path is skipped and the partial rollback state is left. This is an acceptable trade-off (you can't reliably roll back from a second interrupt), but the docstring's "Either way the wiki ends up in its pre-commit state" is slightly stronger than reality under a second interrupt. (src/wiki_studio/promoter.py)
- [note] f-4b96f296: The `_hit` guard ensures only the first matching write fails, so the rollback's restore of the same target succeeds. Good. However, the test patches `Path.write_text` globally, so if the rollback path for a *different* target also used `write_text` (it now uses `write_bytes`), the guard would still be needed. Since rollback now uses `write_bytes` exclusively, the guard is belt-and-suspenders — fine, but the comment "fail the commit write, not the rollback's restore" is now slightly stale since rollback never calls `write_text`. Minor. (tests/test_e2e.py)
- [note] f-08ce7fe3: This asserts no `plan.json` was written, but the conditional expression is awkward and the assertion would pass vacuously if `.audit` doesn't exist. It's testing the right thing (plan.json is written last, so a failure before it means none exists), but the expression is hard to read. Also, if `.audit` exists with other files, `rglob("plan.json")` returning `[]` is the real check — the `if exists()` guard is redundant since `rglob` on a non-existent path returns empty anyway in pathlib? (Actually it raises `FileNotFoundError` on some versions — so the guard is defensive.) (tests/test_e2e.py)
- [note] f-f72f3027: The changelog accurately describes the three defects and the fix. It says "Present since 0.1.0" — worth confirming that's accurate (the `_commit_stage_to_wiki` function and its `OSError`-only rollback presumably date to 0.1.0). If the function was introduced later, this claim would be wrong. (CHANGELOG.md)
- [note] f-85f6eee8: Removing the `original: str  (src/wiki_studio/promoter.py)
