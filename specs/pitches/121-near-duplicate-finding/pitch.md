---
pitch_id: 121-near-duplicate-finding
title: "A near-duplicate finding from titles and summaries: re-measure the issue 54 study's signal (b) on a larger corpus whose labels are made independently and frozen first, then ship a warn-by-default possible-duplicate finding, silenced per pair by a body line, only if a candidate clears the frozen bar"
appetite: 4w
bet_status: shaped
cycle: ""
circuit_breaker: "Core is S1 (the corpus: code-copilot-team's routing and pi spec decisions at fd05256 and memkernel's spec decisions at 8279d76, about 215 items, extracted verbatim, everything the issue 54 corpus was drawn from or overlaps excluded, every page pinned by sha256, D2), S2 (the labels, the candidates and the bar, labelled by a session with no candidate code, reviewed by the owner and frozen, D3, D4, D5) and S3 (the measurement, published whatever it shows, as an evidence PR opened by hand). S4 (the possible-duplicate kind), S5 (ADR-0006 and the documents) and S6 (the 0.12.0 release) ship only if a candidate clears the bar frozen in S2. Cut order, first to last, each with its trigger: (1) end of week 1, if S1's extraction has not landed: both repositories stay, code-copilot-team narrows to the routing family (pi dropped) and memkernel drops its three H3-format pre-0.7 plans (14 items), about 172 pages, and the extension order still applies before the freeze; (2) end of week 2, if S2's freeze has not landed: the labels freeze as reviewed by then, and with fewer than 8 true pairs the verdict is not testable; (3) start of week 3, if no candidate clears the bar, the verdict is not testable, or S3 has not run: S4-S6 are cut, the cycle ends early, and issue 121 stays open with the measurement as its evidence; (4) middle of week 4, if S4 is not downhill: S4-S6 are cut the same way, and the kind becomes a follow-up bet that starts from the frozen winner. End of week 4: S6 ships what is true; if the release cannot be cut, the change waits under [Unreleased]. Never, to save time: drop a repository from the base; include a spec the issue 54 corpus was drawn from or that overlaps it; run any candidate, or compute any similarity score, on the new corpus before the freeze; edit a label, a page, a candidate, the threshold or the bar after the freeze, or add pages after the run; skip the owner's review of the labelling commit; put a model on any path from findings, approve or review_state; change wiki_state._tokenise; add a frontmatter key, a page type, an exit code, a runtime dependency or an MCP tool; ship the kind without ADR-0006 for the related line; make lint --health or --strict report or fail on the new kind; make the kind block promote or approve, or merge, delete or supersede anything; bump findings_version; edit eval/patterns' frozen files, memkernel or code-copilot-team; read over the network; quote closing-keyword text anywhere; weaken or skip a test."
shaped_by: "pitch-shaper (Claude Code) for gosha70"
shaped_date: 2026-11-23
---

<!-- Shape-Up pitch. Origin: https://github.com/gosha70/wiki-studio/issues/121 (filed by the owner on 2026-11-22, no comments on 2026-11-23), drafted by the issue 54 study at 25b9e13 (`eval/patterns/issues/duplicate-title-summary-finding.md`). Evidence: `eval/patterns/report.md` question 4 and "Labels", `eval/patterns/results/duplicates.json`, `eval/patterns/protocol.json`, `eval/patterns/labels.json`. Template for a measure-first pitch: `specs/pitches/120-revision-aware-stale-check/pitch.md` and its bundle `specs/wiki-studio-0-11-0/`. -->
<!-- This pitch shapes the issue; it does not replace it. The owner's preferred shape for the kind (issue 121, 2026-11-19) is carried as written: on by default, silence one pair with a body line, an optional switch per wiki, every finding ends with the exact line to silence it, findings only. The owner answered D1-D8 on 2026-11-23 (D2 against the default: memkernel's spec decisions join the corpus from the start); D9 followed from D2; the owner answered it with the default on 2026-11-23. -->

# Pitch: A near-duplicate finding from titles and summaries

## Problem

Two decision pages can record the same decision in different words, and
nothing in wiki-studio tells a curator so. The two pages then drift
apart: one gets corrected, the other keeps being found and cited.
`findings` reports a disagreement only when a curator has already marked
it with `> [!conflict]` callouts, and the model-free checks compare no
two pages for similarity.

The issue 54 study measured three model-free signals for near-duplicates
against labels frozen before any signal ran. Signal (b), the Jaccard
similarity of the tokens in a page's title and the first paragraph of its
`## Decision` section (the Y-statement), came closest: 2 of 3 true pairs
found, 1 false candidate. Its recorded verdict is "fail". It would pass
only if one disputed label, a decision page and the incident record
behind it labelled `redundant`, were read as `unrelated`. The verdict
rests on three labelled pairs, so no precision or recall can be estimated
from it, and one of (b)'s two finds is a pair `findings` already reports
as `open-conflict`.

Issue 121 asks for an investigation before any code: re-run (b) on a
larger corpus labelled independently, with the labels frozen first;
settle how a decision page and its incident record are labelled; and only
then decide whether a model-free `findings` kind is worth its false
alarms. A kind that is wrong more often than right teaches curators to
ignore findings, so the false-alarm rate has to be measured before the
kind ships.

## Findings from the code and the candidate corpora

wiki-studio was read at main `35aa842` (the 0.11.0 build merged, not yet
tagged) on 2026-11-23. The candidate corpora were read offline in the
local checkouts: code-copilot-team at `fd05256` (2026-11-22) and memkernel
at `8279d76` (2026-11-23; the first read was at `569d28f`, and the
checkout moved during shaping, so every memkernel count below is at
`8279d76`). Nothing was fetched. **The shaper counted pages, sections and
pairs only. It ran no signal and computed no similarity score on any
candidate corpus**, so no number below comes from (b).

1. **The study's (b) is defined exactly and frozen.**
   `eval/patterns/protocol.json` defines (b) as
   `wiki_state._tokenise(title + " " + the first paragraph of ## Decision)`,
   or the title and first body paragraph for a page without
   `## Decision`, compared by Jaccard at `>= 0.25`. The paragraph rule
   lives in `eval/patterns/duplicates.py` (`_first_paragraph`: headings,
   blockquotes, lists and numbered items are skipped). The pass bar was
   "finds every eligible true pair, and false candidates do not outnumber
   true ones"; with no labelled pairs, "not testable, never a pass".
   `tests/test_patterns_frozen.py` pins the study's labels, questions and
   protocol by sha256. A new measurement reads these files and never
   edits them.
