---
pitch_id: 121-similar-pages-at-propose
title: "Similar pages at propose: when a page is proposed, list the existing pages most like it, ranked by the FTS5 ranker find already uses, as a model-free hint that never blocks; measured first on cycle 10's frozen corpus with the query rule and the bar fixed before the run"
appetite: 2w
bet_status: bet
cycle: "11"
circuit_breaker: "Core is S1 (the protocol: query rule, k, which pages are compared, the direction rule and the bar, written down and reviewed by the owner before anything is scored) and S2 (the measurement on eval/duplicates' frozen corpus and labels, published whatever it shows, as an evidence PR opened by hand). S3 (the hint in the library and plan.json), S4 (the CLI and MCP surfaces) and S5 (the documents) are built only if S2 passes the bar frozen in S1. Cut order, first to last, each with its trigger: (1) end of week 1, if S2 has not run or the bar is not met: S3-S5 are cut, the cycle ends early, and issue 121 stays open with both measurements as its evidence; (2) middle of week 2, if S3 is not downhill: S4's MCP result key is cut, and the CLI lines and the plan.json key ship; (3) end of week 2: what has merged waits under [Unreleased]. Never, to save time: score anything on the corpus before S1's protocol is reviewed; change the query rule, k, the direction rule or the bar after the run, or count a second reading toward the verdict; edit eval/duplicates' frozen files; let the hint block propose or promote, or change an exit code; put a model on any path from findings, approve or review_state; change find's ranking, RankerConfig or the search cache format; add a frontmatter key, a page type, an exit code, a runtime dependency or an MCP tool; write into the wiki outside promoter.py; quote closing-keyword text anywhere; weaken or skip a test."
shaped_by: "pitch-shaper (Claude Code) for gosha70"
shaped_date: 2026-11-24
---

<!-- Shape-Up pitch. Origin: https://github.com/gosha70/wiki-studio/issues/121 (still open). The owner's comment there after cycle 10: a new candidate rule needs a new pitch, and the frozen corpus and labels in eval/duplicates/ can be reused to measure it. Evidence: eval/duplicates/report.md (evidence PR #137), spec amendment PR #138 (winner none), the external reviewer's FTS5 check and the build session's reproduction, both on the same 8 frozen true pairs. Template for a measure-first pitch: specs/pitches/121-near-duplicate-finding/pitch.md and specs/pitches/120-revision-aware-stale-check/pitch.md. -->

# Pitch: Similar pages at propose

## Problem

Issue 121 asks whether wiki-studio can tell a curator that two pages
record the same decision. Cycle 10 measured a model-free `findings` kind
for it and the answer was no: word overlap of title and first paragraph
(Jaccard at 0.25, B0 and B1) found 3 of the 8 true pairs in the frozen
corpus, where the bar needed 6. No kind was built, and the issue stays
open.

A finding reports after the fact and has to be right more often than
wrong, or curators learn to ignore it. A different place to help is the
moment a page is written. When someone runs `wiki-studio propose`, they
could be shown the few existing pages most like the new one, read them,
and decide whether they are writing a copy. That is a hint, not a
finding: nobody is told "this is a duplicate", so there is no false-alarm
bar. The cost is noise: a short list on every proposal, mostly of pages
that are not copies.

What it will catch, and what it will not. It is aimed at near-copies and
close rewrites, where the two pages share many words. It will not
reliably catch a later ruling that only moves a location: the
user-home pair in the corpus shares one word and is missed under every
reading so far.

## Findings from the code and the evidence

wiki-studio read at main `466c87e` on 2026-11-24. No score was computed
by the shaper.

1. **`propose` already prints advisory lines before promote.**
   `_do_propose` (`cli.py` 1026-1066) writes the patch-set, prints drift
   warnings and `fact-check:` lines to stderr, then promotes only with
   `--promote`. It calls no model. `propose` has no `--json` output.
2. **There is a precedent for advisory data in a proposal.**
   `edits[].fact_warnings` is an optional key in `plan.json`, written by
   `write_patch_set_dir` (`ingestor_multi.py` 290-307), documented in
   `docs/patch-set-format.md` 80 as "advisory; `promote` ignores the key
   and never blocks on it", printed by the CLI and counted by `nightly`.
   A similar-pages list fits the same pattern.
