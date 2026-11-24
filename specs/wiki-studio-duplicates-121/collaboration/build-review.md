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

The change adds a report and a results-verification test suite for the near-duplicate study. The tests are thorough and well-structured, verifying byte-for-byte reproducibility, report consistency with recorded results, and command parsing. I found a few correctness and robustness concerns in the test code, primarily around fragile string parsing and a potential brittleness in the report-format assertions.

## Findings

- [warning] f-26a98085: The test parses candidate pair lines with `line.split(" ")` and unpacks exactly 5 fields (`left, right, score, label, scope`). If any path or label ever contains a space, or if the format gains a field, this raises `ValueError` rather than a clear assertion failure. It also silently assumes the exact field order/count of the committed JSON's `candidate_pairs` strings. (tests/test_duplicates_results.py)
- [warning] f-d26a7496: The comprehension `{rest[i]: f"{rest[i+1]} {rest[i+2]}" for i in range(0, len(rest), 3)}` assumes `rest` length is a multiple of 3 and that each candidate contributes exactly a `score` and a `found/missed` token. A malformed or extended `true_pair_scores` line would produce a `KeyError`/`IndexError` deep in the test rather than a clear failure, and a trailing partial group is silently dropped by `range` stepping. (tests/test_duplicates_results.py)
- [warning] f-eb4d47e6: The test asserts exact table-row strings appear in the report, but does not assert the *absence* of stale/incorrect rows (e.g., a leftover row from a prior candidate set, or a duplicated row). A report could contain both the correct row and an outdated one and still pass. (tests/test_duplicates_results.py)
- [note] f-e33c8fb6: The three chained `assertEqual` calls on `lines` are redundant: the first already pins `lines` to `[committed["winner_line"]]`, so the subsequent comparisons only re-verify internal consistency of the committed JSON/protocol rather than the report. If `winner_line` and `f"{WINNER_PREFIX}{winner}"` ever diverge, the failure message will point at the report test rather than the data inconsistency. (tests/test_duplicates_results.py)
- [note] f-97bcbe82: The wall-time check uses `assertIn(SECONDS_FORMAT.format(seconds), self.report)`, which is a substring match. A value like `0.150 s` would also match inside `10.150 s` or `0.1500 s`-adjacent text, and two candidates with times that are substrings of each other could cross-satisfy. Low risk given the report's prose, but the check is weaker than it appears. (tests/test_duplicates_results.py)
- [note] f-247b31da: The regex `python -m (eval\.duplicates\.\w+)([^`\n]*)` will also match a command embedded in prose or a fenced block that is illustrative rather than runnable, and it silently ignores any `python -m eval.duplicates.…` invocation whose module is not in `SCRIPTS` only via the `assertIn` — but a typo'd module name in the report would be caught, which is good. However, commands split across lines or with a leading `$ ` prompt are not matched, so a malformed shown command could escape detection. (tests/test_duplicates_results.py)
- [note] f-92e341c9: The report claims every figure is copied as recorded, but the timing section says wall times are "shown to three decimals" and the test only checks key presence for `timing.json`. This is consistent with the stated exception, but the report does not explicitly note that `timing.json` values are not CI-verified (it says "not reproduced by CI" in the Timing section, which covers it). Minor: consider cross-referencing the test name so a reader knows which claims are machine-checked. (eval/duplicates/report.md)
