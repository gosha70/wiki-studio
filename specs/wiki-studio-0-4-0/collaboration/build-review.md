---
feature_id: wiki-studio-0-4-0
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
target_ref: fix/18-multiple-appends
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

The fix correctly addresses issue #18 by giving each edit its own preview file (`preview/<path>`, then `.2`, `.3`, ...) and pointing `plan.json` at the per-edit path, so multiple appends to the same file no longer overwrite each other. The implementation is clean, uses `zip(..., strict=True)` to keep the two lists in lockstep, and is well covered by tests including the curator-edit and `propose --from` paths. I found no blocking correctness issues; a few notes on edge cases and documentation.

## Findings

- [note] f-d6650ea9: The suffix scheme `preview/<path>.2` is derived purely from edit order, not from any existing files on disk. If `write_patch_set_dir` is ever called into a non-empty `output_dir` (e.g. re-proposing into the same directory), stale `preview/<path>.2` files from a prior run could be silently overwritten or left orphaned. Current callers appear to always use fresh dirs, so this is latent, not active. (src/wiki_studio/ingestor_multi.py)
- [note] f-36b60cbe: For a path like `index.md`, the second preview is `preview/index.md.2`, which is fine, but for a path that already ends in a numeric-looking segment (e.g. `concepts/v2.md`) the `.2` suffix could be confused with a real filename. Since `plan.json` is the source of truth and promote reads the pointer, this is cosmetic only. (src/wiki_studio/ingestor_multi.py)
- [note] f-3f8907d3: The doc now says "Always read the pointer," which is good, but it does not state that the suffix is assigned by edit order within the patch-set (so `.2` is the second edit to that path, not a version). A one-clause clarification would prevent a curator from assuming `.2` means "revised". (docs/patch-set-format.md)
- [note] f-808e7a44: The test verifies the curated content lands and appears in `curator-delta.md`, but does not assert that the *first* append (`first`) also landed. A regression where the first preview is dropped while the second is applied would still pass. (tests/test_multiple_appends.py)
- [note] f-e0f52a9b: Keying by raw `edit.path` assumes paths are normalized/consistent across edits (e.g. no `./index.md` vs `index.md`). If the upstream `PageEdit` construction ever allows non-canonical paths, two edits to the "same" file could get distinct counters and both write `preview/index.md`-style collisions. The patch-set format already forbids `..` and requires wiki-relative paths, so this is defensive only. (src/wiki_studio/ingestor_multi.py)
