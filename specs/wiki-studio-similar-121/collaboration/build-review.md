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

The change adds a report (`eval/similar/report.md`) and a test module (`tests/test_similar_results.py`) that verify the committed results are reproducible and that the report faithfully states the recorded figures. The tests are well-structured and the report is thorough, but there are a few correctness concerns around the report's self-consistency checks and the test's coverage of the report's claims.

## Findings

- [warning] f-ab3e50f7: The noise test asserts `row(label, count)` appears in the report, but the report's noise table has a header row ` (tests/test_similar_results.py)
- [warning] f-2fd9399d: The report states "at least 1 of the 3 `supersedes` tries found (1, holds, at the limit)". This is a binding verdict condition, but the test suite only checks the verdict line matches `ranks.json`'s verdict — it does not independently recompute the bar conditions from the try records. If `ranks.json`'s verdict were wrong relative to its own tries, the test would still pass. (eval/similar/report.md)
- [warning] f-1e007983: The report claims "The whole-page reading matches the query rule on every `redundant` try and loses the memkernel `supersedes` try." The test `test_the_report_states_each_readings_ranks_as_recorded` checks each row's cells appear, but does not verify the prose claim (that whole-page matches binding on all redundant tries). A transcription error in the prose would go undetected. (eval/similar/report.md)
- [note] f-5b8313e4: The fixture test checks `superseded_left_out` and `never_listed` pages appear as code spans, but does not verify the fixture's stated page count (32 pages, 2 superseded left out) or that the "third true pair" prose matches `never_listed`. The prose claim "It was not ranked" is unverified. (tests/test_similar_results.py)
- [note] f-165805b0: The test checks each `SECONDS_FORMAT.format(seconds)` appears somewhere in the report, but does not tie each formatted time to its named reading. A swap of two times (e.g., binding 0.099 s vs whole-page 0.105 s) would still pass since both strings appear. (tests/test_similar_results.py)
- [note] f-419218ae: The command regex `python -m (eval\.similar\.\w+)([^`\n]*)` will match the command inside the fenced code block, but `shlex.split(rest)` on `--out-dir DIR` will succeed even if `DIR` is a placeholder that the parser would reject at runtime. This is acceptable for a parse-only check, but the test name "every shown command parses" slightly overstates what is verified (it parses, not that it runs). (tests/test_similar_results.py)
- [note] f-255e5272: The report's limits are honest and well-stated, but the "Development data" limit notes two readings were run before the protocol was written. This is a material caveat for a "pass" verdict; consider whether the verdict line itself should carry a qualifier, or whether the protocol's `verdict_lines` already encodes this. (eval/similar/report.md)
- [note] f-3e7a3e82: The snapshot excludes `__pycache__` by name, which is correct, but does not exclude other transient artifacts (e.g., `.pytest_cache`, editor swap files) that could appear under `eval/` during a run. In practice `rank.py` writes only to `--out-dir`, so this is low risk. (tests/test_similar_results.py)
