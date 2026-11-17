---
cooldown_after_cycle: "06"
started: 2026-11-16
ended: 2026-11-17
duration: 2d
---

<!-- Generated at the end of a cooldown by the cooldown-report agent. -->
<!-- Summarizes bug fixes + lists pitches ready for the next betting table. -->

# Cooldown after Cycle 06

## Summary

Cycle 06 bet on `69-one-set-of-instructions` (issue #69). The curator persona
`WIKI_MAINTAINER.md` now holds the propose, promote, lint and approve loop that
memkernel 0.8.0's templates send agents to. Memory tools stay in memkernel's
template.

**Shipped as wiki-studio 0.9.2 on 2026-11-17.** Build PR #103 (merge
`e2a80c7`, 2026-11-16) closed #69. The owner chose to release before closing
the cycle:
- Release PR #106 (merge `2b65556`) dated the CHANGELOG heading `[0.9.2] —
  2026-11-17`. It added the tested 0.9.2 compatibility row, naming main run
  43804626412 on `e2a80c7`, and recorded the owner's fixes in the automation
  summary.
- The annotated tag `v0.9.2` (object `5eccb1d`) is on `2b65556`. Main CI run
  43984028854 was green there.
- Release workflow run 43985069049 passed. The wheel and sdist sha256 equal
  PyPI's and the release-page copies.
- Main's quickstart install lines resolve from PyPI again.
- The memkernel #86 comment naming #103 was posted.

PRs in the cycle:

- #99 pitch. It took two review rounds: D3 was revised so the persona yields to the host, and one agent name is used with `--by`.
- #100 bet and cycle start.
- #101 spec. The review requested changes:
  - a reservation holds under `auto_approve_on_promote` by stopping after propose
  - approval is bound to the reviewed bytes: `read --json`, then `approve --revision` for each page
- #102 the approval commit (automation.json, origin record).
- #106 the release PR (CHANGELOG date, compatibility row, automation-summary note).
- #103 build. It was an auto-build (pr profile, DeepSeek as the gating reviewer): 4 phases in about 40 minutes, $17.42 of a $150 cap. Phase 1 passed after 2 rounds, phases 2–4 after 1. The per-phase gate was clean and coverage was 93.26%.

The pitch is `bet_status: shipped` and every hill scope is done, S4's release
half included. Both were set at close by hand; the driver does not update the hill.

## Bug fixes shipped

Window: `829e688..2b65556`. None of these fixed released code. All landed inside PR #103 before it merged: one was a review-round fix by the driver, two were the owner's fixes after the external review.

| Commit | Pitch / area | One-line description |
|--------|--------------|----------------------|
| `607683a` | 69-one-set-of-instructions / phase 1 | Review-round fix inside PR #103 (auto-build round 1 findings) |
| `9481865` | 69-one-set-of-instructions / approve step | Skip draft and superseded pages; never approve a changed revision (owner, after external review) |
| `675fec9` | 69-one-set-of-instructions / auto-approval | Check auto-approval page by page against promote's approved list; tests pin all three rules (owner, after external review) |

## Polish & follow-ups

- FR-003 was amended alongside the owner's fixes, with origin records 2026-11-15-1427 and 2026-11-15-1809.
- Between cycles: the 0.9.1 patch fixed #90 (PRs #94, #97, #98; tag `v0.9.1` on `829e688`, 2026-11-15). It shipped as cycle 06 started.
- #95 (`bd5e41b`): ADR-0004 records memkernel #113's ranking.
- #96 (`3760be8`): dependabot bumped opentelemetry-api to 1.45.2.
- #104 (merge `51114b5`): pitch 70 was shaped and then revised after review.

## Process notes

- **Driver put `(Closes #69)` in the PR title only,** so GitHub linked no issue. The body was fixed by hand. This is not yet filed in code-copilot-team; it is related to #427 and #408.
- **The driver never updates the hill.** Scopes were set to done by hand at close.

## Pitches shaped during cooldown

None. Pitch `70-propose-only-curation-pass` was shaped on 2026-11-15, before
this cooldown started. It is listed below as the shaped pitch ready for the
betting table.

## Recommended bets for next cycle

| pitch_id | Appetite | Rationale |
|----------|----------|-----------|
| 70-propose-only-curation-pass | 4w | The only shaped pitch (PR #104, merge `51114b5`). The owner set the order #69, then #70, then #54 on 2026-11-08 and chose #70 for cycle 07 on 2026-11-16. |

Other open issues:

- #54 (research spike). Owner, 2026-11-16: to be shaped next, after #70, for cycle 08.
- #75 (parked until memkernel #90, which is still open)

### Next-bet recommendation

**Next-bet recommendation:** `/bet 70-propose-only-curation-pass`, then `/cycle-start 70-propose-only-curation-pass` for cycle 07.

## Carryover

- [x] Issue #69, one set of instructions: shipped in 0.9.2 (#103, #106).
- [x] Issue #90: shipped in 0.9.1.
- [x] The 0.9.2 release: tag, CHANGELOG date, compatibility row (#106, `v0.9.2`).
- [x] memkernel #86 comment naming #103.
- [ ] Auto-build driver: the title-only closing-keyword gap (to file; related to code-copilot-team #427, #408).
- [ ] Stale memkernel CI pin: CI tests memkernel 0.6.0 while 0.8.0 is on PyPI. memkernel main moved to mcp 2.x, which is not released yet.
- [ ] Optional D7 follow-up: code-copilot-team's own copy of the persona.
- [ ] Issue #70: cycle 07.
- [ ] Issue #54: research spike.
- [ ] Issue #75 and memkernel #90.
