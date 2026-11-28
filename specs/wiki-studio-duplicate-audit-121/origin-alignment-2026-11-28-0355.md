# Origin alignment check — wiki-studio-duplicate-audit-121 (spec amendment)

Gate: run 1 ended at the pause after US3 and was not resumed. Its evidence PR
#157 was opened by hand, reviewed externally at `065fb6d` with no findings
(the reviewer rebuilt the check from the protocol's wording and got the same
pairs at every k), and merged as 5cbc7bf on 2026-11-27 with a merge commit.
Its report's stage line is `Development stage: stop`. This amendment is
FR-035's spec PR: it sets the verdict, records the triggers, writes run 2's
settings and re-approves the bundle. The earlier record
(`origin-alignment-2026-11-27-1904.md`) covers the approval in #155 and stays
as written.

What run 1 established (`eval/duplicate_audit/report.md`):
- The protocol froze in US1 (`6e34b45`) before `audit.py` existed
  (`e9a71dc`); the owner signed it off.
- On cycle 10's 299 frozen pages, every candidate's false pairs outnumber its
  true pairs found: mutual top-1 47 against 4, top-3 164 against 5, top-5 278
  against 6. Trigger 0 fired; no held-out page was extracted or labelled.
- An early PR on the run branch (PR #156) was closed unmerged; its advisory
  suggestions were triaged on it.

This amendment commit does these things:
- **spec.md**, FR-035: the verdict is `stop`; trigger 0 fired, triggers 1-5
  did not; `DUPLICATE_K` is not set; run 2 is US8 alone.
- **plan.md:** departure 19 (the stop and run 2's settings).
- **tasks.md:** the note above US8.
- **automation.json, now run 2's:** branch
  `feature/wiki-studio-duplicate-audit-121`, `max_phases: 8` with
  `--start-phase 8`, the build PR's title, no `pr.closes`; unchanged:
  `milestone_every: 0`, 120 turns, 6000-line review diffs, DeepSeek gating,
  the gate command, two fix sessions per phase, the $150 / 12 h caps.
- **Both hill charts:** S1 and S3 done; S2, S4 and S5 cut (left uphill); S6
  for run 2.
- **This record.**

Origin: wiki-studio issue #121, as in the earlier record. Issue 121 stays
open with cycles 10, 11 and this measurement as its evidence; no PR closes
it.

Working claim, updated for the outcome:
> A mutual-rank audit over the shipped ranker cannot warn about duplicates
> already in a wiki without drowning them in false pairs: on cycle 10's
> frozen corpus every candidate flags at least 12 false pairs per true one.
> No `possible-duplicate` kind is built and nothing changes in `findings`.
> The bet's independent part still ships: `WikiPaths.for_root` reads
> `WIKI_STUDIO_SIMILAR_PAGES` (a bad value raising, D8), so library callers,
> memkernel's export included, can turn the cycle 11 hint off. No model; no
> release step.

Origin items, mapped: as in the earlier record. The change is S2, S4 and S5:
cut by trigger 0. S6 is US8, FR-036 to FR-038.

Mismatches: departure 19 (the outcome), recorded in plan.md.

Verdict: aligned
Confidence: high
