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

The change implements US4 (no duplicate on rerun) by adding an `AlreadyProposed` result type, a pre-draft pending-directory check, and a race-condition fallback that reclassifies an `OutputWriteError` as "already proposed" when the target directory now exists. The core logic is sound and well-tested, but the race-condition fallback is overly broad and can mask genuine write failures, and the `_pending_proposals` change to catch all `OSError` silently swallows permission errors.

## Findings

- [warning] f-27843e2f: The race-condition fallback treats *any* `OutputWriteError` as "already proposed" whenever `(paths.proposals_dir / name).is_dir()` is true. But `OutputWriteError` can be raised for reasons other than the exclusive-create collision (e.g., a partial write that failed after the directory was created, or a failure writing `plan.json` inside a freshly created dir). In those cases the directory exists but the proposal is incomplete/corrupt, yet the finding is silently reported as `already_proposed` and the run exits 0 — masking a real failure and leaving a broken proposal on disk. (src/wiki_studio/nightly.py)
- [warning] f-8c291e55: Broadening `FileNotFoundError` to `OSError` means a `PermissionError` (or `NotADirectoryError` on a path that is a file) is now silently treated as "no pending proposals." Combined with the new pre-draft `is_dir()` check, a permissions problem on `proposals_dir` would cause every finding to be drafted and then fail at write time — but the earlier `_pending_proposals` call would have already reported zero pending, so the report's "pending" section is misleading. The test `test_a_proposals_path_that_is_a_regular_file_is_a_write_failure` exercises the file case but not the permission case. (src/wiki_studio/nightly.py)
- [note] f-352db5ce: The pre-draft check uses `is_dir()`, which returns `False` if the path exists as a *file* (not a directory). In that case drafting proceeds, the exclusive create fails, and the fallback `is_dir()` check also returns `False`, so it correctly falls through to `failed`. This is consistent, but worth a comment noting the file-vs-dir distinction is intentional (the test covers it). (src/wiki_studio/nightly.py)
- [note] f-09cd4624: The race test simulates the collision by having the backend call `api.propose` *before* returning the draft, so the exclusive create in `_draft_all` fails. This exercises the fallback path, but it does not verify that the fallback is *narrow* — i.e., that a non-collision `OutputWriteError` still produces `failed`. A test that forces an `OutputWriteError` for a different reason (e.g., monkeypatching the write to raise after the dir exists) would guard against the over-broad fallback noted above. (tests/test_nightly_drafting.py)
- [note] f-cace44c7: The docstring says "whose proposal directory was already pending (FR-025, FR-026)" but does not mention that the entry may also arise from the race fallback where the directory was created by another run mid-draft. Minor, but the two code paths (pre-check vs. race fallback) are semantically distinct and the docstring conflates them. (src/wiki_studio/nightly.py)
