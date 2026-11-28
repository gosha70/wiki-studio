---
feature_id: wiki-studio-duplicate-audit-121
date: 2026-11-28
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-duplicate-audit-121
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-duplicate-audit-121 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The change makes `WikiPaths.for_root` read `WIKI_STUDIO_SIMILAR_PAGES` like `resolve` does, factoring the parsing into a shared `_read_switch` helper and adding an `env` parameter. The refactor is clean and the tests cover the key cases (unset, empty, case-insensitive, invalid, explicit-wins, custom env). One behavioral concern: `for_root` now raises `ValueError` on a malformed env var where it previously defaulted to `True`, which is a breaking change for existing library callers — this is documented but worth flagging as a compatibility risk.

## Findings

- [warning] f-7bea2d5a: `for_root` previously defaulted `similar_pages` to `True` unconditionally; it now raises `ValueError` on a malformed `WIKI_STUDIO_SIMILAR_PAGES` value. Any existing library consumer (memkernel lint/info/findings/export, migration scripts) that previously worked with a stray env var in the environment will now hard-fail. The CHANGELOG and docs note this, but it is a silent breaking change for downstream callers who never opted into env reading. (src/wiki_studio/paths.py)
- [note] f-6ea9e828: The helper correctly strips and lowercases, treats unset/empty as on, and raises naming the variable and value. Behavior matches the prior inline logic in `resolve` exactly, so the refactor is behavior-preserving for `resolve`. (src/wiki_studio/paths.py)
- [note] f-c9c112ca: Test mutates `os.environ` via `mock.patch.dict(..., clear=True)` after copying — correct, but the copy-then-pop-then-set dance is redundant since `clear=True` already isolates. Minor readability nit only. (tests/test_paths.py)
- [note] f-bd196463: Docs correctly call out the `env={}` escape hatch and the explicit-argument escape hatch. Good. (docs/consumers.md)
- [note] f-13a876b4: The refactor preserves the exact error message format (`{name} must be 'on' or 'off', got {value!r}`) since `ENV_SIMILAR_PAGES` is passed as `name`. Verified against the removed inline code. (src/wiki_studio/paths.py)
