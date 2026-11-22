---
pitch_id: 54-reusable-patterns
title: "Reusable engineering patterns, a research spike: write real patterns as existing decision pages, trace them through propose, approve, find and supersede, measure model-free duplicate candidates on labelled pairs, and publish a recommendation (docs and a template, a separately specified enhancement, or no change)"
appetite: 2w
bet_status: shipped
cycle: "08"
circuit_breaker: "Core is S1 (the fit map), S2's five issue examples as lint-clean decision pages, S3 (the lifecycle trace and the retrieval run) and S6 (the recommendation, published with whatever was measured and labelled as such). Cut order, first to last, each with its trigger: (1) end of week 1, if S2 is not done: drop the code-copilot-team background pages and the remaining corpus records, keep the five issue examples plus the two pages the stale case needs (D5); (2) start of week 2, if S4's labels and thresholds are not frozen: S4 measures only the existing deterministic signal (shared cited source or a direct link) on the labelled pairs, with no new signal; (3) middle of week 2, if S5 has not run: S5 becomes the analytic statement from the code (stale-claim checks that a cited path exists, not its revision) with no git-diff run, and the report says it was not measured. End of week 2: S6 publishes what is true, every unmeasured question named as unmeasured; #54 closes by D8 only when the recommendation is published. Never, to save time: change anything under src/wiki_studio/ (the package, its packaged schema documents and the persona included); change the page schema, findings, findings_version, lint, an exit code or an MCP tool; add a runtime dependency or a network fetch to a test; set or change a duplicate label or a threshold after its run; merge, prune, approve or rewrite a page automatically; claim that patterns change agent behaviour (not measured); edit memkernel, code-copilot-team or the frozen eval copies; weaken or skip a test."
shaped_by: "pitch-shaper (Claude Code) for gosha70"
shaped_date: 2026-11-17
---

<!-- Shape-Up pitch. Origin: https://github.com/gosha70/wiki-studio/issues/54 (no comments on 2026-11-17). Related: gosha70/memkernel#57 (closed, the runtime-side spike), gosha70/memkernel#123 (closed), gosha70/code-copilot-team#389 (open). -->
<!-- specs/retros/cooldown-after-05.md: the owner's order for shaping is #69, then #70, then #54. specs/retros/cooldown-after-06.md: owner, 2026-11-16, #54 is shaped next, after #70, for cycle 08. #70 is cycle 07 (approved, 0.10.0, not built). This pitch shapes the issue; it does not replace it. -->

# Pitch: Reusable engineering patterns, a research spike

## Problem

A coding agent told to "reuse existing code before writing new code"
can only reuse what it can find, and only safely when what it finds is
current and scoped. A runtime memory that once said "use helper X" keeps
saying it after X's contract changes, and it says it to tasks whose
preconditions differ. A curated wiki page could carry why a pattern was
chosen, where its canonical implementation and tests are, what was
rejected and when to look again, and wiki-studio's review gate could
keep an agent's draft from becoming trusted guidance without a person.

Issue #54 asks whether that works with what wiki-studio already has, and
says plainly that it is a research spike: its deliverable is a
recommendation (docs and templates only, a separately specified
enhancement, or no change), not a schema, a page type or a deduplication
service. It asks six questions: can current pages hold a pattern; how
does an agent propose one and what evidence must promotion see; how does
an agent find and cite approved patterns without treating them as
binding; can existing lint, query or findings expose near-duplicates
without merging anything; how does a source or spec change mark a
pattern for review; and what should memkernel keep to point at one.

