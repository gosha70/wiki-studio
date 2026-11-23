# Origin alignment check — wiki-studio-0-11-0 (spec amendment)

Gate: run 1 (US1-US3) ended with the evidence PR #128, merged as 46385c5 on
2026-11-23 with a merge commit. Its report's winner line is `Winner: C2`. This
amendment is D2's spec PR (FR-016): it sets FR-031's winner, writes run 2's
settings and re-approves the bundle. The earlier record
(`origin-alignment-2026-11-22-2028.md`) covers the approval in #127 and
stays as written.

What run 1 established, as recorded in `eval/revisions/report.md`:
- The labels, cases, candidates and bar were reviewed by the owner and the
  external reviewer at the pause after US1, frozen in US2 (`1be4060`, the only
  commit touching `tests/test_revisions_frozen.py`) and not edited after.
- C2 (anchor touch) and C4 pass the frozen bar with 5 of 10 false pages each;
  C2 wins on git processes, 50 against 53. C0 and C1 flag all 10, C3 flags 8.
  Every candidate keeps the merge entry and all five supplementary positives.
- Phase 3 was finished by hand: the auto-build's sessions could not run
  Python, so the build session ran the record (owner step 1's fallback), with
  the owner's agreement (plan, departure 24).
- The external review of the evidence PR found that C2's frozen anchors
  include fragments. A non-binding `post_hoc` block, computed by the scorer
  and checked by CI, measures C2 without them: 3 of 10 false pages, the merge
  entry and all five positives kept, `run-wiki-ingest-rules` no longer
  flagged.

The owner's decision (2026-11-23): ship C2 without fragment anchors. It is
stated as a departure decided after seeing the data (plan, departure 23).
FR-032 uses the scorer's `POST_HOC_RULE` word for word, and FR-034 replays the
shipped rule against the `post_hoc` figures, so the shipped behaviour is
exactly what was measured. Two known limits, both unmeasured, are recorded in
FR-032 and the contract (FR-038) rather than changed: a bare file name's last
dotted part still counts as an anchor, and an anchor can match inside a
longer word. These come from the external reviewer's notes on #128.

This amendment commit does these things:
- **spec.md:**
  - FR-031: the winner is C2, and trigger 2 did not fire;
  - FR-032: C2 with the shipped anchor rule and its two known limits;
  - FR-034: the replay target is the `post_hoc` figures;
  - FR-022: the cap's inputs named, 50 processes giving 500, and 0.012 s
    giving a 10 s timeout;
  - FR-038: the contract states the anchor rule and its limits.
- **tasks.md:** tasks 24 to 26 follow FR-031, FR-032 and FR-034.
- **plan.md:** departures 23 and 24, and run 2's settings.
- **automation.json, now run 2's:**
  - branch `feature/wiki-studio-0-11-0`;
  - `max_phases: 8`, started with `--start-phase 4`;
  - `pr.closes: [120]`;
  - the build PR's title;
  - unchanged from run 1: `milestone_every: 0`, `review.diff_max_lines: 6000`,
    the `pr` profile, DeepSeek gating, the gate command, two fix sessions per
    phase, and the $150 / 12 h caps.
- **The pitch's hill chart:** S1 and S2 set to done. The driver didn't update
  it in run 1.
- **This record.**

Origin: wiki-studio issue #120, "Specify a revision-aware check for a
pattern's cited sources", as in the earlier record. Issue 120 is closed by
run 2's build PR through `pr.closes: [120]`, now that a winner ships. This
amendment PR uses no closing keyword.

Working claim, unchanged from the earlier record except for the outcome of
S2:
> The build ships, inside `findings` only, model-free and read-only:
> - `source-not-at-revision` over a hardened read-only git layer, searching
>   the root's repository and the source roots;
> - the `revision_check` object;
> - `source-revision-changed` by C2, with anchors under 4 characters,
>   letterless anchors and the last dotted part of a backticked path ignored.
>   It flags and still returns.
>
> Release preparation for 0.11.0 follows. Nothing changes in `lint`,
> `lint --health --strict`, `stale-claim`, approvals, `find`, the page
> schema, exit codes, MCP tools, capabilities, `findings_version` or
> dependencies, and there is no network or model.

Origin items, mapped: as in the earlier record. The change is S4: FR-031 to
FR-035 now apply (the winner ships) and FR-036 does not.

Mismatches: departures 23 (post hoc, owner) and 24 (process), both recorded
in plan.md.

Verdict: aligned
Confidence: high
