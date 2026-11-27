# Origin alignment check — wiki-studio-duplicate-audit-121

Gate: the bet pitch `specs/pitches/121-duplicate-audit/pitch.md` was shaped
and revised twice after external review in PR #151 (finding 10: mutual rank
without a floor flags about half of any wiki, so a development stage comes
first, D7; the fourth bar condition; code-copilot-team dropped as a held-out
source; strict switches, D8), and bet for cycle 12 in PR #152 on the owner's
direct "Yes, bet" (2026-11-27). The owner decided D1-D8 on 2026-11-26 and
2026-11-27.

The spec bundle was reviewed on PR #153:
- **The first review** (`3b1df77`) asked for two fixes: the 16 + 4 review
  sample carried into FR-009 and task 13, and the step checklists allowing
  the driver's `hill.json`. It also put two decisions to the owner: the
  switch fix (US8) is uncuttable once a winner is recorded, so memkernel's
  session-start hook can turn the scan off; and an SQLite error in the scan
  is caught (`not-computed`). Both were applied in `4a89c4f`, and the PR
  merged as 9a68def.
- The spec's open items O1-O12 were decided by the owner on 2026-11-27 (plan,
  "Open items for the spec review"; O8, O10 and O11 on their alternatives).

Origin: wiki-studio issue #121, "Specify a near-duplicate finding based on
titles and summaries", still open. The owner's call on 2026-11-26: it stays
open for an after-the-fact audit. Cycle 10 measured title + summary overlap (3
of 8, no finding); cycle 11 shipped the pre-creation `propose` hint (6 of 8
pairs).

Working claim:
> Measure first whether a mutual-rank rule over the shipped ranker (a
> same-type pair flagged when each page ranks the other in its top k, k = 1,
> 3 or 5) can warn about duplicates already in a wiki without drowning them
> in false pairs: a protocol frozen and signed off before any score; a
> development stage on cycle 10's frozen corpus that stops the bet unless a
> candidate's false pairs do not outnumber its true pairs; then a held-out
> set from wiki-studio's own spec and pitch decisions and memkernel's two new
> spec directories, labelled by sessions that never open the audit code,
> reviewed by the owner and frozen; a bar of at least 8 true pairs, three
> quarters found, false no more than true, and at least 2 found pairs that
> are not restatements. Only with a pass, ship a model-free
> `possible-duplicate` findings kind that never blocks, silenced per pair by
> a `[!related]` line (ADR-0006), with a `duplicate_check` object and a 10 s
> bound on a 500-page wiki. Independently, `WikiPaths.for_root` reads both
> off switches, a bad value raising (D8). Nothing changes in `lint`,
> `find`'s ranking, the schema, exit codes, MCP tools, `findings_version` or
> dependencies; no model; findings writes nothing; no release step; issue
> 121 is closed by no PR.

Origin items, mapped:
- Measure first (pitch S1-S3, D1-D4, D7): US1-US7, FR-001 to FR-035.
- The switch fix (S6, D6, D8): US8, FR-036 to FR-038.
- The kind and ADR-0006 (S4-S5, only with a pass): US9-US11, FR-039 to FR-050.
- Fail paths: trigger 0 (FR-021) and FR-034's circuit breaker; the
  amendment fills FR-035's verdict slot.

Mismatches: none beyond the departures recorded in plan.md (1-18).

Verdict: aligned
Confidence: high
