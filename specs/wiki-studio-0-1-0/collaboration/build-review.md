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
target_ref: feature/ai-wiki-0-1-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-1-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

This is a mechanical rename of the `aiwiki` package/CLI/distribution to `wikistudio` across source, tests, docs, workflows, and specs. The rename is largely consistent, but the diff introduces a few correctness and documentation defects: a self-contradictory origin-alignment record, a stale `--cov=aiwiki` reference in the spec's success criteria, and a CHANGELOG entry that silently drops a known-issue note. The code changes themselves are pure identifier substitutions and appear behavior-preserving.

## Findings

- [warning] f-bf3a6f78: The new origin-alignment record contains a self-contradictory sentence: "Distribution name was wikistudio and renamed wikistudio because `wikistudio` is taken on PyPI." The rename source and target are identical, and the stated reason ("wikistudio is taken on PyPI") contradicts the working claim that the project is named wikistudio. This is a copy-paste artifact from the aiwiki→wikistudio rename and makes the alignment record incoherent. (specs/wiki-studio-0-1-0/origin-alignment-2026-10-13-1200.md)
- [warning] f-e6cf2478: The success criterion still reads `poetry run pytest -q --cov=aiwiki --cov-fail-under=80` while every other occurrence in the same file was renamed to `--cov=wikistudio`. This is an inconsistent rename that will mislead anyone verifying the criterion. (specs/wiki-studio-0-1-0/spec.md)
- [note] f-1d1be432: The rename commit removes the known-issue bullet "In the staged-tree lint, a sibling directory whose symlink cannot be created is skipped silently (files are copied instead)." No corresponding code change in this diff removes that behavior, so the known issue is still present but no longer documented. Dropping a known-issue entry without fixing the underlying behavior is a documentation regression. (CHANGELOG.md)
- [note] f-3d356713: ADR-5 states "the repository started as `wikistudio`" and "the PyPI name is held by a `0.0.1` placeholder release until 0.1.0 replaces it." The placeholder-release claim is not verifiable from this diff and, if untrue, would mislead release operators. The origin-alignment record also asserts the repo "was created as wikistudio" while the CHANGELOG and README still reference `gosha70/ai-wiki` as the GitHub repository, which is confusing. (specs/wiki-studio-0-1-0/plan.md)
- [note] f-90a609e0: The plan's `origin.urls` now lists `https://github.com/gosha70/wiki-studio`, but the origin-alignment record and CHANGELOG both state the GitHub repository remains `gosha70/ai-wiki`. The plan therefore points at a URL that may not exist. (specs/wiki-studio-0-1-0/plan.md)
- [note] f-3f686474: The docstring now reads "overridden by a CLI flag or an `WIKISTUDIO_*` variable" — "an" should be "a" before a consonant sound. Minor, but this is user-facing documentation in the package. (src/wikistudio/paths.py)
- [note] f-4d116e12: The rename changed the absolute-path fixture from `/tmp/aiwiki-escape.md` to `/tmp/wikistudio-escape.md`, but the test still asserts the same substring `"path must be relative"` for both the relative-escape and absolute-path cases. This was already flagged as f-a70e8533 in the prior review; the rename did not address it, so the test still cannot distinguish "rejected for the wrong reason" regressions. (tests/test_promoter.py)
- [note] f-17568ec8: The recipe still exports `MEMKERNEL_WIKI_DIR` and then `WIKISTUDIO_WIKI_DIR="$MEMKERNEL_WIKI_DIR"`, which is fine, but the surrounding prose still says "memkernel can point the tool at `MEMKERNEL_WIKI_DIR`" in plan.md ADR-2 while the actual variable consumed by the tool is `WIKISTUDIO_WIKI_DIR`. The plan's ADR-2 consequence is now inaccurate. (docs/consumers.md)
