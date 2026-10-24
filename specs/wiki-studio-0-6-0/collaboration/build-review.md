---
feature_id: wiki-studio-0-6-0
date: 2026-10-24
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-6-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-6-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The revision-precondition feature is well-structured and thoroughly tested: `read_page` gives one-read bytes/text/hash, `base_sha256` travels through `PageEdit`/`plan.json`/`.base.json`, and `_check_preconditions` runs under the lock before commit. I found one correctness gap in the dry-run path (preconditions checked before staged-tree validation, so a dry run can report a precondition failure that a real promote would never reach, and vice versa the ordering differs from the real path), plus a few smaller robustness/consistency notes.

## Findings

- [warning] f-8dd68f8b: In the real-promote path the order is `_validate_staged_tree` then `_check_preconditions`; in the dry-run path it is `_check_preconditions` (under lock) then `_validate_staged_tree` (after release). A proposal that fails staged validation but also has a stale base will surface as a precondition error in dry-run and a validation error in real promote — the dry-run is supposed to be point-in-time evidence of what a real promote would do, so the two should agree on which gate fires first. Also, a dry run can now report "preconditions failed" for a proposal that would never reach the precondition check because staging is invalid. (src/wiki_studio/promoter.py)
- [warning] f-d67b0e77: For `create` the check uses `os.path.lexists(live)` (correctly catching a dangling symlink or a directory at the target), but for `update` it uses `live.is_file()` and treats a non-file (directory, dangling symlink) as `live_sha = None`, producing a "live absent" message. A directory at the update target would then be reported as "the live page is not the revision this update was drafted from (… live absent)" rather than as a distinct error, and the subsequent commit would fail with a less clear message. Minor, but the two branches should be consistent about what "absent" means. (src/wiki_studio/promoter.py)
- [warning] f-cfba1da5: The symlink check walks `Path(rel).parts` and calls `probe.is_symlink()` on each prefix, but `rel` has already been `posixpath.normpath`-ed, so `..` segments are collapsed before the walk — good. However the final `target.resolve().is_relative_to(wiki)` check is the only guard against a symlinked *intermediate* directory that is itself inside the wiki but points outside; the per-component `is_symlink()` walk catches that, but only for components that exist. A symlink created between the `is_symlink()` walk and the `read_bytes()` in `read_page_content` is a TOCTOU window (small, but the docstring claims "no component of it may be a symlink"). (src/wiki_studio/api.py)
- [note] f-dac7545f: `posixpath.normpath(k)` is applied to manifest keys but the result is not validated against `..`/absolute escapes; a manifest key like `"../secret.md"` normalises to `"../secret.md"` and would be looked up in `base_hashes.get(rel)` where `rel` comes from `file.relative_to(root)` (always clean), so it is harmless today — but the manifest is agent-authored input and the normalisation silently accepts keys that can never match. A malformed-but-parseable manifest with an escaping key is accepted without complaint. (src/wiki_studio/api.py)
- [note] f-4c919bd9: `_parse_patch` rejects a non-string `base_sha256` with `PromoteValidationError`, but a string of the wrong shape (e.g. `"XYZ"`) is passed through to `PageEdit` and only caught later by `validate_patch_set` inside `_validate_before_staging`. That is fine functionally, but the error surfaces as a per-edit validation error rather than a plan-parse error, and the test `test_a_malformed_base_hash_is_refused_before_anything_is_written` relies on this. Consider validating shape here too for a clearer message and a single place that owns "what a base_sha256 looks like in plan.json". (src/wiki_studio/promoter.py)
- [note] f-d0514003: `_promote_locked` now returns a union `PromoteResult  (src/wiki_studio/promoter.py)
- [note] f-45fa8c93: The test asserts `seen == [("preconditions", True), ("validation", False)]`, which pins the current (precondition-before-validation) ordering. If the ordering is fixed per the first finding, this test must change; if the ordering is kept deliberately, the test should carry a comment saying so, otherwise a future reader will "fix" the order and be surprised by the failure. (tests/test_promote_preconditions.py)
- [note] f-5c480122: The row says "older readers ignore it" — true for the field, but an older *promoter* reading a 0.6.0 plan.json with `base_sha256` will silently apply the update without checking it, which is exactly the stale-overwrite the feature exists to prevent. Worth stating explicitly so a mixed-version deployment is not mistaken for protection. (docs/patch-set-format.md)
- [note] f-37449fbf: The hash is attached only when the prompt showed the page. If the backend returns an `update` for a page that exists but was not selected as a candidate, the edit is unguarded — correct per the design, but the resulting promote failure message tells the user to "regenerate the proposal from a fresh `wiki-studio read`", which is not actionable for an ingest-produced proposal (the user did not author it). Consider a distinct hint for ingest-origin unguarded updates. (src/wiki_studio/ingestor_multi.py)
