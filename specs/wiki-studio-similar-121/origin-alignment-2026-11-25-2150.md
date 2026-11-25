# Origin alignment check — wiki-studio-similar-121

Gate: the bet pitch `specs/pitches/121-similar-pages-at-propose/pitch.md` was
shaped and revised after review in PR #140, took the owner's two points after
that merge in PR #141, and was bet for cycle 11 in PR #143. The owner decided
D1-D10 on 2026-11-24 (every default) and added two review changes on
2026-11-25 (a `supersedes` condition in the bar; the issue 54 fixture as a
reading that is not binding).

The spec bundle was reviewed on PR #144:
- **The first review** (`3f58188`) asked for two fixes and two wording points,
  none changing the rules or the bar: pin each issue 54 fixture page by
  sha256 in `protocol.json`'s `inputs`; make the audit include the commit that
  adds `rank.py` (`R^..HEAD`); state the fixture's tries exactly (2 pairs both
  ways, 4 tries, and the cross-type pair reported without ranking); note that
  `ingestor_multi` imports `SimilarList` only for type checking. All four were
  applied in `9d05aab`, and the PR merged as 81839b0.
- **The owner's optional point after the merge:** pin the fixture's
  `index.md` too, since it decides which pages are compared and the tie
  order. This approval adds it to FR-002 and task 4.
- The spec's open items O1-O9 were accepted on their defaults by the owner on
  2026-11-25, before the spec PR.

Origin: wiki-studio issue #121, "Specify a near-duplicate finding based on
titles and summaries", still open; the owner's comment on it of 2026-11-24
says a new candidate rule needs a new pitch and can reuse the frozen corpus
and labels in `eval/duplicates/`. Cycle 10 measured a findings kind (evidence
PR #137, amendment PR #138): 3 of 8 true pairs found, 6 needed, winner none.

Working claim:
> Measure first whether listing the existing pages most like a proposed
> page, ranked by the FTS5 ranker `find` already uses, shows the true
> partner: the rule, k and the bar (10 of 13 tries, and at least 1 of the 3
> `supersedes` tries) are frozen before any score exists, on the frozen
> `eval/duplicates/` corpus and labels. Only with a pass, ship it as a
> model-free hint in `propose` that never blocks: `edits[].similar_pages` in
> `plan.json`, CLI stderr lines, an MCP `propose` result key, the
> `WIKI_STUDIO_SIMILAR_PAGES=off` switch, documents and an `[Unreleased]`
> entry. Nothing changes in `findings`, `lint`, `find`'s ranking, the
> ranker configuration, the cache format, the page schema, exit codes, MCP
> tools or dependencies; no model; no release step; issue 121 is closed by
> no PR (D10).

Origin items, mapped:
- Measure first on the frozen corpus (pitch S1-S2, D2): US1-US3, FR-001 to
  FR-017.
- The hint in the library and `plan.json` (S3, D3-D9): US4, FR-019 to FR-022.
- CLI and MCP surfaces (S4, D7): US5, FR-023 to FR-025.
- Documents and CHANGELOG (S5): US6, FR-026 and FR-027.
- Fail path (pitch trigger 1): FR-017's circuit breaker; the amendment
  fills FR-018's verdict slot.
- Issue 121 stays open (D10): run 2's PR is opened by hand with no closing
  keyword.

Mismatches: none beyond the departures recorded in plan.md.

Verdict: aligned
Confidence: high
