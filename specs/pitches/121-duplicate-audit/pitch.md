---
pitch_id: 121-duplicate-audit
title: "A duplicate audit in findings: for pages already in the wiki, flag two same-type pages that rank each other at the top of the shipped similar-pages ranker, as a model-free warning that never blocks and is silenced per pair by a related line; measured first, with the rule and the bar frozen before any score, on a fresh held-out labelled set"
appetite: 4w
bet_status: shaped
cycle: ""
circuit_breaker: "Core is S1 (the protocol: candidates, index rule, bar, held-out extraction and labelling rules, written down and reviewed by the owner before any score exists), S2 (the held-out set: extracted verbatim at pinned commits, labelled by a session with no candidate code, reviewed by the owner and frozen) and S3 (the measurement on the held-out set, binding, and on cycle 10's frozen corpus, reported only, published whatever it shows as an evidence PR opened by hand). S4 (the possible-duplicate kind) and S5 (ADR-0006 and the documents) are built only if a candidate clears the bar frozen in S1. S6 (both off switches read by WikiPaths.for_root) is independent of the verdict and is cut first. Cut order, first to last, each with its trigger: (1) whenever S3 or S4 is late, S6 is cut and the gap returns to the carryover list; (2) end of week 1, if S2's extraction has not landed: the held-out base narrows to wiki-studio's own spec and pitch decisions, and the later memkernel and code-copilot-team specs are dropped; (3) end of week 2, if S2's freeze has not landed: the labels freeze as reviewed by then, and with fewer than 8 true pairs the verdict is not testable; (4) start of week 3, if no candidate clears the bar, the verdict is not testable, or S3 has not run: S4-S5 are cut, the cycle ends early, and issue 121 stays open with three measurements as its evidence; (5) middle of week 4, if S4 is not downhill or the frozen rule misses the time bound frozen in S1: S4-S5 are cut, and the kind becomes a follow-up bet that starts from the frozen winner. End of week 4: what has merged waits under [Unreleased]. Never, to save time: compute a score on the frozen corpus or the held-out set before S1's protocol is reviewed; run a candidate on the held-out set before its labels are frozen; change a candidate, k, the index rule or the bar after the run, or count a second reading toward the verdict; make the scan faster with a rule that was not measured; edit eval/duplicates', eval/similar's or eval/patterns' frozen files; let the kind block promote or approve, join lint --health, or change an exit code; put a model on any path from findings, approve or review_state; write from findings (the on-disk search cache included); bump findings_version; add a frontmatter key, a page type, an exit code, a runtime dependency or an MCP tool; ship the kind without ADR-0006; quote closing-keyword text anywhere; weaken or skip a test."
shaped_by: "pitch-shaper (Claude Code) for gosha70"
shaped_date: 2026-11-26
---

<!-- Shape-Up pitch. Origin: https://github.com/gosha70/wiki-studio/issues/121 (open). The owner's call on 2026-11-26: the issue stays open for an after-the-fact audit, a model-free findings kind that tells a curator two pages already in the wiki may record the same thing. The owner's preferred shape for a finding is in the issue body (2026-11-19). Evidence: eval/duplicates/report.md (cycle 10, winner none), eval/similar/report.md and results/ranks.json (cycle 11, pass), specs/retros/cooldown-after-11.md. Templates: specs/pitches/121-near-duplicate-finding/pitch.md and specs/pitches/121-similar-pages-at-propose/pitch.md. -->

# Pitch: A duplicate audit in findings

## Problem

Issue 121 asks for a way to tell a curator that two pages record the same
thing. Cycle 11 shipped half of it: when a page is proposed, `propose` lists
the 5 most similar existing pages of the same type, so the writer can stop
before making a copy. That hint sees only new pages, at writing time, and
only if someone reads it. Duplicates still appear over time: two sessions
ingest overlapping sources, a hint is ignored, a page is rewritten until it
says what another page says. Nothing reports the pairs already in the wiki.

The owner kept the issue open for that: a model-free `findings` kind that
reports, for pages already in the wiki, that two of them may record the same
thing. A finding is reported on every run and has to be right more often
than wrong, or curators learn to ignore it. Cycle 10 tried word overlap of
title and first paragraph and found 3 of 8 true pairs (bar 6). The ranker
the hint uses did better at writing time, but nobody knows how many false
pairs it would flag across a whole wiki.

