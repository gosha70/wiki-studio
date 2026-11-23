---
feature_id: wiki-studio-0-11-0
date: 2026-11-23
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-11-0-evidence
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-11-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The freeze test is well-structured and correctly pins the study files and case files by sha256, with a sensible exception for `record.py`-written `hunks.json` files. The main correctness concern is that the exception predicate `is_recorded_hunks` uses `path.parent.parent == KEYWORD_QUOTING_DIR`, which is fragile against symlinks/`..` segments and, more importantly, does not verify the file is actually a regular file at the expected depth — but the bigger issue is that the test does not guard against the freeze test file itself being edited, and the `case_files_present` walk will silently miss files if `CASES_DIR` doesn't exist (raising `FileNotFoundError` rather than a clear assertion). Overall the test is sound for its stated purpose.

## Findings

- [note] f-59753a97: `path.parent.parent == KEYWORD_QUOTING_DIR` compares `Path` objects by string equality of their resolved-or-not forms; if `CASES_DIR.rglob` ever yields paths with different normalization (e.g., symlinked `eval/revisions`), the comparison could silently fail and cause `hunks.json` to be treated as a frozen case file, breaking the test on legitimate `record.py` output. (tests/test_revisions_frozen.py)
- [note] f-8dd3aa21: If `CASES_DIR` does not exist (e.g., a checkout missing the eval tree), `rglob` returns an empty iterator and the test `test_pinned_case_files_are_exactly_the_case_files_present` fails with a confusing "set() != {…}" message rather than a clear "cases directory missing" error. (tests/test_revisions_frozen.py)
- [note] f-ef100746: The test asserts `is_recorded_hunks` returns False for `case_dir / "nested" / RECORDED_HUNKS_NAME`, but does not assert True for a `hunks.json` at the correct depth in a *different* keyword-quoting case id (e.g., `pre-pr-doc-audit/hunks.json`), so a regression that hardcodes `pre-pr-strict-mode` would not be caught. (tests/test_revisions_frozen.py)
- [note] f-0bc54635: The docstring says "This module is written once and never edited after the US2 phase," but there is no mechanism (e.g., a self-hash or a CI check) enforcing that; the claim is aspirational and could mislead a future maintainer into thinking the test is tamper-evident. (tests/test_revisions_frozen.py)
- [note] f-433ad629: The pinned hashes are hardcoded literals with no provenance comment (e.g., the commit sha they were taken from), making it hard to audit whether the pins match the reviewed commit `af53cef`/`1be4060`. (tests/test_revisions_frozen.py)