Nobody has answered these on the wiki side. memkernel answered the
runtime half in its own spike (#57, closed 2026-11-11). Today a team
that wants curated patterns writes decision pages by hand, with no
convention, no evidence checklist, no measured view of how duplicates
show up, and no stated answer on staleness.

## Findings from the code

wiki-studio was read at main `cb7fc6d` (0.9.2 released; 0.10.0 spec
approved, not built) on 2026-11-17. memkernel was read, read-only, at
main `87bbd04` (its #57 corpus is in tag `v0.9.0`). code-copilot-team was
read, read-only; commit `00d49c0` is present locally. These facts drive
the decisions and the rabbit holes.

1. **Structural lint checks no body section.** `lint.py` checks
   frontmatter keys, `page_type`, slug, placement, `sources:` presence
   (lines 372-373), links and reachability. It has no rule for the H2
   sections `page-types.md` lists. `prose_lint.py` (line 644) checks
   only sentence counts in `## Summary` and `## Key ideas`. A body
   convention therefore costs nothing in lint, and nothing enforces it
   either.
2. **The `decision` type already has most of a pattern's slots.**
   `page-types.md` (line 104) requires `## Decision`, `## Context`,
   `## Alternatives considered` and `## Consequences`, with status and
   date in frontmatter, not in H2s. Mapped to #54's fields: intent goes
   in Decision; applicable constraints in Context; rejected alternatives
   in Alternatives considered; revisit criteria in Consequences; the
   canonical implementation and validation evidence as `sources:` entries
   (`path:` with `sha:`, plus `issue:`/`pr:`) and links in the body;
   status in frontmatter `status:`. "Owner" has no slot: the approval
   record names the approver, and nothing names a maintainer.
3. **Unknown frontmatter keys pass lint, but adding one is a schema
   change.** `lint.py` has no allow-list of keys. memkernel keeps
   top-level single-line scalars and `sources:` only (ADR-0002, ADR-0004),
   so `revisit_when: …` would survive its round trip. CLAUDE.md makes
   any frontmatter key a change to the published contract that needs an
   ADR. The issue puts a new required schema out of scope.
4. **ADR-0004 rejected a new H2 for a body convention.** Its "Why not"
   list refuses a dedicated `## Disagreements` section because "it adds an
   H2 the page-type templates do not list". ADR-0001 and ADR-0004 are
   the precedent for an optional body convention, registered by an ADR
   because `findings` parses it. A convention nothing parses is prose
   guidance, not a schema change.
5. **Approval is bound to bytes, not to status.** `review.py` (lines
   1-20): an approval is an immutable record keyed by page key, sha256 of
   the revision and the policy hash; `status: stable` never approves;
   any byte change makes the page `approval-stale`. `approve --revision`
   takes the sha256 from `read --json` (`cli.py` line 315). A candidate
   pattern is a pending proposal (`propose --from DIR`, `cli.py` line
   489), promotion is lint-gated, and approval is a separate step. No
   new verb is needed to carry a pattern from candidate to approved.
6. **Supersession already exists end to end.** `superseded_by` must
   name a live page (lint), `find` and `query` treat a superseded page as
   ineligible (`discovery.py` line 278), and `findings` reports
   `superseded-still-indexed`. A pattern replaced after an API change is
   expressible today.
7. **A changed source does not mark a page.** `_check_stale_claims`
   (`health_lint.py` lines 110-120) checks that a cited `path:` exists,
   and says it does not compare `sha:` with git and does not fetch URLs.
   A pattern whose canonical helper changed in place stays clean. This
   is the gap memkernel #57 found on its side (a `decision` citing a
   file was never revalidated), which memkernel #123 closed there by
   flagging and still returning the record, because hiding it would
   have hidden valid safety rules.
8. **There are deterministic pair signals, and no duplicate kind.**
   `_candidate_pairs` (`health_lint.py` lines 371-417) pairs pages that
   share a cited source path or link to each other, and feeds only the
   model-checked contradiction pass. `_check_missing_cross_links`
   (line 236) counts whole-word entity mentions, with glossary `avoid:`
   terms as aliases. The `fts5` ranker scores page text. `findings`
   (`findings.py` lines 57-82) has twelve kinds and none compares two
   pages for similarity.
9. **`find` and `query` do not report review state.** The discovery
   result carries pages, hashes and ineligible pages, not approval. An
   agent that must cite only approved patterns combines `find` with
   `review_state` (CLI `findings`, or the MCP `review_state` tool) and
   cites the revision from `read --json`. `query` answers with
   `(page, fragment)` citations checked against the prompt (`querier.py`
   line 165).
10. **Two patterns that disagree already have a form.** ADR-0004's
    `[!conflict]` callout and its three `findings` kinds mark two pages
    that disagree. "Keep two similar patterns distinct" is a different
    case: the pages agree but apply under different preconditions.
11. **memkernel's spike built the corpus #54 needs.** memkernel #57's
    `eval/decisions-57/corpus.md` holds 12 real code-copilot-team
    decisions, two per kind: reuse, native-vs-dependency,
    rejected-for-safety, stale, false-reuse-trap and conflict. Each has
    `decision`/`requirement`/`chosen`/`rejected`/`evidence`/`revisit-when`
    lines and a replay block (`later-task`, `expected`, `trap`). Four of
    the kinds are #54's examples one to one; the false-reuse traps are
    "keep two similar patterns distinct"; the conflict pair is a
    true duplicate candidate. Its research note (Q6) already says a
    decision worth trusting widely is promoted to a wiki-studio page
    whose `corrects:` replaces the runtime record, and that governed
    import keeps title and body (ADR-0004, "memkernel round trip").
12. **The coordination issues are closed.** #38 (closed 2026-10-30),
    #51 (closed 2026-10-28) and memkernel #48 are done. The issue's
    "compatibility" criterion reduces to: the spike changes none of their
    contracts (revision preconditions, containment, citations, locking,
    receipts, human gates).
13. **The eval tree is where measured evidence lives.** `eval/navigation`
    holds frozen runs, a preregistered held-out protocol
    (`heldout/protocol.md`) and a runner,
    `python -m eval.navigation.discovery run --fixture DIR --shared DIR`,
    that reads `gold.json`, `questions.json` and `wiki/` and reports hit
    at 1 and 5 per ranker with no backend. `eval/composition/` is a
    design-only document with a drafted successor issue beside it, the
    precedent for "recommend, and file the feature as a new issue". Ruff
    covers `eval/`; coverage is measured on `wiki_studio` only.
14. **Packaged schema documents ship only in a release; `docs/` does
    not wait.** `src/wiki_studio/schema/page-types.md` reaches users and
    every ingest prompt only through a release. A `docs/` page is live
    on GitHub at merge. CLAUDE.md requires every command a user-facing
    page shows to be checked, and every `pip install` line to join the
    `quickstart-memkernel` job.
15. **This repository has no wiki of its own.** The real pattern
    material is code-copilot-team's (its `knowledge/wiki` has about 20
    content pages, two of them decisions) and memkernel #57's corpus.

