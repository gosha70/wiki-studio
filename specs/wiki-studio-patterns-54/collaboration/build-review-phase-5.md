---
feature_id: wiki-studio-patterns-54
date: 2026-11-18
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-patterns-54
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-patterns-54 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The US5 duplicate-candidates script is well-structured and correctly enforces the frozen-labels precondition before computing anything. The signal implementations match the documented FR-014 semantics, and the test coverage exercises the frozen-hash refusal path, README consistency, and result reproducibility. I found a few correctness and design concerns worth addressing, but nothing that blocks the feature.

## Findings

- [warning] f-76d17ab9: When both pages have empty token sets, `union` is empty and the pair is skipped (correct), but when only one side is empty the intersection is empty and the ratio is 0 — fine. However, `_tokenise` is imported from `wiki_state` and its exact tokenisation contract (stopwords, stemming, casing) is not asserted anywhere; if `_tokenise` changes, the (b) signal silently drifts from the frozen protocol without any test catching it. The committed `duplicates.json` would then mismatch and the test would fail, but only after the fact. (eval/patterns/duplicates.py)
- [warning] f-969e1539: For `combined`, the mark is `link_only and not b_fired and not c_fired`. But `link_only` is computed from `parts` (the (a) parts), which is only populated when the pair is in `a_candidates`. For a pair that fires only via (b) or (c) and is also an annotation pair, `parts` is `()` so `link_only` is False — correct. But for a pair that fires via (a) direct-link AND (b), the mark is False even though the pair is annotation-linked; the README says "a pair found only through such a link is marked `annotation_linked`", which matches. Still, the asymmetry between `a` (marks any link-only hit) and `combined` (marks only if b and c did not fire) is subtle and undocumented in code. (eval/patterns/duplicates.py)
- [warning] f-9f86b685: The `wiki_dir` argument is passed as an absolute `Path` (`fixture`), while `for_root` is given `fixture.parent`. If `WikiPaths.for_root` expects `wiki_dir` to be relative to the root, this would resolve incorrectly; if it expects absolute, it works. The test suite passes, so it works today, but the contract is implicit and fragile. (eval/patterns/duplicates.py)
- [warning] f-4394b1ca: `_entity_vocabulary` walks `fixture.rglob("*.md")` to build the entity slug list, but `_page_info` only reads pages listed in the manifest. If the fixture contains markdown files not in the manifest (e.g., a stray draft), those slugs enter the vocabulary and can inflate `_entity_mentions` counts, changing (c) results without any manifest change. The committed result is stable today, but the coupling is invisible. (eval/patterns/duplicates.py)
- [note] f-ea46ea11: The skip list treats any block starting with `- `, `* `, `+ ` as non-prose, so a Decision section whose first paragraph is a bulleted list yields an empty first paragraph and (b) falls back to an empty token set. That is a defensible choice, but it means (b) silently degrades for list-first Decisions. The README does not mention this. (eval/patterns/duplicates.py)
- [note] f-7effc0ef: `rests_on_annotation_links` is `true_count > 0 and linked_true == true_count`. For a signal that finds zero true pairs (like (c)), this is False — correct. But for a signal that finds all true pairs and all are annotation-linked, it is True, which the README says never happens here. The definition is fine, but the name suggests "the verdict depends on annotation links", which is only true when the signal also passes. A signal that fails but finds only annotation-linked true pairs would report `rests_on_annotation_links: true` despite the verdict not resting on them. (eval/patterns/duplicates.py)
- [note] f-d4257483: The test calls `record_result(actual, "duplicates.json")` on mismatch, which writes the committed file. In CI this would silently rewrite the golden file rather than fail. The other US4 tests use the same pattern, so this is consistent with the existing convention, but it means a regression in `duplicates.py` would be auto-accepted on the next run. (tests/test_patterns_eval.py)
- [note] f-7bb11deb: The README states the (a) false-candidate breakdown as "3 distinct-by-precondition, 0 unrelated, 33 background unlisted" — matching the JSON. But the prose says "(a) and `combined` find all three but return 36 false candidates against 3 true", which is correct. The table's "Annotation-linked among those" column for (a) shows 1, matching `found_labelled_annotation_linked: 1`. Consistent. (eval/patterns/README.md)
- [note] f-242a171a: If `protocol.json` is missing or malformed, `check_frozen` raises an uncaught exception rather than returning 1 with a clear message. The frozen-label mismatch path is handled, but a missing protocol file produces a traceback. (eval/patterns/duplicates.py)
