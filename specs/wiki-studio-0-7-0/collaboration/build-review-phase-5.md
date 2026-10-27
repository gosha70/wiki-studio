---
feature_id: wiki-studio-0-7-0
date: 2026-10-26
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-7-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-7-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The `superseded_by` feature is implemented cleanly: lint validation covers empty/absolute/escaping/self/missing/non-page/chain/cycle cases, `review_state` reports `superseded`, `approve` refuses superseded pages, and `promote` refuses creates that would produce a broken target. The `corrects` line is preserved byte-for-byte and not interpreted, matching the spec. A few correctness edge cases around the superseded-set construction and the `_field`/`startswith` detection are worth flagging.

## Findings

- [warning] f-e45925f8: The detection uses `startswith("superseded_by:")` on raw frontmatter lines, so a line like `superseded_by:foo` (no space) or `superseded_by :` (space before colon) is not detected, while `_field` may still parse it — inconsistent with how other keys are read. Also a line `superseded_by_extra: x` would not match (good), but `superseded_by:` with trailing content on the same line is fine. More importantly, if the key appears twice, only the first is used by `_field` but the `any(...)` check just records presence; the value stored is `_field(...)` which may differ from the matched line. (src/wiki_studio/lint.py)
- [warning] f-e0f887c0: The chain check tests `normalised in superseded` where `superseded` is the set of *all* pages carrying `superseded_by`, regardless of whether their own target is valid. This is intentional for cycle detection, but it means a page whose `superseded_by` is itself invalid (e.g., empty or missing target) still counts as "superseded" for the chain check on other pages — producing a chain violation on a page pointing at it even though the intermediate page's marker is broken. That may be acceptable (both are violations), but the error message "target is itself superseded" is misleading when the intermediate page's marker is invalid. (src/wiki_studio/lint.py)
- [note] f-35d1c3f4: `lexists` returns True for symlinks and broken symlinks. A `superseded_by` pointing at a symlink would be reported as "not a page" (correct, since symlinks are not pages), but a broken symlink also yields "not a page" rather than "does not exist" — minor message inconsistency. Also, `normalised` is a posix path joined onto `wiki_dir`; on Windows this is fine, but the containment check only rejects `..` prefixes, not e.g. a normalised path that resolves through a symlinked directory inside the wiki. (src/wiki_studio/lint.py)
- [note] f-57e69755: `normpath` collapses `a/../b` to `b`, so `concepts/../../outside.md` normalises to `../outside.md` and is caught — good. But a target like `concepts/./beta.md` normalises to `concepts/beta.md` and is accepted, which is fine. However, a target containing a backslash on POSIX (e.g., `concepts\\beta.md`) is treated as a literal filename and will report "does not exist" rather than being flagged as a malformed path — acceptable but worth a test. (src/wiki_studio/lint.py)
- [note] f-13bd1eb0: The test bypasses the very check it is meant to exercise by patching the promoter's `superseded_by` helper. This is a reasonable way to construct the "record exists for live bytes" state, but it couples the test to an internal function name; if that helper is renamed the test silently stops testing what it claims. (tests/test_superseded_by.py)
- [note] f-69713edb: The changelog says "a `promote` that would create one is refused (exit 9)" — good — but does not mention that `approve` also refuses a superseded page (exit 9). The ADR test asserts this, so the changelog should mention it for parity. (CHANGELOG.md)
- [note] f-1b2fe232: Good move — the constant is now shared. Confirm no other module still defines a local copy (grep for `"superseded_by"` string literals) to avoid drift. (src/wiki_studio/review.py)
