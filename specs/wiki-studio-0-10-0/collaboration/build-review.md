---
feature_id: wiki-studio-0-10-0
date: 2026-11-17
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-10-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-10-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The change adds drafting capability to the nightly pass, gated behind an explicit `--backend`, with a link-only validation contract (FR-019), deterministic proposal naming, and a bounded attempt budget. The architecture is sound: drafting is opt-in, the model-free path is preserved, and the exit-code precedence is documented. I found a few correctness concerns around the `by`/`backend_name` resolution, the `_link_first_mention` region logic, and the exit-code precedence when a report write fails after a proposal write failure.

## Findings

- [warning] f-2431b86e: When `backend` is a `Backend` instance, `backend_display_name(resolved, None)` is called with `None` as the second argument; if that helper expects a name hint, the recorded `backend_name` may be wrong or empty, and `by` is not consulted as a fallback. This affects the `plan.json` proposer field and the report's drafting state. (src/wiki_studio/api.py)
- [warning] f-de2e21eb: The overlap test `match.start() < end and start < match.end()` is correct for half-open intervals, but `regions` from `code_regions` and `INLINE_LINK_RE` are combined without deduplication or sorting; if `code_regions` returns overlapping or unsorted spans the `any(...)` still works, but the `best` selection by `match.start()` across two `form` iterations can pick a later match in the first form over an earlier match in the second form only if starts tie — verify the tie-break is intentional and add a test with both slug and spaced-slug present. (src/wiki_studio/backends/test.py)
- [warning] f-1f68b1e9: The docstring promises "an unwritable report exits 6 whatever else failed; then a lock timeout 10; then a failed proposal write 6; then a structural lint failure 1; then the first draft failure's 3 or 4." But `report_failed` only suppresses the error line; the `exit_code` from `result.exit_code` is overwritten to `OutputWriteError.exit_code` (6) unconditionally when the report write fails, which matches the doc. However, when `report_failed` is True the error line is suppressed even though the underlying cause (e.g. lock timeout 10) is masked by 6 — confirm this is the intended precedence and that `result.exit_reason()` is not needed for the report-write case. (src/wiki_studio/cli.py)
- [warning] f-5d02507f: The diff introduces `DraftingState` and `result.exit_reason()` but the truncated diff does not show `NightlyResult.exit_reason` being defined or `DraftingState` being attached to the result. If `exit_reason()` returns `None` for a non-zero exit that came from a draft failure (3/4), the CLI's `if reason is not None` guard silently prints nothing, violating FR-010's "every non-zero exit prints one error line naming the cause." (src/wiki_studio/nightly.py)
- [warning] f-4a3addfd: `api.nightly` raises `ValueError` for negative `max_proposals` before resolving the backend, but the docstring says "A given backend is resolved before lint runs, whatever `max_proposals` is (BackendNotFoundError, exit 2); a negative `max_proposals` ... raise ValueError (exit 1) before anything runs." The ordering between the negative check and backend resolution is ambiguous in the docstring and the code checks `max_proposals < 0` first — so a negative `max_proposals` with an unknown backend yields exit 1, not exit 2. Confirm this matches the spec's precedence. (src/wiki_studio/nightly.py)
- [note] f-754bd763: `_body_start` returns 0 if the first line is not `---`, but a file starting with a BOM or leading blank line before `---` will be treated as having no frontmatter, so a mention inside what is actually frontmatter could be linked. This is a test backend, so impact is low, but it can mask real bugs in `_link_first_mention`. (src/wiki_studio/backends/test.py)
- [note] f-e6a5e6a2: `nightly` now takes `backend`, `max_proposals`, and `by` as keyword-only args, which is good, but `backend_name` is derived inside `api.nightly` rather than passed through, coupling the API layer to backend display naming. Consider having `_nightly_run` accept `backend_name` explicitly (it already does) and letting the CLI compute it, so the API stays a thin wrapper. (src/wiki_studio/api.py)
- [note] f-b795f038: The new test file is large (1390 lines) but the diff does not show tests for the combined precedence cases (report-write + lock timeout, draft failure + lint failure). Given the CLI docstring's explicit precedence claim, these combinations deserve direct tests. (tests/test_nightly_drafting.py)
