---
feature_id: wiki-studio-similar-121
date: 2026-11-25
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-similar-121-evidence
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-similar-121 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The change freezes the similar-pages study protocol (README + protocol.json) and adds a test that pins both files by sha256, verifies every input hash, and checks that the 13 tries match the true pairs of the frozen duplicate labels. The design is sound and the test is well-scoped for a "freeze before scoring" phase. I found one correctness concern in the test's coverage assertion and a couple of minor notes.

## Findings

- [warning] f-72535662: The coverage test asserts `tried == set(true_pairs(self.labels))`, but `true_pairs` includes `conflicting` dispositions. The protocol's `direction_rule` says a `conflicting` pair would be tried both ways, yet the README states the frozen labels hold 0 `conflicting`. If a future label edit adds a `conflicting` pair, this test would fail with a confusing message rather than a clear "protocol must be updated" signal — and conversely, the test does not verify the direction rule (redundant both ways, supersedes once, later-as-query) beyond the redundant-both-ways check. (tests/test_similar_frozen.py)
- [note] f-548db702: The protocol pins the `supersedes` direction (later ruling as query) via a hand-written table in the README, but the test only checks that each supersedes try is a true pair — it does not verify the query is the *later* page. A swapped direction would pass the freeze test silently. (eval/similar/protocol.json)
- [note] f-dca9b2d8: The README says "the 34 fixture pages `index.md` links" but the `inputs` array in protocol.json lists 39 entries (5 top-level + 34 fixture pages). The count is consistent, but the README's phrasing ("the 34 fixture pages") could be misread as the total input count. Minor clarity issue. (eval/similar/README.md)
- [note] f-30546cd5: The protocol hardcodes `weights: [4.0, 4.0, 2.0, 1.0]` and `tokenizer: "porter unicode61"` as literals alongside a reference to `discovery.DEFAULT_RANKER_CONFIG`. If the default config changes upstream, the protocol's literal values and the actual ranker would diverge, and the freeze test would not catch it (it only hashes inputs, not the ranker config). (eval/similar/protocol.json)
- [note] f-f90096d0: The test verifies input hashes but does not verify that `protocol.json`'s `inputs` list actually covers the corpus pages (those are pinned transitively via `corpus.json` by `test_duplicates_frozen.py`). This is documented in the docstring, so it's acceptable, but a reader might expect the similar study's freeze to be self-contained. (tests/test_similar_frozen.py)
