---
feature_id: wiki-studio-0-3-1
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
target_ref: fix/15-index-actions
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-3-1 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The change is a focused prompt-contract fix for issue #15: a single `INDEX_LOG_ACTION_RULE` constant is threaded into the multi-page prompt, the wiki-state text, and the patch-set schema, with the validator deliberately untouched. The implementation is small, well-tested, and matches the spec's FR-001–FR-005. I found no blocking correctness issues; a few notes concern test robustness and one minor prompt-wording ambiguity.

## Findings

- [note] f-be629640: The rule text says "index.md (and any <dir>/index.md) changes only through an 'append-index' edit" but does not explicitly forbid `append-index` on a non-index path or `append-log` on a non-log path; the validator presumably enforces this, but the prompt could be read as permitting `append-index` on any file. The spec only requires the rule as stated, so this is a wording nit, not a contract gap. (src/wiki_studio/prompt.py)
- [note] f-549e5d49: The negative assertion `self.assertNotIn(f" {root_type}", INDEX_LOG_ACTION_RULE.split("content pages")[1])` is brittle: it depends on the exact substring "content pages" appearing once and on the leading-space prefix. If the rule is reworded (e.g., "content page types"), the split silently yields the whole string and the test may pass vacuously or fail spuriously. (tests/test_index_actions.py)
- [note] f-829ebdf2: The test asserts two specific validator messages ("page_type 'index' is not promotable for create/update" and "'sources:' must be a non-empty list"). This couples the test to validator internals; if the validator's message wording changes in a future release, the test breaks even though behavior is unchanged. Acceptable for a regression test pinned to this release, but worth a comment noting the coupling. (tests/test_index_actions.py)
- [note] f-b020bcf3: The rule is appended after the path-prefix instruction and before the gate-only branch. For the `gate-only` task, the rule is still appended even though gate-only presumably does not produce edits. This is harmless (extra context) but slightly inconsistent with the "legacy prompt is unchanged" intent for non-multi tasks. (src/wiki_studio/backends/copilot_cli.py)
- [note] f-45080550: The CHANGELOG states "Run 2 is kept as measured on 0.3.0," which is good, but does not mention that the fix is prompt-only and that no validator behavior changed. The spec's FR-002 makes this explicit; a one-line note in the CHANGELOG would help consumers understand the fix is advisory to the model, not a new enforcement. (CHANGELOG.md)
- [note] f-1bdc333e: The constant is built by string concatenation with `", ".join(sorted(PROMOTABLE_PAGE_TYPES))` at import time. This is fine, but it means the rule text is not a literal and cannot be grepped as a whole in the source. Minor maintainability note; the test `test_rule_lists_exactly_the_promotable_types` covers the dynamic part. (src/wiki_studio/prompt.py)
