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

The scorer implementation is well-structured, deterministic, and thoroughly tested. The frozen-input guard, integer threshold arithmetic, and protocol-driven candidate construction are all sound. I found a few correctness concerns around edge cases in the secondary fixture path, the `select` tie-break logic, and error handling that could mask real failures, but none appear to invalidate the primary scoring path.

## Findings

- [warning] f-54aeaac6: The tie-break key `(false_candidates, name != tie, order.index(name))` relies on `name != tie` being False for the tie candidate, but if `tie` is not in `passing` (e.g., B0 fails the bar while B1 passes), the tuple still works — however if `tie` is not in `order` at all, `order.index(name)` is fine but the intent is unclear. More importantly, if `tie` names a candidate not in `passing`, the second element is always True for all passing candidates, so the tie-break silently degrades to `order.index`. This is correct behavior but fragile; consider asserting `tie in order` at load time. (eval/duplicates/candidates.py)
- [warning] f-60689282: `recorded.update(...)` for `pattern_pairs` silently overwrites any key collision with `background_pairs`. If a pair appears in both lists with different dispositions, the pattern_pairs value wins without warning. For a "not binding" secondary artifact this is low-risk, but silent overwrite could mask a fixture inconsistency. (eval/duplicates/candidates.py)
- [warning] f-d3c6eed4: The `except (OSError, ValueError, KeyError)` block catches `KeyError` from protocol field access but not `TypeError` (e.g., if `protocol["candidates"]["order"]` is not iterable) or `re.error` from a malformed pattern. A malformed protocol would crash with a traceback rather than the clean "nothing was written" message, and worse, could partially write if the exception occurs after `out_dir.mkdir`. (eval/duplicates/candidates.py)
- [warning] f-2253910d: `true_labels = list(protocol["labels"]["true"])` is used both for membership (`pair.label in true_labels`) and for `by_disposition` key ordering. If the protocol's `true` list order differs from `reporting_splits.by_disposition` order, the output dict key order will follow the protocol's `true` list, not the reporting splits. Since output is `sort_keys=True` this is cosmetic, but the `by_disposition` dict is built from `true_labels` rather than `splits["by_disposition"]`, so a disposition in `splits` but not in `true` would be silently omitted. (eval/duplicates/candidates.py)
- [warning] f-becf1afc: `stated` merges `labels["pairs"]` and `labels["cross_pairs"]` via dict comprehension; a pair appearing in both with different dispositions silently takes the `cross_pairs` value. Same class of issue as the secondary fixture. (eval/duplicates/candidates.py)
- [note] f-06c9920a: `eligible` filters out pages where `superseded_by(texts[rel]) is not None`, but `page_texts` is built from `eligible` while `pairs` is `combinations(eligible, 2)` — consistent. However `pages` in the output reports `len(rels)` (all pages) while `eligible_pages` reports `len(eligible)`; the `pairs` count is over eligible only. This is documented but a reader could misread `pages` as the pair basis. (eval/duplicates/candidates.py)
- [note] f-caa8e8a9: If `protocol["threshold"]["numerator"]` were negative (malformed protocol), `is_candidate` would return True for any non-empty union. No validation guards against this. (eval/duplicates/candidates.py)
- [note] f-075f2710: If `pages == 0` (empty corpus), `Decimal(0) / Decimal(0)` raises `InvalidOperation`. The `check_frozen` guard doesn't prevent an empty-but-hashed corpus. `score_corpus` would then crash inside `candidate_view` after `corpus_pages` returns `[]`. (eval/duplicates/candidates.py)
- [note] f-96cc261b: `text_rules` are applied in order via `pattern.sub`, and B1's rules are `base.text_rules + text_rules`. If a B1 text rule's replacement could be re-matched by a later rule, order matters. The protocol defines the order, so this is by design, but a comment noting "rules apply in protocol order, first to last" would aid future maintainers. (eval/duplicates/candidates.py)
- [note] f-29154fd4: `test_eval_duplicates_is_unchanged_by_a_run_elsewhere` runs against the real committed corpus and labels. If those are ever regenerated (e.g., during US6), this test's `before` snapshot will still pass (it snapshots at test time), but the test depends on the real `protocol.json` hashes matching the real files — which is the intended invariant. Good coverage; consider also asserting the run's exit code is 0 explicitly (it is, via `assertEqual(code, 0, stderr)`). (tests/test_duplicates_eval.py)
- [note] f-f59eeea1: The docstring says "the true pairs by disposition and by scope" but the output also includes `by_repository` for true pairs? Checking `candidate_view`, `by_repository` is per-candidate, not in `true_pairs`. The docstring is accurate. No issue. (eval/duplicates/candidates.py)
- [note] f-c0bfd75b: `_tokenise`, `_title`, `_first_paragraph` are imported from other modules despite the leading underscore. This is intentional per the docstring ("imported read-only"), but it couples the eval to private APIs. If those helpers change signature, the eval breaks silently at import time. (eval/duplicates/candidates.py)
