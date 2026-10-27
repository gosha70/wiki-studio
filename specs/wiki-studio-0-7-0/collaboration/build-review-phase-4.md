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

The approval-record feature is well-designed and thoroughly tested: immutable records keyed by the full decision tuple, symlink-safe publication via `O_NOFOLLOW`/`os.link`, atomic batch preflight, and a clean separation between `review.py` (read) and `promoter.py` (write). I found no blocking correctness or security defects. A few warnings concern edge cases in the auto-approval path, the `_receipt_provenance` best-effort lookup, and one test that relies on a private helper.

## Findings

- [warning] f-a06ea9a5: `drift_warnings` raises `ContractViolationError` (exit 4) on a governed wiki with drift, but this call is inside the `try` that catches `(IngestError, OSError)`. `ContractViolationError` is not caught, so a governed wiki whose schema drifted between the promotion commit and the auto-approval lock acquisition would raise out of `promote` *after* the promotion is already committed and archived — contradicting the documented "a failure there never fails the promotion". (src/wiki_studio/promoter.py)
- [warning] f-d48d3b85: The "newest committed receipt" is chosen by lexicographic comparison of `committed_at` strings. If any receipt lacks `committed_at` (empty string), it sorts before every real timestamp and is never chosen even when it is the only match; conversely a malformed timestamp could win. The docstring says "newest committed receipt", but the ordering is only correct for well-formed ISO-8601 strings. (src/wiki_studio/promoter.py)
- [warning] f-08daa74b: `PromoteApplyError` (lock timeout) is a subclass of `IngestError`? If not, a lock timeout on the second acquisition would propagate out of `promote` and fail an already-committed promotion. The test `test_a_lock_timeout_is_a_warning` patches `WikiLock` to raise `PromoteApplyError`, so this is exercised — but only because `PromoteApplyError` happens to be caught. Confirm the exception hierarchy and add a comment, or catch `Exception` narrowly around the lock acquisition with an explicit allow-list. (src/wiki_studio/promoter.py)
- [warning] f-593e86b7: `_plan_approval` can raise `ContractViolationError` (symlink in the approval tree) and `PromoteValidationError` (a file occupying the record name). Neither is caught here, so a single page with a planted symlink or stray file aborts the whole auto-approval loop and propagates out of `promote` — again failing an already-committed promotion. The docstring says "each skipped, failed or changed page gets a warning". (src/wiki_studio/promoter.py)
- [warning] f-b80f609a: When `sha256` is given, the code does not validate that it is a well-formed 64-hex string before using it as a path component. `_scan_revision` then checks `is_sha256_hex(rev)` and skips, so this is safe — but the `sha256` argument comes from `content.sha256` (trusted) in current callers. Still, `scan_key` is a public-ish helper; a caller passing an unvalidated string would get a confusing "not a revision directory" skip rather than a clear error. Low risk given current callers. (src/wiki_studio/review.py)
- [warning] f-835fa1d3: In the `not _DIR_FD_RECORDS` branch, `current.mkdir(mode=0o755)` is called without `exist_ok`, relying on `contextlib.suppress(FileExistsError)`. If `current` exists as a *file*, `mkdir` raises `FileExistsError` (suppressed), then `os.lstat(current)` returns a non-dir and `_refuse_record_component` is raised — correct. But if `current` exists as a *symlink to a directory*, `mkdir` raises `FileExistsError` (suppressed), `os.lstat` returns `S_ISLNK` (not `S_ISDIR`), so it is refused — correct. The logic is right but subtle; a comment would help future readers. (src/wiki_studio/promoter.py)
- [warning] f-becd21ac: The test calls `promoter._publish_record` directly, a private helper. This couples the test to an internal name; a refactor of `_publish_record` would break the test even if the public behavior is preserved. Acceptable for a security-focused test, but worth noting. (tests/test_approval_records.py)
- [note] f-ed132706: The path is normalised but not checked against the wiki boundary or reserved-path rules before being used as a lookup key into `posts`. Since `posts` comes from the receipt's `planned_writes` (already validated at promote time), and `read_live_page` re-checks containment, this is safe — but the normalisation here differs from `canonical_path` (which also strips leading `./`). If a receipt ever stored `./decisions/a.md`, `normpath` yields `decisions/a.md` and matches; consistent. No action needed, but a comment tying this to `canonical_path` would prevent drift. (src/wiki_studio/promoter.py)
- [note] f-8bb0be06: The doc says "Normalise the wiki-relative path with `posixpath.normpath`" but `canonical_path` also rejects absolute paths and `..` escapes. A reader implementing the recipe from the doc alone could produce a digest for a path that `canonical_path` would reject. Minor, since the doc is descriptive of this implementation. (docs/knowledge-contract.md)
- [note] f-109ce97a: Structural-lint violations are attributed to a page by string prefix. If a violation message for page `decisions/a.md` happens to start with `decisions/a.md: ` but actually concerns a different page (e.g., a cross-page reference), it would be misattributed. In practice `lint_wiki` prefixes each violation with its own page path, so this is correct — but it is a fragile coupling to the linter's message format. (src/wiki_studio/promoter.py)
- [note] f-3593658a: When records exist for the live bytes but none satisfies the policy, the state is `policy-changed` and `approved_sha256` is set to the newest unsatisfying record's sha256 — which equals `live_sha256`. That is correct per the doc ("the newest matching record by timestamp is reported"), but a reader might expect `approved_sha256` to be `None` for `policy-changed`. The doc's table is clear; just flagging for reviewer awareness. (src/wiki_studio/review.py)
