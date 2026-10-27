---
feature_id: wiki-studio-0-7-0
date: 2026-10-26
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-7-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-7-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The change adds a well-structured test suite for the memkernel bridge contract, a snapshot-hazard reproduction, and a clean-install CI job. The tests are thorough and the documentation is clear. I found a few correctness and robustness concerns in the test helpers and CI configuration, but nothing that blocks the feature's intent.

## Findings

- [warning] f-481648f1: The filter `path.name == "plan.json" and ".audit" in path.parts` matches any `plan.json` anywhere under a directory literally named `.audit`, but the docstring claims it tracks `.audit/**/plan.json` specifically. If a wiki ever contains a nested `.audit` directory outside the proposals tree (e.g. a page directory named `.audit`), the snapshot would include unrelated files. More importantly, the restore loop deletes any tracked file not in `self.files`, so a `plan.json` created under a stray `.audit` path during the export window would be silently removed. (tests/helpers/memkernel_snapshot.py)
- [warning] f-1d1982e8: `created` directories are removed deepest-first, but the loop only removes a directory if it is empty. If a tracked file inside a created directory could not be restored (added to `problems`), the directory stays — which is correct — but the code does not surface that the directory is now orphaned. More subtly, `self.wiki_dir.rglob("*")` is evaluated after files are restored, so a directory that was created and then had its file restored will be empty and removed; that is intended, but the `problems` list does not distinguish "file restore failed" from "directory cleanup failed", making diagnosis harder. (tests/helpers/memkernel_snapshot.py)
- [warning] f-c320a170: The two subTests share `self.paths` and `self.wiki` but use distinct page slugs (`page-a`, `page-b`) and distinct proposal names, so they do not collide. However, the second subTest patches `wiki_studio.promoter._write_receipt` with `_Fail(..., 2, ...)`, which fails on the *second* call. If the promoter's call order changes (e.g. a future refactor writes the receipt once before commit and once after), the test would silently pass or fail for the wrong reason. The test is coupled to an internal call count. (tests/test_bridge_contract.py)
- [warning] f-6384c318: The test sleeps 0.5s and asserts the child has not finished and has not staged. On a slow or loaded CI runner, the child may not have started at all within 0.5s, so `child.poll() is None` passes trivially and `(sync / "staged").exists()` is False for the wrong reason (child not yet scheduled). The test would then pass without actually exercising lock contention. (tests/test_bridge_contract.py)
- [warning] f-fa314130: `thread.join(60)` followed by `assertFalse(thread.is_alive())` is correct, but if the thread is still alive the `finally` block kills the child and the test raises `AssertionError` — leaving the thread running against a killed child. The thread may then raise inside `bridge_promote` and append to `outcomes` after the test has already failed, producing a confusing secondary traceback. (tests/test_bridge_contract.py)
- [note] f-d77acaca: If `sha256(text)` produces all-zero bytes in the first `dimension` bytes (astronomically unlikely but possible), `norm == 0` and the vector is all zeros. Chroma may reject zero vectors or treat them as identical, causing flaky behavior. The branch is defensive but the fallback is not obviously safe. (tests/integration/test_memkernel_clean_install.py)
- [note] f-091687eb: The test asserts `again.imported` equals `exported.written` on the second import, then asserts the memory set is unchanged. This relies on memkernel's importer being idempotent by `source` path. If memkernel changes to dedupe by content hash instead, the assertion `sorted(again.imported) == sorted(exported.written)` would still hold but the memory count assertion might not. The test is coupled to memkernel's dedupe key. (tests/integration/test_memkernel_clean_install.py)
- [note] f-2d9dd2bc: The job is non-blocking until green on main, which is reasonable, but there is no tracking issue or TODO comment with a removal date. A non-blocking job can rot silently. (.github/workflows/ci.yml)
- [note] f-f2e372a7: The section header says "Since wiki-studio 0.6.0" but the CHANGELOG entry is under 0.7.0 Unreleased. The behavior described (lock, receipts, no outer rollback) is indeed 0.6.0, but a reader landing here from the 0.7.0 changelog may be confused about which version introduced what. (docs/consumers.md)
- [note] f-a39e8dd7: The function returns `list[str]` (restore problems) but on the `with_snapshot=False` path returns `[]` unconditionally, which is fine, yet the docstring says "returns restore's problems" — for the no-snapshot case there is no restore, so the empty list is a sentinel. A reader may misread it as "restore succeeded". (tests/test_snapshot_hazard.py)
