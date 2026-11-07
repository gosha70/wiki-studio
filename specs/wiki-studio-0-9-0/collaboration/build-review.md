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
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-9-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The release-bump diff is mechanically consistent: version strings in `pyproject.toml`, `src/wiki_studio/__init__.py`, `README.md`, `CHANGELOG.md`, `docs/quickstart-memkernel.md`, and the two tests that pin the version all move from 0.8.1 to 0.9.0 together. The only substantive concern is the new `docs/compatibility.md` row, which is marked **Pending** rather than **Tested** — a documentation/process gap rather than a code defect, but worth flagging since the compatibility table is a contract artifact.

## Findings

- [note] f-fbff906c: The 0.9.0 compatibility row is marked "Pending" and cites no CI run, unlike every prior row which names a green run on `main`. This is acceptable for a build-phase PR but the row must be updated before the release is tagged, or the table will claim an untested pair. (docs/compatibility.md)
- [note] f-9643f559: The 0.9.0 row lists only `memkernel-compat`, dropping `memkernel-loop`, `quickstart-memkernel`, and `demo-correction-loop` that the 0.8.1 row claimed. If those jobs still run and pass, the row understates coverage; if they were removed, that is a regression in CI coverage that should be called out. (docs/compatibility.md)
- [note] f-98d56f4b: The test hard-codes `"0.9.0"` alongside the `__version__` comparison. This is intentional (it catches a forgotten bump) but means every release requires touching this test; consider whether the hard-coded literal should instead be derived from `pyproject.toml` to avoid the dual-source-of-truth. (tests/test_cli_contract.py)
- [note] f-4da57494: The `[Unreleased]` section was renamed to `[0.9.0]` but no `[Unreleased]` section was re-added at the top. Future changes will have nowhere to land without re-creating it. (CHANGELOG.md)