## Appetite

**2w** (D1), one cycle, cycle 08. The work content for an LLM executor
is about 12-17 hours across six scopes:

| Scope | Estimate |
|-------|----------|
| S1 Inventory and the fit map | 1.5-2h |
| S2 The pattern corpus | 3-4h |
| S3 The lifecycle trace and retrieval | 2-3h |
| S4 Duplicate candidates on labelled pairs | 2.5-3.5h |
| S5 Revisit signals | 1-1.5h |
| S6 Recommendation, guidance and closure | 2-3h |

No package code changes. The code outputs are small scripts under
`eval/patterns/` (the trace recorder, the duplicate-candidate script, the
staleness check), not shipped in the wheel, plus one test that runs them
on the fixture. Everything else is documents: the fixture pages, the
protocol, the report with the recommendation and, if the recommendation
is docs and a template, `docs/patterns.md`.

Why not 4w: a spike that needs more than two weeks is building a
feature, which the issue puts out of scope. Why not less: the review
gate needs rounds on the pitch, the spec and the evidence PR, and the
labels must be frozen in a commit before the duplicate run, which fixes
an order the work cannot compress.

Planned order:

- **Week 1:** S1; S2's pages, lint-clean; S4's labels and thresholds
  frozen in their own commit; S3's trace and retrieval run. Check
  triggers 1 and 2.
- **Week 2:** S4's run; S5; S6. The evidence PR goes to review. Check
  trigger 3.

## Solution shape

A study under `eval/patterns/`, with no change to the package:

```
eval/patterns/
  README.md          the protocol: corpus, pins, labels, thresholds, what is and is not measured
  wiki/              the fixture wiki: index.md, log.md, decisions/<pattern>.md, background pages
  labels.json        candidate pairs and their dispositions, frozen before S4 runs
  questions.json     one later-task question per pattern, from the corpus replay blocks (S3)
  trace.py           records propose → lint → promote → approve → find → read → edit → supersede (S3)
  duplicates.py      model-free candidate pairs from the signals in finding 8 (S4)
  staleness.py       cited path + sha vs the pinned source tree, by git (S5)
  results/*.json     each run's output, as recorded
  report.md          the answers to the six questions, the overhead table, the recommendation (S6)
docs/patterns.md     only if the recommendation is "docs and a template" (D2)
```

