---
feature_id: wiki-studio-duplicate-audit-121
date: 2026-11-27
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-duplicate-audit-121-evidence
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-duplicate-audit-121 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The audit script is well-structured and the test suite is thorough, covering the frozen-input checks, mutual-rank logic, restatement rules, bar/selection/stop-rule edges, and refusals. I found a few correctness concerns around the `flagged` function's rank computation, the `select_winner` tie-breaking logic, and some edge cases in the synthetic-page and page-type filtering paths that warrant attention before this is considered done.

## Findings

- [warning] f-0f2f1d96: The rank is computed via `list(listed).index(other)`, which is O(n) per lookup and, more importantly, relies on `listed` being a list-like that supports `.index`. If `lists` values are ever passed as tuples or other sequences without `.index`, this raises `AttributeError`. The `Mapping[str, Sequence[str]]` type hint permits tuples, but the code assumes `.index`. Also, if a page appears twice in a list (shouldn't happen, but not enforced), `.index` returns the first occurrence, silently misreporting the rank. (eval/duplicate_audit/audit.py)
- [warning] f-f9075223: The tie-break "a tie to the smaller k" is implemented by iterating `sorted(candidates, key=lambda c: c[1])` and only replacing `best` on a strict `<`. This works for the ratio comparison, but the docstring says "a tie to the smaller k" — the code relies on iteration order (ascending k) plus strict `<` to preserve the first (smallest-k) winner on ties. That is correct, but fragile: if `candidates` ever contains duplicate k values or the sort key changes, the invariant silently breaks. Also, `int(counts["false"]) * int(best[2]["true"]) < int(best[2]["false"]) * int(counts["true"])` divides by zero implicitly when `true == 0` on both sides — `0 < 0` is False, so a candidate with `true == 0` and `false == 0` (passing bar only if `min_true_pairs == 0`) would never be selected even though it's arguably the best. Given `min_true_pairs >= 1` in the frozen protocol this is currently unreachable, but the function is not defensive. (eval/duplicate_audit/audit.py)
- [warning] f-0e231ae1: If `pages` is empty (empty corpus), `len(pages) == 0` and `i % 0` raises `ZeroDivisionError`. The `audit` function calls `synthetic_pages(pages, count)` unconditionally on the held-out path. An empty held-out corpus is unlikely but not guarded, and the error would surface as a `ZeroDivisionError` caught by the broad `except` in `run`, producing a confusing "nothing was written" message rather than a clear diagnostic. (eval/duplicate_audit/audit.py)
- [warning] f-02385c7f: `lists[page.key] = [by_path[path].key for path in ranked if by_path[path].page_type == page.page_type]` assumes every path returned by `index.rank` is in `by_path`. Since `order` is built from `pages` and the index contains exactly those rows, this holds — but only because `similar_query`/`rank` is trusted to return only paths from `order`. If `rank` ever returns a path not in `order` (e.g., a future change to `SearchIndex.rank`), this raises `KeyError` mid-loop, leaving the connection in a state where the deleted row was not re-inserted (the `INSERT_ROW` after `rank` is skipped). The `with SearchIndex(connection)` context manager may or may not roll back; the in-memory DB is discarded anyway, but the failure mode is opaque. (eval/duplicate_audit/audit.py)
- [warning] f-adc3ec44: The script deletes a row and re-inserts it with `INSERT_ROW` (no explicit rowid). In SQLite FTS5, deleting and re-inserting assigns a new rowid, which changes the internal ordering. The test `test_every_list_equals_a_fresh_index_without_the_page` compares against a fresh index built without the page, and passes — but that's because `rank` is called with an explicit `order` list, so rowid ordering doesn't affect the result. However, if `SearchIndex.rank` ever falls back to rowid order for ties, the remove-and-reinsert pattern would produce different tie-breaking than a fresh index. This is a latent correctness hazard documented as "pitch finding 12" but not fully pinned by a test that exercises tie-breaking. (eval/duplicate_audit/audit.py)
- [note] f-e19b949d: `if (root / chosen.corpus_json).is_file(): problems += check_pages(...)`. If `corpus.json` is missing but `freeze.json` pins its hash, the freeze check already reports the mismatch (since `_sha256_or_missing` returns `"missing"`). So the page check is correctly skipped. But if `corpus.json` exists and is valid per freeze, yet a page file is missing, `check_pages` catches it. This is correct, but the asymmetry (development always checks pages, held-out conditionally) deserves a comment explaining why. (eval/duplicate_audit/audit.py)
- [note] f-5a7ee0f1: `winner_verdict, no_candidate, not_testable = protocol["verdicts"]` assumes exactly three elements in a specific order. If the protocol ever adds a fourth verdict or reorders, this silently misassigns. The frozen protocol is pinned by hash, so this is safe today, but the coupling is implicit. (eval/duplicate_audit/audit.py)
- [note] f-bb074d8d: `round(count * PER_100 / pages, PER_100_DIGITS) if pages else 0.0` — correct, but `pages` is `len(pages)` from the corpus, which is guaranteed non-empty only if `corpus.json` has at least one page. An empty corpus would yield `pages == 0` and `_per_100` returns `0.0`, which is fine, but `synthetic_pages` would then crash (see above). (eval/duplicate_audit/audit.py)
- [note] f-b8821438: The test compares only `<set>.json` bytes across two runs, not `<set>-timing.json`. That's correct (timing is non-deterministic), but the docstring says "the same bytes twice (FR-016)" without qualifying that timing is excluded. A reader might assume both files are byte-identical. (tests/test_duplicate_audit_script.py)
- [note] f-8bfdc515: `test_eval_is_unchanged_by_a_run_elsewhere` runs against the real repository's `eval/` directory and the real `protocol.json`. If the real development corpus is not frozen (e.g., a developer edited a page locally), this test fails with a refusal rather than a clear "inputs not frozen" message. It also makes the test suite depend on committed state that may drift. (tests/test_duplicate_audit_script.py)
- [note] f-0c762c1a: `except (OSError, ValueError, KeyError, TypeError, sqlite3.Error)` catches `KeyError` and `TypeError`, which can mask programming errors (e.g., a typo in a dict key) as "nothing was written" refusals. This is intentional for robustness but makes debugging harder. (eval/duplicate_audit/audit.py)
