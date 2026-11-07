---
feature_id: wiki-studio-0-9-0
date: 2026-11-07
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-9-0
rounds_completed: 2
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-9-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 2
**Verdict**: PASS

## Summary

Round 1 findings are addressed: the new tests now assert actual counts (1/1/1) and finding entries for all three conflict kinds through the MCP surface, the shape test asserts zero values, the contract documents cardinality and zero-valued kinds, and the CLI/README fixes are in place. I found no new blocking issues; a couple of minor notes remain on test robustness and doc precision.

## Findings

- [note] f-c2bed626: The test asserts exact ordering of the three conflict findings (`open-conflict`, `conflict-one-sided`, `conflict-dangling`) via a list comparison, which couples the test to the emission order of unrelated kinds. If a future kind is inserted between them, or ordering changes, the test fails for reasons unrelated to conflict detection. (tests/test_mcp_adapter.py)
- [note] f-e0656ac0: The cardinality paragraph says "one callout yields at most one finding, because a marker line names only its first `.md` link" — but it does not state what happens when the first `.md` link is a valid page and a later link is dangling (the callout is classified by the first link, so the dangling target is silently ignored). This is implied but not explicit, and consumers reading `conflict-dangling` counts may expect the dangling target to surface. (docs/knowledge-contract.md)
- [note] f-7752ed52: The new assertion `{kind: result.counts[kind] for kind in CONFLICT_KINDS} == dict.fromkeys(CONFLICT_KINDS, 1)` uses `result.counts[kind]` (subscript), which would raise `KeyError` rather than fail cleanly if a kind were dropped from `counts`. That is acceptable but produces a less diagnostic failure than an explicit `assertIn`/`assertEqual` per kind. (tests/test_conflict_callouts.py)
- [note] f-0ac8c95d: The README now links to an absolute GitHub URL for `citation-rules.md#when-sources-disagree`. This resolves on GitHub and PyPI, but pins the link to `main`; if the anchor is renamed on `main` before a release, the released README's link breaks retroactively. Acceptable for now, but worth noting the coupling. (README.md)
