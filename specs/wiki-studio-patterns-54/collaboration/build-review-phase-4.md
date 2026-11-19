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

The US4 trace and retrieval scripts are well-structured, deterministic, and correctly exercise the real CLI verbs in-process against temporary copies. I found one correctness issue in the retrieval `hit_at_5` computation that can silently misreport a miss as a hit when a question has multiple gold pages, plus a couple of smaller robustness notes. The trace script and its committed result look sound.

## Findings

- [warning] f-d3f6bb1f: `hit_at_5` is computed as `all(page in selected for page in gold)`, which is vacuously True when `gold` is empty and, more importantly, conflates "all gold pages retrieved" with "the gold page retrieved within top 5". For a single-gold question this is fine, but the semantics differ from `hit_at_1` (which checks `selected[0] in gold`) and from the README's "hit at 5" wording. If any question ever has multiple gold pages, a partial retrieval would be scored as a miss even though the primary target was found, and an empty `gold` would score as a hit. (eval/patterns/retrieval.py)
- [note] f-ed41b677: The docstring says "True when the trap is above the reuse target, or present while the target is absent", but the code returns `target is None or target not in selected or selected.index(trap) < selected.index(target)`. When `target is None` this returns True whenever the trap is present, which matches the docstring, but the `target is None` branch is only reachable if a question sets `trap` without `reuse_target` — worth a guard or a comment so a future question author doesn't accidentally get a "trap outranks" credit with no target to compare against. (eval/patterns/retrieval.py)
- [note] f-6b2c3a0f: The helper inserts `superseded_by:` immediately before the first line starting with `sources:`. If a page ever has `sources:` as a nested key (e.g. inside another mapping) or a comment line beginning with `sources:`, the insertion lands in the wrong place. The current fixture page is fine, but the helper is fragile against future fixture edits. (eval/patterns/trace.py)
- [note] f-fc018fb7: The index-first test compares `actual["rankers"]["index-first"]` to the committed value but does not compare `questions_sha256`, `max_pages`, or `environment`. The separate `test_retrieval_records_the_questions_hash` covers the hash, but `max_pages` and `environment` drift would go unnoticed for the index-first path (the fts5 test also skips these). (tests/test_patterns_eval.py)
- [note] f-a89e3519: `(state,) = api.review_state(paths, pages=[page])` assumes exactly one state is returned for a single-page query. If `review_state` ever returns zero or more than one entry for a single page (e.g. a future change to include superseded pages separately), this raises `ValueError` with an opaque message. The trace would then fail with a confusing error rather than a clear one. (eval/patterns/trace.py)
- [note] f-ba50133b: The README states the test suite "compares every `index-first` entry on any machine and every `fts5` entry wherever this Python's SQLite has FTS5", which matches the tests, but it does not mention that `questions_sha256`, `max_pages`, and `environment` are only partially checked (see testing finding above). Minor, but the README's claim of coverage is slightly stronger than the tests enforce. (eval/patterns/README.md)
