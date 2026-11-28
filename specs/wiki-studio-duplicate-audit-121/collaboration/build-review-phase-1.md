---
feature_id: wiki-studio-duplicate-audit-121
date: 2026-11-27
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-duplicate-audit-121-evidence
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-duplicate-audit-121 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The change freezes the duplicate-audit study protocol (README + protocol.json) with a hash-pinning test, before any audit code exists. The protocol is internally consistent and the freeze test correctly pins the README, protocol, and development inputs. I found one correctness issue in the freeze test's coverage of the protocol's own invariants, plus a few notes on documentation/design consistency.

## Findings

- [warning] f-410c9847: The freeze test pins the bar's four values but does not pin the verdict/winner-line vocabulary, the candidate flag rule, or the restatement rule order — the very things the README says are frozen. A future edit to `protocol.json` that changes `verdicts`, `winner_lines`, or `restatement.order` would pass this test while silently changing the study. (tests/test_duplicate_audit_frozen.py)
- [warning] f-1284b2f4: The README states condition 2 as "finds at least three quarters of the true pairs, rounded up, counted per true pair: `4 * found >= 3 * n`". The integer form `4*found >= 3*n` is equivalent to `found >= ceil(3n/4)` only when n is such that 3n/4 is not already an integer; for n divisible by 4 the two agree, but the README's prose "rounded up" and the integer form are consistent — however the protocol.json `bar.rule` restates it as "4 * found >= 3 * n, counted per true pair" without the "rounded up" gloss, and neither pins that `found` counts distinct true pairs (not flagged pairs). (eval/duplicate_audit/protocol.json)
- [note] f-4f009df7: The README pins `eval/similar/rank.py` by sha256 and says "The audit script imports `rank.py`'s `slug_paths`, so it is pinned as an input." But the protocol also depends on `discovery.similar_query`, `discovery.DEFAULT_RANKER_CONFIG`, `search_index.build_document`, and `review.frontmatter_value` — none of which are pinned. A change to any of those would silently alter the measured path without tripping the freeze. (eval/duplicate_audit/README.md)
- [note] f-0318ad0d: The memkernel pin is recorded as "the commit its local `main` pointed to when this phase ran" — a moving reference resolved once. The protocol records the resolved sha, which is good, but the README's phrasing ("the commit its local `main` pointed to when this phase ran") invites a reader to re-resolve `main` later and get a different commit. The frozen sha is the binding one; the prose should say so unambiguously. (eval/duplicate_audit/protocol.json)
- [note] f-7c7a51d4: Rule (b) requires the spec bundle's `origin_issue` to be "an integer equal to the leading number of the pitch id". The README notes memkernel's `origin_issue` is null "because its `plan.md` `issue:` names a memkernel issue as a string, never an integer" — but the protocol's `corpus_json.origin_issue` field says "the integer on the `issue:` line ... else null". If a future bundle writes `issue: 121` (unquoted integer) in a memkernel plan, rule (b) would fire for a memkernel pitch/spec pair, contradicting the README's blanket "A memkernel bundle never meets (b) either." (eval/duplicate_audit/README.md)
- [note] f-bbf81c87: The docstring says the module "is edited only by a protocol change the owner asks for at the pause after US1, in the same commit as that change and before `audit.py` exists." This is a process constraint, not enforced by the test. A future contributor could edit the constants without a protocol change and the test would still pass (it would just pin the new bytes). (tests/test_duplicate_audit_frozen.py)
- [note] f-3171b9c0: The README says the sample is "drawn once, from the labelling commit's labels, before any owner change, and never re-drawn." The protocol's `review_sample.when` matches. But the sample script `eval/duplicate_audit/sample.py` does not yet exist (it is listed as written after sign-off). The freeze test does not check that `sample.py` will use `random.Random(121).sample(sorted(population), k)` — that is only prose. If `sample.py` is written later with a different draw, the freeze test will not catch it. (eval/duplicate_audit/README.md)
