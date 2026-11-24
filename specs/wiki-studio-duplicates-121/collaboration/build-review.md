---
feature_id: wiki-studio-duplicates-121
date: 2026-11-24
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-duplicates-121-evidence
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-duplicates-121 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The freeze artifacts are internally consistent: the pinned hashes in `test_duplicates_frozen.py` match the values recorded in `protocol.json` and `labels.json`, the page-set check is sound, and the protocol document faithfully restates the README's prose. I found no blocking correctness issues; the findings below are warnings and notes about robustness of the freeze test and a couple of documentation/consistency points.

## Findings

- [warning] f-3595a492: The page-set check uses `CORPUS_DIR.rglob("*")` and filters `is_file()`, which will also pick up any stray files (e.g. `.DS_Store`, editor backups, `__pycache__` artifacts) placed under `corpus/`, causing spurious failures unrelated to the frozen corpus. It also silently ignores empty directories, which is fine, but the stray-file sensitivity is a real fragility for a "never edited" test. (tests/test_duplicates_frozen.py)
- [warning] f-771e3ca6: The test pins `README.md` by hash, but the README is the human-facing document that the spec says may gain a "disagreement found later" section in the report — not the README — so this is consistent. However, pinning the README means any future typo fix or clarification to the README (which is not a scored artifact) will fail the freeze test, conflating "frozen study inputs" with "frozen documentation." (tests/test_duplicates_frozen.py)
- [note] f-7eea8e2a: The README states rule 6's pattern as `[a-z][0-9]{1,2} (eval/duplicates/README.md)
- [note] f-1dd70f3c: The integer form `4 * shared >= union` is stated as equivalent to Jaccard `>= 0.25`, which is correct only because `shared/union >= 1/4` ⇔ `4*shared >= union` for `union > 0`. The `empty_union` note covers the `union == 0` case, so this is sound, but the protocol does not state that `shared` and `union` are integer cardinalities of token sets (it is implied by "size of the intersection/union" in the README but not in the JSON). (eval/duplicates/protocol.json)
- [note] f-d9e6d03e: The README correctly notes the review-sample's `drawn_from_labels_sha256` differs from `labels_sha256` because the owner changed one label after the draw. This is good transparency, but the protocol's `review_sample.owner_changed_labels_after_the_draw: true` flag is the only machine-readable signal; a scorer reading `protocol.json` alone would not know which label changed or that the sample's labels are stale relative to `labels.json`. (eval/duplicates/README.md)
- [note] f-8f820780: The test asserts `protocol["corpus_sha256"] == FROZEN_FILE_SHA256[CORPUS_JSON]` and the same for labels, which is correct, but it does not assert that `protocol.json`'s own hash is consistent with anything (it can't be, self-referentially) nor that `review-sample.json`'s recorded `drawn_from_labels_sha256` is present. The latter is a documented invariant in the README; a light assertion would catch accidental edits. (tests/test_duplicates_frozen.py)