3. **The ranker exists.** `discovery.select` ranks index-linked pages
   with FTS5 (`porter unicode61`, bm25 weights path 4, title 4,
   headings 2, body 1) through the on-disk search cache, and skips
   superseded pages and pages not linked from `index.md`. The query is the
   question's tokens joined by OR (`search_index.build_query`), so a whole
   page can be a query. `select` caps the list at 5
   (`DEFAULT_MAX_QUERY_PAGES`). The search cache takes no `WikiLock`, so
   ranking can run outside the lock `api.propose` holds while it writes.
4. **FTS5 may be missing.** `select` then falls back to the index-first
   ranker, which ranks by the index line, not the page text, and reports a
   `fallback_reason`.
5. **The MCP `propose` tool returns `{name, proposal_dir, warnings}`**
   (`mcp_adapter/tools.py` 169-201). An agent proposing over MCP never sees
   the CLI's stderr, so a hint printed only by the CLI never reaches it.
   ADR-0003 fixes the tool set at eight; a result key is not a new tool.
6. **The evidence so far is suggestive only.** Both checks were run after
   the fact on the same 8 frozen true pairs, ranking the partner with each
   page as the query, self excluded:
   - the external reviewer's check: the partner is in the top 5 for 5-6 of
     the 8 pairs. It indexed the pages under their real corpus paths, which
     carry the spec names, so it is flattered the way finding 7 describes.
     Counted under S1's 13-try rule, its ranks give exactly 10 of 13, with
     1 of the 3 `supersedes` tries found: the bar below sits exactly where a
     flattered reading landed, so a pass is not assured (the external
     review of this pitch, arithmetic on ranks already published; nothing
     new was scored);
   - the build session's reproduction (in-memory `build_in_memory`,
     `DEFAULT_RANKER_CONFIG`, the 299 corpus pages): whole page with
     frontmatter as the query, 6 of 8 in the top 5 in at least one
     direction; frontmatter stripped, 4 of 8.

   So the result depends on how the query is built, and the pitch has to
   fix that rule before any measurement.
7. **The corpus can flatter a query that carries the frontmatter.** Each
   corpus page's frontmatter holds a slug built from repository, spec and
   item number and a `sources:` path to the spec (for example
   `specs/routing-context-limit/plan.md`), and each page's file path
   carries the spec's name (`code-copilot-team/routing/cct-routing-context-limit-plan-07.md`).
   The ranker weighs path words 4. So a query with the frontmatter matches
   pages extracted from the same spec through words a curated wiki page's
   path would not carry. That is the likely, unverified, reason the
   whole-page reading scores higher, and it is why the protocol below
   indexes corpus pages under paths made from their titles, as a curated
   page's path is, never under the corpus paths.
8. **The labels and their limits are fixed.** 8 true pairs (5 `redundant`,
   3 `supersedes`), 7 within a family, all decision pages; frozen and
   pinned by `tests/test_duplicates_frozen.py`. Every page is a decision
   page, so a same-page-type rule measures nothing here.

## Appetite

**2w** (D1). Work content for an LLM executor is about 8.5-12 hours; the
core (S1, S2) is about 3-4.5 hours plus the owner's review of the
protocol. The time goes to review gates, not code: the protocol is
reviewed before the run, the measurement goes through review as an
evidence PR, and only then does the build start.

