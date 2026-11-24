# Origin alignment check — wiki-studio-duplicates-121 (spec amendment)

Gate: run 1 (US1-US6) ended at the pause after US6 and was not resumed. Its
evidence PR #137 was opened by hand, reviewed externally at `3d418f8`, and
merged as 40fdc86 on 2026-11-24 with a merge commit. Its report's winner line
is `Winner: none`. This amendment is FR-026's spec PR: it sets FR-027's winner,
records the triggers that fired and re-approves the bundle. The earlier record
(`origin-alignment-2026-11-23-2108.md`) covers the approval in #136 and stays
as written.

What run 1 established, as recorded in `eval/duplicates/report.md`:
- The corpus is 299 decision pages from code-copilot-team at `fd05256` and
  memkernel at `8279d76`: the three base families and all eight steps of the
  extension order.
- The owner reviewed the labels at the pause after US3. The owner's one change
  (`50d27b3`) brought the true pairs from 7 to 8. The freeze is `9584a46`, the
  only commit touching `tests/test_duplicates_frozen.py`, and no frozen input
  changed after it.
- B0 and B1 each find 3 of the 8 true pairs, against the 6 the bar needs, with
  3 false candidates each. Both fail on recall. Winner: none.
- The external review of #137 reproduced both rules' results with an
  independent scorer written from FR-018. It found that no disputed label, and
  not the reused labelling session, can change the outcome.

This amendment commit does these things:
- **spec.md**, FR-027:
  - the winner is `none`;
  - trigger 3 fired, and triggers 1 and 2 did not; cut 1 was not invoked;
  - FR-035's time bound is not set, since it needs a winner. The recorded
    timings are given.
- **plan.md:** departures 24 (the phase 3 review bypass), 25 (the reused
  labelling session) and 26 (the winner is none, no run 2).
- **tasks.md:** a note that US7-US9 are cut.
- **The pitch's hill chart:** S1-S3 set to done. The driver didn't update it in
  run 1. S4-S6 were not started, and the hill chart has no "cut" status.
- **This record.**

`automation.json` is unchanged: there is no run 2.

Origin: wiki-studio issue #121, as in the earlier record. Issue 121 stays open
with the measurement as its evidence (FR-027, FR-039). This amendment PR uses
no closing keyword.

Working claim, updated for the outcome:
> Issue 121 asked for an investigation before any code. The measurement was
> run on a larger, independently labelled corpus with the labels frozen
> first. Neither candidate cleared the frozen bar, so no `possible-duplicate`
> kind is built. Nothing under `src/` changes and there is no CHANGELOG entry.
> No release step is part of this bundle.

Origin items, mapped: as in the earlier record. The change is S4-S6: none of
them is built, because of FR-027's `none` and trigger 3.

Mismatches: departures 24 and 25 (process) and 26 (the outcome), all recorded
in plan.md.

Verdict: aligned
Confidence: high
