---
feature_id: ai-wiki-0-1-0
date: 2026-10-12
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/ai-wiki-0-1-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: ai-wiki-0-1-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The release-hygiene changes (US4) are small and mostly documentation/CI: a PyPI trusted-publishing workflow, CHANGELOG, NOTICE, SECURITY, README, plus a `--version` flag and its test. The `--version` implementation and test are correct, and the workflow's tag/version check is sound. The main correctness concerns are in the release workflow's smoke test (version-string comparison against a possibly non-canonical tag) and a few documentation/consistency issues that could mislead consumers.

## Findings

- [warning] f-69466b28: The smoke test compares `ai-wiki --version` output to the raw tag with the leading `v` stripped. If a tag is pushed as `v0.1.0` this works, but tags like `v0.1.0-rc1` or `v0.1.0+local` would fail the equality even though `poetry version -s` may normalize differently, and the earlier tag/version check uses the same raw comparison. This couples release success to exact tag spelling rather than the canonical PEP 440 version. (.github/workflows/release.yml)
- [warning] f-1af66e15: The workflow triggers on any `v*` tag, including non-release tags (e.g. `v0.1.0-docs`, `vnext`). The version-match guard will reject mismatches, but a tag like `v0.1.0` pushed twice, or a tag matching the current version but not intended as a release, will still attempt a PyPI publish. There is no `if` guard or environment protection beyond the `pypi` environment. (.github/workflows/release.yml)
- [warning] f-cba151da: The publish job downloads the `dist` artifact but does not verify its contents or checksums before handing it to `pypa/gh-action-pypi-publish`. If the build job were compromised or the artifact tampered with between jobs, the publish step would upload whatever is present. This is a supply-chain hardening gap rather than a functional bug. (.github/workflows/release.yml)
- [note] f-536af1ad: The change adds `--version` to the passthrough condition so top-level `--version` is not rewritten into a legacy verb. This is correct for the top-level case, but the comment above the branch still says "Top-level help/version" while the code now also handles `--version`; the surrounding logic for "if a verb is already present, let it through" is unchanged and still correct. No functional issue, but the comment/code drift is worth a one-line update. (src/aiwiki/cli.py)
- [note] f-4a589083: The test asserts `__version__ == "0.1.0"` hard-coded. This will fail on every version bump and forces a test edit per release, which is exactly the kind of coupling the release workflow is trying to avoid. It also does not verify that `--version` works when combined with a verb or with other global flags. (tests/test_cli_contract.py)
- [note] f-a4d52ea4: The README lists exit code 2 as "backend not found ... usage error". The CHANGELOG's "Removed" section says the bash linter is gone and `lint` no longer exits 2 when it is missing. These are consistent, but the README does not mention that `lint` previously used exit 2 for a missing linter, which could confuse users migrating from the old script. Minor documentation gap. (README.md)
- [note] f-ee812e57: The Known issues list is thorough and honest, but several entries describe correctness-relevant behaviours (e.g. `audit_flush` treating non-"not a git repository" failures as "file absent at HEAD"; `build_log_record` recording in-root sources as repo-relative even with `--allow-out-of-repo`). These are deferred to 0.2, which is a reasonable scope decision, but the CHANGELOG does not link them to tracking issues. Without issue references, they risk being lost. (CHANGELOG.md)
- [note] f-28757b5c: Poetry is installed without a pinned version, so the build environment can drift between releases. Combined with `poetry version -s` being used for the tag check, a future Poetry release that changes version normalization could break the release pipeline silently. (.github/workflows/release.yml)
