---
cooldown_after_cycle: "11"
started: 2026-11-25
ended: 2026-11-26
duration: 2d
---

<!-- Generated at the end of a cooldown by the cooldown-report agent. -->
<!-- Summarizes bug fixes + lists pitches ready for the next betting table. -->

# Cooldown after Cycle 11

## Summary

Cycle 11 bet on `121-similar-pages-at-propose` (issue 121): a model-free hint
in `propose` that lists the 5 existing pages of the same type most like a new
page, ranked by `find`'s FTS5 ranker.

**Measured, then built.** Evidence PR #146 (merge `fcdf1ae`) carries the
protocol, the ranking script and the report. Build PR #148 (merge `5927122`)
ships the hint.

**Measurement** (`eval/similar/report.md`):
- Found 11 of 13 tries (bar 10); 1 of 3 `supersedes` (bar 1). Verdict: pass.
- The two misses are the location-only rulings, at ranks 6 and 35.
- Noise: 7 companion pages and 47 unrelated pages in the lists.
- Not binding: whole page 10 of 13 (0 `supersedes`), body only 8 of 13, the
  issue 54 fixture 4 of 4.
- Development data, so weak evidence. The external reviewer reproduced the
  result on their own from the spec.

**Shipped to main** (CHANGELOG `[Unreleased]`, Added):
- `edits[].similar_pages` or `edits[].similar_pages_error` in `plan.json`.
- `similar:` lines on stderr from the CLI.
- A `similar_pages` key from the MCP `propose` tool.
- `WIKI_STUDIO_SIMILAR_PAGES=off` turns it off.

PRs in the cycle:

- #140, #141 the pitch.
- #143 the bet and cycle start.
- #144 the spec bundle.
- #145 the approval and run 1 settings.
- #146 the evidence PR (run 1, US1 to US3).
- #147 the spec amendment: verdict pass, run 2 settings.
- #148 the build PR (run 2, US4 to US6), two review fixes.

The pitch is `bet_status: shipped`. Hill scopes S1 to S5 are done. Issue 121
stays open; the owner decides by hand whether the hint answers it.

## Bug fixes shipped

Window: from `466c87e`. None. The `fix(...)` commits on main are review rounds
inside the cycle's own PRs: `47ec9c6` (run 2, phase 5), and on PR #148
`b91e968` (the CLI prints the search-cache warning, as `find` does) and
`c3c130b` (a `DiscoveryWarning` filtered as an error never blocks `propose`).

| Commit | Pitch / area | One-line description |
|--------|--------------|----------------------|

## Polish & follow-ups

None outside the cycle. Open:

- **The off switch does not reach library callers.** `WIKI_STUDIO_SIMILAR_PAGES`
  is read only by `WikiPaths.resolve`, which the CLI and the MCP server use;
  `WikiPaths.for_root` defaults the hint to on and ignores the variable, as
  FR-021 specified. `for_root` is what `docs/consumers.md` shows library
  callers and what memkernel's export uses when it calls `api.propose`. The
  external review of PR #149 measured it: with the variable set to `off` and
  paths from `for_root`, 100 of 100 new pages still got a list, and a
  100-page proposal on a 500-page wiki took 4.9 s instead of 0.03 s. The
  README and CHANGELOG say the variable "turns it off" without naming this
  limit. Found after PR #148 merged; a follow-up should either read the
  variable in `for_root` too or state the limit.
- **Cosmetic:** the search-cache warning prints once per new page (twice with
  two creates), where `find` prints it once.

## Process notes

- **Run 2 started fresh with `--start-phase 4`** (plan departure 16).
- **The resume after US4 skipped phase 4.** It used `--resume --start-phase 4`,
  and the driver skipped phase 4. The external review of PR #147 had caught
  that a plain `--resume` would rebuild steps 1 to 3.
- **Run 1's first sign-off cited a review the owner pasted** (plan departure
  17), corrected in `automation-summary.md`.
- **Auto-build sessions cannot run Python.** The ranking run was a
  main-session step at a pause.
- **The driver cannot open a PR that closes nothing**, so evidence PR #146
  and build PR #148 were opened by hand.
- **PR #141 merged without an external review.** It got the `reviewed` label
  at 15:26 UTC on 25 November and merged at 15:42, and was never sent to the
  external reviewer; the reviewer read its diff later, while reviewing PR #143,
  and found it fine. CLAUDE.md says the label follows the external review of
  the current head. A smaller case: PR #144's label was added 39 seconds
  before the reviewer's approval of that head; the merge came after it.
- **The hill chart was set by hand again**, in PR #147 and in this cycle's
  close. The driver does update a chart, but only a `hill.json` in the spec
  directory it runs on (`auto-build-loop.sh` 167-168, code-copilot-team's "Hill-chart
  automation", its issue 405); this pitch's chart sits under `specs/pitches/`. The `tasks.md`
  headings already carry the `(S1)`-`(S5)` tokens it needs.

## Pitches shaped during cooldown

| pitch_id | Appetite | Shaped | Status |
|----------|----------|--------|--------|

## Recommended bets for next cycle

| pitch_id | Appetite | Rationale |
|----------|----------|-----------|

No shaped pitches. Open issues:

- Issue 121: stays open until the owner decides whether the hint answers it.
- Issue 142: ADR-0002, register `memkernel_ref`, `memkernel_sha256` and
  `memkernel_hash_scheme` as memkernel-owned keys.
- Issue 75: its remaining work is in memkernel.

### Next-bet recommendation

**Next-bet recommendation:** none. Shape a new pitch with `/shape <topic>`
before the betting table.

<!-- author note: which topic to shape next (issue 142 is a candidate) is the owner's call -->

## Carryover

- [x] Issue 121's similar-pages hint (PR #140 to PR #148); the issue stays open.
- [ ] Issue 142: ADR-0002 memkernel keys.
- [ ] The off switch does not reach library callers (`WikiPaths.for_root`), including memkernel's export; the docs do not state the limit.
- [ ] The search-cache warning prints once per new page.
- [ ] The hill chart is set by hand: the driver moves only a `hill.json` in the spec directory, and pitch charts live under `specs/pitches/` (carried from cycle 09, dropped in cycles 10 and 11 by mistake).
- [ ] File the code-copilot-team issue about `--resume` and `--start-phase` (drafted; waits for the owner).
- [ ] The driver cannot open a PR that closes nothing.
- [ ] Issue 75: the remaining work is in memkernel.
- [ ] Stale memkernel CI pin: `ci.yml` `MK_VERSION` is still 0.6.0, while PyPI has 0.7.0, 0.8.0 and 0.9.0 (carried from cycle 09). It matters more now: the hint runs inside memkernel's export, and CI exercises that path only against 0.6.0.
- [ ] Optional follow-up: code-copilot-team's own copy of the persona (carried from cycle 09; its state is not checked from this repository).
- [ ] The hill chart has no cut status.
