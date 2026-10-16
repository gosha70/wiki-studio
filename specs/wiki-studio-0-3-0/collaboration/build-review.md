---
feature_id: wiki-studio-0-3-0
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
target_ref: feature/wiki-studio-0-3-0
rounds_completed: 2
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-3-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 2
**Verdict**: PASS

## Summary

Round 2 review of the navigation evaluation feature. The builder addressed most Round 1 findings with documentation and defensive fixes; two findings were disputed with reasonable spec-based justifications. I found one new correctness issue in the `excluded_reason` logic that affects `answered_by_index` questions, plus a few minor notes.

## Findings

- [warning] f-04b753fb: The `excluded_reason` for a question whose gold is `INDEX_NAME` is set to `"answered_by_index"`, but the `hit_at_1`/`hit_at_max`/`wiki_words`/`grep_words` fields are left `None` because the `if entry["excluded_reason"] is None:` guard skips them. This is intentional per the builder's resolution of f-6d06b89e, but the `answered_by_index` list is computed from `with_gold` (which includes index-gold questions) while `evaluated` excludes them — so `navigation.evaluated` and `navigation.answered_by_index` are disjoint, which is correct, but the `words.evaluated` count and `ratio_set` also exclude them silently. A reader comparing `counts.with_gold` (3) to `navigation.evaluated` (3) will not see the index-gold questions at all in the aggregate. In run 1 there are zero such questions, so the bug is latent, but the aggregate counts will silently drop index-gold questions once any exist. (eval/navigation/run.py)
- [note] f-709e2059: The builder's dispute of f-cf677c0b is defensible under FR-005's literal wording, but the comment added does not mention that when gold is absent from `selected`, `gold_pos = len(sel)` and any selected distractor returns `True` — which is the same as "gold missing entirely." The comment says "a gold page outside the selection ranks below every selected page," which is the justification, but a future reader may not realize this conflates two failure modes in the `distractor_outranks` metric. The `hit_at_max` field does separate them, as the builder notes. (eval/navigation/run.py)
- [note] f-8cd7690c: The builder's dispute of f-5dcb4dc4 is correct that `grep -w` treats hyphens as non-word characters, so `page-type` matches inside `page-type-export`. However, the docstring says "the same word constituents as `grep -w` (letters, digits, underscore)" — this is accurate for `\b` but the reader may not connect that a hyphenated token like `page-type` will match `page-type-export` because the hyphen is a boundary. The docstring does say this explicitly in the next sentence, so this is a minor clarity note only. (eval/navigation/run.py)
- [note] f-a7cf6f7a: The test copies the fixture with `ignore_patterns("proposals", "ingest-logs", "__pycache__")` but does not ignore `results.json`. Since `compute()` does not read `results.json`, this is harmless, but if `compute()` ever gains a dependency on it the test would silently use stale data. Low risk. (tests/test_navigation_eval.py)
- [note] f-15d3f2b0: The row says "over the same 3 questions (none had empty grep output)" — this correctly addresses f-3376048f. However, the `words.evaluated` field in `results.json` is 3, matching `navigation.evaluated`, but the README does not state that `words.evaluated` equals `navigation.evaluated` by construction (both filter on `gold != INDEX_NAME` and `grep_words` truthiness). A reader may wonder if the two 3s are coincidental. (README.md)
- [note] f-7f796f6d: The builder's dispute of f-64a52dd0 is correct that `CONTEXT_LINES` is fixed at 2 by the spec, and the merge of touching windows with 0 context would join adjacent matching lines whose word count is identical either way. However, the function is public-ish (used by tests) and the `+ 1` in `start <= merged[-1][1] + 1` is a subtle off-by-one that only makes sense with context > 0. A future change to `CONTEXT_LINES` could silently change behavior. (eval/navigation/run.py)
