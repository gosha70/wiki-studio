---
feature_id: wiki-studio-0-1-0
date: 2026-10-13
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: chore/rename-wiki-studio
rounds_completed: 2
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-1-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 2
**Verdict**: PASS

## Summary

The rename from `wikistudio` to `wiki_studio` (import) with `wiki-studio` (distribution/console script) is applied consistently across source, tests, docs, and CI. All three Round 1 blocking findings (memkernel fixture namespace) are resolved by pinning the namespace to `wiki-studio` (the repository name) and asserting the prefix in `test_fixture_wiki.py`. The remaining Round 1 warnings (task 1 and FR-009 prose) are also fixed. I found no new correctness, security, or API-design issues introduced by this change.

## Findings

- [note] f-8783c774: The CHANGELOG documents `WIKI_INGEST_BACKEND` as a deprecated alias of `WIKI_STUDIO_BACKEND`, but does not state that the previously-shipped (unreleased) `WIKISTUDIO_*` names are no longer honoured. The origin-alignment record at 2026-10-13-2100 explicitly says "No compatibility aliases for the unreleased names", so this is intentional, but a reader of the CHANGELOG alone cannot tell whether `WIKISTUDIO_BACKEND` still works. (CHANGELOG.md)
- [note] f-6973147a: The module docstring still says "Invoked as `wiki_studio <verb> ...` (console script)". The console script is `wiki-studio` (hyphen); `wiki_studio` is only the module name used with `python -m`. This is user-facing in `--help`-adjacent contexts. (src/wiki_studio/cli.py)
- [note] f-beca3d0a: The rename of `ENV_BACKEND` from `WIKISTUDIO_BACKEND` to `WIKI_STUDIO_BACKEND` is a silent breaking change for any consumer that set the old variable. The deprecation path only covers `WIKI_INGEST_BACKEND`. Given the package is unreleased this is acceptable, but a one-line stderr warning when `WIKISTUDIO_BACKEND` is set (mirroring the `WIKI_INGEST_BACKEND` handling) would be cheap insurance and consistent with the existing deprecation pattern. (src/wiki_studio/backends/__init__.py)
