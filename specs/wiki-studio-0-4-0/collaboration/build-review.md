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

- [note] f-90ddfc3c: `missing` is computed as `[d for d in (plan.target.parent, *plan.target.parent.parents) if not d.exists()]`, which walks all the way up to the filesystem root. If the wiki root itself (or any ancestor) does not yet exist, those ancestors get added to `created_dirs` and `mkdir(parents=True)` will create them — but rollback only `rmdir`s them in reverse order, which is correct. However, if two planned writes share a missing parent, the second write's `missing` list will be empty (parent now exists), so no double-add — good. The real edge: `created_dirs` may contain directories that pre-existed but were removed by a concurrent process between the `exists()` check and `mkdir`; rollback would then `rmdir` a directory it did not create. Latent, not active for single-process promote. (src/wiki_studio/promoter.py)
- [note] f-867a785d: `applied` is guaranteed non-empty because the append happens before the write that raised, so `applied[-1]` is the failing target. This is correct, but it relies on the invariant that the exception can only originate from inside the loop body after the append. If a future refactor moves the append or adds code before it that can raise, this would IndexError. A brief comment or an explicit `assert applied` would harden it. (src/wiki_studio/promoter.py)
- [note] f-86b259d6: Catching `Exception` (not `BaseException`) during rollback is the right call — a `KeyboardInterrupt` during rollback should propagate rather than be swallowed into `rollback_errors`. But note that if rollback itself is interrupted by `KeyboardInterrupt`, the original exception's `add_note` path is skipped and the partial rollback state is left. This is an acceptable trade-off (you can't reliably roll back from a second interrupt), but the docstring's "Either way the wiki ends up in its pre-commit state" is slightly stronger than reality under a second interrupt. (src/wiki_studio/promoter.py)
- [note] f-4b96f296: The `_hit` guard ensures only the first matching write fails, so the rollback's restore of the same target succeeds. Good. However, the test patches `Path.write_text` globally, so if the rollback path for a *different* target also used `write_text` (it now uses `write_bytes`), the guard would still be needed. Since rollback now uses `write_bytes` exclusively, the guard is belt-and-suspenders — fine, but the comment "fail the commit write, not the rollback's restore" is now slightly stale since rollback never calls `write_text`. Minor. (tests/test_e2e.py)
- [note] f-5b962abf: The tree comparison uses `q.is_dir() or q.read_bytes()` as the value, which means a directory and a file with the same relative path would compare equal only if both are directories — but a file and a directory can't share a path, so this is fine. However, the dict comprehension iterates `wiki.rglob("*")` which does not include `wiki` itself; if the commit created `wiki` (it can't, since `wiki` is the root), this would miss it. Not an issue here. (tests/test_e2e.py)
- [note] f-f72f3027: The changelog accurately describes the three defects and the fix. It says "Present since 0.1.0" — worth confirming that's accurate (the `_commit_stage_to_wiki` function and its `OSError`-only rollback presumably date to 0.1.0). If the function was introduced later, this claim would be wrong. (CHANGELOG.md)
- [note] f-5311ccdb: Removing the `original: str` field is correct (rollback now uses `original_bytes` exclusively), but the `new_content: str` field is still used only for `write_text`; for binary plans it's set to `""`. This is fine, but a reader might wonder why `new_content` exists alongside `new_bytes`. A one-line comment on `new_content` ("text payload; empty for binary plans") would clarify. (src/wiki_studio/promoter.py)
