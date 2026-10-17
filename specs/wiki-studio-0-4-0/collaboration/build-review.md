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
target_ref: fix/23-preview-normalised-paths
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

The fix correctly normalises edit paths with `posixpath.normpath` before allocating preview files, so `index.md` and `./index.md` no longer collide. The change is minimal, well-tested, and documented. One minor concern about the interaction between normalised preview paths and the raw `edit.path` retained in `plan.json` is worth noting but does not block.

## Findings

- [note] f-5cbfaaee: `posixpath.normpath` collapses `..` segments (e.g. `a/../index.md` → `index.md`) and leading `./`, but the raw `edit.path` is still written into `plan.json` and presumably validated elsewhere. If validation rejects `..` but not `./`, this is fine; if validation is absent or inconsistent, a path like `foo/../index.md` could normalise to `index.md` and share a preview with a legitimate `index.md` edit while `plan.json` still records the raw path — worth confirming the validator rejects `..` before this point. (src/wiki_studio/ingestor_multi.py)
- [note] f-e96d70f5: The test asserts the preview filenames and that both appends land in order, but does not assert that `promote` accepts the `./index.md` edit (i.e. that the raw path in `plan.json` is still resolvable). The test does call `api.promote` and checks the resulting index, which implicitly covers this — good — but a direct assertion that the second edit's `path` is preserved as `./index.md` (already present) plus a check that promote did not error is sufficient. No change required; noting for completeness. (tests/test_multiple_appends.py)
- [note] f-07a2b463: The doc now says `<path>` is normalised, but does not state what normalisation means (e.g. `./` stripped, `..` rejected). A one-clause clarification would help readers understand the boundary between "accepted spelling" and "rejected path". (docs/patch-set-format.md)