**A pattern is a `decision` page (D3).** The spike writes each example as
an existing `decision` page, with an optional convention inside the four
existing sections and no new H2 (finding 4): Decision opens with a
one-line statement ("In the context of …, we chose … over …, because
…", memkernel #57's Y-statement, which fits its 200-character preview);
Context carries "Applies when" and "Does not apply when" lines;
Alternatives considered names each rejected option and why; Consequences
carries "Revisit when". The canonical implementation and its tests are
`sources:` entries with `sha:`. The spike tests whether this convention
earns its place; "no convention" is an allowed outcome.

**The trace (S3)** runs the real verbs on a temporary copy of the fixture
with the test backend, so nothing calls a model and nothing writes into
`eval/`. It shows what happens and what does not: a candidate is a
pending proposal; promotion is lint-gated; approval binds the reviewed
bytes; `find` returns the pattern for its later-task question; an edit
makes the approval stale; a superseded pattern drops out of `find`; a
changed source marks nothing (finding 7).

**Duplicates (S4)** are candidate pairs from model-free signals, compared
with dispositions labelled and frozen before the run: redundant (merge
candidate), distinct by precondition, conflicting (a `[!conflict]` case)
and unrelated. The output is a table of true and false positives per
signal. Nothing merges, prunes or edits a page.

**The recommendation (S6)** answers each of the six questions with the
evidence, tabulates overhead, assesses approval, audit, revision,
citation, containment and rollback, and ends in one of the issue's three
outcomes. A proposed enhancement (for example a `findings` kind or a
revision-aware stale check) is drafted as a new issue's text beside the
report, not built.

## Scopes

Build order: S1 first. S2 before S3, S4 and S5. S4's labels are frozen
before S4 runs. S6 last.

### S1: Inventory and the fit map, ~1.5-2h

- **The map.** A table in `eval/patterns/README.md`: each of #54's seven
  fields (intent, applicable constraints, canonical implementation link,
  rejected alternatives, validation evidence, owner/status, revisit
  criteria) against where it can live today (finding 2), what checks it
  (lint, prose lint, `findings`, approval: finding 1, 5) and what reaches
  memkernel (title, body, scalars, `sources:`: finding 3, 11). The
  "owner" row says what exists (the approver in the record, `--by`) and
  what does not.
- **The behaviour inventory.** One paragraph each, with file and line:
  page types, propose and promote, approval and review state,
  citations, lint and health lint, `findings`, discovery, supersession,
  conflict callouts. Taken from findings 1-10, rechecked at the pinned
  commit.
- **Compatibility.** One short section: #38, #51 and memkernel #48 are
  closed, the spike changes none of their contracts, and memkernel #57
  and #123 are the runtime side (finding 11, 12).

### S2: The pattern corpus, ~3-4h

- **Pages (D5).** memkernel #57's 12 records rewritten as `decision`
  pages under `eval/patterns/wiki/decisions/`, in the S1 convention, each
  citing its code-copilot-team evidence by `path:` and `sha:` at the
  pinned commits the corpus records, plus `issue:`/`pr:` entries. Five
  are marked as #54's examples: reuse a helper (trace archive reuses
  `redact_text`), native feature over a dependency (stdlib rows API, not
  Parquet), reject a shorter solution that weakens safety (never bypass
  a git lock with an alternate index), supersede after a change (the
  benchmark UI record and a successor page with `superseded_by`), keep
  two similar patterns distinct (config redaction is not free-text
  redaction, against the trace archive page). The other stale record
  gets its successor too, so the corpus is 14 pages.
- **Background (D5).** A copy of code-copilot-team's `knowledge/wiki`
  content pages at one pinned commit, so duplicate candidates and
  retrieval face same-domain pages that are not patterns. Its `schema/`
  directory is not copied.
- **Checks.** `wiki-studio lint` passes on the fixture (a test). The
  pages pass prose lint where it applies. The README records each
  page's source record, pin and conversion time (overhead, S6).

### S3: The lifecycle trace and retrieval, ~2-3h

- **The trace.** `eval/patterns/trace.py` copies the fixture to a
  temporary directory, runs `init`, `propose --from` with one candidate
  pattern drafted from a memkernel-style decision record, `lint`,
  `promote`, `read --json`, `approve --revision`, `findings`, `find`,
  then an edit (approval goes stale), then a promote that supersedes the
  pattern (it leaves `find`; `superseded-still-indexed` until the index
  line moves), and a cited-file change (nothing reports it). Each step's
  command, exit code and the relevant output lines go to
  `results/trace.json`. `--by` names one agent on propose, promote and
  approve, as the persona does.
- **The evidence checklist.** What a candidate must carry before a
  curator promotes it, tested against the five examples: the canonical
  implementation (`path:` + `sha:`), at least one test or verification
  outcome, the originating spec, issue or PR, the rejected options with
  reasons, and a revisit trigger. A missing item is a reason to send the
  proposal back, by persona guidance, not by code.
- **Retrieval.** One question per pattern from its corpus `later-task`
  line, run through `find --json` with both rankers at five pages,
  through the existing runner if the fixture fits its format, else a
  short loop over `api.find` (rabbit hole). Recorded: hit at 1 and 5 for
  the pattern page; for each false-reuse trap, whether the trap page
  outranks the right one; for each superseded pattern, that the
  successor is returned and the old page is ineligible.
