---
cooldown_after_cycle: "08"
started: 2026-11-19
ended: 2026-11-22
duration: 4d
---

<!-- Generated at the end of a cooldown by the cooldown-report agent. -->
<!-- Summarizes bug fixes + lists pitches ready for the next betting table. -->

# Cooldown after Cycle 08

## Summary

Cycle 08 bet on `54-reusable-patterns` (issue 54), a 2w research spike. The
study asked whether the wiki should get reusable patterns, and in what form.

**No release.** The study ships no package code: nothing under
`src/wiki_studio/` changed. Build PR #117 (merge `25b9e13`, 2026-11-19 UTC, a
merge commit) closed issue 54 (closed by #117).

**Recommendation: docs and a template** (`docs/patterns.md`), not a new
finding or verb:
- No duplicate signal passed its frozen bar. Signal (b) (titles and summaries)
  is one disputed label away from passing, and the report says so.
- The revision check flagged 13 pages; 12 of the 13 flags were false.
- Three follow-up issue drafts are in `eval/patterns/issues/`. The owner chose to file all three on 2026-11-22, as issues 119, 120 and 121, with links pointing at files at 25b9e13:
  - [issue 119](https://github.com/gosha70/wiki-studio/issues/119), the pattern template in page-types (draft: [eval/patterns/issues/pattern-template-in-page-types.md](https://github.com/gosha70/wiki-studio/blob/25b9e13/eval/patterns/issues/pattern-template-in-page-types.md))
  - [issue 120](https://github.com/gosha70/wiki-studio/issues/120), a revision-aware stale check (draft: [eval/patterns/issues/revision-aware-stale-check.md](https://github.com/gosha70/wiki-studio/blob/25b9e13/eval/patterns/issues/revision-aware-stale-check.md))
  - [issue 121](https://github.com/gosha70/wiki-studio/issues/121), a title-and-summary duplicate finding (draft: [eval/patterns/issues/duplicate-title-summary-finding.md](https://github.com/gosha70/wiki-studio/blob/25b9e13/eval/patterns/issues/duplicate-title-summary-finding.md))

PRs in the cycle:

- #115 spec, two review rounds.
- #116 the approval commit.
- #117 build. It was an auto-build (pr profile, DeepSeek as the gating
  reviewer): seven steps, each passing in one round. The labels were frozen in
  step 3 (commit `dbd8c60`) before any signal code was written.
  - Step 2's first review was inconclusive: a 4,041-line diff against the
    reviewer's 500-line view. Rerun with `CCT_REVIEW_DIFF_MAX_LINES=6000`, it
    passed.
  - Cost $157.63 against the $150 cap (the driver checks the cap only before
    each step).
  - The owner opened #117 by hand during the milestone pause and asked the
    build session to reuse it.
  - Four commits after the build, outside DeepSeek's review, were reviewed by
    the external reviewer (`0087e6f`, `9b74f7a`, `7ae4abe`, `d834a43`). One
    corrected an earlier wrong claim that the disputed label decides no
    verdict.
  - The owner signed off; the driver then added three run-record commits and
    did not rewrite the branch.

The pitch is `bet_status: shipped` and all six hill scopes are done. Both were
set at close by hand.

Also during the cycle:
- An advisory DeepSeek PR-review workflow (PR #118, merged as `ff30e34`), on plain `pull_request`. The repository secret
  `DEEPSEEK_API_KEY` was set.
- GitHub blocks `pull_request_target` by default in public repositories from
  2026-12-02. The owner created an Active Actions policy allowing it for
  `.github/workflows/review-gate.yml` only; the gate ran under it.

## Bug fixes shipped

Window: from `25b9e13` (2026-11-19 UTC). None. Every build step passed its
review in one round, so PR #117 has no review-round fix commits. The four
post-build commits are review-round corrections to the study inside the build
PR, not fixes to released code. No fix to released code landed in the window.

| Commit | Pitch / area | One-line description |
|--------|--------------|----------------------|

## Polish & follow-ups

- #118 (merged as `ff30e34`): the advisory DeepSeek PR-review workflow.
- The Actions policy for `review-gate.yml` under `pull_request_target` (repository setting, by the owner).

## Process notes

- **Cost-cap overrun.** $157.63 against a $150 cap, because the driver checks the cap only before each step.
- **The 500-line review default will stop large data steps again.** `CCT_REVIEW_DIFF_MAX_LINES=6000` worked for step 2.
- **Weigh DeepSeek's advisory reviews against live evidence.** On #118 most of its findings were wrong, and it missed the real SIGPIPE bug.
- **The three drafted issues are filed** (owner, 2026-11-22): issue 119 (the pattern template in page-types), issue 120 (a revision-aware stale check) and issue 121 (a title-and-summary duplicate finding).
- **The driver never updates the hill.** Scopes were set to done by hand at close.

## Pitches shaped during cooldown

None.

## Recommended bets for next cycle

No shaped pitches.

| pitch_id | Appetite | Rationale |
|----------|----------|-----------|

Candidates, all to be shaped:

- Issues 119, 120 and 121, filed from the study's drafts on 2026-11-22: to be shaped if the owner picks one.
- Issue 75 (parked; memkernel's lifecycle test design started on 2026-11-18 as memkernel PR #144, still open).

### Next-bet recommendation

**Next-bet recommendation:** none shaped. Run `/shape <topic>` to draft the next bet before the betting table.

## Carryover

- [x] Issue 54, the reusable-patterns study (#115, #116, #117).
- [x] Advisory DeepSeek PR-review workflow, #118 (merged as `ff30e34`).
- [x] File the three follow-up drafts (issues 119, 120, 121).
- [ ] Stale memkernel CI pin: CI tests memkernel 0.6.0 while newer memkernel releases exist.
- [ ] Optional follow-up: code-copilot-team's own copy of the persona.
- [ ] Auto-build driver bugs: code-copilot-team #427, #463 and #471 are closed there; recheck on the next build that a resumed run no longer replaces an adopted PR's description or appends "(Closes #N)" to its title (seen on #117 in this cycle).
- [ ] File in code-copilot-team: the cost cap is checked only before each step, so a run can finish over it ($157.63 against $150 in this cycle).
- [ ] File in code-copilot-team: the 500-line default review limit (`CCT_REVIEW_DIFF_MAX_LINES`) stops a data-heavy step as "inconclusive"; this cycle needed 6,000.
- [ ] Optional, from step 2's review: no test checks the background copy's `links_rewritten` counts in the patterns study's manifest.
- [ ] Issue 75 and memkernel PR #144.
