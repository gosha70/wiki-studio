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

The change adds a substantial, well-structured MCP conformance suite, host-run checker, and CI jobs, plus version bump to 0.8.0. The suite is adapter-agnostic and the tests exercise both the SDK path and an in-process path. I found a few correctness and robustness issues in the conformance runner and host-run checker that are worth addressing before merge, but nothing that undermines the core design.

## Findings

- [warning] f-46dd7e9b: The pinning relies on private module attributes (`LATEST_HANDSHAKE_VERSION`, `LATEST_MODERN_VERSION`) that are not part of the SDK's public API. If the SDK renames or removes them, `_pinned` raises `CaseFailure` and case 1 fails by name — which the ADR acknowledges — but the failure mode is a hard fail of the whole version run rather than a clear "cannot test this version" signal. Consider distinguishing "SDK cannot be pinned" (SuiteError / SKIP) from "server refused the version" (PASS with refusal). (conformance/mcp/run.py)
- [warning] f-4753996d: `_answered` reads the relay's record file, which may contain partial lines if the server crashed mid-write, and it does not distinguish a JSON-RPC response from an unrelated JSON object that happens to have a `result` key. More importantly, it is used to decide whether a refusal is "clean" — a server that emits a non-JSON-RPC JSON object with `result` would be counted as answering. (conformance/mcp/run.py)
- [warning] f-756a0b63: The check assumes the updated page's `pre_sha256` equals the fixture's original file hash. That holds only if the host run updated the page from its pristine fixture state. If a host run legitimately updates a page that was already modified earlier in the same run (e.g., two updates), the second update's `pre_sha256` would not match the fixture and the case would fail spuriously. The scenario is fixed to one update, so this is latent, but the checker is documented as applying to any recorded run. (conformance/mcp/run.py)
- [warning] f-11387b42: `outside_fixture` is computed from `FIXTURE_PROJECT` (the pristine fixture), but `outside_end` is computed from the run's `end-state/`. The fixture's `variants/` directory is not copied into the project root by `copy_fixture`, so this is consistent — but the comparison also excludes `DERIVED_PREFIX` files only by substring match on the key, which would also exclude a legitimate user file whose name contains that substring. Minor, but the exclusion should be anchored to the `knowledge/` directory. (conformance/mcp/run.py)
- [warning] f-8879838c: If `negotiation.failed` is set and the method returns early (the `no response` branch), `case_clean_stdout` is never called and case 12 is filled by the `setdefault` loop as FAIL "not reached". That is acceptable, but if negotiation succeeded and then a later session failed, `case_clean_stdout` still runs over all records including the failed session's — which is correct. The concern is the early-return path: it returns `self.ordered()` before the `setdefault` loop, so cases 2-12 are absent from `self.results` and `ordered()` will `KeyError`. (conformance/mcp/run.py)
- [warning] f-5b451bc3: The loop `for block in data.get("content") or []:` sets `payload` from the first text block that parses as a dict, then `break`s unconditionally. If the first text block is not JSON (e.g., a human-readable message) and a later block is the JSON payload, the payload is missed and `structuredContent` is used instead. For the adapter this is fine, but the suite is adapter-agnostic. (conformance/mcp/run.py)
- [warning] f-b789aa1b: If `check_host_run` raised `SuiteError` (missing files), `_host_main` returns before writing. If it returned results, the verdict is written. But `manifest["verdict"]` is written even when `code != EXIT_PASS`, which is intended ("a failed verdict is committed as it is"). No bug, but the `--record` path does not fsync or write atomically; a crash mid-write leaves a truncated manifest. (conformance/mcp/run.py)
- [note] f-1a5080dd: The relay forwards SIGTERM to the child but not SIGINT or SIGHUP. If the parent (the SDK client) is interrupted, the child may be orphaned. The relay is short-lived and the SDK manages the process group, so this is minor. (conformance/mcp/relay.py)
- [note] f-1c7213d3: Two symlinks pointing to the same file via different relative paths produce different snapshot entries. For the end-state hash this is deterministic given the same tree, so it is fine for the intended use, but it means a host run that recreates a symlink with an equivalent-but-different target string would fail the hash check. (conformance/mcp/run.py)
- [note] f-1932788a: This asserts cases 2-11 pass but does not assert case 12 (clean stdout) or case 1 (negotiate), which are exercised only through the SDK path. The in-process path cannot exercise case 12 meaningfully (no relay), so this is expected, but the test name says "every case". (tests/test_mcp_conformance.py)
- [note] f-fa4f6bfd: The table has a header and no rows, with prose explaining that rows are added from green CI runs. This is honest, but a reader scanning the table sees an empty table. Consider a placeholder row or a note directly under the header. (docs/compatibility.md)
- [note] f-7de1655a: The tool contract forbids `ranker_config` as an argument, but `find` returns a `ranker` field. If a future adapter exposes a `ranker` argument (to select the ranker per call), the suite would not catch it. The spec (FR-035/036) should be the source of truth; confirm whether `ranker` is intentionally allowed as an argument. (conformance/mcp/run.py)
- [note] f-d06586f3: On Windows, `shlex.split` uses POSIX rules by default and will mangle backslash paths. The suite is documented as run in CI on ubuntu-latest, but `CLAUDE.md` shows it as a local dev command too. (conformance/mcp/run.py)