- **Citing without binding.** The report shows the sequence an agent
  uses (finding 9): `find`, then `review_state` to keep approved pages,
  then `read --json` to cite path and sha256, then the "Applies when /
  Does not apply when" lines checked against the task. It names the
  cases in the corpus where the pattern must not be reused.

### S4: Duplicate candidates on labelled pairs, ~2.5-3.5h

- **Labels first.** `labels.json` lists the pairs the corpus annotations
  identify (the conflict pair, the two false-reuse traps against their
  look-alikes, each stale record against its successor) plus every pair
  any signal could produce on the fixture, each with a disposition:
  redundant, distinct-by-precondition, conflicting, unrelated. Labels,
  the signals and their thresholds land in one commit before
  `duplicates.py` runs, as the held-out protocol did (finding 13). A
  label is never changed after the run; a disagreement found later is
  reported, not edited.
- **Signals (D4).** In `eval/patterns/duplicates.py`, model-free, reading
  the fixture: (a) shared cited source path or a direct link, the
  `_candidate_pairs` rule; (b) overlap of title and Decision-line tokens
  under the querier's token pattern and stop list; (c) shared entity
  mentions with glossary aliases, as `missing-cross-link` counts them.
  It imports from `wiki_studio` read-only and writes only
  `results/duplicates.json`.
- **Output.** Per signal and combined: candidate pairs, true and false
  positives against the labels, the labelled redundant pairs missed, and
  each pair's disposition as a reviewer would record it. The
  superseded pages are excluded as `find` excludes them, and the report
  says how many pairs that removes.

### S5: Revisit signals, ~1-1.5h

- **The measurement.** `eval/patterns/staleness.py` takes a local
  code-copilot-team checkout and, for each pattern's `path:` + `sha:`,
  reports whether the file exists at a later pinned commit and whether
  it changed since `sha` (`git diff --quiet sha..later -- path`). It is
  run by hand once, like the held-out run; its output is committed to
  `results/staleness.json`. No test runs it (it needs the checkout).
- **The comparison.** For each pattern: what `stale-claim` reports
  today (path existence only, finding 7), what the revision check
  reports, and whether the pattern really needs review (the corpus
  `revisit-when` line against the change). The report states the false
  flags as memkernel #57 did, and whether "flag, still return" (#123's
  rule) fits the wiki: a flagged page stays approved and eligible, and a
  finding asks for a review.
- **Spec and test changes.** The report says which of #54's triggers
  (changed source, new spec revision, security finding, failed test) a
  `sources:` entry can carry today, and which none can.

### S6: Recommendation, guidance and closure, ~2-3h

- **`eval/patterns/report.md`.** The six questions, each answered with
  the evidence and its limits; the overhead table (pages written, words
  per page against the memkernel record, conversion time, retrieval
  hits, false candidate pairs, false staleness flags); the assessment of
  approval, audit, revision, citation, containment and rollback; and
  the recommendation, one of the issue's three outcomes, with what is
  not measured (whether an agent chooses better with patterns in reach).
- **`docs/patterns.md` (D2).** Written only if the recommendation is
  docs and a template: the `decision` page template for a pattern, the
  evidence checklist, the find-then-review-state-then-read sequence, the
  revisit guidance, and what memkernel keeps (D6). Every command it
  shows is checked by a test against the fixture (CLAUDE.md); a `pip
  install` line, if any, joins the `quickstart-memkernel` job.
- **Follow-ups.** Each proposed enhancement is drafted as an issue text
  under `eval/patterns/` (as `eval/composition/successor-issue.md`), and
  filed by the owner. Candidates the spike may reach: a revision-aware
  stale check, a candidate-duplicate `findings` kind, the template in
  the packaged `page-types.md`, a persona paragraph.
- **The test and the changelog.** One test runs `duplicates.py` and the
  retrieval loop on the fixture and checks their output matches the
  committed results, and lints the fixture. `CHANGELOG.md` `[Unreleased]`
  gets one Docs line if `docs/patterns.md` ships (D7). No version bump.
- **Closure (D8).** The evidence PR closes #54 when the report is
  published. The pitch PR uses no closing keyword.

## Rabbit holes

- **Citations that point outside the fixture.** Pattern pages cite
  code-copilot-team paths, which do not exist under this repository's
  root, so `stale-claim` flags every one. *Workaround:* the fixture is
  measured with that expectation stated; S5 runs against a local
  code-copilot-team checkout by hand, and CI never needs it. No
  `--source-root` change and no network.