| Scope | Estimate |
|-------|----------|
| S1 The protocol, frozen before the run | 1-1.5h (plus the owner's review) |
| S2 The measurement and the evidence PR | 2-3h |
| S3 The hint in the library and in `plan.json` (only with a pass) | 3-4h |
| S4 The CLI and MCP surfaces (only with a pass) | 1.5-2h |
| S5 Documents and CHANGELOG (only with a pass) | 1-1.5h |

Planned order: week 1, S1 (in the spec bundle, before any scoring), the
owner's review, S2's run at a main-session pause, the evidence PR opened
by hand. Week 2, the spec amendment records pass or fail; with a pass,
S3, S4 and S5.

Lessons carried from cycles 09 and 10: auto-build sessions cannot run
Python, so the scoring run is a main-session step at a pause, never
inside a driver phase; the evidence PR is opened by hand and names the
issue as "issue 121", never after a closing keyword; anything found after
the run goes into a "Post hoc (not binding)" section of the report and
never moves the bar.

## Solution shape

```
propose (CLI, library, MCP)
  -> validate the edits (unchanged)
  -> for each create: rank the live wiki's pages against the new page   (S3, outside the WikiLock)
       query  = the page's title + its body after the frontmatter       (D3)
       pages  = index-linked, not superseded, same page_type, not in this proposal   (D5)
       list   = the top k (k = 5, no score floor)                        (D4)
  -> write plan.json with edits[].similar_pages (advisory, promote ignores it)   (S3)
  -> CLI: "similar: <path>  <title>" lines on stderr; MCP: a similar_pages key   (S4)
  -> promote, if asked, exactly as today
```

**The query rule (D3).** The new page's frontmatter `title`, a space,
then the page's lines after the frontmatter, as `build_document` reads a
page's body. No other frontmatter key is in the query: keys such as
`sources:` and `slug` describe where a page came from, not what it says,
and on the frozen corpus they carry the source spec's name (finding 7).

**The list.** Up to k pages, best first, each with its wiki path and
title. It is computed for every `create` in the proposal (D6), against the
live wiki only, never against other pages of the same proposal. The
pages compared are the ones `find` can return (linked from `index.md`, not
superseded), of the same `page_type` as the new page. No score floor:
bm25 scores are not comparable across queries, and a floor would be an
unmeasured knob.

**Where it shows (D7).** One computation in `api.propose`, recorded in
`plan.json` as `edits[].similar_pages` beside `fact_warnings`, so every
surface reads the same list: the CLI prints it to stderr after the
`fact-check:` lines, the MCP `propose` result gains a `similar_pages` key,
and a library caller reads `plan.json`. `nightly` and `promote` ignore it.

**When it cannot run (D8).** Without FTS5 the list is not computed, and
the CLI prints one line saying so and why (the probe's reason); the
`plan.json` entry records that it did not run. It does not fall back to
the index-first ranker, which ranks by index lines and is unmeasured.

**The switch (D9).** On by default. `WIKI_STUDIO_SIMILAR_PAGES=off`, read
into `WikiPaths` like `WIKI_STUDIO_GIT_CALL_LIMIT`, turns it off. No CLI
flag, as cycle 10's D8 chose for the duplicate check.

**The measurement (D2), fixed in S1 before anything is scored.**

- *Data:* `eval/duplicates/corpus.json`, its 299 pages and `labels.json`,
  read-only, their sha256 checked against `protocol.json` first. Nothing
  under `eval/duplicates/` is edited. The new files live in
  `eval/similar/`.
- *Index:* every corpus page indexed with `DEFAULT_RANKER_CONFIG` under
  `decisions/<slug>.md`, the slug made from the page's title in kebab-case
  (with `-2`, `-3` added in `corpus.json` order when slugs collide; three
  titles are each shared by two corpus pages). That is how a curated page is
  named (its `slug` equals the filename stem, `page-types.md` 14, by
  convention the title in kebab-case), so the path column gives the same
  title-word weight the shipped hint would get, and it carries no spec
  name (finding 7). The external review of this pitch found that numbered
  neutral paths would have measured a different rule from the one shipped.
- *Query and list:* the D3 rule; the query page itself excluded; top k.
- *Tries (the direction rule):* the hint runs when the second page of a
  pair is proposed. For a `supersedes` pair that is the later ruling, so
  it is tried once, the later page as the query. For a `redundant` pair
  either page could come second, so it is tried both ways. 5 x 2 + 3 = 13
  tries.
- *Bar:* the partner is in the list in at least **10 of the 13 tries**
  (three quarters, rounded up, cycle 10's share) **and in at least 1 of the
  3 `supersedes` tries** (the owner, 2026-11-25), so a pass cannot rest on
  the near-copy pairs alone. Below either, the hint is not built. The two
  directions of one `redundant` pair are not independent tries: the 13
  tries come from 8 pairs, and the report says so.
- *Reported, not binding:* the partner's rank in every try; the curated
  issue 54 fixture (`eval/patterns/wiki/`, its pages under their own
  paths, read-only), ranked exactly as the hint would rank them: its 2
  superseded pages left out and each query compared only with pages of
  its own page type (S-4, D5), so the reading tests the rule that would
  ship; each of its 3 true pairs as recorded tried both ways with the same
  query rule and k, and a pair across page types reported as one the hint
  never lists (the owner, 2026-11-25; never part of the verdict); the other
  pages in each list by label (`companion`, `distinct-by-precondition`,
  `unrelated`), which is the noise a proposer would read; the whole-page
  and body-only readings for comparison, marked not binding.
- *Stated plainly:* the 8 pairs are development data. Two readings were
  already run on them (finding 6), so a pass is weak evidence. There is no
  held-out set in this appetite; the issue 54 fixture, never run through
  this ranker, is the only curated reading, and it is not binding.

## Scopes

Build order: S1, S2 (the evidence PR), the spec amendment, then S3, S4,
S5 only with a pass.

### S1: The protocol, frozen before the run, ~1-1.5h plus the owner's review

`eval/similar/README.md` and `protocol.json`: the D3 query rule written
to the line, k, the title-slug paths, the direction rule and its 13 tries,
the bar, the not-binding readings, the development-data caveat. Reviewed
by the owner in its own commit before any score exists. No scoring code
in that commit.

### S2: The measurement and the evidence PR, ~2-3h

`eval/similar/rank.py` uses only existing pieces (`build_document`,
`build_in_memory`, `SearchIndex.rank`) and checks the frozen hashes
first. Run once by hand at a pause; `results/ranks.json` is committed as
written and a CI test reruns it and compares byte for byte (timing kept in
a separate file CI does not compare). `report.md` gives the table, pass or
fail, the noise counts and the limits. The evidence PR is opened by hand.

### S3: The hint in the library and in `plan.json`, ~3-4h (only with a pass)

The ranking function in `discovery.py` (reusing the eligibility and the
cached FTS5 path, run outside the `WikiLock`), the `edits[].similar_pages`
key written by `api.propose` for each create, the FTS5-missing record and
the switch in `WikiPaths`. Tests: the function gives the same ranks as
S2's script on the frozen corpus; the hint never changes an exit code,
never blocks, never writes into the wiki; a cache problem falls back to
ranking in memory as `find` does; off by the switch; superseded,
other-type and same-proposal pages never listed.

### S4: The CLI and MCP surfaces, ~1.5-2h (only with a pass)

`_do_propose` prints `similar: <path>  <title>` lines on stderr per
create (and the one line when it did not run); the MCP `propose` result
adds `similar_pages`, read from `plan.json`; the adapter tests and the
conformance fixture updated. Trimmed first if S3 runs late (cut 2): the
MCP key goes, the CLI lines stay.

### S5: Documents and CHANGELOG, ~1-1.5h (only with a pass)

`docs/patch-set-format.md` (the new optional key, beside
`fact_warnings`), `docs/mcp-adapter.md` (the result key), the README's
propose section (what the list is, that it is noise-prone and misses
location-only rulings, the switch), and `CHANGELOG.md` under
`[Unreleased]`. Every command a page shows gets its cheapest real check.

## Rabbit holes

- **Picking the query rule from the numbers.** Two readings are already
  known on these pairs. *Workaround:* the rule, k and the bar are fixed in
  S1 and reviewed before the run; other readings are reported as not
  binding; nothing changes after the run.
- **The corpus flattering the ranker** (finding 7). *Workaround:* title-slug
  paths and no frontmatter in the query; the report says the corpus is
  extracted spec decisions, not curated pages, and that 7 of 8 pairs are
  within one family, where shared jargon helps.
- **Long queries.** A whole page is an OR of hundreds of tokens.
  *Workaround:* time it on the 299 pages in S2 and on a 500-page fixture in
  S3; no token cap unless the time is a problem, and then only one written
  into the spec and applied to S2's script too.
- **The search cache during propose.** `propose` never touched the cache
  before. *Workaround:* rank outside the `WikiLock` through the existing
  cached path, which already falls back to memory on a busy or broken
  cache; never take the lock twice.
- **Tuning the list.** A score floor, a normalised bm25, a stop list, a
  different k per page type. *Workaround:* none of it in this bet; each is
  a new rule and a new measurement.

## No-gos

- No `findings` kind and no `lint` change; the hint is not a finding and
  `lint --health --strict` never sees it.
- No blocking: propose and promote behave and exit as today whatever the
  list says, including when it cannot run.
- No model on any path; no change to `find`'s ranking, `RankerConfig`
  (it would change `ranker_config_hash` and rebuild every cache) or the
  search cache format.
- No frontmatter key, page type, exit code, MCP tool, capability or
  runtime dependency. The `plan.json` key and the MCP result key are
  optional and additive, as `fact_warnings` was.
- No hint on `ingest` or `query --file-back` in this bet; they write
  proposals through their own path.
- No edit to `eval/duplicates/`'s or `eval/patterns/`'s frozen files; no
  new labels.
- No release step in the cycle; the owner alone decides when a version is
  released.
- No text with a closing keyword before an issue reference anywhere;
  write "issue 121".

## Circuit breaker

Core is S1 and S2: the protocol frozen before the run and the
measurement published whatever it shows. S3, S4 and S5 are built only
with a pass.

1. **End of week 1, if S2 has not run or the bar is not met:** S3-S5 are
   cut and the cycle ends early. Issue 121 stays open with cycle 10's
   measurement and this one as its evidence.
2. **Middle of week 2, if S3 is not downhill:** S4's MCP result key is
   cut; the CLI lines and the `plan.json` key ship.
3. **End of week 2:** what has merged waits under `[Unreleased]`.

"Exhausted" means two working weeks. A third review round on one PR is an
escalation to the owner: a fix session, a cut from the list above, or a
hold. The never-list is in the frontmatter.

## Decisions

Settled by the project, listed so the spec does not reopen them:

- **S-1. Model-free, stdlib only.** FTS5 is SQLite's, already used.
- **S-2. A hint never blocks** and never changes an exit code,
  `review_state`, an approval or what `find` returns.
- **S-3. `promoter.py` stays the only writer into the wiki.** The hint
  writes only into the proposal directory (through `api.propose`, which
  already writes it) and the search cache beside the lock (through
  `search_index.py`, its only writer).
- **S-4. Superseded pages are never listed**, as in `find`.
- **S-5. The frozen corpus and labels are reused read-only**, as the
  owner's comment on issue 121 allows.
- **S-6. No release step**; the owner decides releases.

## Owner decisions (2026-11-24)

Asked by the build session and decided by the owner on 2026-11-24:
**every decision below takes its default** (D1 2w, D2 measure first, D3
title plus the body after the frontmatter, D4-D10 as listed). The
alternatives stay recorded for the spec review.

- D1: Appetite — default: **2w** (measure, then build) — alternative:
  4w, adding a fresh held-out set of labelled pairs so a pass is not
  weak evidence — why it matters: 2w accepts that the only data is the 8
  pairs already looked at.
- D2: Measure first, or build straight — default: **measure first** on
  the frozen corpus, with the query rule, k, the 13-try direction rule and
  the bar (10 of 13, with 1 of the 3 `supersedes` tries) fixed in S1 before the run, and the 8 pairs named as
  development data; build only with a pass — alternative: build straight,
  since a hint has no false-alarm bar, and report the ranks as
  documentation only — why it matters: measuring first can end the cycle
  in week 1 with nothing built; building straight ships a list nobody has
  shown helps.
- D3: The query rule — default: **title plus the body after the
  frontmatter** — alternatives: the whole page with frontmatter (6 of 8
  in the build session's reading, likely flattered by the corpus, finding
  7); the body only (4 of 8); title plus first paragraph (cycle 10's text)
  — why it matters: the result swings with it, and it must be fixed before
  the run.
- D4: How many pages, and a score floor — default: **k = 5, no floor**
  (the cap `find` already has, and the k both checks used) — alternative:
  k = 3 (less noise, lower chance of showing the partner) — why it
  matters: k is the noise a proposer reads on every create.
- D5: Which pages are compared — default: **same `page_type` only,
  superseded and non-index-linked pages excluded** (as cycle 10's D6 and
  as `find`) — alternative: every content page type, so a decision page
  also sees an incident about the same event — why it matters: same type
  cuts noise but hides cross-type copies; the corpus is all decisions, so
  neither choice is measured.
- D6: Creates only, or updates too — default: **creates only** —
  alternative: also updates, excluding the page itself — why it matters:
  a copy is usually born as a new page; listing on every update doubles
  the noise.
- D7: Where the list shows — default: **`plan.json` key plus CLI stderr
  plus an MCP `propose` result key** (one computation in `api.propose`,
  following `fact_warnings`) — alternatives: CLI stderr only (smallest,
  but agents proposing over MCP never see it); add a `--json` output to
  `propose` (new surface, not needed with the `plan.json` key) — why it
  matters: most proposers are agents, many over MCP.
- D8: Without FTS5 — default: **no list, one line saying it did not run
  and why** — alternative: fall back to the index-first ranker as `find`
  does (unmeasured, ranks by index lines) — why it matters: a fallback
  list would look the same but mean less.
- D9: On by default or opt-in — default: **on, with
  `WIKI_STUDIO_SIMILAR_PAGES=off`** read into `WikiPaths`, no CLI flag —
  alternative: off unless the variable is `on`, or a `--similar` flag —
  why it matters: opt-in hints are rarely turned on; on-by-default puts
  the noise on everyone.
- D10: Issue 121 after the build — default: **it stays open**; the
  owner decides by hand whether the hint answers it, since the issue asked
  for telling a curator after the fact and this is a hint before —
  alternative: the owner closes it by hand when S5 merges, citing the
  hint and both measurements — why it matters: the PR texts must not close
  it either way; only the owner does.

## Bet log

| Date | bet_status | Note |
|------|------------|------|
| 2026-11-24 | shaping | Drafted from issue 121 (open; the owner's comment after cycle 10 invites a new pitch on the frozen corpus), `eval/duplicates/report.md` (winner none), the external reviewer's FTS5 check and the build session's reproduction. wiki-studio read at main 466c87e: `cli.py` (`_do_propose`), `api.propose`, `ingestor_multi.write_patch_set_dir` (`fact_warnings`), `discovery.py`, `search_index.py`, `mcp_adapter/tools.py`, ADR-0003, `docs/patch-set-format.md`. No score computed by the shaper. |
| 2026-11-24 | shaping → shaped | 5 scopes, 2w, work content 8.5-12h (core S1-S2 3-4.5h). Core: the protocol frozen before the run and the measurement as a hand-opened evidence PR. S3-S5 (the hint in `api.propose` and `plan.json`, CLI and MCP surfaces, documents) only with a pass of 10 of 13 tries at k = 5. D1-D10 open for the owner with defaults, not yet asked (the shaping agent cannot ask). |
| 2026-11-24 | shaped (owner decisions) | The owner took every default: D1 2w; D2 measure first, building only with a pass; D3 the query is the title plus the body after the frontmatter; D4 k = 5, no floor; D5 same page type, superseded and non-index-linked pages excluded; D6 creates only; D7 `plan.json` key, CLI stderr and an MCP result key; D8 no list without FTS5, one line saying why; D9 on, with `WIKI_STUDIO_SIMILAR_PAGES=off`; D10 issue 121 stays open and the owner decides by hand. bet_status unchanged. |
| 2026-11-25 | shaped (revised after review) | External review of PR #140 at 47aecae. (1) The measurement indexes corpus pages under title slugs (`decisions/<slug>.md`, collisions numbered), as curated pages are named, instead of numbered neutral paths, so the measured rule is the shipped one (finding 7, Solution shape, S1, rabbit holes). (2) The owner added a bar condition: at least 1 of the 3 `supersedes` tries, besides 10 of 13. (3) Finding 6 corrected: the reviewer's earlier check used the real corpus paths, so it is flattered too; under the 13-try rule its ranks give exactly 10 of 13. (4) The owner added the curated issue 54 fixture as a reading that is not binding. bet_status unchanged. |
| 2026-11-25 | shaped (two points after merge) | The owner's two points on merged PR #140: three titles are shared by two corpus pages each (the exact count); the issue 54 reading ranks as the hint would, its 2 superseded pages left out and each query compared only with its own page type. bet_status unchanged. |
| 2026-11-25 | bet | Bet for cycle 11. |
