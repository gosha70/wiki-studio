---
feature_id: wiki-studio-0-8-1
date: 2026-11-03
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-8-1
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-8-1 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The change adds a standalone quickstart page whose fenced blocks are executed in CI by a new test harness, plus a dedicated `quickstart` CI job that installs the built wheel with the `mcp` extra into a fresh venv. The design (page-as-source-of-truth, block grammar, forbidden-backend guard) is sound and well-documented. I found a few correctness and robustness concerns in the harness and CI wiring, but nothing that blocks the feature.

## Findings

- [warning] f-eccd8b8e: The parser accepts `bash run` / `python run` only when `run` is the second token, but the docstring says "one word for the renderer and the rest for this module" — a block like `bash run exit=9 contains=state:approved` is fine, yet a block like `bash run` with a trailing token that is neither `exit=` nor `contains=` (e.g. a typo `exitt=9`) is silently ignored rather than rejected, so a mistyped expectation would pass CI without asserting anything. (tests/helpers/quickstart_blocks.py)
- [warning] f-155eca14: The forbidden-backend guard is a plain substring scan over block text; it will miss `wiki-studio  ingest` (double space), `wiki-studio \\\n ingest` (line continuation), `--backend=claude`, or `api . ingest`. It also false-positives on a comment or echo containing the literal string. This is a guard, not a security boundary, but the docstring claims the page "is refused" — the claim is stronger than the check. (tests/helpers/quickstart_blocks.py)
- [warning] f-3a4867cb: The close-fence check requires the closing fence to be at least as long as the opening fence and the same character, which is correct CommonMark, but the opening regex `^ {0,3}(?P<fence>`{3,} (tests/helpers/quickstart_blocks.py)
- [warning] f-9670172b: The docstring says every `WIKI_STUDIO_*` and `MEMKERNEL_*` variable is removed except `MEMKERNEL_EMBEDDING_MODEL`, but the visible diff does not show the scrubbing implementation. If the scrub is prefix-based on `os.environ` keys, it must also drop `WIKI_STUDIO_ACTOR` (which the page relies on being unset so `--by` wins) — verify the implementation actually removes it, otherwise a developer's shell could leak an actor into the run. (tests/helpers/quickstart_blocks.py)
- [warning] f-3bca18d0: `ls dist/*.whl` will expand to multiple paths if `poetry build` ever produces more than one wheel (e.g. an sdist is not a wheel, but a future multi-package build would be), and the quoted `"$(...)[mcp]"` would then be a single invalid requirement string. Also, if `dist/` is empty the glob is passed literally and pip fails with a confusing error. (.github/workflows/ci.yml)
- [warning] f-29a9e748: The CI comment says "The import check guarantees the page's conformance check is not skipped here," but the import check in the workflow only imports `mcp` and `wiki_studio.api` — it does not verify that `tests/test_quickstart.py` actually exercises the `bash server-cmd` block or the MCP conformance path. If the test file silently skips the server-cmd block (e.g. because `wiki-studio-mcp` is not on PATH), the CI job still passes. (tests/test_quickstart.py)
- [note] f-30bc1d04: The page asserts exit 9 for a stale base revision. If the CLI's exit code for stale-base ever changes, the page and the test both drift together (since the test reads the page), so the test cannot catch a regression in the exit code — it only catches a regression in the CLI's behavior relative to the page. That is the intended design (page is source of truth), but it means the exit-code contract is only pinned by the page, not by an independent assertion. (docs/quickstart.md)
- [note] f-09252cdc: The page says the install block is "not executed in CI" but the CI job does effectively execute the equivalent install (wheel + `[mcp]` extra). The wording is accurate (the literal `pip install 'wiki-studio[mcp]'` line is not run) but could confuse a reader into thinking the install path is untested. (docs/quickstart.md)
- [note] f-3b916c69: A 120s per-block timeout is generous for the shown blocks but the CI job has a 30-minute budget; if a block hangs (e.g. `wiki-studio-mcp` waiting on stdin), the timeout is the only backstop. Confirm the timeout is actually applied to `subprocess.run` calls (not visible in the truncated diff) and that a timeout produces a `QuickstartBlockError` naming the block rather than a bare `TimeoutExpired`. (tests/helpers/quickstart_blocks.py)
