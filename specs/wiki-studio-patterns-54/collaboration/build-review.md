---
feature_id: wiki-studio-patterns-54
date: 2026-11-18
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-patterns-54
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-patterns-54 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The US7 phase adds a research report, a docs page, two drafted follow-up issues, and tests that pin the report's structure and the docs page's commands. The changes are documentation and test-only, with no package code touched. The tests are reasonable but have a few correctness gaps around what they actually verify versus what the docs claim.

## Findings

- [warning] f-ab70a91d: The docs commands are run against a temp copy of the fixture wiki, but `find`/`findings`/`read` are executed without first promoting/approving anything, so the test only proves the commands exit 0 on the fixture's existing state — it does not verify the docs' claim that `findings` filters to approved pages or that `read --json` returns a sha256. A regression in review-state filtering would still pass. (tests/test_patterns_eval.py)
- [warning] f-703f10bc: This test couples the existence of `docs/patterns.md` to the recommendation line, but `PatternsDocsTest.setUpClass` skips when the file is absent. If the recommendation were changed to "no change" while the file still existed, the report test would fail — but if the file were deleted and the recommendation left as "docs and a template", only this one test catches it. The coupling is fragile and the skip in `PatternsDocsTest` masks the inconsistency. (tests/test_patterns_eval.py)
- [warning] f-042cc0bc: The docs instruct `wiki-studio lint --prose` but the surrounding text says "Nothing in lint or `findings` checks the convention itself" — accurate, but the docs also claim "every page passed structural lint and prose lint" as evidence the convention works. Since prose lint is advisory and does not check `Applies when:`/`Revisit when:`, a reader could infer the convention is validated by lint. The report states this correctly; the docs page is slightly misleading. (docs/patterns.md)
- [note] f-a305417d: The report's recommendation line is the only line starting with "Recommendation:", and the test enforces exactly one. But the body also contains the phrase "Recommendation" in prose (e.g., "the list is a recommendation from the wiki side"). The test's `startswith("Recommendation:")` filter is correct, but a future edit adding a second line beginning "Recommendation:" in a quoted block would break it. Low risk, worth a comment. (eval/patterns/report.md)
- [note] f-0f777ab9: The report's `wiki-studio` lines are parsed but not executed, unlike the docs page's lines. If the report shows a command that parses but would fail at runtime (e.g., a flag combination the parser accepts but the command rejects), the test passes. This is acceptable for a report but worth noting the asymmetry. (tests/test_patterns_eval.py)
- [note] f-b15ad0b1: The issue text asserts a citation error but the report's staleness section does not repeat this specific claim in the "Limits" or evidence bullets — it appears only in the issue draft. If the issue is filed, the claim should be traceable to `results/staleness.json`. Verify the results file records the missing-file case, or soften the issue text to "the study's revision check surfaced one citation error" without naming the file unless the results file supports it. (eval/patterns/issues/revision-aware-stale-check.md)
- [note] f-29b8845e: The docs page tells memkernel to keep `corrects:` "as memkernel #57's research note says" but does not link to that note or explain what `corrects:` does in wiki-studio. A reader following the docs has no way to verify the key exists or what it means without leaving the page. (docs/patterns.md)
