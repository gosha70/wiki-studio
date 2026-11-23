---
cooldown_after_cycle: "09"
started: 2026-11-22
ended: 2026-11-23
duration: 2d
---

<!-- Generated at the end of a cooldown by the cooldown-report agent. -->
<!-- Summarizes bug fixes + lists pitches ready for the next betting table. -->

# Cooldown after Cycle 09

## Summary

Cycle 09 bet on `120-revision-aware-stale-check` (issue 120): findings that
compare a page's cited source against the git revision it was written from.

**Merged, not released.** Build PR #130 (merge `35aa842`, 2026-11-23 UTC)
carries the work; issue 120 was closed by #130. `pyproject.toml` says 0.11.0,
but the release PR #131 is open and unmerged: the owner chose on 2026-11-23
not to release now. The CHANGELOG `[0.11.0]` section dated 2026-11-23 exists
only in #131.

What shipped to main:
- Two findings, `source-not-at-revision` and `source-revision-changed`, and the
  `revision_check` object.
- A hardened read-only git layer (`revisions.py`): a cap of 500 git calls per
  run (`WIKI_STUDIO_GIT_CALL_LIMIT`) and a 10 s timeout per call.
- ADR-0005, and docs that state two known limits.

**Measurement** (`eval/revisions/report.md`):
- C2 (anchor touch) and C4 passed with 5 of 10 false pages. C2 won on git
  processes, 50 against 53. C0 and C1 flagged 10 false pages, C3 8. Every
  candidate kept the merge entry and found 5 of 5 real positives.
- Reported only: every candidate flags `run-wiki-ingest-rules`; none flags
  `vllm-backend-doc`.
- Post hoc, not binding (found in the external review): C2's frozen anchors
  included fragments. Without them, C2 flags 3 of 10 false pages and does not
  flag `run-wiki-ingest-rules`. The owner chose on 2026-11-23 to ship C2 without
  fragment anchors, recorded as plan departure 23; FR-034's replay test
  asserts the post-hoc figures.

PRs in the cycle:

- #124 the pitch, three review rounds.
- #125 the bet and cycle start.
- #126 the spec bundle, one review round (ambiguity order, `--relative`).
- #127 the approval and run 1 settings; a second commit set
  `review.diff_max_lines` to 6000.
- #128 the evidence PR (run 1, US1 to US3).
- #129 the spec amendment: winner C2 without fragment anchors, run 2 settings.
- #130 the build PR (run 2, US4 to US8).
- #131 the release PR, open.

The pitch is `bet_status: shipped`; hill scopes S1 to S5 are done and S6 is
downhill (the release is still to come). Both were set at close by hand.

## Bug fixes shipped

Window: from `46385c5` / `598d0b3`. None. No fix commit landed, and no fix to
released code: the work is unreleased.

| Commit | Pitch / area | One-line description |
|--------|--------------|----------------------|

## Polish & follow-ups

- code-copilot-team was updated to `fd05256` before the build; it carries the
  `review.diff_max_lines` and mid-phase cost-cap fixes.

## Process notes

- **Auto-build sessions cannot run Python.** Run 1 parked at phase 3. The build
  session ran the record by hand, committed phase 3 by hand, and DeepSeek's
  review was run by hand (plan departure 24).
- **The driver cannot open a PR that closes nothing.** It falls back to
  plan.md's origin issue, so the evidence PR #128 was opened by hand.
- **`--resume` ignores the parked phase.** In run 2, phase 6's first session hit
  the account usage limit and wrote nothing, so it parked as "no changes". A
  plain `--resume` restarted at phase 1 (the driver never reads the starting
  phase back from its ledger, although its help text says it does) and parked
  again (about $0.74). A fresh run with `--start-phase 6` on the kept branch
  finished.
- **Costs by ledger:** run 1 $15.76, run 2a $12.71, run 2b $9.39.
- **The owner's shell sets `CCT_REVIEW_DIFF_MAX_LINES=4000`**, which overrides
  automation.json; runs used `env -u`.
- **Main CI on `35aa842`:** attempt 1's Build Check failed on a PyPI read
  timeout; attempt 2 was green.
- **Every DeepSeek gating review passed in one round** (steps 1, 2 and 4 to 8). Step 3's review was run by hand, was advisory, and suggested changes.
- **The driver never updates the hill.** Neither run moved it; set by hand at close.

## Pitches shaped during cooldown

| pitch_id | Appetite | Shaped | Status |
|----------|----------|--------|--------|
| `121-near-duplicate-finding` | 4w | 2026-11-23 | shaped; PR #132 open, revised after one review round; D1 to D10 decided by the owner |

## Recommended bets for next cycle

| pitch_id | Appetite | Rationale |
|----------|----------|-----------|
| `121-near-duplicate-finding` | 4w | The only shaped pitch (issue 121); the owner decided D1 to D10. Its S4 (code) needs 0.11.0 tagged first. The owner deferred the 0.11.0 release on 2026-11-23 and asked to continue with the open issues; issue 121 is the only one with work in this repository (issue 75's remaining work is in memkernel). |

### Next-bet recommendation

**Next-bet recommendation:** `121-near-duplicate-finding` once #132 merges. Run `/bet 121-near-duplicate-finding` followed by `/cycle-start 121-near-duplicate-finding` for cycle 10; tag 0.11.0 before its S4 (code).

## Carryover

- [x] Issue 120, the revision-aware stale check (#124 to #130).
- [ ] Tag and release 0.11.0 (#131 open; re-date its CHANGELOG to the release day).
- [ ] File the code-copilot-team issue about `--resume` ignoring the parked phase (draft ready, owner's call).
- [ ] Issue 75: memkernel's lifecycle spec (memkernel PR #144) merged 2026-11-19; the remaining work is memkernel's build and paid runs, nothing in wiki-studio.
- [ ] Stale memkernel CI pin: CI tests memkernel 0.6.0.
- [ ] Optional follow-up: code-copilot-team's own copy of the persona.
- [ ] The driver's hill chart was not moved by either run (set by hand at close).
