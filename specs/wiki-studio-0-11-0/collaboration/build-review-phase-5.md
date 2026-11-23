---
feature_id: wiki-studio-0-11-0
date: 2026-11-23
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-11-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-11-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The change adds a `source-not-at-revision` finding kind and a `revision_check` run-state object to `findings`, wired through the API, CLI, nightly report, and MCP tool. The integration is mostly clean and additive within `findings_version` 1, but there are a few correctness concerns around the `revision_check` summary line, the `_revision_findings` description for the "not at commit" cause, and the `check_sources` call being unconditional even when the check is off.

## Findings

- [warning] f-8a93a723: The description says "the path exists at that repository's HEAD {repository.head}" unconditionally, but `repository.head` may be `None` (e.g., a repository that was used but whose HEAD could not be resolved, or a skipped repo). If `head` is `None`, the message reads "HEAD None", which is misleading. Also, the claim "the path exists at that repository's HEAD" is asserted without verification — the code only knows the path is absent at the cited sha, not that it exists at HEAD. (src/wiki_studio/findings.py)
- [warning] f-a3d3f1ba: `check_sources` is invoked even when the revision check will be off (no usable repository, git missing). That is presumably fine because `check_sources` itself detects the off state, but it means every `findings` call now shells out to git (or attempts to) even for callers that never cared about revisions. More importantly, if `check_sources` raises on an unexpected git failure rather than returning an off-state, `findings` would now fail where it previously succeeded. Confirm `check_sources` is total (never raises) for all git failure modes, including timeouts and permission errors. (src/wiki_studio/findings.py)
- [warning] f-9dce56a0: The summary line uses `STATE_ON`/`STATE_OFF` constants but the "on" branch does not include the reason when some repositories were skipped. The text output therefore cannot distinguish "on with all repos used" from "on with some repos skipped" beyond the count — acceptable, but the `not_checked` breakdown (e.g., "no sha", "not found, skipped") is only in JSON. The CLI text line is the primary human surface; consider whether the count of not-checked sources is enough. Not blocking, but the summary is the only human-readable signal that sources were skipped. (src/wiki_studio/revisions.py)
- [note] f-d94b8f65: `searched` is built from `check.repositories` (all repositories, including skipped ones), but the `CAUSE_COMMIT_NOT_FOUND` description says "none of the repositories searched has". If a repository was skipped, it was not searched, so the message overstates coverage. The test `test_a_commit_missing_while_a_repository_is_skipped_is_not_checked` confirms skipped repos suppress the finding entirely, so this branch only fires when all repos were usable — but the code does not enforce that invariant locally; it relies on `check_sources` semantics. (src/wiki_studio/findings.py)
- [note] f-381c089f: The `else` branch assumes any non-`CAUSE_NOT_AT_COMMIT`/`CAUSE_COMMIT_NOT_FOUND` reason is a malformed sha. If `revisions` later adds a new cause constant, this silently mislabels it as malformed. Prefer an explicit `elif source.reason == CAUSE_MALFORMED_SHA` (or equivalent) and a fallback that does not claim "malformed". (src/wiki_studio/findings.py)
- [note] f-4a5e9bb0: This test asserts the skipped-repo case yields no finding, which is correct per spec, but it does not assert the `revision_check` state is still `on` with the skipped repo listed. Add an assertion on `revision_check.repositories[1]["status"] == "skipped"` to lock the invariant that a skipped repo does not turn the whole check off. (tests/test_revision_findings.py)
- [note] f-d3bf5798: The fixture mutates the root into a git repo mid-`build_fixture_wiki`, and the comment notes it must run before the glossary page is written because "the staged-tree lint would reject" it. This ordering dependency is fragile: a future reordering of `build_fixture_wiki` will silently break the fixture. Consider isolating the git-repo setup into its own test case rather than entangling it with the shared fixture. (tests/test_findings.py)
- [note] f-77fe0570: The changelog says the limit defaults to 500 and that "once it is reached, the remaining sources are reported as not checked, never as findings." This is a good invariant, but there is no test in the diff exercising the call-limit path. Add a test that sets `WIKI_STUDIO_GIT_CALL_LIMIT` low and asserts sources beyond the limit appear in `not_checked` and produce no findings. (CHANGELOG.md)
