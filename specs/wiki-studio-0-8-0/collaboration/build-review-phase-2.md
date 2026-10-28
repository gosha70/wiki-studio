---
feature_id: wiki-studio-0-8-0
date: 2026-10-27
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-8-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-8-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The implementation is well-structured and the test suite is unusually thorough (property tests, process-kill recovery, symlink refusal, read-only fallback). I found one correctness issue worth flagging around the `_apply_diff`/`_matches` interaction when a cache is rebuilt mid-transaction, plus a few smaller notes on error classification and the `info` read-only path. Nothing appears blocking.

## Findings

- [warning] f-485f77b2: Add a short comment in `_rank_on_disk` explaining that the second attempt is the "rebuild after removal" and that a second `CacheCorruptError` means the file system is producing unusable files, hence `CacheUnusableError`. (src/wiki_studio/search_index.py)
- [warning] f-c6728b26: Narrow `CacheCorruptError` to `sqlite3.DatabaseError` whose message matches known corruption signatures (e.g. "file is not a database", "database disk image is malformed", "no such table"), and let other `DatabaseError`s propagate or be wrapped as `CacheUnusableError` with a distinct reason. (src/wiki_studio/search_index.py)
- [warning] f-3620f707: Consider treating a zero-byte regular file as `missing` (or `present` with a "will be rebuilt" reason) in `describe_cache`, since `_ensure_regular_file` creates it empty and SQLite will initialize it on the next write. (src/wiki_studio/search_index.py)
- [note] f-51ce971b: Add a brief comment noting that `wiki_path` is the primary discriminator and `wiki_id` is a secondary check, so the empty-string fallback is safe. (src/wiki_studio/discovery.py)
- [note] f-e2ed151c: Add a one-line comment that `catch_warnings` restores the outer filter state on exit, so re-emitting non-discovery warnings via `showwarning` preserves prior behavior. (src/wiki_studio/cli.py)
- [note] f-9b199fa5: Assert on the stable prefix (`"search cache"` and `FALLBACK_TEXT`) and, if you want to check the cause, match on `"readonly"` case-insensitively or on the `_SQLITE_READONLY` classification via a helper. (tests/test_search_index.py)
- [note] f-467d45b5: Sort the deletion set explicitly (`for path in sorted(stored.keys() - current.keys())`) to make the operation order deterministic and future-proof. (src/wiki_studio/search_index.py)
- [note] f-aeff3a5d: Add one sentence: "`ValueError` from `WikiPaths` construction maps to exit 1; `ContractViolationError` from `rank_cached`/`describe_cache` maps to exit 4." (docs/knowledge-contract.md)
- [note] f-5629b19a:  O_EXCL  (src/wiki_studio/search_index.py)