- **The existing discovery runner may not fit.** It expects a corpus,
  a stop list and grep negative-control inputs shaped for the navigation
  runs. *Workaround:* use it if `--fixture`/`--shared` accept the
  pattern fixture as is; otherwise a twenty-line loop over `api.find`.
  The runner is never edited.
- **Labels that drift toward the result.** With a small corpus, it is
  easy to relabel a pair once a signal "obviously" got it right.
  *Workaround:* labels and thresholds are committed before the run
  (S4), and the evidence PR keeps one commit per step and is never
  squashed, as the 0.8.0 evidence PR was.
- **A convention that grows into a schema.** "Owner", "status" and
  "revisit" invite frontmatter keys. *Workaround:* the spike writes them
  as body lines in existing sections only; a key is a recommendation
  for an ADR, not something the fixture adopts (finding 3).
- **Measuring agent benefit.** "Does an agent reuse better with
  patterns" needs agent runs at historical commits. *Workaround:* out of
  scope, named as unmeasured, as memkernel #57 named it. #75 is the
  measurement issue.
- **Overlap with `nightly` (0.10.0).** Its report lists `findings`, so a
  duplicate kind would show up there. *Workaround:* none needed. The
  spike reads `findings` as it is on main and depends on nothing in
  0.10.0 (D9). A follow-up issue for a `findings` kind notes that the
  `nightly` report would carry it.

## No-gos

- No change under `src/wiki_studio/`: no verb, flag, exit code, MCP tool,
  `findings` kind, lint rule, prompt, persona or packaged schema document.
- No page-schema change: no frontmatter key, page type or directory, no
  `schema.version` or `findings_version` change, and no ADR (D2).
- No automatic merge, prune, rewrite, promote or approve of any page, in
  the fixture or anywhere.
- No semantic or embedding similarity, no model in any signal, and no
  runtime dependency; `eval/patterns/` scripts use the standard library
  and `wiki_studio`.
- No network access in a test; S5's git run is by hand and recorded.
- No edit to memkernel, code-copilot-team, `eval/navigation`'s frozen
  runs or the frozen persona copy. A memkernel recommendation is text in
  the report (D6).
- No claim that patterns improve agent outcomes.
- No release of its own (D7).

## Decisions

The owner **decided D1-D8** on 2026-11-17 in the main session, each by
the recommended default. Each item keeps the default, its reason and the
alternatives, so the record shows what was weighed. D9-D11 are *settled* by the
issue, the owner's sequencing or the repository's evidence practice, and
are listed so the spec does not reopen them.

- **D1. Appetite (decided by the owner, 2026-11-17: the default).**
  Owner, 2026-11-17: the default, 2w for cycle 08. The default was **2w, cycle 08.** The work content
  is 12-17 hours; the two weeks hold the review rounds and the
  labels-before-run order. Alternative: **4w**, if the owner wants a
  prototype `findings` kind or a revision-aware stale check built inside
  the spike, which turns it into a feature and needs its own spec
  questions.
- **D2. Where the deliverable lives (decided by the owner, 2026-11-17:
  the default).** Owner, 2026-11-17: the default, the `eval/patterns/`
  study, `docs/patterns.md` only if recommended, no ADR. The default was **a study under
  `eval/patterns/` (fixture, labels, scripts, results, `report.md` with
  the recommendation), plus `docs/patterns.md` only if the
  recommendation is docs and a template; no ADR.** No schema changes, so
  CLAUDE.md asks for no ADR, and the eval tree is where measured
  evidence lives (finding 13). Alternatives: (a) also an ADR-0005
  recording the recommendation, as a decision record even without a
  schema change; (b) `docs/patterns.md` only, with the evidence inside
  it; (c) a `docs/research/` note, as memkernel did.
- **D3. Which page type a pattern uses (decided by the owner,
  2026-11-17: the default).** Owner, 2026-11-17: the default, the
  `decision` type with an optional convention in its existing sections.
  The default was **the
  existing `decision` type, with an optional body convention inside its
  four sections (Y-statement first line; "Applies when" / "Does not
  apply when" in Context; "Revisit when" in Consequences; evidence as
  `sources:` with `sha:`), and no new H2.** The four sections already
  map to six of the seven fields (finding 2), lint is unaffected
  (finding 1), and ADR-0004 rejected a new H2 for the same kind of
  convention (finding 4). The spike may conclude that plain decision
  pages are enough. Alternatives: (a) no convention, plain decision
  pages; (b) `concept` or `workflow` pages for patterns that are
  procedures; (c) a `pattern` page type, which the issue puts out of
  scope before evidence.