2. **The disputed label is a labelling-rule gap, not a typo.** The study
   had four dispositions: `redundant` and `conflicting` (true),
   `distinct-by-precondition` and `unrelated` (false). A decision page
   and the incident record it came from are different page types a
   curator keeps apart on purpose; none of the four fits them cleanly.
   The report also notes that the set had no "supersedes" value for a
   successor and the page it replaces (`report.md`, "Labels").
3. **`_tokenise` has properties a larger corpus will expose.**
   `wiki_state._tokenise` (`wiki_state.py` 142-146) keeps
   `[a-z0-9][a-z0-9-]*` runs, lowercased, minus a 27-word stop list. So:
   a Markdown link's target contributes path tokens (`incidents`, the
   target slug, `md`); a hyphenated slug is one token and never matches
   its words; `redact_text` splits into `redact` and `text`; `api.py`
   gives `api` and `py`; numbers and commit prefixes (`2026`, `57`,
   `a24a00e`) are tokens; there is no stemming (`commit` and `commits`
   differ); non-ASCII letters split words. The packaged Y-statement
   template (`page-types.md` 128-133: "In the context of <situation>, we
   chose <choice>." / "We chose it over <alternative>." / "The reason:
   <why>.") puts `context`, `we`, `chose`, `over` and `reason` in every
   pattern page; none is a stop word, so on a corpus of template pages
   every pair shares them. A page whose `## Decision` holds only a list
   falls back to its title alone, and two short token sets reach 0.25
   easily. `_tokenise` also drives ingest's candidate selection
   (`wiki_state.py` 239-281), so the kind must not change it.
4. **The conflict scan is the model for the kind and for the silence
   line.** `conflicts.py` reads `> [!conflict]` marker lines without a
   model (marker after at most three spaces and the `>`,
   case-insensitive, optional fold sign, the first `.md` link names the
   other page, fenced code skipped), reads the whole review set whatever
   the scope, and `findings.py` keeps only findings touching in-scope
   pages (293-297). ADR-0004 registered that body form with no
   frontmatter key and no schema bump; ADR-0005 did the same for
   `Revisit when:`. A `> [!related]` line is the same kind of change and
   takes ADR-0006. `_first_paragraph` skips blockquotes, so adding a
   silence line never changes a page's score.
5. **New kinds are additive.** `docs/knowledge-contract.md` 403: "Kinds
   may be added within `findings_version: 1`"; `counts` names every kind.
   The conflict and revision kinds were added this way with no new
   capability. `api.findings(paths, *, pages=None)` reaches the CLI,
   `nightly` and the MCP `findings` tool, and `tests/test_findings.py`
   pins its signature to `paths` and `pages`, so a switch must travel in
   `WikiPaths`, as `WIKI_STUDIO_GIT_CALL_LIMIT` does (`paths.py` 38,
   390-393; no CLI flag).
6. **A finding never blocks.** `findings` reads only, takes no lock and
   exits 0 on a completed run; `lint --health --strict` is the CI gate
   and runs `health_lint`, not `findings`. A kind placed in `findings.py`
   leaves that gate as it is.
7. **code-copilot-team's wiki is not independent and is too small.**
   `knowledge/wiki/` has 19 typed content pages: 2 decisions, 4
   incidents, 4 concepts, 5 playbooks, 4 workflows (plus `overview`,
   glossary, index, log). 18 of the 19 were the issue 54 study's
   background pages, already scored by (b); the 19th,
   `pre-pr-close-keyword-audit`, quotes closing-keyword phrases and was
   left out for that reason. It holds one decision-and-incident pair that
   link each other (`infra-verification-as-gate` and
   `executable-artifacts-shipped-unexecuted`), the same shape as the
   disputed pair. 22 commits touched the wiki; none merged two pages.
8. **memkernel has no wiki corpus, but its specs hold decisions.** Its
   `eval/decisions-57/corpus.md` (12 records) was the issue 54 corpus.
   `eval/datasets/memkernel_eval.json` has 15 synthetic memories (4
   decisions). The other eval sets test memory behaviour, not pages. It
   has no wiki directory and 5 ADRs. Its 20 spec directories with a
   decision section hold **112 top-level decision items** by the
   extraction rule of finding 13 (the first count, about 147, also
   counted the sub-bullets of bold-paragraph items).
9. **ADR sets are too small to supply true pairs.** memkernel 5,
   wiki-studio 5, document-assistant 5, rlmkit 4: 19 records, 36
   within-repository pairs, and three of memkernel's are copies in
   `eval/navigation/corpus`. Few, if any, are duplicates of each other.
10. **code-copilot-team's specs are the largest source of decisions.**
    116 spec directories; 56 have a decision section in `plan.md` or
    `spec.md` (`## Decisions`, `## Design decisions`, `## Design
    decisions to confirm at approval` and variants). By finding 13's rule
    they hold **367 top-level decision items in 58 files**. By family:
    session-analytics 107, routing 84 (10 spec directories, 11 files:
    `routing-effective-endpoint` has decisions in both its plan and its
    spec), auto-build 32, wiki 30, pi 29 (5), benchmark 28, api 15,
    llm-catalog 15, memkernel-integration 7, one-harness-home 6, plugin 5,
    init 3, redaction 3, simplest-complete-change 3. A family's later
    specs build on its earlier ones, which is where a wiki would gain
    duplicate or superseded decision pages; how often they restate a
    decision is what the labels will show. (The first count, about 273
    items, missed bold-paragraph items.)
11. **What the issue 54 corpus was drawn from, and how it was checked.**
    The 12 records' `evidence` lines cite 21 distinct path-at-commit
    sources, **all in code-copilot-team**: specs of session-analytics
    (trace-archive, similarity-ui, benchmark-step, benchmark-ui),
    benchmark (adapters-backends, llm-judge), auto-build
    (loop-merge-profile) and `init-permission-profiles`, plus code and the
    safety rule and skill. None cites memkernel. memkernel added the
    corpus in `8fae17e` (2026-11-11) with no spec of its own. Two memkernel
    specs name `eval/decisions-57/` because they evaluate on it:
    `memkernel-0-10-decision-revalidation` and
    `memkernel-0-11-anti-rot-injection` (10 items). A scan of memkernel's
    specs for the records' distinctive terms (`redact_text`, `correlate`,
    `require_green_ci`, balanced profile, alternate index, raw JSONL,
    clusters view, `spearman`, SWE-bench) found only a generic
    "correlate" in `memkernel-0-15-harness-foundations` (a run's
    outcome, not the correlate seam) and a match in `memkernel-0-5`, which
    has no decision section. So the base **excludes**: in
    code-copilot-team, every family a record was drawn from (session-analytics
    107, benchmark 28, auto-build 32), `init-permission-profiles` (3, cited
    by a record) and `redaction-canaries` (3, the same topic as two
    records), 173 items; in memkernel, the two specs that evaluate on the
    corpus, 10 items.
