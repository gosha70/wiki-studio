---
cooldown_after_cycle: "07"
started: 2026-11-17
ended: 2026-11-18
duration: 2d
---

<!-- Generated at the end of a cooldown by the cooldown-report agent. -->
<!-- Summarizes bug fixes + lists pitches ready for the next betting table. -->

# Cooldown after Cycle 07

## Summary

Cycle 07 bet on `70-propose-only-curation-pass` (issue 70). The new `nightly`
verb runs a propose-only curation pass. It writes a model-free report. With an
explicit backend it also writes link-only drafts, named per finding, so a
rerun never creates a duplicate.

**Shipped as wiki-studio 0.10.0 on 2026-11-18.** Build PR #111 (merge
`93fe442`, 2026-11-17) closed issue 70 (closed by #111). Release prep:
- Release PR #112 (merge `2fe98df`) dated the CHANGELOG heading, added the
  0.10.0 compatibility row, added the CLAUDE.md line for `nightly` and
  recorded a note in the automation summary.
- The annotated tag `v0.10.0` (object `f404388`) is on `2fe98df`. Main CI run
  44241408370 was green there.
- Release workflow run 44351640411 passed. The wheel and sdist sha256 equal
  PyPI's and the release-page copies.
- Main's quickstart install lines resolve 0.10.0 from PyPI.

PRs in the cycle:

- #104 pitch. It took two review rounds: D5 (link-only drafts are checked), D21 (a person approves nightly drafts), D9 (exit-code precedence).
- #105 the cycle 06 close-out, held until 0.9.2 shipped.
- #106 the 0.9.2 release PR.
- #107 bet and cycle 07 start.
- #108 spec. A draft plus review rounds:
  - the owner kept link text unconstrained, against the reviewer's recommendation, except that empty link text is refused
  - fixed line forms for the index and the log
  - one cap on proposals plus attempts
  - links inside code are refused
- #109 the approval commit (automation.json, origin record).
- #111 build. It was an auto-build (pr profile, DeepSeek as the gating reviewer): 6 phases, each passing in one round, $87.12 of a $150 cap. Coverage was 93.35–93.57%, with 1471 tests at phase 6.
- #112 the release PR.

The build session ran FR-024's manual real-backend check with the Claude Code
CLI 2.1.325: 2 minimal drafts, the wiki byte-identical, and a rerun created
nothing. The evidence is in a comment on #111.

The pitch is `bet_status: shipped` and all six hill scopes are done. Both were
set at close by hand; the driver does not update the hill.

## Bug fixes shipped

Window: `93fe442..2fe98df`. None. Every build phase passed its review in one
round, so PR #111 has no review-round fix commits, and no fix to released code
landed in the window.

| Commit | Pitch / area | One-line description |
|--------|--------------|----------------------|

## Polish & follow-ups

- #112 (merge `2fe98df`): the 0.10.0 release prep (CHANGELOG date, compatibility row, CLAUDE.md line, automation-summary note).
- #110 (merge `9178147`): pitch `54-reusable-patterns` was shaped.
- Between cycles: 0.9.2 shipped on 2026-11-17 (tag `v0.9.2` on `2b65556`), and the memkernel #86 comment naming #103 was posted.

## Process notes

- **Driver again put the closing keyword in the PR title only** (seen in #103 and #111). The body was edited by hand. This is not filed yet; it is related to code-copilot-team #427 and #408.
- **The driver never updates the hill.** Scopes were set to done by hand at close.
- **Infrastructure incident.** code-copilot-team's home moved to `~/.cct` (b99333c). The migration left `~/.cct/providers.toml` and its four backups empty, which blocked the driver. The owner rotated the DeepSeek key and restored the file on 2026-11-17. Filed as gosha70/code-copilot-team#463.
- **Owner decision noted by the reviewer:** `is_dir()` stays the test for "already proposed", so a symlinked directory counts.

## Pitches shaped during cooldown

None. Pitch `54-reusable-patterns` was shaped during the cycle, while the build ran: it was committed at 2026-11-17T20:39Z, and the build merged at 2026-11-18T03:28Z. Its PR #110 (`9178147`) merged after the build. It is listed below as the shaped pitch ready for the betting table.

## Recommended bets for next cycle

| pitch_id | Appetite | Rationale |
|----------|----------|-----------|
| 54-reusable-patterns | 2w | The only shaped pitch. The owner set the order #69, then #70, then #54, and picked it for cycle 08 (D1: 2w for cycle 08). The circuit breaker names its cut order with a trigger for each cut. |

Other open issues:

- #75 (parked until memkernel #90, which is still open).

### Next-bet recommendation

**Next-bet recommendation:** `/bet 54-reusable-patterns`, then `/cycle-start 54-reusable-patterns` for cycle 08.

## Carryover

- [x] Issue 70, the `nightly` verb: shipped in 0.10.0 (#111, #112).
- [x] The 0.10.0 release: tag, CHANGELOG date, compatibility row (#112, `v0.10.0`).
- [x] The 0.9.2 release (#106, `v0.9.2`).
- [x] memkernel #86 comment naming #103.
- [ ] Auto-build driver: the title-only closing-keyword gap (to file; related to code-copilot-team #427, #408).
- [ ] Stale memkernel CI pin: CI tests memkernel 0.6.0 while newer memkernel releases exist.
- [ ] Optional D7 follow-up: code-copilot-team's own copy of the persona.
- [ ] Issue 54: research spike, cycle 08.
- [ ] Issue #75 and memkernel #90.
