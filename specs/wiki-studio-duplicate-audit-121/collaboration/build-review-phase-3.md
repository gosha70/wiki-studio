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

The change adds a development-stage report and a test module that verifies the committed results reproduce byte-for-byte and that the report's tables match the committed JSON. The tests are well-structured and the report is internally consistent with the described protocol. A few correctness and robustness concerns remain around the report-parsing tests and the rerun's environment assumptions.

## Findings

- [warning] f-be93f876: The regex `python -m (eval\.duplicate_audit\.\w+)([^`\n]*)` will also match the module name inside prose or fenced blocks that aren't actual commands, and `shlex.split(rest)` on trailing prose (e.g. "and checks that...") could raise or parse garbage. The test asserts `module in SCRIPTS` which will fail loudly if a future doc mentions a different module, but the failure mode is opaque. More importantly, `rest` may include trailing punctuation/words from the sentence, so `parse_args` may silently accept them as positional args or error confusingly. (tests/test_duplicate_audit_development.py)
- [warning] f-5ae14c0d: Byte-for-byte equality of `development.json` depends on stable JSON serialization (key order, separators, float formatting) and on the environment (SQLite FTS5 tokenizer version, porter stemmer behavior). The test skips only when FTS5 is absent, but a different SQLite build with a different porter implementation could produce different rankings and thus different bytes, causing spurious CI failures across environments. (tests/test_duplicate_audit_development.py)
- [warning] f-2dec26a8: `snapshot_tree(EVAL_DIR)` is taken before and after the rerun, but the rerun writes to a temp dir outside `eval/`. This test only proves the script doesn't write into `eval/` — it does not prove the script doesn't mutate inputs elsewhere (e.g., a cache dir, `__pycache__` is excluded, but other side effects like `.sqlite` temp files under repo root would be missed). The claim in the docstring ("leaves eval/ unchanged") is narrower than the report's claim that the script "reads nothing outside the repository" and "runs no git". (tests/test_duplicate_audit_development.py)
- [note] f-200b40be: `assertIsInstance(timing["seconds"], float)` will fail if the value is an `int` (e.g., `0` or `1` serialized as integer). JSON round-trips `0.0` as `0.0` but a producer writing `int(seconds)` would break. Consider `assertIsInstance(timing["seconds"], (int, float))` or `assertGreaterEqual`/`assertIsInstance(..., numbers.Real)`. (tests/test_duplicate_audit_development.py)
- [note] f-d2704a00: `candidate_row` reconstructs the expected row from `development.json`, so this test verifies the report matches the JSON — but if both were generated from the same buggy source, the test passes. That's acceptable given the byte-for-byte rerun test, but the two tests are coupled: if the rerun test is skipped (no FTS5), the report-vs-JSON test still passes even if the JSON itself is wrong. Worth noting the coverage gap when FTS5 is unavailable. (tests/test_duplicate_audit_development.py)
- [note] f-f0407be2: These are strong claims asserted in prose but only partially tested (the rerun test checks `eval/` unchanged, not network/git/model). If the audit script's behavior changes later, the report could silently become false. Consider referencing the specific test that enforces each claim, or softening to "the rerun test confirms it writes only to the given out-dir." (eval/duplicate_audit/report.md)
- [note] f-ccf61cf9: The `SCRIPTS` mapping is hardcoded to `{"eval.duplicate_audit.audit": audit}`. If the report later references another module (e.g., a future `eval.duplicate_audit.verify`), the test fails with `assertIn(module, SCRIPTS)` rather than a clear "unknown module in report" message. Minor, but the failure message will be a bare assertion. (tests/test_duplicate_audit_development.py)