12. **The base corpus, after the exclusions.** code-copilot-team's routing
    (84) and pi (29) families, 113 items in 16 files, and memkernel's
    remaining 18 spec directories, 102 items: **about 215 pages**. Pairs:
    23,005 in all; 9,043 within a family (routing 3,486, pi 406,
    memkernel, treated as one family, 5,151); 2,436 across code-copilot-team's
    two families; 11,526 across the two repositories. Left for the
    extension order: 81 code-copilot-team items (api 15, llm-catalog 15,
    wiki-studio-adoption 14, wiki-audit-trail and wiki-audit-flush 16,
    memkernel-integration 7, one-harness-home 6, plugin-generate-from-sources
    5, simplest-complete-change 3); memkernel has nothing left to add.
    One line in memkernel's `memkernel-0-16-lifecycle-corrections`
    decision section matches the closing-keyword pattern; the item that
    holds it is listed by id and left out (S1), so the base may be one
    page smaller.
13. **The two repositories write decisions in three forms.** Counted per
    decision section, in the precedence the extraction rule uses:
    - *H3 items* (code-copilot-team 4 sections, memkernel 3): `### D2 —
      Calibration corpus source`; memkernel's three pre-0.7 plans
      (`copilot-memory-mvp`, `memkernel-0-3`, `memkernel-0-4`, 14 items)
      write each as `### ADR-1: MCP-first, FastAPI secondary` with
      `**Context**:`, `**Decision**:` and `**Consequences**:` lines.
    - *Bold paragraphs at column 0* (code-copilot-team 17, memkernel 7):
      `**S1. A wiki's identity: two tags (#80 option A).**`, followed by
      column-0 bullets that belong to it (`- **The tags.** …`).
    - *Bold-led list items* (code-copilot-team 38, memkernel 10):
      `- **D1 Key.** (session, tool_use_id, extractor), …`,
      `- **D-upsert-key** — …`, `3. **Reports bind to corpus AND policy.**`,
      with indented continuation lines; amendments use the same form
      (`- **A1 (the owner's, 2026-11-15, review of #127).**`).
    A plain bullet count misreads the second form (it counts the
    sub-bullets as items), which is why the first counts were wrong.
