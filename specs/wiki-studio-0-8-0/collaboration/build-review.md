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

The MCP adapter is well-structured: the stdlib-only core boundary is enforced by both an AST test and a wheel-level CI check, the tool surface is locked down (no root/actor/backend/escape-hatch arguments), and the error mapping and trace design are sound. I found a few correctness concerns around the wire observer's thread-safety and lifecycle, the `as_tool` signature/annotation handling, and the `--trace` path resolution, plus some smaller notes.

## Findings

- [warning] f-83c7b051: The inbound pump closes `in_write` at EOF, but the outbound pump also closes `real_stdout` (a dup of fd 1) at EOF. If the SDK's stdio transport still holds fd 1 open when the outbound relay hits EOF (e.g. client closes stdin early), the relay closes the dup'd fd while the process may still write to fd 1 — and more importantly, `observed_stdio`'s `finally` calls `os.dup2(real_stdout, _STDOUT_FD)` after `outbound.join()`, but `real_stdout` was already closed by `_pump`. That `dup2` will raise `OSError` (suppressed) and fd 1 is left pointing at the now-closed pipe write end, so any late stderr/stdout write or interpreter shutdown flush can fail or be lost. (src/wiki_studio/mcp_adapter/trace.py)
- [warning] f-bd0f6414: JSON-RPC ids may be ints or strings; `json.dumps(1)` and `json.dumps("1")` differ, which is correct, but a client that reuses an id before the prior response arrives (allowed for notifications only, but some clients pipeline) will overwrite the pending entry and lose the earlier duration/outcome. Also `_initialize_id` is compared by string key, so a client that sends `initialize` with id `1` and later a `tools/call` with id `1` (after the init response) is fine, but a pipelined init+call with the same id would mis-attribute the protocol version. (src/wiki_studio/mcp_adapter/trace.py)
- [warning] f-63f541e7: `get_type_hints` resolves string annotations to actual types, but the wrapper's `__signature__` is built from `inspect.signature(method, eval_str=True)`. If a tool method uses `from __future__ import annotations` (it does — `tools.py` has it), `get_type_hints` will evaluate `list[dict[str, Any]]` etc. fine, but any forward reference to a `TYPE_CHECKING`-only name (e.g. `Path`, `Callable`, `LaunchConfig` in `tools.py`) will raise `NameError` at wrapper-build time. `tools.py` imports `Path`/`Callable`/`LaunchConfig` only under `TYPE_CHECKING`, and `find`/`propose`/`promote`/`findings`/`review_state` annotate with `list[str]  (src/wiki_studio/mcp_adapter/server.py)
- [warning] f-fe9eca3e: `trace = args.trace if args.trace.is_absolute() else (Path.cwd() if cwd is None else cwd) / args.trace`. When `cwd` is passed (tests), the trace is resolved relative to `cwd`; when not (real launch), relative to `Path.cwd()`. But `WikiPaths.resolve` is called with `cwd=cwd`, so the wiki may be resolved relative to a different base than the trace if `cwd` is None but the process cwd differs from where the user expects. More concretely: `open_trace` checks `path_inside_dir(path, paths.wiki_dir)` — if `paths.wiki_dir` is relative and `trace` is absolute (or vice versa), the containment check may be wrong. `WikiPaths.resolve` presumably absolutizes, but the trace path is not passed through the same normalization. (src/wiki_studio/mcp_adapter/config.py)
- [warning] f-30a33eb9: `warnings.catch_warnings(record=True)` with `simplefilter("always", DriftWarning)` records only `DriftWarning`; other warnings are re-emitted via `warnings.showwarning(...)` inside the lock, but `showwarning` writes to stderr — which is correct — yet the re-emission happens while `_WARNINGS_LOCK` is held, and `showwarning` may itself trigger warnings (unlikely) or block on stderr. More importantly, `warnings.catch_warnings` is not reentrant-safe across threads even with the lock if another thread (e.g. the SDK's worker) emits a warning concurrently — the lock only serializes `propose` calls, not other warning emitters. The comment acknowledges this but the mitigation is incomplete. (src/wiki_studio/mcp_adapter/tools.py)
- [note] f-635d63ce: `chosen = resolve_ranker(ranker)[0] if ranker is not None and ranker.strip() else self.config.ranker`. If `ranker` is a non-string (e.g. a client sends `ranker: 5`), `ranker.strip()` raises `AttributeError`, which becomes `InternalError` (class name only) rather than a `ValueError` with a helpful message. The SDK's schema validation should reject non-strings, but defense-in-depth suggests an explicit `isinstance(ranker, str)` check. (src/wiki_studio/mcp_adapter/tools.py)
- [note] f-a4c6dec6: `base = edit.get(EDIT_BASE_SHA256)` then `if base is not None and not isinstance(base, str)`. If the client sends `base_sha256: null` explicitly, `base` is `None` and it's treated as absent — which is probably intended, but the doc says "an update carries read_page's sha256 as base_sha256"; a `null` on an `update` silently becomes an unguarded update (subject to `allow_unguarded_updates`, which the adapter never sets, so it will be refused by `promote`). That's safe but the error message at promote time may be confusing. (src/wiki_studio/mcp_adapter/tools.py)
- [note] f-8620f7ec: `serve` returns 0 after `server.run(TRANSPORT_STDIO)` returns. If the SDK raises (e.g. transport error), the exception propagates out of `main` and the process exits with a traceback on stderr and a non-zero code — which is fine, but `main`'s contract says "exit 2 when it cannot start"; a mid-session crash is not a launch error. The current behavior (uncaught exception) is acceptable but inconsistent with the documented exit codes. (src/wiki_studio/mcp_adapter/server.py)
- [note] f-2bfb0095: The test sets `sys.modules['mcp'] = None` in a subprocess, which makes `import mcp` raise `ImportError` — good. But it does not verify that `wiki_studio.mcp_adapter.server` raises the *specific* `INSTALL_INSTRUCTION` message in that subprocess (only that the stdlib modules import). The in-process test `test_the_server_module_raises_import_error_with_the_instruction` covers it, but only when `mcp` is actually installed (it patches `sys.modules`). If `mcp` is not installed, `patch.dict(sys.modules, {"mcp": None, ...})` still works, so coverage is fine — just noting the subprocess test could assert the message too. (tests/test_mcp_adapter.py)
- [note] f-5ab4c7d0: The ADR explicitly states the transitive licence list "has not been [re-checked from poetry.lock] yet" and must be checked in the commit that updates `poetry.lock`. This is honest, but it means the dependency review is incomplete at merge time. If `poetry.lock` is not updated in this PR, the ADR ships with a known gap. (docs/adr/0003-optional-mcp-dependency-and-tool-contract.md)
- [note] f-31578724: The context manager dups and replaces fd 0 and fd 1, but on exit only restores fd 1 (`os.dup2(real_stdout, _STDOUT_FD)`). fd 0 is left pointing at the read end of the inbound pipe, and `real_stdin` is never closed. After `observed_stdio` exits, the process's stdin is a pipe whose write end was closed by the inbound pump at EOF — so reads return EOF, which is probably fine for shutdown, but the leaked `real_stdin` fd and the un-restored fd 0 are untidy and could confuse a caller that reuses `serve` in-process (e.g. tests). (src/wiki_studio/mcp_adapter/trace.py)
- [note] f-815e0f83: `_outcome` reads `result.get("isError")` and then parses the first text block's `exit_code`. If the SDK wraps the error differently (e.g. `isError` at the top level of the response rather than inside `result`), the outcome falls back to `OUTCOME_UNCODED_ERROR` (1). The test `test_the_trace_records_each_request` asserts `("tools/call", "find", 1)` for the `max_pages: 6` case, which matches the `ValueError` exit code 1 — but that's coincidental (both are 1). A `PathOutsideRootError` (exit 7) traced through the wire would reveal whether the parsing is correct; the test does not cover a non-1 exit code over the wire. (src/wiki_studio/mcp_adapter/trace.py)