## Findings from the code and the evidence

wiki-studio read at main `587c6fb` on 2026-11-26. No score was computed by
the shaper; the figures below are arithmetic on ranks already published.

1. **`findings` writes nothing.** Its docstring and the contract say it takes
   no lock, no backend and writes nothing. The hint ranks through `select`,
   which refreshes the on-disk search cache. So the audit cannot reuse
   `similar_pages` as it is: it ranks in an in-memory index
   (`search_index.build_in_memory`, `SearchIndex.rank`), as
   `eval/similar/rank.py` did, with the hint's query rule (`similar_query`:
   title, a space, the body after the frontmatter), `DEFAULT_RANKER_CONFIG`
   and the same-type filter.
2. **Calling the hint once per page would read the wiki once per page.**
   `similar_pages` calls `select`, which reads every eligible page. An audit
   of N pages would read N x N pages. One index built once, queried once per
   page, avoids that.
3. **Cycle 11 measured with the query page absent from the index**
   (`rank.py` 369: each try builds a fresh index without the query page).
   bm25 depends on the whole index, so ranks taken with the page present
   would differ slightly from the published ones. FTS5 can delete a row,
   rank, and insert it back, which gives "query page absent" from one index.
4. **The silence line has a ready parser.** `conflicts.py` scans
   `> [!conflict]` marker lines line by line (at most three spaces, the `>`,
   the marker, fenced code skipped) and resolves the first `.md` link from
   the page's directory (`_body_lines`, `_marker_target`, `_resolve_target`).
   A `[!related]` marker fits the same helpers. ADR-0001 to ADR-0005 exist,
   so the related line takes ADR-0006.
5. **Kinds and objects may be added within `findings_version: 1`.**
   `docs/knowledge-contract.md` says so, and `revision_check` is the
   precedent for an object that says whether a check could run.
6. **The cycle 11 off switch does not reach library callers.**
   `WIKI_STUDIO_SIMILAR_PAGES` is read only by `WikiPaths.resolve` (CLI, MCP
   server); `WikiPaths.for_root`, which `docs/consumers.md` shows and
   memkernel's export uses, defaults to on and ignores the variable. The
   cycle 11 cooldown measured it: 100 of 100 new pages still got a list with
   the variable `off`; a 100-page proposal on a 500-page wiki took 4.9 s
   instead of 0.03 s. A duplicate switch built the same way would have the
   same gap.
7. **What the published ranks already say about recall.** On cycle 10's 8
   frozen true pairs, cycle 11's ranks (each page as the query, same type,
   query page absent) are: the 4 near-copy pairs (`effective-endpoint` x 3,
   `context-limit`) at rank 1 both ways; the `shadow-plan` pair at 4 and 3;
   the memkernel `supersedes` pair at 3; the pi project-config pair at 6;
   the user-home pair at 35. The two `supersedes` pairs whose partner was in
   reach were tried one way only. So a rule "each page has the other in its
   top k" finds, on these pairs: **k = 1: 4 of 8; k = 3: 4 or 5 of 8; k = 5:
   5 or 6 of 8** (the "or" is the memkernel pair's unknown reverse rank).
   False pairs are **not known for any k**: cycle 11 ranked 13 queries, an
   audit queries every page. These 8 pairs have now been read by three
   cycles, so they are development data, and any further score on them
   while shaping would weaken the evidence (the cycle 11 lesson).
8. **Held-out sources, counted by heading only.** Not used by any study so
   far: wiki-studio's own spec decisions (18 spec directories, about 124
   items by a rough heading count) and its pitches' `## Decisions` sections
   (11 pitches; count in S2); the specs added since cycle 10's pins in
   memkernel (2 directories, about 20 items) and code-copilot-team (3
   directories, about 7 items). Rejected: code-copilot-team's
   `knowledge/wiki` (19 typed pages, 18 of them the issue 54 background, so
   not independent, cycle 10 finding 7) and the families cycle 10 excluded
   (the issue 54 fixture was drawn from them and ranked in cycle 11).
9. **Cost.** Cycle 11's binding pass took 0.099 s for 13 tries on 299
   pages, about 7.6 ms per try, each try building its own 298-page index. A
   500-page wiki means 500 queries per `findings` run, which hosts run at
   session start and the MCP `findings` tool serves.

## Appetite