- **D4. What the duplicate heuristic is (decided by the owner,
  2026-11-17: the default).** Owner, 2026-11-17: the default, a
  throwaway eval script with the preregistered bar. The default was **a
  throwaway script, `eval/patterns/duplicates.py`, not shipped; if a
  signal earns its keep, the recommendation drafts a new issue for a
  `findings` kind.** The issue forbids a compulsory service and asks
  for evidence first. "Earns its keep" is fixed in the frozen protocol
  before the run; the default bar is that the signal finds every
  labelled redundant and conflicting pair with no more false candidate
  pairs than true ones on the fixture. Alternatives: (a) prototype it as
  a `findings` kind in the package (package change, release, D1's 4w);
  (b) no heuristic, a manual review of the corpus only.
- **D5. The corpus (decided by the owner, 2026-11-17: the default).**
  Owner, 2026-11-17: the default, memkernel #57's 12 records, two
  successors and code-copilot-team's wiki as background. The default was **memkernel #57's 12 real
  code-copilot-team records rewritten as `decision` pages, plus a
  successor page for each of the two stale records (14 pages), five of
  them marked as #54's examples, plus code-copilot-team's
  `knowledge/wiki` content pages at one pinned commit as background.**
  The records are real, already labelled by kind and replay, and cover
  #54's five cases (finding 11); this repository has no wiki (finding
  15). Alternatives: (a) only the five examples, no background (smaller,
  and too few pairs for a duplicate measurement); (b) synthetic pages;
  (c) new examples from other repositories.
- **D6. memkernel (decided by the owner, 2026-11-17: the default).**
  Owner, 2026-11-17: the default, memkernel untouched, with the
  recommendation in the report. The default was **not touched; the report says what
  memkernel should keep to point at a pattern** (the page's `page_id`,
  wiki path, the approved revision's sha256 from `read --json`, its
  Y-statement first line, and `corrects:` on the wiki page naming the
  runtime record it replaces, as memkernel #57's Q6 says), **and the
  owner may comment on memkernel #57 or open a memkernel issue from
  it.** The issue puts memkernel policy out of scope. Alternative: a
  drafted memkernel issue text beside the report.
- **D7. Release (decided by the owner, 2026-11-17: the default).**
  Owner, 2026-11-17: the default, no release of its own. The default was **no release of its own.** Nothing in
  the wheel changes. If `docs/patterns.md` ships, it is live on GitHub
  at merge and gets one `[Unreleased]` Docs line that rides the next
  release (0.10.0 or later). A follow-up that edits packaged documents
  gets its own release. Alternative: a docs-only patch release.
- **D8. How #54 closes (decided by the owner, 2026-11-17: the
  default).** Owner, 2026-11-17: the default, the evidence PR closes #54
  when the report is published. The default was **the evidence PR closes #54
  when `report.md` is published, whatever its outcome; each proposed
  enhancement becomes a new issue, filed by the owner from the drafted
  text.** The issue's deliverable is the recommendation. The pitch PR
  uses no closing keyword. Alternative: #54 stays open until the
  follow-up issues are filed, or until a docs release carries
  `docs/patterns.md`.
- **D9. No dependency on 0.10.0 (settled).** The spike runs on main as
  it stands at cycle 08's start and uses no `nightly` code or report.
  If 0.10.0 has shipped by then, the report notes it; nothing waits on
  it, and nothing in it is reopened.
- **D10. No package code and no schema change (settled).** The issue
  puts a new schema, a page type and a compulsory dedup service out of
  scope. The spike's code is under `eval/patterns/` only.
- **D11. Labels before the run (settled).** S4's labels and thresholds
  are committed before its run and never changed after, as the held-out
  protocol and the 0.8.0 evidence PR did.

## Circuit breaker

Core is S1 (the fit map), S2's five issue examples as lint-clean
decision pages, S3 (the trace and retrieval) and S6 (the recommendation,
published with whatever was measured and labelled as such). S4 and S5
are the measured parts and shrink before they are cut.

The cut order, first to last, each with its trigger:

1. **End of week 1, if S2 is not done:** drop the code-copilot-team
   background pages and the remaining corpus records; keep the five
   issue examples plus the two pages the stale case needs (D5).
2. **Start of week 2, if S4's labels and thresholds are not frozen:**
   S4 measures only the existing signal (shared cited source or direct
   link) on the labelled pairs, with no new signal.
