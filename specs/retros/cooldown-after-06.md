---
cooldown_after_cycle: "06"
started: 2026-11-16
ended: 2026-11-16
duration: 1d
---

<!-- Generated at the end of a cooldown by the cooldown-report agent. -->
<!-- Summarizes bug fixes + lists pitches ready for the next betting table. -->

# Cooldown after Cycle 06

## Summary

Cycle 06 bet on `69-one-set-of-instructions` (issue #69). The curator persona
`WIKI_MAINTAINER.md` now holds the propose, promote, lint and approve loop that
memkernel 0.8.0's templates send agents to. Memory tools stay in memkernel's
template.

**0.9.2 is not released yet.** Build PR #103 (merge `e2a80c7`, 2026-11-16)
closed #69 and is merged on main, but the owner is holding the tag. Still to do:

- the release PR: date the CHANGELOG heading, and add the 0.9.2 compatibility row naming the green main run
- the memkernel #86 comment naming #103

PRs in the cycle:

- #99 pitch. It took two review rounds: D3 was revised so the persona yields to the host, and one agent name is used with `--by`.
- #100 bet and cycle start.
- #101 spec. The review requested changes:
  - a reservation holds under `auto_approve_on_promote` by stopping after propose
  - approval is bound to the reviewed bytes: `read --json`, then `approve --revision` for each page
- #102 the approval commit (automation.json, origin record).
- #103 build. It was an auto-build (pr profile, DeepSeek as the gating reviewer): 4 phases in about 40 minutes, $17.42 of a $150 cap. Phase 1 passed after 2 rounds, phases 2–4 after 1. The per-phase gate was clean and coverage was 93.26%.

The pitch is `bet_status: shipped` and every hill scope is done. Both were set
at close by hand; the driver does not update the hill.

## Bug fixes shipped

Window: `829e688..51114b5`. All fixes landed inside PR #103, before it merged.

| Commit | Pitch / area | One-line description |
|--------|--------------|----------------------|
| `607683a` | 69-one-set-of-instructions / phase 1 | Auto-build review round 1 findings |
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

| pitch_id | Title | Appetite | Status |
|----------|-------|----------|--------|
| 70-propose-only-curation-pass | Propose-only curation pass (verb `nightly`) | 4w | shaped (bet commit for cycle 07 on `specs/bet-cycle-07`, unpushed) |

## Recommended bets for next cycle

| pitch_id | Appetite | Rationale |
|----------|----------|-----------|
| 70-propose-only-curation-pass | 4w | The only shaped pitch. The owner already bet it for cycle 07, and the order #69 then #70 was set on 2026-11-08. |

Other open issues:

- #54 (research spike). Owner, 2026-11-16: next after #70, shaped for cycle 08.
- #75 (parked until memkernel #90, which is still open)

### Next-bet recommendation

**Next-bet recommendation:** `/bet 70-propose-only-curation-pass`, then `/cycle-start 70-propose-only-curation-pass` for cycle 07. The bet commit already exists on `specs/bet-cycle-07`.

## Carryover

- [x] Issue #69, one set of instructions: merged (#103); release pending.
- [x] Issue #90: shipped in 0.9.1.
- [ ] The 0.9.2 release: tag, CHANGELOG date, compatibility row.
- [ ] memkernel #86 comment naming #103.
- [ ] Auto-build driver: the title-only closing-keyword gap (to file; related to code-copilot-team #427, #408).
- [ ] Stale memkernel CI pin: CI tests memkernel 0.6.0 while 0.8.0 is on PyPI. memkernel main moved to mcp 2.x, which is not released yet.
- [ ] Optional D7 follow-up: code-copilot-team's own copy of the persona.
- [ ] Issue #70: cycle 07.
- [ ] Issue #54: research spike.
- [ ] Issue #75 and memkernel #90.