**4w** (D1). Work content for an LLM executor is about 15-21 hours; the core
(S1-S3) is about 9-12.5 hours plus two owner reviews. The time goes to the
held-out set and the review gates: protocol reviewed before any score,
labels reviewed before any candidate touches them, the measurement reviewed
as an evidence PR, then the build. A 2w bet without a held-out set would
measure only false pairs on data already read three times (D1's
alternative).

| Scope | Estimate |
|-------|----------|
| S1 The protocol, frozen before any score | 1.5-2h (plus the owner's review) |
| S2 The held-out set, extracted, labelled, frozen | 5-7h (plus the owner's review) |
| S3 The measurement and the evidence PR | 2.5-3.5h |
| S4 The `possible-duplicate` kind (only with a pass) | 4-5h |
| S5 ADR-0006 and the documents (only with a pass) | 1.5-2.5h |
| S6 Both off switches read by `for_root` (independent, cut first) | 0.5-1h |

Planned order: week 1, S1 in the spec bundle, the owner's review, S2's
extraction; week 2, labelling, the owner's review, the freeze; start of week
3, S3's run at a main-session pause and the evidence PR opened by hand, the
spec amendment records the verdict; weeks 3-4, S4 and S5 with a pass. S6 can
land in any week.

Lessons carried from cycles 09-11: auto-build sessions cannot run Python, so
extraction and scoring are main-session steps at pauses; the evidence PR is
opened by hand and names "issue 121"; anything found after the run goes into
a "Post hoc (not binding)" section and never moves the bar.

## Solution shape

Two parts, as in cycles 10 and 11: a measurement under a new
`eval/duplicate-audit/` directory that decides, then, only with a pass, a
read-only kind that implements the winner exactly.

```
findings (CLI, library, MCP, nightly)
  -> the existing kinds, unchanged
  -> possible-duplicate (S4), unless the switch is off or FTS5 is missing
       pages  = index-linked, not superseded content pages (as find and the hint)
       index  = one in-memory FTS5 index over them (never the on-disk cache)
       ranks  = for each page A: query = similar_query(A), A removed from the
                index for its own query, keep same-type pages in rank order
       flag   = {A, B} when B is in A's top k and A is in B's top k  (k frozen in S1, D3)
       skip   = a pair joined by a conflict callout or a related line, either side
       report = one warning per pair, ending with the exact related line
  -> duplicate_check object: ran | off | FTS5 missing (with the reason), pages compared
```

**The candidates (D3), fixed in S1 before any score.** One rule, mutual
rank, at three values of k: **k = 1, 3, 5** (5 is the hint's list length).
Mutual rank needs no score floor, so nothing depends on bm25 scores, which
are not comparable across queries. Among candidates that pass the bar, the
fewest false pairs per true pair wins; a tie goes to the smaller k.

**The held-out set (D2).** Extracted verbatim by cycle 10's extraction rule
(H2 sections containing "decision", three item forms, the body built in its
four steps), imported read-only from `eval/duplicates/extract.py` where its
functions allow, else reimplemented and tested to reproduce the frozen
corpus pages byte for byte. Base: wiki-studio's spec and pitch decisions at
a pinned commit, plus the specs memkernel and code-copilot-team added since
cycle 10's pins, at pinned commits; each page pinned by sha256; pages
indexed under title-slug paths, as in cycle 11. Labelled as in cycle 10 (D3
of that pitch): one session with no candidate code groups pages by the
question they answer and gives each pair one of six dispositions
(`redundant`, `conflicting`, `supersedes` true; `companion`,
`distinct-by-precondition`, `unrelated` false); cross-family pairs are
`unrelated` unless the labeller lists them from one summary pass; the owner
reviews every true and `companion` label and 20 seeded false pairs.

**The bar (D4), on the held-out set only.** The labels hold at least 8 true
pairs, else "not testable"; the winner finds at least three quarters of
them, rounded up; its false pairs do not outnumber its true ones. Cycle 10's
bar, so the verdicts compare. Reported, not binding: every count per 100
pages, split by pair scope (pitch and spec of one feature, within a
repository, across repositories), and the same three candidates on cycle
10's frozen corpus with its labels, which gives the first false-pair counts
on it.

**The time bound (D5).** Frozen in S1: on a 500-page synthetic wiki the
kind adds at most **10 s** to `findings` on the CI runner (the owner, D5). S3 times the
winner on both sets; S4 tests the bound. If the frozen rule misses it, the
kind is cut (trigger 5), never replaced by a faster rule nobody measured.

**What a flag means and what a curator does** (cycle 10's shape, unchanged).
"These two pages may record the same thing; read both." Three answers, each
an existing mechanism: merge (keep one, set `superseded_by` on the other;
superseded pages are never compared); mark a disagreement (conflict callouts,
ADR-0004; the pair is then `open-conflict` and this kind skips it, so no pair
is reported twice); or mark them as deliberately separate with the related
line.

**The related line (ADR-0006).** On either page, in the conflict callout's
form:

```markdown
> [!related] Not a duplicate of [Retry policy](../decisions/retry-policy.md).
```

Marker `[!related]`, case-insensitive, optional fold sign; the first `.md`
link on the marker line names the other page, resolved from the page's
directory; fenced code skipped; one side is enough. A related line naming no
content page silences nothing and is not reported. No frontmatter key, so
the schema shared with memkernel is unchanged and its bridge carries the
body as written. Every finding names both pages and both ranks, then ends
with the exact line to paste into the first page of the pair (sorted by
path), the relative link already computed.

**Settled shape, carried from the owner's decisions in cycle 10.** Severity
`warning`; never blocks promote or approve; `findings` only, never
`lint --health` (cycle 10 D7); same page type only, every content page type
compared, with only decision pages measured and the documents saying so
(cycle 10 D6, D10); a scoped run (`--paths`) reads the whole eligible set
and keeps findings touching an in-scope page, as the conflict scan does;
`nightly` lists the kind and drafts nothing. The switch:
`WIKI_STUDIO_DUPLICATE_CHECK` (unset or empty is on, else `on` or `off`, any
other value exits 1, as `WIKI_STUDIO_SIMILAR_PAGES`), read into `WikiPaths`;
off means the kind counts zero and `duplicate_check` says off.

## Scopes

Build order: S1, S2, S3 (the evidence PR), the spec amendment, then S4 and
S5 only with a pass. S6 at any point.

### S1: The protocol, frozen before any score, ~1.5-2h plus the owner's review

`eval/duplicate-audit/README.md` and `protocol.json`: the three candidates,
the index rule (one index, query page removed for its own query), the query
rule, the same-type filter, the held-out sources and pins, the extraction
and labelling rules, the bar, the time bound, the readings that are not
binding, the development-data caveat. Its own commit, no scoring code,
reviewed by the owner before anything is scored on either set.

### S2: The held-out set, extracted, labelled, frozen, ~5-7h plus the owner's review

`extract.py` run once by hand at a pause; `corpus/`, `corpus.json` with
pins and sha256. Then the labelling commit (`labels.json`, no candidate
code in the tree), the seeded review sample, the owner's review, the freeze
pinned by a test. With fewer than 8 true pairs the verdict is "not
testable", stated before any candidate runs.

### S3: The measurement and the evidence PR, ~2.5-3.5h

`audit.py` uses only shipped pieces (`similar_query`, `build_document`,
`build_in_memory`, `SearchIndex.rank`, `DEFAULT_RANKER_CONFIG`) and checks
every frozen hash first. Run once by hand; `results/` committed as written,
rerun by a CI test byte for byte (timing in a separate file CI does not
compare). `report.md`: the held-out table and verdict (a winner, none, or
not testable), the frozen-corpus counts (not binding), the limits. Evidence
PR opened by hand, one commit per step, nothing under `src/`.

### S4: The `possible-duplicate` kind, ~4-5h (only with a pass)

The winner exactly, in a new module beside `conflicts.py`; the related-line
scan sharing `conflicts.py`'s line helpers; `KIND_POSSIBLE_DUPLICATE` after
the conflict kinds; the `duplicate_check` object; the switch. Tests: the
kind replayed on the held-out set gives exactly S3's flagged pairs;
superseded pages, conflict-joined pairs and related-line pairs skipped; a
dangling related line silences nothing; the printed line, pasted in,
silences the finding; scoped run; switch; FTS5 missing; the 500-page bound;
`lint --health --strict`, `review_state`, `approve` and `find` unchanged;
nothing written (no search cache, no wiki file); the no-backend guard and
the single-writer scan still pass.

### S5: ADR-0006 and the documents, ~1.5-2.5h (only with a pass)

`docs/adr/0006-related-line.md` (the body line, the `not_duplicate_of:` key
weighed and refused); `schema/citation-rules.md` beside "When sources
disagree"; `docs/knowledge-contract.md` (the kind's row, `duplicate_check`,
the switch); the README environment table; `docs/patterns.md` (the three
answers to a flag); what was measured, stated plainly (decision pages only,
extracted, not curated); `CHANGELOG.md` under `[Unreleased]`; CLAUDE.md's
layout line. Every command a changed page shows gets its cheapest real
check.

### S6: Both off switches read by `for_root`, ~0.5-1h (independent, cut first)

`WikiPaths.for_root` reads `WIKI_STUDIO_SIMILAR_PAGES` (and, with S4,
`WIKI_STUDIO_DUPLICATE_CHECK`) when the caller passes no value, with the
same validation as `resolve`; an explicit argument still wins. Tests for
both constructors; README and CHANGELOG lines. Without a pass it covers the
similar-pages switch alone (D6).

## Rabbit holes

- **Choosing k from the published ranks.** Finding 7 already shows recall
  on the development pairs. *Workaround:* all three values of k are frozen
  in S1; the binding run is on the held-out set; nothing changes after it.
- **The held-out set holds too few true pairs.** About 150-250 pages may
  hold fewer than 8 duplicates (cycle 10 needed 299 for 8). *Workaround:*
  the pitch decisions join the base because pitch and spec restate
  decisions, a real way duplicates arise; "not testable" is a stated
  outcome; no source is added after labelling starts.
- **Measuring one index rule and shipping another** (finding 3).
  *Workaround:* S1 fixes "query page removed from the index for its own
  query", implemented the same way in `audit.py` and in the kind (delete,
  rank, insert back), and S4's replay test compares them.
- **Extraction on new formats.** wiki-studio's specs and pitches may hold
  item forms cycle 10's rule extracts badly. *Workaround:* the rule is not
  tuned; an item extracted badly is kept as written, labelled by content and
  listed in the README.
- **A faster scan.** Token prefilters, caching ranks between runs,
  candidate pruning. *Workaround:* none in this bet unless it gives
  identical pairs, proven by the replay test; otherwise trigger 5.

## No-gos

- No model on any path from `findings`, `approve` or `review_state`.
- No write from `findings`: no search cache, no wiki file; `promoter.py`
  stays the only wiki writer.
- No automatic merge, supersession, deletion or approval change.
- No `lint`, `lint --health` or `--strict` change; no `findings_version`
  bump (the kind and `duplicate_check` are additive).
- No frontmatter key, page type, directory, exit code, MCP tool, capability
  or runtime dependency; the related line gets ADR-0006.
- No change to `find`'s ranking, `RankerConfig`, the search cache format or
  the hint.
- No user-tunable k or threshold: a tuned value is not the measured rule.
- No grouping of near-duplicates into clusters and no curator-cost study
  (future questions, the owner and reviewer said).
- No edit to `eval/duplicates/`, `eval/similar/` or `eval/patterns/` frozen
  files; no score on frozen pages before S1's protocol is reviewed.
- No release step in the cycle; the owner alone decides releases.
- No closing keyword before an issue reference anywhere; write "issue 121".
  No PR closes issue 121; the owner decides by hand.

## Circuit breaker

Core is S1-S3: the protocol frozen first, the held-out labels frozen before
any candidate touches them, and the measurement published whatever it shows.
S4 and S5 are built only with a pass. S6 is independent and cut first.

1. **Whenever S3 or S4 is late:** S6 is cut; the switch gap returns to the
   carryover list.
2. **End of week 1, if S2's extraction has not landed:** the base narrows
   to wiki-studio's spec and pitch decisions.
3. **End of week 2, if S2's freeze has not landed:** labels freeze as
   reviewed; fewer than 8 true pairs means not testable.
4. **Start of week 3, if no candidate passes, the verdict is not testable,
   or S3 has not run:** S4-S5 are cut, the cycle ends early, issue 121 stays
   open with cycles 10, 11 and this measurement as its evidence.
5. **Middle of week 4, if S4 is not downhill or the frozen rule misses the
   time bound:** S4-S5 are cut; the kind becomes a follow-up bet from the
   frozen winner.

End of week 4: what has merged waits under `[Unreleased]`. "Exhausted"
means four working weeks. A third review round on one PR is an escalation
to the owner: a fix session, a cut from the list above, or a hold. The
never-list is in the frontmatter.

## Owner decisions (2026-11-26)

Asked by the build session and decided by the owner on 2026-11-26: **D1,
D2, D3, D4 and D6 take their defaults; D5 takes the alternative of 10 s**
(the bound is at most 10 s added to `findings` on a 500-page synthetic
wiki, the kind cut if the frozen rule misses it). The alternatives stay
recorded for the review.

- D1: Appetite and data — default: **4w, with a fresh held-out labelled
  set that gives the verdict**; cycle 10's frozen corpus is development
  data, reported only — alternative: 2w, frozen corpus only, the verdict on
  pairs three cycles have read (recall is already roughly known, finding 7;
  only false pairs would be new) — why it matters: without a held-out set a
  pass is weak evidence, and it doubles the appetite.
- D2: Held-out source — default: **wiki-studio's own spec and pitch
  decisions at a pinned commit, plus the specs memkernel and
  code-copilot-team added since cycle 10's pins** (about 150 spec items plus
  the pitch decisions) — alternatives: wiki-studio's specs only (cleaner,
  likely too few true pairs); curated pages from code-copilot-team's
  `knowledge/wiki` (19 pages, not independent) — why it matters: it sets
  whether 8 true pairs are reachable and how close the pages are to a real
  wiki.
