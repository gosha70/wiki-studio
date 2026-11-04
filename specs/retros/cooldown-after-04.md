---
cooldown_after_cycle: "04"
started: 2026-11-04
ended: 2026-11-04
duration: 1d
---

<!-- Generated at the end of a cooldown by the cooldown-report agent. -->
<!-- Summarizes bug fixes + lists pitches ready for the next betting table. -->

# Cooldown after Cycle 04

## Summary

Cycle 04 (`10-release-b-launch-and-measurement`, started at `07ef1b9` on
2026-11-03) shipped as wiki-studio 0.8.1 on 2026-11-04. The tag is annotated
`v0.8.1` on main `44e50a0`, the merge of PR #77, which dated the CHANGELOG
heading. Two PRs came before it:

- Evidence PR #76 (merge `e8edfe9`) added the recorded correction-loop run,
  the demo page quotes and the tested compatibility row.
- Build PR #74 (merge `a0bd609`) was an auto-build with DeepSeek as the gating
  reviewer, at $80.91 of a $150 cap. The phase 2 review breaker was bypassed
  after its false positive was disproved. The bypass is recorded in
  `specs/wiki-studio-0-8-1/collaboration/build-review-phase-2.md`.

The pitch is `bet_status: shipped` and all five hill scopes are done.
Release workflow run 41833546435 built the wheel and sdist, and their hashes
equal PyPI's.

PR #74 closed issue #10 by restatement. Pitch PR #68's body had closed the
issue early through a closing keyword, so it was reopened before #74 merged.
The measurement continues in the successor issue wiki-studio #75; memkernel
#90 carries the design, `eval/composition/design.md`. Both are open.

During this cooldown, the adoption row in `eval/composition/design.md` was
updated to name the committed recorded run, with a note that it changed after
filing; it is committed with this report. No pitch was shaped in the cooldown.

## Bug fixes shipped

Window: `07ef1b9..44e50a0`. All fixes landed inside PR #74, before merge.

| Commit | Pitch / area | One-line description |
|--------|--------------|----------------------|
| `74248c3` | 10-release-b-launch-and-measurement / phase 2 | Auto-build review round 1 findings |
| `2578ea3` | 10-release-b-launch-and-measurement / phase 2 | Auto-build review round 2 findings |
| `a429d20` | 10-release-b-launch-and-measurement / recorder | External review: the recorder is bound to the captured commit, and every attempt leaves a manifest |
| `e1de3d1` | 10-release-b-launch-and-measurement / recorder | External review: an interrupted attempt leaves a failed manifest |
| `2dbd276` | 10-release-b-launch-and-measurement / tests | Regression test: the recorder writes an attempt manifest on every exit path |

## Polish & follow-ups

- `83aef2d` (PR #74): the phase 2 bypass is shown on the review surfaces, and the protocol states the binding and attempt rules.
- `c999515` (PR #74): README, the roadmap and the CHANGELOG cite the filed issue numbers.
- `edc3036`, `dc5dda0`, `c8d7e85` (PR #76): the recorded correction-loop run (FR-014), the demo page quotes and the green run ids in the compatibility row.
- `10c68fa` (PR #77): the CHANGELOG heading carries the tag date.
- The release page first lacked the dist files and had one relative link. Both were fixed after the reviewer checked the page; neither fix is a repo commit.
- With this report: the adoption row in `eval/composition/design.md` names the committed recorded run (updated after filing as memkernel #90).

## Process notes

- **The auto-build driver still reports a bypassed phase as PASS and overwrites the review artifact.** The bypass record had to be restored by hand (`a2b9077`, `83aef2d`). This needs a per-phase bypass record in the driver, plus a summary and PR body that state the bypass.
- **Closing keywords in PR bodies close issues.** "closing #10" in pitch PR #68 closed #10 on merge. Check `closingIssuesReferences` before opening a PR.
- **Release-page checklist.** Attach the wheel and sdist to the GitHub release, use absolute links only, and compare the dist hashes with PyPI's.

## Pitches shaped during cooldown

| pitch_id | Title | Appetite | Status |
|----------|-------|----------|--------|

No pitch has `bet_status: shaped`. All four pitches under `specs/pitches/` are `shipped`.

## Recommended bets for next cycle

| pitch_id | Appetite | Rationale |
|----------|----------|-----------|

No shaped pitches exist, so no bet is recommended. Candidates to shape:

1. **Issue #75: measure the governed composition with a task set that can discriminate the arms.** The design is in `eval/composition/design.md`. It needs memkernel-side work (memkernel #90). Withdrawing deprecation and deletion also needs memkernel 0.7. <!-- author note: priority, and whether to wait for memkernel 0.7 -->
2. **Issue #54: govern reusable engineering patterns and assess duplicate knowledge.** Carried over from cooldown 03. <!-- author note: not yet scoped -->
3. **Issues #69, #70, #71.** These were filed during cycle 04:
   - #69: one set of maintainer instructions shared with memkernel's template
   - #70: a scheduled curation pass that only proposes
   - #71: mark disagreements between sources without a model

   <!-- author note: whether any becomes a small-batch pitch -->

Items carried over from cooldown 03 that are not cycles on their own:

- The discovery evidence set is small: 21 development and 53 held-out questions.
- The Kiro host run (not release-blocking).

### Next-bet recommendation

**Next-bet recommendation:** `/shape <topic>`. No shaped pitches are available, so draft the next bet before the betting table meets.

## Carryover

- [x] Issue #10, the Release B launch items and the integration measurement design: shipped in 0.8.1.
- [x] The adoption row in `eval/composition/design.md` names the recorded run (with this report).
- [ ] Issue #75 and memkernel #90: the composition measurement; memkernel runs it, and the obsolete-answer rate is complete only with memkernel 0.7 (withdrawal on deprecation and deletion).
- [ ] Issue #54: reusable engineering patterns and duplicate knowledge.
- [ ] Issues #69, #70, #71.
- [ ] Auto-build driver: a per-phase bypass record, and no PASS reported for a bypassed phase.
- [ ] Kiro host run (not release-blocking).
- [ ] A larger discovery evidence set.
- [ ] Owner, outside this repo: link the composition quickstart from memkernel's README.
- [ ] Owner, outside this repo: update the memkernel.dev project page.
