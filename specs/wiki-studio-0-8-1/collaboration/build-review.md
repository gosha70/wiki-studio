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

This is a docs-and-version release (0.8.1) with no runtime, API, or schema changes; the diff is limited to CHANGELOG, README, roadmap, compatibility, CLAUDE.md, two new eval/composition issue texts, and the version bump in `pyproject.toml`, `__init__.py`, and the CLI contract test. The correctness surface is small and the version bump is consistent across all three locations. The main risks are documentation-accuracy claims (pending CI runs, placeholder permalinks) and the fact that the compatibility row is marked "Pending" while the CHANGELOG asserts the jobs are blocking.

## Findings

- [note] f-80b13a72: The 0.8.1 compatibility row is marked **Pending** with no green run id, while CHANGELOG and roadmap describe the `quickstart`, `quickstart-memkernel`, and `demo-correction-loop` jobs as blocking and shipped. A reader could reasonably read the compatibility matrix as claiming tested compatibility that has not yet been demonstrated on `main`. (docs/compatibility.md)
- [note] f-59538b8c: The comment and successor-issue bodies contain unfilled placeholders that must be substituted in an interactive step after the build. If the substitution is missed, the posted comment will contain literal `{design_permalink}` text and a broken link, and the issue will close on a restatement that points nowhere. (eval/composition/issue-10-comment.md)
- [note] f-d67eb24e: The CHANGELOG, README, and roadmap all defer issue numbers to a post-merge step. If the follow-up edit is forgotten, three documents will permanently reference "the memkernel issue" without a number, and the `Closes #10` claim in the PR body will be the only durable record. (CHANGELOG.md)
- [note] f-cbc46409: The version assertion is hard-coded to `"0.8.1"` and must be bumped in lockstep with `pyproject.toml` and `__init__.py` on every release. This is the existing pattern, so it is not a regression, but it is a three-place edit that is easy to miss. (tests/test_cli_contract.py)
- [note] f-1f736c0e: The README cites specific numbers (25/25, +0.0, 4,309,745 tokens, 19-20 million per arm) from an external report. These are accurate to the linked report as far as can be checked from the diff, but they are load-bearing claims in the project's own evidence narrative and will silently rot if the upstream report is amended. (README.md)