- D3: The candidates — default: **mutual top-k at k = 1, 3, 5**, fewest
  false per true wins, tie to the smaller k — alternatives: add a
  self-normalised score floor (the partner's bm25 as a share of the page's
  own), which needs a threshold nobody has measured; or the cycle 10
  Jaccard as a cheap prefilter, which caps recall at what it found (3 of 8)
  — why it matters: it is the rule that ships, frozen before any score.
- D4: The bar — default: **cycle 10's bar on the held-out set**: at least 8
  true pairs, three quarters found, false not outnumbering true —
  alternative: half found, same false limit (an audit can trade recall for
  fewer false alarms; on the development pairs k = 1 reaches 4 of 8, so
  three quarters makes a pass unlikely for small k) — why it matters: it
  decides whether anything ships; set knowing finding 7.
- D5: The time bound — default: **at most 5 s added to `findings` on a
  500-page synthetic wiki**, the kind cut if the frozen rule misses it —
  alternatives: 10 s; or no bound, the cost documented — why it matters:
  hosts run `findings` at session start and over MCP, and the kind is on by
  default.
- D6: The `for_root` switch gap — default: **fixed in this bet for both
  switches (S6)**, independent of the verdict, cut first — alternative: a
  separate cooldown fix; the new switch then follows `resolve` only and the
  README states the limit for both — why it matters: a second switch built
  the cycle 11 way repeats a known gap for library callers, memkernel's
  export included.

