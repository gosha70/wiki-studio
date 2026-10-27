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

The implementation is well-structured and thorough: the contract module cleanly separates read-side validation from write-side manifest management, the contained loader correctly unifies prompt and fingerprint reads, and the test coverage is extensive. I found a few correctness concerns around the `init` flow's ordering of operations, a potential TOCTOU in `_update_schema_fingerprint`, and a subtle issue with the CLI's drift-warning deduplication. None appear blocking, but the `init` ordering issue is worth addressing.

## Findings

- [warning] f-7d287957: On a fresh wiki the directory does not exist yet, so `_refuse_manifest_symlinks` calls `paths.wiki_dir.is_symlink()` (fine) and `contain(MANIFEST_NAME, paths.wiki_dir)` — but `read_manifest_bytes` then calls `_read_contained` which calls `contain(rel, wiki_dir)` and `os.open(target, ...)`. If `wiki_dir` does not exist, `os.open` raises `FileNotFoundError` which is caught and returns `None` — OK. But `contain()` may itself raise on a non-existent wiki_dir depending on its implementation; verify `contain` tolerates a missing base directory, otherwise `init` on a fresh wiki fails before `mkdir`. Add a test that `api.init` on a completely absent wiki dir succeeds (the existing tests call `api.init` on a fresh `WikiPaths` but `ManifestCase.setUp` does not create the wiki dir — confirm this path is exercised). (src/wiki_studio/promoter.py)
- [warning] f-81bcf2af: The read of `read_manifest_bytes` and the subsequent `_replace_manifest` are both under the wiki lock, which is correct. However `_replace_manifest` uses `os.replace` which will happily replace a symlink at the manifest name with the new file — the docstring acknowledges this ("a symlink at the manifest name would be replaced, never followed"). But `_update_schema_fingerprint` calls `parse_manifest(data, ...)` on bytes read via `read_manifest_bytes` which uses `O_NOFOLLOW`, so a symlink would already have been refused on read. The concern is only if the symlink is introduced between the read and the replace — a narrow TOCTOU. Given the lock, this is acceptable, but worth a comment noting the lock is what closes the window. (src/wiki_studio/promoter.py)
- [warning] f-fd65a868: The dedup `[w for w in result.warnings if w not in drift]` compares strings. If `promote` produces a drift warning with identical text (it will, since both call `drift_message` with the same fingerprints), this works. But if `promote` re-reads the schema and the fingerprint changed between `propose` and `promote` (e.g., a concurrent edit), the messages differ and both print — arguably correct, but the comment "printed once already" is then misleading. More importantly, `result.warnings` may contain the drift message from `promote`'s own `check_write_contract` call, which is the same string only if the schema is unchanged. This is fragile string-matching; consider tagging warnings with a category or having `promote` accept a flag to suppress the drift warning when the caller already emitted it. (src/wiki_studio/cli.py)
- [note] f-25bc70b6: When `existing is None` and `_create_manifest` returns False (lost the race), the code calls `read_manifest(paths)` to validate the winner's manifest but discards the result and leaves `manifest_state = MANIFEST_EXISTING`. That is correct behavior, but if the winner's manifest is malformed the `read_manifest` raises — good. However if `update_schema` is also set, the code then calls `_update_schema_fingerprint` which re-reads under the lock — fine. The `read_manifest` call is redundant with the subsequent `_update_schema_fingerprint` read but harmless. Consider a comment clarifying the intent. (src/wiki_studio/promoter.py)
- [note] f-6cd88d3a: When `regular_only=False` and the entry is a directory, the function returns `None` (treated as absent). The test `test_a_directory_at_an_override_name_falls_back_to_the_packaged_copy` confirms this is intended. But a FIFO or socket at an override name would also be treated as absent — arguably fine, but a device file could block on `os.fdopen(...).read()`. Since `regular_only=False` is only used for schema overrides and the `fstat` check runs before `fdopen`, a non-regular file is closed and returns `None` — so no blocking read occurs. This is correct; noting for clarity. (src/wiki_studio/contract.py)
- [note] f-c621f0e4: The strict rejection of unknown policy keys (`unknown = sorted(set(policy) - set(POLICY_KEYS))`) means a future 0.8.0 adding a policy key would make 0.7.0 refuse the manifest as malformed rather than as "newer". This is arguably correct (fail-closed), but the error message says "is not a policy key" rather than hinting at a version mismatch. A host that hand-edits a policy key expecting forward-compat will get a confusing error. (src/wiki_studio/contract.py)
- [note] f-45740687: Patching `promoter.os.fsync` patches the `os` module globally (since `promoter.os` is the `os` module), so this also affects `_fsync_dir` and any other fsync in the call path. The test asserts the manifest does not exist after failure, which is the right assertion, but the patch is broader than intended. Consider patching `promoter._write_new_file` or a narrower seam. (tests/test_manifest.py)
- [note] f-6f0db6ff: The doc says only `promoter.py` writes the manifest, but `contract.py` defines `new_manifest` and `manifest_bytes` which are the serialization helpers. This is accurate (promoter calls them), but a reader might expect `contract.py` to be write-free — it is, since it only builds dicts/bytes. Fine as-is; noting for precision. (docs/knowledge-contract.md)
- [note] f-a14e9267: When `--json` is passed, drift warnings go to stderr and the JSON to stdout — correct. But `api.info` is called before the `if args.json` branch, so a `ContractViolationError` from `api.info` propagates and is handled by the top-level error handler (exit 4) — good. No issue. (src/wiki_studio/cli.py)
- [note] f-929035dd: `os.open in os.supports_dir_fd` etc. is evaluated once at import. On platforms where `os.supports_dir_fd` is a set that is populated lazily or differs per-call, this could be stale. In practice CPython populates it at import. The test `test_the_path_based_fallback_creates_and_replaces_the_same_way` patches `_DIR_FD_MANIFEST` to `False`, confirming the fallback works. Acceptable. (src/wiki_studio/promoter.py)