3. **Middle of week 2, if S5 has not run:** S5 becomes the analytic
   statement from the code (finding 7) with no git run, and the report
   says it was not measured.

- **End of week 2.** S6 publishes what is true, every unmeasured
  question named as unmeasured. #54 closes by D8 only when the
  recommendation is published.
- **Never, to save time:** change anything under `src/wiki_studio/`;
  change the page schema, `findings`, `findings_version`, lint, an exit
  code or an MCP tool; add a runtime dependency or a network fetch to a
  test; set or change a label or threshold after its run; merge, prune,
  approve or rewrite a page automatically; claim that patterns change
  agent behaviour; edit memkernel, code-copilot-team or the frozen eval
  copies; weaken or skip a test.

"Exhausted" means two working weeks have passed. A third review round
on the evidence PR is an escalation to the owner, who chooses a fix
session, a cut from the list above, or a hold.

## Questions for the owner

Asked by the main session on 2026-11-17; all answered, each by the
default. D1 2w for cycle 08; D2 the `eval/patterns/` study, with
`docs/patterns.md` only if the recommendation is docs and a template, and
no ADR; D3 a pattern is a `decision` page with an optional convention
inside its four existing sections and no new H2; D4 the duplicate
heuristic is a throwaway eval script, with the preregistered bar for
drafting a `findings` kind issue; D5 memkernel #57's 12 records, a
successor for each of the two stale records, and code-copilot-team's
wiki content pages as background; D6 memkernel untouched, the report
says what memkernel should keep; D7 no release of its own, one
`[Unreleased]` Docs line if `docs/patterns.md` ships; D8 the evidence PR
closes #54 when the report is published, and each proposed enhancement
becomes a new issue.

## Bet log

| Date | bet_status | Note |
|------|------------|------|
| 2026-11-17 | shaping | Pitch drafted from wiki-studio #54 (no comments) and cooldown-after-06 (owner, 2026-11-16: #54 shaped next, for cycle 08). wiki-studio read at main cb7fc6d: `page-types.md`, `lint.py`, `prose_lint.py`, `health_lint.py`, `findings.py`, `review.py`, `discovery.py`, `querier.py`, `cli.py`, `mcp_adapter`, ADR-0004, `eval/navigation`, `eval/composition`, pitch 70 and the 0.10.0 spec. memkernel read at main 87bbd04: #57's research note and `eval/decisions-57/corpus.md`; #57 and #123 closed. #38, #51 and memkernel #48 closed. |
| 2026-11-17 | shaping → shaped | 6 scopes, 2w, work content 12-17h, no package code. Core: S1, S2's five examples, S3, S6. Cut first: the background pages, then S4's new signals, then S5's git run. 11 decisions; D1-D8 open for the owner with defaults, not yet asked (AskUserQuestion was unavailable to the shaping agent). |
| 2026-11-17 | shaped (decided) | Owner answered D1-D8 in the main session (2026-11-17), every one by the default: 2w for cycle 08; the `eval/patterns/` study, `docs/patterns.md` only if recommended, no ADR; `decision` pages with an optional convention in the existing sections; a throwaway duplicate script with a preregistered bar; memkernel #57's 12 records plus two successors plus code-copilot-team's wiki as background; memkernel untouched; no release of its own; the evidence PR closes #54. The main session verified findings 1, 7 and 11 (no H2 rule in `lint.py`; `_check_stale_claims` checks path existence, not `sha:`; memkernel #57 closed 2026-11-11 with `eval/decisions-57/corpus.md`, 12 records, two per kind). Updated: Decisions (intro, D1-D8), Questions for the owner (answered). Scopes, circuit breaker and appetite unchanged. |
| 2026-11-18 | bet | Bet for cycle 08. |
| 2026-11-18 | building | Cycle 08 started; hill chart initialized. |
| 2026-11-22 | shipped | Cycle 08 closed. The research spike merged in build PR #117 (merge 25b9e13; issue 54 closed by it), with no release (no package code). Recommendation: docs and a template (docs/patterns.md); three follow-up issue drafts in eval/patterns/issues/. Spec PR #115, approval PR #116. The driver passed all seven steps in one review round each; step 2's first review was inconclusive (a 4,041-line diff against the 500-line review view) and passed on a rerun at 6,000 lines; the run cost $157.63 against the $150 cap. Four owner-side commits after the build were reviewed externally. All six scopes done; the hill was not updated during the cycle (auto-build driver), set to done at close. |