## Bet log

| Date | bet_status | Note |
|------|------------|------|
| 2026-11-26 | shaping | Drafted from issue 121 (open; the owner's call on 2026-11-26: it stays open for an after-the-fact audit) and its body's preferred shape (2026-11-19), `eval/duplicates/report.md`, `eval/similar/report.md` and `results/`, `specs/retros/cooldown-after-11.md`. wiki-studio read at main 587c6fb: `findings.py`, `conflicts.py`, `discovery.py` (`similar_pages`), `search_index.py`, `paths.py`, ADR-0004, `docs/knowledge-contract.md`, `eval/similar/rank.py`. No score computed by the shaper; held-out sources counted by heading only. |
| 2026-11-26 | shaping → shaped | 6 scopes, 4w, work content 15-21h (core S1-S3 9-12.5h). Core: protocol frozen first, held-out set labelled and frozen, measurement as a hand-opened evidence PR. S4-S5 (`possible-duplicate`, ADR-0006, documents) only with a pass; S6 (`for_root` reads both switches) independent, cut first. D1-D6 open for the owner with defaults (the shaping agent cannot ask). |
| 2026-11-26 | shaped (owner decisions) | The owner took D1 4w with a fresh held-out labelled set that alone decides; D2 wiki-studio's own spec and pitch decisions plus the specs memkernel and code-copilot-team added since cycle 10's pins; D3 mutual top-k at k = 1, 3, 5; D4 cycle 10's bar on the held-out set; D5 **10 s** (the alternative, not the 5 s default); D6 the `for_root` switch gap fixed in this bet for both switches (S6, cut first). bet_status unchanged. |
