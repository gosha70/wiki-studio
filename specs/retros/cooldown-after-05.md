---
cooldown_after_cycle: "05"
started: 2026-11-08
ended: 2026-11-08
duration: 1d
---

<!-- Generated at the end of a cooldown by the cooldown-report agent. -->
<!-- Summarizes bug fixes + lists pitches ready for the next betting table. -->

# Cooldown after Cycle 05

## Summary

Cycle 05 (`71-conflict-callouts`, issue #71, spec merged at `18abaa4`) shipped
as wiki-studio 0.9.0 on 2026-11-08. The tag is annotated `v0.9.0` on main
`b66b3be`, the merge of release-prep PR #91. Release workflow run 42443801004
passed; the wheel and sdist sha256 equal PyPI's and the release-page copies.
Main CI run 42443361715 was green on `b66b3be`.

PRs in the cycle:

- #85 pitch, #86 bet, #87 spec (merge `18abaa4`).
- #88 was opened by hand while the driver was parked; it was closed.
- Build PR #89 (merge `c648e9f`) closed #71. It was an auto-build (pr profile,
  DeepSeek as the gating reviewer) at $35.70 of a $150 cap.
- #91 release prep: the CHANGELOG heading dated 2026-11-08 and the compatibility
  row Tested on main run 42440785170.
- #92 (merge `3413dea`): ADR-0004 links memkernel #111.

The pitch is `bet_status: shipped` and every hill scope is done; both were set
at close by hand (the driver never updates the hill, code-copilot-team #405).

## Bug fixes shipped

Window: `18abaa4..3413dea`. All fixes landed inside PR #89, before merge. No
fix landed on main after the release PRs.

| Commit | Pitch / area | One-line description |
|--------|--------------|----------------------|
| `a65a59e` | 71-conflict-callouts / phase 1 | Auto-build review round 1 findings |
| `d9da1c0` | 71-conflict-callouts / phase 1 | Auto-build review round 2 findings |
| `0154448` | 71-conflict-callouts / phase 3 | Auto-build review round 1 findings |

## Polish & follow-ups

- `2f64036`, `2aed4b5` (PR #89): the owner amended the spec's link rule after review. The other page is the first `.md` link on the marker line, a URL-scheme `.md` target points outside the wiki, and a link title is dropped as lint does; a fresh origin-alignment record accompanies it.
- `3fd0c61` (PR #89): US1 wording fixed from the PR #88 review.
- `f8f4bfd` (PR #89): final wording from the PR #89 review.
- `3930466`, `a4d3efe` (PR #91): the CHANGELOG heading carries the tag date; the compatibility row names the green run ids.
- `f9b33b8` (PR #92): ADR-0004 links memkernel #111.
- Follow-ups filed: wiki-studio #90 (two link-less conflict markers on one page report one conflict-dangling; dedup in `conflicts.py`), memkernel #111 (where the three conflict kinds rank in `CURATION_KIND_ORDER`), code-copilot-team #427.

## Process notes

- **Review breaker on phase 1 (escalation esc-1).** DeepSeek blocked because the ADR described US2/US4 code not yet written. After the spec amendment and the US1 fix, the run resumed with `/review-decide retry`. Phase 1 passed on round 4; phases 2–5 passed (phase 3 after two rounds).
- **Driver resume needs `CCT_PROJECT_DIR`.** It ignores the current directory.
- **Finalize "updated" the closed #88 instead of opening a PR** (code-copilot-team #427).
- **`build-review.md` is overwritten by each phase** (known, code-copilot-team #404).
- **The driver never updates the hill** (code-copilot-team #405); scopes were set to done by hand at close.

## Pitches shaped during cooldown

| pitch_id | Title | Appetite | Status |
|----------|-------|----------|--------|

No pitch has `bet_status: shaped`. All pitches under `specs/pitches/` are `shipped`.

## Recommended bets for next cycle

| pitch_id | Appetite | Rationale |
|----------|----------|-----------|

No shaped pitches exist, so no bet is recommended. Candidates to shape (open issues):

1. **Issue #90: duplicate link-less conflict markers report one conflict-dangling.** A bug from cycle 05; small enough for cooldown or a small batch. Owner, 2026-11-08: fix in cooldown and release it as a 0.9.1 patch, outside a cycle.
2. **Issue #75: measure the governed composition.** Needs memkernel #90; the obsolete-answer rate needs memkernel 0.7. Owner, 2026-11-08: parked until memkernel #90 lands; not a cycle 06 candidate.
3. **Issue #54: reusable engineering patterns and duplicate knowledge.** Carried over since cooldown 03. Owner, 2026-11-08: not first; shaped after #69.
4. **Issues #69 and #70:**
   - #69: one set of maintainer instructions shared with memkernel's template
   - #70: a scheduled curation pass that only proposes

   Owner, 2026-11-08: #69 is shaped first for cycle 06 (counterpart of memkernel #86); #70 waits, after #69.

Items carried over that are not cycles on their own:

- The discovery evidence set is small.
- The Kiro host run (not release-blocking).

### Next-bet recommendation

**Next-bet recommendation:** `/shape 69` (the owner's pick, 2026-11-08). No shaped pitches are available, so draft the next bet before the betting table meets.

## Carryover

- [x] Issue #71, conflict callouts: shipped in 0.9.0.
- [ ] Issue #90: conflict-dangling dedup in `conflicts.py`.
- [ ] memkernel #111: ranking of the three conflict kinds in `CURATION_KIND_ORDER`.
- [ ] Issue #75 and memkernel #90: the composition measurement (complete only with memkernel 0.7).
- [ ] Issue #54: reusable engineering patterns and duplicate knowledge.
- [ ] Issues #69, #70.
- [ ] Auto-build driver: code-copilot-team #427 (finalize updated a closed PR), #404 (per-phase review artifact), #405 (hill updates), resume without `CCT_PROJECT_DIR`; and from cooldown 04, a per-phase bypass record.
- [ ] Kiro host run (not release-blocking).
- [ ] A larger discovery evidence set.
