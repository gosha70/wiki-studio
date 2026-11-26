# Origin alignment check — wiki-studio-similar-121 (spec amendment)

Gate: run 1 (US1-US3) ended at the pause after US3 and was not resumed. Its
evidence PR #146 was opened by hand, reviewed externally at `88cacf6` with no
findings, and merged as fcdf1ae on 2026-11-26 with a merge commit. Its
report's verdict line is `Verdict: pass`. This amendment is FR-018's spec PR:
it sets the verdict, records the triggers, sets FR-022's time-bound inputs,
writes run 2's settings and re-approves the bundle. The earlier record
(`origin-alignment-2026-11-25-2150.md`) covers the approval in #145 and stays
as written.

What run 1 established, as recorded in `eval/similar/report.md`:
- The protocol was frozen in US1 (`8864f52`) before `rank.py` existed
  (`f52c117`) and was not edited after; the owner signed it off.
- The partner was in the top 5 in 11 of 13 tries and in 1 of the 3
  `supersedes` tries: a pass. The two misses are the location-only rulings
  (ranks 6 and 35). Noise: 7 `companion` and 47 `unrelated` pages beside the
  partners.
- The external reviewer reproduced all 13 tries from the spec, independently
  of `rank.py`.
- One process correction: the first sign-off cited a review the owner pasted,
  not the external reviewer's (plan, departure 17).

This amendment commit does these things:
- **spec.md**, FR-018: the verdict is `pass`; trigger 1 did not fire;
  FR-022's bound is 10 s (0.099036 s over 13 tries).
- **plan.md:** departures 16 (the pass and run 2's settings) and 17 (the
  sign-off correction).
- **tasks.md:** a note that US4-US6 are built by run 2.
- **automation.json, now run 2's:** branch `feature/wiki-studio-similar-121`,
  `max_phases: 6` with `--start-phase 4`, the build PR's title, no
  `pr.closes`; unchanged: `milestone_every: 0`, 120 turns, 6000-line review
  diffs, DeepSeek gating, the gate command, two fix sessions per phase, the
  $150 / 12 h caps.
- **The pitch's hill chart:** S1 and S2 set to done.
- **This record.**

Origin: wiki-studio issue #121, as in the earlier record. Issue 121 stays
open; run 2's PR is opened by hand with no closing keyword (D10).

Working claim, updated for the outcome:
> The measurement passed, so the build ships, inside `propose` only, a
> model-free hint that never blocks: for each create, the 5 existing pages
> of the same page type most like it by `find`'s FTS5 ranker, recorded as
> `edits[].similar_pages` in `plan.json`, printed on the CLI's stderr and
> returned as an MCP `propose` result key, with `WIKI_STUDIO_SIMILAR_PAGES=off`
> to turn it off; documents and an `[Unreleased]` entry say it is aimed at
> near-copies and close rewrites and misses location-only rulings. Nothing
> changes in `findings`, `lint`, `find`'s ranking, the ranker configuration,
> the cache format, the page schema, exit codes, MCP tools or dependencies;
> no model; no release step.

Origin items, mapped: as in the earlier record. The change is S3-S5: US4-US6
and FR-019 to FR-029 now apply.

Mismatches: departures 16 (the outcome) and 17 (process), both recorded in
plan.md.

Verdict: aligned
Confidence: high