14. **Spec decisions are not wiki pages.** Items are often one paragraph
    (memkernel's bold-paragraph items run to a page), and their labels
    carry identifiers (`D5`, `D-upsert-key`, `S1.`, `ADR-1:`) that would
    become tokens. Title extraction has to strip them, and the report has
    to say the pages are extracted, not curated.

So a larger independent corpus exists, but only by extraction, and the
number of true pairs it holds is unknown until it is labelled. **"Not
testable" is a valid outcome**, and the pitch is shaped so that it ends
the cycle early with the evidence published.

## Appetite

**4w** (D1, decided by the owner), one cycle, with an early exit. Work
content for an LLM executor is about 20.5-27 hours across six scopes;
the core (S1-S3) is about 13.5-17.5 hours. D2's second repository added
about 1h to S1 (a second pin and the H3 section mapping), 2-3h to S2
(about 215 pages to cluster instead of 96) and 0.5h to S3 (results by
repository and by pair scope).

| Scope | Estimate |
|-------|----------|
| S1 The corpus, extracted verbatim from two repositories and pinned | 4-5h |
| S2 Labels, candidates and bar, frozen | 6-8h (plus the owner's review) |
| S3 The measurement and the evidence PR | 3.5-4.5h |
| S4 The `possible-duplicate` kind (only with a winner) | 4-5h |
| S5 ADR-0006, contract and documents (only with a winner) | 2-3h |
| S6 Release 0.12.0 (only with a winner) | 1-1.5h |

Why 4w and not 2w: as in issue 120's cycle, the order cannot compress.
The labels freeze in their own commit after the owner reviews them; the
measurement goes through review as an evidence PR; the spec's winner slot
is set by an amendment after that PR merges; only then does the build
start. That is three review-gated steps before the release, each with an
external review round. The owner weighed 2w (S1-S3 only, the kind as a
follow-up bet) and chose the full project.

Why not 6w: if no candidate clears the bar, or the corpus cannot supply
enough true pairs, the cycle ends at the start of week 3.

**Does 4w still hold after D2?** Yes for the core. Week 1 is now the
tight one: two extractions and about 215 pages to cluster before the
owner's review. Cut 1 is a defined narrowing that keeps both
repositories; the freeze (trigger 2) stays at the end of week 2.

Planned order:

- **Week 1:** S1's extraction from both repositories (main session), the
  labelling commit (S2, no candidate code), the owner's review of it.
  Check trigger 1 at the end of the week.
- **Week 2:** the freeze commit; S3's scoring run (main session); the
  evidence PR, opened by hand, goes to review. Check trigger 2 at the end
  of the week.
- **Week 3:** the evidence PR merges; the spec amendment names the winner
  or records "none" (trigger 3). With a winner, S4 starts.
- **Week 4:** S4 finished (trigger 4 at the middle of the week), S5, S6.

**Lessons carried from the issue 120 cycle.**

- Auto-build sessions cannot run Python. Every step that runs a script
  (S1's extraction, the pair list, the first run of the frozen-hash test,
  S3's scoring) is planned as a main-session step at a milestone pause,
  never inside a driver phase. A driver phase may write a script and its
  tests; the main session runs them before the milestone is passed.
- The driver cannot open a PR that names no issue for closure (it falls
  back to `plan.md`'s origin issue). The evidence PR is opened by hand,
  and its body names issue 121 as "issue 121", never after a closing
  keyword. `scripts/pre-pr-check.sh` runs before it.
- The spec bundle is written before the measurement with the winner slot
  open; after the evidence PR merges, the owner's amendment sets it to the
  winner or `none` and re-approves (the 0.11.0 bundle's "Departures from
  the pitch", item 2).
- The scorer's rules are written down to the token before the freeze
  (finding 3, S2), so a surprise like 0.11.0's fragment anchors is less
  likely. A flaw found after the freeze goes into a "Post hoc (not
  binding)" section of the report, as `eval/revisions/report.md` did; it
  never changes the bar or the verdict.

## Solution shape

Two parts, as in issue 120. First a measurement under a new
`eval/duplicates/` directory that decides whether a candidate is good
enough. Then, only with a winner, a read-only kind in `findings` that
implements it exactly.

```
eval/duplicates/
  README.md          protocol: corpus rule, exclusions, extension order, labels, candidates, bar (S1, S2; frozen)
  extract.py         run once, by hand: verbatim extraction from both repositories at their pins (S1)
  corpus.json        per page: repository, commit, spec path, line span, form, sha256 (S1; frozen)
  corpus/<repository>/<family>/   one decision page per extracted item (S1; frozen)
  labels.json        clusters, dispositions and reasons (S2; frozen, sha256-pinned)
  protocol.json      candidates, threshold, bar, selection rule (S2; frozen)
  candidates.py      scores B0 and B1 from the frozen pages (S3)
  results/           candidates.json, secondary.json (S3)
  report.md          the table, the verdict, the winner or "none", the limits (S3)

src/wiki_studio/duplicates.py   the winning candidate, the skip rules, the related-line parser (S4)
src/wiki_studio/findings.py     one kind: possible-duplicate (S4)
docs/adr/0006-related-line.md   the > [!related] body line (S5)
```

**The corpus (D2, decided by the owner against the default: both
repositories from the start).** The base is code-copilot-team's routing
and pi spec decisions at `fd05256` (113 items) and memkernel's spec
decisions at `8279d76` (102 items), about 215 pages, less everything the
issue 54 corpus was drawn from or overlaps (finding 11). Both commits
are recorded in `corpus.json`, every page carries its sha256, and the
frozen test checks both.

**The extraction rule** is fixed in S1 before any page is read for
labelling, and is the same for both repositories:

- *Where:* every `specs/<name>/spec.md` and `plan.md` at the pinned
  commit; a decision section is an H2 whose text contains "decision"
  (any case), up to the next H2. When a spec directory has decision
  sections in both files, both are read.
- *What an item is,* by precedence within one section (finding 13): if
  the section has H3 headings, each H3 with its text is one item; else, if
  it has bold paragraphs at column 0, each such paragraph with everything
  up to the next one (its column-0 bullets included) is one item; else
  each bold-led column-0 list item with its indented continuation is one
  item. A definition or scope note extracted this way (`**Terms.**`) is
  kept and labelled by content.
- *Title:* the H3 text or the bold text, with a leading identifier
  (`D5`, `D-upsert-key`, `S1.`, `A1`, `R2`, `ADR-1:`) and a trailing
  parenthetical removed; when nothing is left, the item's first sentence.
- *Body:* `## Decision` holds the item's text verbatim. An H3 item with
  `**Context**:`, `**Decision**:` and `**Consequences**:` lines
  (memkernel's three pre-0.7 plans) has each line moved, unchanged, to
  the matching section, so `## Decision`'s first paragraph is the
  decision and not its context. No word of an item is rewritten, so the
  labeller does not write the text it labels (the issue 54 risk: the
  build wrote both the pages' links and the labels).
- *Frontmatter:* `page_type: decision`, a slug from the repository, spec
  name and item number, the title, and a `sources:` entry with the spec's
  path and the pinned commit.

**The extension rule.** If the labelled base holds fewer true pairs than
D4's minimum of 8, the labeller adds code-copilot-team's remaining
families in a fixed order, before the freeze and before any candidate
runs: api; llm-catalog; wiki-studio-adoption; wiki-audit-trail and
wiki-audit-flush; memkernel-integration; one-harness-home;
plugin-generate-from-sources; simplest-complete-change (81 items in all,
finding 12). The excluded families are never added. If the whole set
still holds fewer than 8 true pairs, the verdict is **not testable**.

**The labels (D3, D5, decided by the owner).** One labelling session
that has never seen candidate code works per family (routing, pi,
memkernel): it reads every page of the family and groups pages that
record the same decision into clusters, then gives every pair inside a
cluster a disposition and a one-line reason naming the decision. Pairs
across families, and across the two repositories, follow D9 (owner,
2026-11-23: scored, `unrelated` unless the labeller lists them after one
pass over every family's cluster summaries). Six dispositions:

- true: `redundant` (the same decision, in other words), `conflicting`
  (the same question, opposite choices), `supersedes` (a later decision
  replaces an earlier one, which a wiki would mark with `superseded_by`);
- false: `companion` (two pages about the same event or rule kept apart
  on purpose, such as a decision and the incident behind it),
  `distinct-by-precondition`, `unrelated`.

The labelling commit holds the pages and every label and no candidate
code. The owner reviews every true and `companion` label and 20 false
pairs drawn with a fixed seed, split across the families in proportion
to their within-family pairs (routing 8, pi 1, memkernel 11). The
issue 54 label stays as recorded; its disputed pair is re-read under the
new rule only in the secondary, non-binding re-score (S3).

**The candidates (S2).** Two, both model-free, both at the study's
frozen threshold of 0.25, both over every pair in scope:

- **B0, the study's (b) exactly:** `_tokenise(title + " " + first
  paragraph)` with `eval/patterns/duplicates.py`'s paragraph rule,
  imported read-only.
- **B1, B0 with a frozen text normalisation before `_tokenise`:** a
  Markdown link keeps its text and loses its target; bare URLs dropped;
  tokens that are only digits, or 7-40 hex characters with a digit,
  dropped; the Y-statement template's fixed words (`context`, `we`,
  `chose`, `over`, `reason`, the list frozen from `page-types.md`'s
  template text) dropped. Everything else as B0.

The threshold is not varied. The report gives each true pair's score
under both, as a distribution, not binding. A same-page-type restriction
is not a candidate: the corpus holds only decision pages, so it would
measure nothing (D6 sets the shipped scope instead).

**The bar (D4, decided by the owner).** A candidate passes only when all
three hold: (1) the frozen labels hold at least **8** true pairs, else
the verdict is not testable; (2) it finds at least **three quarters of
the true pairs, rounded up**; (3) its false candidates do not outnumber
its true ones across every pair in scope (the study's ratio rule). Among
passing candidates the fewest false candidates wins; a tie goes to B0,
the simpler. The report also gives false candidates per 100 pages, the
figure a curator feels, and splits every count by pair scope (within a
family, across code-copilot-team's families, across repositories).

**What a flag means, and what a curator does with it.**
`possible-duplicate` says: "these two pages may record the same decision;
read both". It is a reason to look, never a verdict. A curator does one
of three things, each with an existing mechanism:

1. **Merge:** keep one page and set `superseded_by` on the other in one
   promoted patch-set. `find` stops returning the superseded page and the
   finding goes away (superseded pages are ineligible).
2. **Mark a disagreement:** add `> [!conflict]` callouts to both pages
   (ADR-0004). The pair is then `open-conflict`, and `possible-duplicate`
   skips it, so the pair is never reported twice.
3. **Mark them as deliberately separate:** add the related line to either
   page. The check skips that pair from then on.

**The silence line (owner's shape, ADR-0006).** On either page of the
pair, a blockquote marker line in the conflict callout's form:

```markdown
> [!related] Not a duplicate of [Retry policy](../decisions/retry-policy.md)
```

The marker is `[!related]`, case-insensitive, optional fold sign, after
at most three spaces and the `>`; the first `.md` link on the marker line
names the other page, resolved from the page's directory; fenced code is
skipped. One side is enough. A related line that names no content page
silences nothing and is not itself reported (no new kind). No frontmatter
key changes, so the schema shared with memkernel does not change, and
memkernel's bridge carries the body unchanged.

**Every finding says how to silence it.** The description names the two
pages and their score, then ends with the exact line to add to the first
page of the pair (sorted), with the relative link already computed.

**Skip rules in the shipped kind.** A superseded page is never compared;
a pair joined by a conflict callout on either side (open or one-sided) is
skipped; a pair joined by a related line is skipped. One finding per
pair, severity `warning`. The scan reads the whole review set whatever
the scope, and a scoped run (`--paths`) keeps the findings that touch an
in-scope page, as the conflict scan does.

**Defaults the owner decided.** On by default. A switch per wiki turns
it off (D8: `WIKI_STUDIO_DUPLICATE_CHECK=off`, read into `WikiPaths`). In
`findings` only, not `lint --health` (D7). Same page type only (D6), so a
decision page and its incident record are never compared.

## Scopes

Build order: S1, S2, S3 (the evidence PR), the spec amendment, then S4,
S5, S6 only with a winner.

### S1: The corpus, extracted verbatim from two repositories and pinned, ~4-5h

- `eval/duplicates/extract.py`, run once by hand in the main session:
  reads each spec file with `git show <commit>:<path>` in the local
  checkout of each repository (code-copilot-team at `fd05256`, memkernel
  at `8279d76`; argument lists, no shell, no network, nothing written to
  either repository) and writes one fixture page per item under
  `corpus/<repository>/<family>/` by the extraction rule.
- The exclusions of finding 11 are a fixed list in the script and the
  README, with the reason for each (cited by a record, in a family a
  record was drawn from, the same topic, or evaluates on the corpus) and
  the check that found it.
- `corpus.json`: per page, the repository, the commit, the spec path, the
  item's line span, its form (H3, bold paragraph, list item), the
  extracted title and the sha256 of the page.
- The README states the extraction rule, the exclusions, the extension
  order, the counts per repository and family, and that the pages are
  extracted, not curated (finding 14).
- An extracted item that quotes a closing-keyword phrase (one known, in
  memkernel's `memkernel-0-16-lifecycle-corrections`) is listed in the
  README by id and left out of the fixture, as issue 54 left out the
  pre-pr playbook; no such text is copied.
- A test pins every page to `corpus.json` and checks the rule on one
  fixed item of each form, including a memkernel H3 item's section
  mapping and a bold-paragraph item with its bullets (the main session
  runs it).
- The extracted pages are lint-checked with `wiki-studio lint` on a
  temporary wiki before the labelling starts, so the scorer reads valid
  pages.

### S2: Labels, candidates and bar, frozen, ~6-8h plus the owner's review

- **The labelling commit**, written by a session that has never run any
  candidate and has no candidate code in its tree (D3): `labels.json`
  with the clusters per family, every in-cluster pair's disposition and
  reason, and the cross-family and cross-repository pairs listed by D9's
  rule. The labelling is per page, not per pair: about 215 pages in three
  families, the memkernel family the largest by text. The extension rule
  applies here, before the freeze, if the base holds fewer than 8 true
  pairs.
- **The owner's review (D3)** of every true and `companion` label, and
  of 20 false within-family pairs drawn with a fixed seed (routing 8,
  pi 1, memkernel 11). A label the owner changes is changed in that
  commit's PR, before the freeze.
- **The labelling rule for a decision and its incident record (D5)** is
  written into the README with an example from the issue 54 pair and
  code-copilot-team's `infra-verification-as-gate` pair.
- **The freeze commit:** `protocol.json` with B0 and B1 defined to the
  token (the normalisation's patterns and the template-word list), the
  threshold, the pair scope (D9), the bar, the selection rule and the
  not-testable rule; a test pinning `corpus.json`, every page,
  `labels.json` and `protocol.json` by sha256, as
  `tests/test_patterns_frozen.py` does. It lands after the owner's review
  and before any candidate code exists. Nobody edits a label, a page, a
  candidate, the threshold or the bar after it.

### S3: The measurement and the evidence PR, ~3.5-4.5h

- `eval/duplicates/candidates.py` scores B0 and B1 on the frozen pages
  and labels and writes `results/candidates.json`: per candidate, true
  and false candidates, true pairs found out of n (or "not testable"),
  false candidates by disposition (`companion`, `distinct-by-precondition`,
  `unrelated`), by pair scope and by repository, and per 100 pages, each
  true pair's score, wall time. The main session runs it; a CI test
  reruns it from the committed pages and checks the output equals the
  committed file.
- `results/secondary.json`, not binding: B0 and B1 on the issue 54
  fixture with its frozen labels, read both as recorded and with the
  disputed pair as `companion`, so the two readings sit beside the new
  result. The issue 54 files are read, never edited.
- `report.md`: the table; the verdict (a winner, "no candidate clears the
  bar", or "not testable"); the limits: extracted spec decisions, two
  repositories by one author, three families unless extended, decisions
  only (so nothing is measured across page types), a count out of n for
  recall, not an estimate. A "Post hoc (not binding)" section only if a
  flaw is found after the freeze, such as a cross-repository false
  candidate the owner reads as a true pair.
- **The evidence PR**, opened by hand from the main session: one commit
  per step (extraction, labelling, freeze, run, report), never squashed,
  nothing under `src/wiki_studio/`. Its body names issue 121 without a
  closing keyword.

### S4: The `possible-duplicate` kind, ~4-5h (only with a winner)

- `src/wiki_studio/duplicates.py`: the winning candidate exactly
  (`_tokenise` imported, unchanged; the paragraph rule and, for B1, the
  normalisation reimplemented in the package, since the package cannot
  import `eval/`), the skip rules, and the related-line parser in
  `conflicts.py`'s line-based form.
- `findings.py`: `KIND_POSSIBLE_DUPLICATE` added to `FINDING_KINDS` after
  the conflict kinds; one finding per pair; the description ends with the
  related line to add. Same page type only (D6).
- The switch (D8) read into `WikiPaths`; off means the kind is listed in
  `counts` at zero and never computed.
- Tests: the winner replayed on the frozen corpus gives exactly the
  committed candidates; superseded pages skipped; open and one-sided
  conflict pairs skipped; a related line on either side silences the pair
  and a dangling one silences nothing; the description's related line,
  pasted into the page, silences the finding; a scoped run; the switch;
  `lint --health` and `--strict` unaffected; `review_state`, `approve`
  and `find` unchanged on a flagged page; `nightly`'s report and the MCP
  `findings` tool list the kind; the no-backend guard and the single-writer
  scan still passing; a 500-page synthetic wiki finishes within a bound
  the spec sets from S3's wall time.

### S5: ADR-0006, contract and documents, ~2-3h (only with a winner)

- `docs/adr/0006-related-line.md`: the `> [!related]` body line, optional,
  no frontmatter key, no schema bump, memkernel unaffected (the bridge
  carries the body), with the frontmatter alternative the issue named
  (`not_duplicate_of:`) weighed and refused.
- `src/wiki_studio/schema/citation-rules.md` (packaged): the related line
  beside "When sources disagree".
- `docs/knowledge-contract.md`: the kind's row in the findings table and
  the switch; README's environment table; `docs/patterns.md`: what to do
  with a flag (the three actions).
- `CHANGELOG.md` `[Unreleased]`; CLAUDE.md's layout line for
  `duplicates.py`. Every command a changed page shows gets its check.

### S6: Release 0.12.0, ~1-1.5h (only with a winner)

The next minor after 0.11.0, which must be tagged and released first.
Version bumped in `pyproject.toml` and `__init__.py` together, the
CHANGELOG dated, the compatibility row, the release page with the
workflow's wheel and sdist. The build PR names issue 121 for closure only
if the kind ships; without a winner no PR names it, and it stays open
with the evidence.

## Rabbit holes

- **Too few true pairs.** Three families of extracted decisions may hold
  only a handful of duplicates, and a filter tuned to them by accident
  would pass on luck. *Workaround:* the minimum of 8, the fixed extension
  order, "not testable" as a stated outcome, and no candidate run before
  the freeze.
- **The labeller learning the signal.** The labeller knows (b) compares
  titles and summaries and could lean on wording. *Workaround:* labels
  are by decision content with a reason naming the decision; no
  candidate code is in the labelling tree; the owner reviews every true
  label and a seeded sample of the false ones.
- **Extraction edge cases in three forms** (finding 13): an H3 item
  without the `**Decision**:` line, a bold paragraph that is a heading
  for a list, an amendment item whose title is only an identifier and a
  date. *Workaround:* the precedence and the empty-title fallback are
  fixed in S1; an item the rule extracts badly is still extracted as
  written and labelled by content, and the README lists it. The rule is
  not tuned after the pages are read.
- **Cross-repository pairs.** Half of the 23,005 pairs cross the two
  repositories, and labelling them pair by pair is not feasible.
  *Workaround:* D9's default, one pass over the families' cluster
  summaries, with an unlisted pair counted false; a disagreement found
  after the run goes to the post-hoc section.
- **Family jargon.** Every routing page says `routing`, `profile`,
  `tier`, `backend`; every memkernel page says `memory`, `recall`,
  `store`. Jaccard on short texts sharing jargon may flag many
  within-family pairs. *Workaround:* none in the candidates; that is
  what the measurement is for. A stop list per wiki, an IDF weighting or
  a tuned threshold is a new candidate and a new bet, not a fix after the
  run.
- **Tokenisation surprises after the freeze** (finding 3: link targets,
  hyphenated slugs, numbers and commit prefixes, template words, empty
  summaries). *Workaround:* B1 states the normalisation to the token
  before the freeze; anything else found later goes into the post-hoc
  section and stays out of the verdict.
- **Building a general similarity engine.** MinHash, embeddings, an
  inverted index. *Workaround:* none of it; the shipped kind is the
  winner as measured, a plain pairwise loop. If S4's 500-page test shows
  it too slow, the spec may index tokens to skip pairs with no shared
  token, which gives identical results.
- **Arguing the issue 54 label again.** *Workaround:* it stays frozen;
  the new labels apply only to the new corpus, and the secondary re-score
  shows both readings without a verdict.

## No-gos

- No model on any path from `findings`, `approve` or `review_state`; the
  kind is computed from page text only.
- No automatic merge, deletion, supersession, approval change or page
  rewrite; `nightly` lists the kind and drafts nothing for it.
- No frontmatter key, page type or directory, and no page-schema change
  without an ADR; the related line gets ADR-0006, as the conflict callout
  got ADR-0004.
- No change to `lint`, `lint --health` or `--strict`; the new kind never
  makes `lint --health --strict` fail (D7).
- No change to `wiki_state._tokenise` or to ingest's candidate selection.
- No user-tunable threshold in this bet: a tuned threshold is not the
  measured candidate.
- No `findings_version` bump, no new capability, exit code, runtime
  dependency or MCP tool.
- No spec the issue 54 corpus was drawn from or that overlaps it in the
  corpus (finding 11).
- No edit to `eval/patterns/`'s frozen files (labels, questions,
  protocol, results, report), `eval/navigation`'s frozen runs, memkernel
  or code-copilot-team; no network read.
- No text with a closing keyword before an issue reference anywhere: not
  in the pitch, the corpus, the report, a commit message or a PR body.
  Issues are written "issue 121".

## Circuit breaker

Core is S1, S2 and S3: the two-repository corpus, the frozen labels and
bar, and the measurement published whatever it shows. S4, S5 and S6 ship
only if a candidate clears the frozen bar. Both repositories, the
exclusions, the extension rule and the owner's review are never cut; the
labels freeze with what is reviewed when trigger 2 fires.

The cut order, first to last, each with its trigger:

1. **End of week 1, if S1's extraction has not landed:** both
   repositories stay. code-copilot-team narrows to the routing family
   (pi's 29 items dropped) and memkernel drops its three H3-format pre-0.7
   plans (14 items, the form that needs the section mapping): about 172
   pages, 7,314 within-family pairs. The extension order still applies
   before the freeze.
2. **End of week 2, if S2's freeze has not landed:** the labels freeze
   as reviewed by then; with fewer than 8 true pairs, the verdict is not
   testable.
3. **Start of week 3, if no candidate clears the bar, the verdict is not
   testable, or S3 has not run:** S4-S6 are cut and the cycle ends early.
   Issue 121 stays open with the measurement as its evidence.
4. **Middle of week 4, if S4 is not downhill:** S4-S6 are cut the same
   way; the kind becomes a follow-up bet that starts from the frozen
   winner.

- **End of week 4.** S6 ships what is true. If the release cannot be
  cut, the change waits under `[Unreleased]`.
- **Never, to save time:** drop a repository from the base; include a
  spec the issue 54 corpus was drawn from or that overlaps it; run a
  candidate or compute a score on the new corpus before the freeze; edit
  a label, page, candidate, threshold or the bar after it, or add pages
  after the run; skip the owner's review; put a model on the findings
  path; change `_tokenise`; add a frontmatter key, page type, exit code,
  runtime dependency or MCP tool; ship the kind without ADR-0006; let the
  kind reach `lint --health` or block promote or approve; bump
  `findings_version`; edit the frozen issue 54 files, memkernel or
  code-copilot-team; read over the network; quote closing-keyword text;
  weaken or skip a test.

"Exhausted" means four working weeks have passed. A third review round
on one PR is an escalation to the owner, who chooses a fix session, a cut
from the list above, or a hold.

## Decisions

The owner **decided D1-D8** on 2026-11-23 in the main session. D2 went
against the recommended default (memkernel's spec decisions join the
corpus from the start); the other seven took the default. Each item keeps
the default and the alternatives, so the record shows what was weighed.
D9 followed from D2; the owner answered it with the default on 2026-11-23. S-1 to S-9 are settled by the issue, the
code or the contract, and are listed so the spec does not reopen them.

- **D1. Appetite (decided by the owner, 2026-11-23: the default).**
  **4w, the full project**, with an early exit, knowing S4-S6 ship only
  with a winner. Alternative weighed: 2w, S1-S3 only, the kind a
  follow-up bet.
- **D2. The corpus (decided by the owner, 2026-11-23, against the
  default).** Owner: **add memkernel's specs too.** The base is
  code-copilot-team's routing and pi spec decisions at `fd05256` (113
  items) and memkernel's spec decisions at `8279d76` (102 items), about
  215 pages, extracted verbatim by one rule (finding 13), each repository
  pinned by commit and each page by sha256. Excluded: everything the
  issue 54 corpus was drawn from or overlaps (finding 11: 173
  code-copilot-team items, 10 memkernel items). The fixed extension order
  of 81 code-copilot-team items applies after the two-repository base.
  The default was code-copilot-team's routing and pi families alone (96
  items by the first count), extended in order; the other alternative,
  code-copilot-team's wiki, is not independent (finding 7).
- **D3. Who labels (decided by the owner, 2026-11-23: the default).**
  One session that has never seen candidate code labels, clustering each
  family; the owner reviews every true and `companion` label plus 20
  false pairs drawn with a fixed seed (split routing 8, pi 1, memkernel
  11 by within-family pairs). Alternative weighed: two labellers blind to
  each other, agreement reported.
- **D4. The bar (decided by the owner, 2026-11-23: the default).** At
  least 8 true pairs, else "not testable"; pass = finds at least three
  quarters of them, rounded up, and false candidates do not outnumber
  true ones; candidates B0 and B1 at 0.25; fewest false candidates wins,
  a tie to B0.
- **D5. A decision and its incident record (decided by the owner,
  2026-11-23: the default).** A new `companion` disposition counted
  false; `supersedes` counted true; the issue 54 label stays frozen.
  Alternative weighed: `redundant`, the study's reading.
- **D6. Which pairs the shipped kind compares (decided by the owner,
  2026-11-23: the default).** Pages of the same page type only.
  Alternative weighed: all content pages, companion pairs silenced one
  related line at a time.
- **D7. `lint --health` (decided by the owner, 2026-11-23: the
  default).** No: the kind is in `findings` only, so `lint --health
  --strict` in CI never fails on it.
- **D8. The switch per wiki (decided by the owner, 2026-11-23: the
  default).** `WIKI_STUDIO_DUPLICATE_CHECK=off`, read into `WikiPaths`
  like the git call limit, no CLI flag. Alternative weighed: a key in
  `.wiki-studio.json`, a manifest contract change with its own decision
  record.
- **D9. Pairs across families and across repositories (raised by D2;
  owner, 2026-11-23, the default).** Every pair is scored and counted. A
  cross-family or cross-repository pair is `unrelated` unless the labeller
  lists it after one pass over a one-line summary of every cluster in all
  three families (about 1h, inside S2's estimate); the owner reviews every
  listed pair with the true labels. The shipped kind would compare such
  pairs in a real wiki, so their false alarms are counted.
- **S-1. The silence line is a body line** (the owner's shape in issue
  121): `> [!related]` in the conflict callout's form, on either page,
  with ADR-0006. The issue weighed a frontmatter key and preferred the
  body line because it leaves the shared schema alone.
- **S-2. Model-free** (issue 121's out-of-scope list, CLAUDE.md).
- **S-3. Additive within `findings_version: 1`** (finding 5), no
  capability, as the conflict and revision kinds were.
- **S-4. No double report.** A pair joined by a conflict callout on
  either side is skipped; superseded pages are ineligible, as in the
  study and in `find`.
- **S-5. A finding never blocks** and never changes `review_state`,
  approvals or `find` (finding 6).
- **S-6. Every finding ends with the exact related line** (the owner's
  shape).
- **S-7. The issue 54 study stays frozen**, its disputed label included;
  the new labels apply to the new corpus only.
- **S-8. Release 0.12.0** if the kind ships, after 0.11.0 is out.
- **S-9. Script runs are main-session steps; the evidence PR is opened
  by hand** (the issue 120 cycle's lessons).

## Questions for the owner

These are the pitch's open decisions (the template's "Open decisions"
list). **D1-D8 were asked by the main session on 2026-11-23 and
answered**; the answers are recorded under "Decisions" above.

- D1 answered: 4w, the full project (default).
- D2 answered against the default: add memkernel's specs too, from the
  start, beside code-copilot-team's routing and pi families.
- D3 answered: one labeller with no candidate code; the owner reviews
  every true and companion label plus 20 seeded false pairs (default).
- D4 answered: at least 8 true pairs; three quarters found; false not
  outnumbering true; fewest false wins, tie to B0 (default).
- D5 answered: `companion` false, `supersedes` true, the issue 54 label
  frozen (default).
- D6 answered: same page type only (default).
- D7 answered: findings only (default).
- D8 answered: `WIKI_STUDIO_DUPLICATE_CHECK=off` in `WikiPaths` (default).

One more decision was raised by D2's answer; the owner answered it with
the default on 2026-11-23. No decision remains open.

- D9 (answered 2026-11-23: the default): Are pairs across families and across the two repositories scored
  and labelled — default: **scored and counted; such a pair is
  `unrelated` unless the labeller lists it, after one pass over a
  one-line summary of every cluster in all three families (about 1h,
  inside S2's estimate); the owner reviews every listed pair with the
  true labels** — why it matters: 13,962 of the base's 23,005 pairs cross
  a family (11,526 of them cross the repositories), and the shipped kind
  would compare them in a real wiki, so leaving them out would hide their
  false alarms. Alternatives: score within-family pairs only (9,043
  pairs, cheaper, but blind to cross-family false alarms); or label every
  cross-repository pair one by one (11,526 pairs, not feasible in the
  appetite).

## Bet log

| Date | bet_status | Note |
|------|------------|------|
| 2026-11-23 | shaping | Pitch drafted from wiki-studio issue 121 (no comments) and the issue 54 study (`eval/patterns/report.md` question 4 and "Labels", `results/duplicates.json`, `protocol.json`, `labels.json`). wiki-studio read at main 35aa842: `findings.py`, `conflicts.py`, `wiki_state.py` (`_tokenise`), `paths.py`, ADR-0004, ADR-0005, `docs/knowledge-contract.md` (Findings), `schema/page-types.md`. Corpora counted offline, no signal run: code-copilot-team at fd05256 (wiki 19 typed pages, 18 of them issue 54 background; specs about 273 named decision items in 41 specs, routing and pi 96 with no topic overlap), memkernel at 569d28f (no wiki corpus; about 147 spec decision items). |
| 2026-11-23 | shaping → shaped | 6 scopes, 4w with an early exit, work content 17-22.5h (core S1-S3 10-13h). Core: corpus, frozen labels and bar, measurement as a hand-opened evidence PR. S4-S6 (`possible-duplicate`, ADR-0006, 0.12.0) only if B0 or B1 clears the frozen bar. D1-D8 open for the owner with defaults, not yet asked (the shaping agent cannot ask). |
| 2026-11-23 | shaped (decided) | Owner answered D1-D8 on 2026-11-23 in the main session. Seven defaults; D2 against the default: memkernel's spec decisions join the corpus from the start. Recounted offline with one extraction rule over three item forms (H3, bold paragraph, bold-led list item; finding 13), which replaces the first grep counts: code-copilot-team at fd05256 367 items in 58 files, routing 84 and pi 29 (113); memkernel at 8279d76 (the checkout had moved from 569d28f) 112 items in 20 spec directories. Overlap with the issue 54 corpus checked: its 12 records cite 21 sources, all in code-copilot-team, none in memkernel; excluded 173 code-copilot-team items (session-analytics, benchmark, auto-build, init-permission-profiles, redaction-canaries) and 10 memkernel items (the two specs that evaluate on decisions-57). Base about 215 pages, 23,005 pairs (9,043 within a family, 11,526 across repositories); extension order of 81 code-copilot-team items after the base. D9 added, open: pairs across families and repositories scored, `unrelated` unless listed after one pass over cluster summaries. Appetite 20.5-27h (core 13.5-17.5h; S1 4-5h, S2 6-8h, S3 3.5-4.5h), still 4w. Updated: frontmatter circuit breaker (both repositories in core, cut 1 keeps both: routing only and memkernel without its three H3 plans, about 172 pages); findings 8, 10-14; Appetite and planned order; Solution shape (the corpus, the extraction rule, exclusions, extension order, labels, owner's review sample split routing 8, pi 1, memkernel 11, bar by pair scope); S1, S2, S3; rabbit holes (extraction forms, cross-repository pairs, memkernel jargon); no-gos; Circuit breaker; Decisions (D1-D9); Questions for the owner (answered, D9 open). |
| 2026-11-23 | shaped (decided, D9) | Owner answered D9 on 2026-11-23 with the default: every pair is scored and counted; a cross-family or cross-repository pair is `unrelated` unless the labeller lists it after one pass over the cluster summaries, and the owner reviews every listed pair. No decision remains open. |
