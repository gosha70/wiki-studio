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

This is a design-only document (plus a README pointer) that preregisters nothing and runs nothing, so the correctness surface is limited to factual claims, internal consistency, and the accuracy of code/file citations. The document is unusually careful about its own scope and correctly refuses to overclaim from the 0.5.0 diagnostics. The main correctness risks are unverifiable external citations and a few internal claims that depend on code behavior the reviewer cannot confirm from the diff alone.

## Findings

- [note] f-06520eeb: The document cites specific line numbers in external memkernel v0.5.0 files (task.json:14, task.json:23, config.frozen.json:21, report-0.5.0.md:23, 87-108, 110-118, 155-163, 325-338). These cannot be verified from this diff and are load-bearing for the §1.1 ceiling argument. (eval/composition/design.md)
- [note] f-b8b990a8: The claim that `approve` refuses `status: draft` and that governed import imports approved revisions only is central to the "curator step is mandatory" argument, but the cited line range is not shown in the diff and the behavior is asserted, not demonstrated. (eval/composition/design.md)
- [note] f-226c1c3a: The gate-breach definition depends on precise file paths and field names (`submission_digest`, `actor`, `started_at`, `committed_at`, `approved_sha256`, `.applied/<name>/receipt.json`, `.audit/approvals/`, `.audit/proposals/<name>/`). If any of these drift, the breach count silently becomes wrong (either over- or under-counting). (eval/composition/design.md)
- [note] f-da1ecdaf: Requirement 3 says the correction must travel only through the arm's own workflow and that the shared-artifact rule "has to change," but §3.1's arm table does not state what each arm's correction path is in the new comparison (only §2.1 prose does). A reader building the arm from §3.1 alone would not know the fs_grep and memkernel correction paths. (eval/composition/design.md)
- [note] f-84e92ed1: The informed reference for 2.345 under banker's rounding is stated as 2.34. Banker's rounding to the nearest cent of 2.345 is ambiguous in binary floating point (2.345 is not exactly representable), and the "round half to even" rule applied to the exact decimal 2.345 gives 2.34, but a naive float implementation may give 2.35. This is a task-design correctness risk: the checker may disagree with the intended reference depending on implementation. (eval/composition/design.md)
- [note] f-805bfbc9: The session-1 question ("can a change ready Thursday 16:00 UTC be deployed that week?") has an informed answer ("next window is following Monday") that depends on the correction also specifying the new window's opening day/time. The sketch states the window "closing Thursday at 15:00 UTC" but does not state when the next window opens, so the informed reference is underdetermined by the stated correction. (eval/composition/design.md)
- [note] f-56b4d818: The diagnostic counts are quoted as facts from the 0.5.0 report but the document does not state the denominator's scope (per-arm? per-group? all trials?). A reader cannot tell whether "177 Bash calls" is the wiki_studio arm's total across all groups or only lc-wiki. (eval/composition/design.md)
- [note] f-47b51901: The policy is described as "may only use the exported draft and the task's correction brief" and "must not special-case task ids," but there is no stated mechanism to enforce the no-special-casing rule. A scripted curator that reads the correction brief can trivially branch on its content. (eval/composition/design.md)
- [note] f-33fc03ba: The note says the arm files are "frozen at wiki-studio 0.4.1 and are not edited," which is consistent with §3.1, but it does not warn that the new composition arm must not reuse the 0.4.1 instruction's `status: draft` behavior (which §3.2 says makes pages invisible to governed import). (docs/agent-arm/README.md)
- [note] f-a2e410ae: The row cites `test_release_b_loop.py` for the retry property but does not state whether that test currently passes or is skipped; a design doc citing a test as evidence should note its status. (eval/composition/design.md)
