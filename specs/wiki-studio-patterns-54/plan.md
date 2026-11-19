---
spec_mode: full
feature_id: wiki-studio-patterns-54
risk_category: research
justification: "A research spike with no package change, but its value rests entirely on measurement discipline: labels and gold frozen in their own commit before any signal runs, a corpus and a background pinned to exact bytes in two other repositories, deterministic committed results that tests reproduce, an FTS5-dependent ranker, a by-hand git run against a sibling checkout, a conditional user-facing doc whose commands must be checked, and an evidence PR that closes an issue; a full spec pins the protocol, the per-phase truth rule and the cut order before an unattended build."
status: approved
date: 2026-11-18
collaboration_mode: single
origin:
  issue: 54
  urls:
    - https://github.com/gosha70/wiki-studio/blob/main/specs/pitches/54-reusable-patterns/pitch.md
    - https://github.com/gosha70/wiki-studio/issues/54
    - https://github.com/gosha70/wiki-studio/pull/110
    - https://github.com/gosha70/wiki-studio/pull/114
    - https://github.com/gosha70/memkernel/issues/57
    - https://github.com/gosha70/memkernel/issues/123
    - https://github.com/gosha70/memkernel/blob/v0.9.0/eval/decisions-57/corpus.md
    - https://github.com/gosha70/code-copilot-team/issues/389
    - https://github.com/gosha70/wiki-studio/blob/main/specs/retros/cooldown-after-06.md
  origin_claim: |
    Issue 54 (no comments on 2026-11-17), shaped by the bet pitch
    specs/pitches/54-reusable-patterns/pitch.md (cycle 08, building; reviewed
    in PR #110, merged 9178147; bet and cycle start PR #114 at 5d2eb5d) from
    specs/retros/cooldown-after-06.md (owner, 2026-11-16: #54 shaped next,
    for cycle 08). Related: gosha70/memkernel#57 (closed, the runtime-side
    spike and its corpus), gosha70/memkernel#123 (closed), and
    gosha70/code-copilot-team#389 (open). The issue, as the pitch states it,
    is a research spike: its deliverable is a recommendation ("docs and
    templates only, a separately specified enhancement, or no change"), not a
    schema, a page type or a deduplication service. It asks six questions:
    can current pages hold a pattern; how does an agent propose one and what
    evidence must promotion see; how does an agent find and cite approved
    patterns without treating them as binding; can existing lint, query or
    findings expose near-duplicates without merging anything; how does a
    source or spec change mark a pattern for review; and what should
    memkernel keep to point at one. Owner decisions D1-D8 (2026-11-17, each
    by its default): 2w for cycle 08; an eval/patterns/ study with
    docs/patterns.md only if it recommends a template, no ADR; a pattern is
    a decision page with an optional convention inside its four existing
    sections and no new H2; the duplicate heuristic is a throwaway eval
    script with a preregistered bar ("finds every labelled redundant and
    conflicting pair with no more false candidate pairs than true ones on the
    fixture"); the corpus is memkernel #57's 12 records plus a successor for
    each of the two stale records plus code-copilot-team's wiki as
    background; memkernel untouched; no release of its own; the evidence PR
    closes issue 54 when the report is published and each proposed
    enhancement becomes a new issue. Settled: D9 no dependency on 0.10.0;
    D10 no package code and no schema change; D11 labels and thresholds
    committed before the run and never changed after. The #114 reviewer's
    four notes: label all 91 pattern pairs before any signal runs, a flagged
    background pair false unless the corpus annotations say otherwise; report
    the counts behind the pass bar, a pass being grounds to draft an issue
    and not general evidence; pin the corpus to a memkernel tag or commit and
    sha256 and code-copilot-team's wiki to a commit; skip the fts5 ranker
    where SQLite lacks FTS5, as the repository's other FTS5 tests do.
---

# Plan: reusable engineering patterns, a research spike (issue 54)

The bet pitch `specs/pitches/54-reusable-patterns/pitch.md` is the shaping
record (reviewed on PR #110, merged 9178147; owner decisions D1-D8 on
17 November 2026; bet and cycle 08 start PR #114 at 5d2eb5d). Its "Findings
from the code" were re-checked against `main` 427f6ce (0.10.0 released) on
18 November 2026 with current line numbers (spec, design references):
findings 1 (`lint.py` has no section rule; `sources:` presence 372-373),
2 (`page-types.md` `decision` 104-121), 5 (approval bound to bytes,
`review.py` 1-21; `approve --revision` now at `cli.py` 315-320, `propose
--from` at 550), 6 (`discovery.py` 278), 7 (`health_lint.py` 110-155), 8
(`_candidate_pairs` 371-417, `_check_missing_cross_links` 236-315,
`FINDING_KINDS` 70-83), 9 (`read --json` at `cli.py` 580-584) and 13 (the
eval tree; ruff covers `eval/`, coverage `wiki_studio` only) hold. The
issue's body was not re-fetched while this bundle was written (no shell or
network in the writing session); its words are taken from the pitch, and
the origin-alignment record at approval reads the issue itself. Facts found
while re-checking that shape the spec:

1. **Prose lint's sentence limit is shorter than the corpus's
   Y-statements.** `lint --prose` limits a sentence to 25 words
   (`schema/__init__.py` 119, `prose_lint.py` 22-27); every corpus
   `decision:` line runs to roughly 35-45 words. The pitch asks that pages
   pass prose lint where it applies and that Decision open with a one-line
   statement; both cannot hold. The owner chose to split so pages pass
   (Q3). The PR #115 reviewer measured that two sentences still leave five
   opening sentences over 25 words with `prose_lint.count_words` (618-620),
   and that a three-sentence form stays at 24 or fewer for all 12 records;
   FR-008 uses it and records the sentence count.
2. **Discovery sees only pages `index.md` links.** `discovery.py` 4-7 and
   410-424: the candidates are the index's intra-wiki links, so a page the
   index does not link is never considered, and its ineligibility can never
   be observed. Every page the retrieval measures, the two superseded pages
   included, is index-linked (FR-010, owner, 2026-11-18), so `findings`
   reports `superseded-still-indexed` for those two on the fixture
   (findings.py 157-184), as expected.
3. **The `fts5` ranker writes a cache beside the wiki.** The search cache
   defaults to a file beside the wiki's lock (`paths.py` 131-133, 389-391),
   so `find` on `eval/patterns/wiki` in place would write next to it under
   `eval/`. Retrieval and the trace run on temporary copies (FR-017, FR-018).
4. **`stale-claim` resolves cited paths against the project root.**
   `health_lint.py` 141 builds `paths.root / cited_path`, so every
   code-copilot-team path on the fixture is flagged (the pitch's rabbit
   hole). The trace creates a file at its page's cited path inside its own
   root, to show the existence check passing and a changed file staying
   unreported (FR-017).
5. **The discovery runner does not fit.** It needs a `corpus/` and a
   `stopwords.txt` for its grep negative control
   (`eval/navigation/discovery.py` 199-221), shaped for the navigation runs.
   The pitch's fallback applies: a short loop over `api.find` in
   `retrieval.py` (FR-018); the runner is not edited.
6. **How eval code is checked and shipped.** Tests import eval modules and
   private `wiki_studio` names (`tests/test_discovery_eval.py` 27-33). The
   gate runs ruff on `eval/` (`ci.yml` 31-33) but mypy on `src/` only (46)
   and coverage on `wiki_studio` only (67-69). The wheel packages
   `wiki_studio` only (`pyproject.toml` 27-31), so nothing under `eval/`
   ships; `tests/test_package_boundaries.py` scans the package and not
   `eval/` (46, 78) and needs no change. The audit checks `pyproject.toml`
   is unchanged (FR-034).
7. **The FTS5 skip pattern.** `tests/test_discovery.py` computes
   `HAS_FTS5 = discovery.fts5_available().available` (44), skips a class with
   `@unittest.skipUnless(HAS_FTS5, "this Python's SQLite has no FTS5")` (195)
   and skips the `fts5` ranker inside a per-ranker loop (271);
   `tests/test_search_index.py` does the same (43, 98). FR-021 follows it.
8. **The corpus's annotations define the gold.** Each record's `seed:` line
   names the pages a later task needs: "this record", "this record and the
   superseding record" (or "the correction"), "this record and its
   partner", "this record and the trace-archive reuse record". The clusters
   trap names no look-alike page, so it has no trap page (FR-013). The
   git-lock record names a background page as evidence
   (`knowledge/wiki/incidents/git-safety-bypasses.md`), the one annotated
   background pair the corpus gives (FR-012).
9. **The background needs a link rule and one exclusion.** Of
   code-copilot-team's 21 `.md` pages at the pin (verified by the PR #115
   reviewer; non-page files such as `open-questions/.gitkeep` and
   `scripts/lint-wiki.sh` are not copied), many carry `../`
   links, some leaving the wiki or pointing into `schema/`, which structural
   lint would reject inside this repository (`lint.py` 13-21). They are
   rewritten to GitHub URLs at the pin (FR-009). `playbooks/pre-pr-close-keyword-audit.md`
   quotes closing-keyword phrases, which no file of this PR may
   carry; it is not copied (FR-009, Q4).
10. **Pins (verified by the PR #115 reviewer).** memkernel's CHANGELOG at
    tag `v0.9.0` has the `[0.9.0]` heading at line 9 and the
    `eval/decisions-57/` line at 60; `v0.9.0` is tag object `d427381` on
    commit `7f26012`; `corpus.md` there hashes to `10e61af7…ca503`, holds 12
    records, and every `seed:` line is in one of FR-013's four forms.
    memkernel 0.10.0 (released 18 November 2026) has no local tag and is not
    needed. For code-copilot-team the pitch read `00d49c0`, an ancestor of
    `master` `8f287f1`; all 12 commits the corpus cites are ancestors of the
    pin. The build re-verifies both (FR-005).
11. **The freeze has a precedent.** `tests/test_frozen_runs.py` pins frozen
    eval files by sha256 (50, 454); `tests/test_patterns_frozen.py` does the
    same for the labels, questions and protocol, and the git history audit
    shows they changed in one commit (FR-016, FR-034).
12. **Fixture pages carry no `page_id`; the default policy does not
    auto-approve.** `propose --from` assigns a `page_id` to pages it creates
    (page-types.md 36-39), so the trace records no sha256 value, only
    whether hashes match. `DEFAULT_POLICY` is all false (`contract.py` 67),
    so the trace's approve step is explicit.
13. **Cross-repository citations need the owner prefix.** `issue: 98` would
    name this repository's issue; `citation-rules.md` 32-33 gives
    `issue: gosha70/<repo>#<n>`. FR-006 uses it.
14. **Signal (a)'s link part would be circular** (PR #115 review). FR-006
    writes intra-wiki links exactly for corpus-annotated pairs (the conflict
    callouts and Consequences links, config-redaction and the trace archive,
    each stale page and its successor, the git-lock incident link), and
    `_candidate_pairs` fires on any direct link (`health_lint.py` 411-414),
    so (a) would find pairs the build linked from the same source as the
    labels. FR-014 reports (a)'s shared-path part as (a-path) with its own
    verdict and marks annotation-linked true pairs; FR-024 flags a verdict
    resting only on them; FR-030 says such a pass is not evidence of
    detection. Signal (c) is unaffected: it subtracts the two pages' own
    slugs, which cancels a mutual link.

## Departures from the pitch

Each is recorded so the origin-alignment record at approval can cite it.

1. **Labelling is its own phase (US3)**, before the trace (US4) and the
   duplicate run (US5), as the #114 reviewer asked: under auto-build each
   phase is one commit, so the labels and thresholds land in their own
   commit. Retrieval's gold (`questions.json`) is frozen in the same
   phase, so no gold is written after a measurement exists. The pitch's
   order (S1, S2, labels frozen, S3, then S4's run, S5, S6) is kept.
2. **All 91 pattern pairs are labelled** (reviewer note 1), replacing S4's
   "pairs the annotations identify plus every pair any signal could
   produce", which would need a signal's output before labelling (FR-012).
3. **A flagged pair involving a background page is false unless the corpus
   annotates it** (reviewer note 1, FR-012, FR-014), so background–background
   pairs count in the false column, reported by category.
4. **The pass bar reports its counts and its meaning** (reviewer note 2,
   FR-024), and is "not testable", never a pass, when no eligible pair is
   labelled redundant or conflicting (FR-014).
5. **The corpus is vendored with its sha256, and a manifest is added**
   (reviewer note 3, FR-005, FR-011). The pitch's tree has no `corpus/`
   or `manifest.json`; without the copy CI could check no pin.
6. **`retrieval.py` is its own script** (fact 5, FR-018). The pitch's tree
   lists none; S3 allowed a short loop over `api.find`.
7. **More than one test, split by phase.** S6 names one test (duplicates,
   retrieval, lint). The spec adds the fixture checks (US2), the freeze test
   (US3), the trace's reproduction (US4), the refusal on changed labels
   (US5) and a unit test of the staleness logic on a synthetic git
   repository (US6), because each phase's diff must carry its own proof. S5's
   "no test runs it" still holds: no test runs it on the checkout.
8. **The Y-statement is three sentences** (fact 1, FR-008, Q3): the
   pitch's one-line statement cannot pass prose lint. The owner chose to
   split it (Q3, two sentences); after the PR #115 review the form is three
   sentences in one paragraph, with `Chosen:` its own paragraph, and
   `manifest.json` records the sentence count in place of a split flag.
9. **The background has a link rule and an exclusion** (fact 9, FR-009, Q4).
10. **Conversion time is not measured.** S2 and S6 ask for per-page
    conversion time; an unattended build has no per-page clock. The report
    says so; words per page against the record stand in (FR-011, FR-030).
11. **The trace's candidate is a real example page.** S3 has "one
    candidate pattern drafted from a memkernel-style decision record". The
    trace removes one example page (itself drafted from a memkernel record)
    from its temporary copy and proposes it, so the candidate's content is
    real and the end state matches the fixture (FR-017). Its `find` steps use
    `index-first` so its output is the same on every SQLite; retrieval
    measures both rankers (FR-018).
12. **Successors say only what the corpus and the cited file say** (FR-007);
    the pitch does not say where their content comes from.
13. **The conflict pair carries ADR-0004's callout** (FR-006), the form the
    corpus's `partner:` line describes; the pitch does not say.
14. **Thresholds are fixed in the spec** (FR-014, Q5); the pitch leaves
    their values to the frozen protocol.
15. **`CLAUDE.md` gains one layout line** for `eval/patterns/` (FR-001), as
    each eval tree has one.

After the external review of this spec's PR #115 (head 41e62d8), the owner
decided one point and the review fixed the rest, on 18 November 2026:

16. **The superseded pages stay in `index.md` (owner).** The first draft
    left them out and made them reachable through their successors, which
    made "a superseded page is never selected" untestable, since `find`
    considers only index-linked pages (fact 2). FR-010 keeps their index
    lines; `superseded-still-indexed` reports 2 on the fixture, expected and
    tested (FR-011); retrieval exercises discovery.py 278 (FR-014, FR-018).
17. **Signal (a) is split and annotation-linked pairs are marked** (fact 14;
    FR-014, FR-023, FR-024, FR-030).
18. **Gold details.** A stale record's gold is its successor only, the stale
    page in `superseded`; the config-redaction question's gold includes its
    trap page, so a top-ranked trap counts as a hit at 1 there, and "trap
    outranks" shows it (FR-013, FR-014).
19. **An evidence item without a commit.** A test path is body text; the
    git-lock record's incident page becomes a body link to the copied
    background page, an annotation link under item 17 (FR-006).
20. **Smaller corrections.** FR-009 copies `.md` files only; FR-005's git
    allowlist names `fetch --tags` with its one condition; FR-001 no longer
    compares with `eval/navigation/__init__.py` (it is empty); the memkernel
    CHANGELOG lines are the tag's (9, 60).

Close target: issue 54, by the evidence PR's merge (`pr.closes: [54]`,
FR-035). No other issue is closed; the pitch PR (#110), the bet PR (#114)
and this spec PR use no closing keyword.

## Architecture decisions

- **ADR-1: A study, not a feature.** Everything lives under
  `eval/patterns/` plus two test modules; the scripts import `wiki_studio`
  read-only, and the package, its schema and its contracts do not move.
- **ADR-2: Freeze, then measure.** Labels, gold, signals, thresholds and
  the pass bar are one commit (US3), pinned by a test that is never edited
  after it and by the git history; the run refuses changed labels.
- **ADR-3: Deterministic, committed results.** Each script prints JSON from
  a temporary copy; the phase commits it; a test regenerates and compares
  (the `fts5` comparison only where FTS5 exists). The by-hand git run (US6)
  is the one result no test regenerates.
- **ADR-4: Each phase is true on its own diff.** The README grows a section
  per phase; the report and its recommendation exist only in US7;
  `docs/patterns.md` only with that outcome.

## Files

| File | Phase | Change |
|---|---|---|
| `eval/patterns/__init__.py` (new) | US1 | Header only |
| `eval/patterns/README.md` (new) | US1-US6 | Purpose, fit map, inventory, compatibility (US1); corpus and pins (US2); protocol (US3); trace, retrieval, checklist, citing (US4); duplicates (US5); revisit signals (US6) |
| `CLAUDE.md` | US1 | One layout line |
| `eval/patterns/corpus/decisions-57.md` (new) | US2 | memkernel's corpus at `v0.9.0`, byte for byte |
| `eval/patterns/manifest.json` (new) | US2 | Pins, pattern pages, background pages |
| `eval/patterns/wiki/**` (new) | US2 | 14 pattern pages, background pages, `index.md`, `log.md` |
| `eval/patterns/labels.json`, `questions.json`, `protocol.json` (new) | US3 | Frozen |
| `tests/test_patterns_frozen.py` (new) | US3 | sha256 pins and structure; never edited after US3 |
| `eval/patterns/trace.py`, `retrieval.py` (new) | US4 | FR-017, FR-018 |
| `eval/patterns/duplicates.py` (new) | US5 | FR-022 |
| `eval/patterns/staleness.py` (new) | US6 | FR-026 (absent under cut 3) |
| `eval/patterns/results/*.json` (new) | US4-US6 | `trace.json`, `retrieval.json` (US4); `duplicates.json` (US5); `staleness.json` (US6) |
| `tests/test_patterns_eval.py` (new) | US2, US4-US7 | FR-011, FR-021, FR-025, FR-029, FR-032, FR-033 |
| `eval/patterns/report.md` (new) | US7 | FR-030 |
| `eval/patterns/issues/*.md` (new) | US7 | FR-031 (none with the outcome "no change") |
| `docs/patterns.md` (new), `CHANGELOG.md` | US7 | Only with the outcome "docs and a template" (FR-032) |

## Interfaces

```python
# eval/patterns/trace.py, retrieval.py, duplicates.py, staleness.py — each:
def main(argv: list[str] | None = None) -> int: ...       # argparse; prints JSON, or writes --out
# trace.py
def run_trace() -> dict[str, Any]: ...                     # FR-017; temporary root, deterministic observations
# retrieval.py
def run_retrieval() -> dict[str, Any]: ...                 # FR-018; both rankers, temporary copy
# duplicates.py
def check_frozen(labels: Path, protocol: Path) -> None: ...  # SystemExit(1) when labels_sha256 differs
def run_duplicates() -> dict[str, Any]: ...                # FR-022..FR-024
# staleness.py
def check_sources(checkout: Path, pin: str, sources: list[tuple[str, str, str]]) -> list[dict[str, Any]]: ...  # (page, path, sha)
```

Commands: `python -m eval.patterns.trace [--out PATH]`,
`python -m eval.patterns.retrieval [--out PATH]`,
`python -m eval.patterns.duplicates [--out PATH]`,
`python -m eval.patterns.staleness --checkout PATH [--out PATH]`.

## Phases (one auto-build phase per `## US<n>:` group of tasks.md)

| Phase | Pitch scope | What | Main files |
|---|---|---|---|
| US1 | S1 | README purpose, fit map, inventory, compatibility; layout line | `eval/patterns/README.md`, `__init__.py`, `CLAUDE.md` |
| US2 | S2 | Pins, corpus copy, 14 pattern pages, background, index and log, manifest, fixture tests | `eval/patterns/wiki/**`, `corpus/`, `manifest.json`, `tests/test_patterns_eval.py` |
| US3 | S4 (labels) and S3 (gold) | Labels, questions, protocol; freeze test | `labels.json`, `questions.json`, `protocol.json`, `tests/test_patterns_frozen.py` |
| US4 | S3 | Trace, retrieval, checklist, citing sequence | `trace.py`, `retrieval.py`, `results/`, tests |
| US5 | S4 (run) | Duplicate signals on the frozen labels | `duplicates.py`, `results/duplicates.json`, tests |
| US6 | S5 | Staleness run, comparison, triggers | `staleness.py`, `results/staleness.json`, tests |
| US7 | S6 | Report, issue drafts, conditional docs, audit | `report.md`, `issues/`, `docs/patterns.md`?, tests |

The circuit breaker (pitch): cut 1 (end of week 1, S2 not done) keeps the
five examples and the two pages the stale case needs and drops the other
records and the background, so US3 labels the pairs among the pages that
exist (the count changes from 91 and is stated); cut 2 (start of week 2,
labels not frozen) leaves US5 with signal (a) and its (a-path) part only; cut 3 (middle of
week 2, S5 not run) is FR-029's analytic fallback. Core is US1, the five
examples, US4 and US7.

## Owner-run steps

1. Before the driver (Q1-Q5 answered 2026-11-18): review and approve this bundle; write
   `automation.json` (profile `pr`, `max_phases: 7`, `pr.closes: [54]`,
   `merge.method: "merge"`, the gate below) and the origin-alignment record
   in the approval commit. Confirm that the session can read
   `/Users/gosha/dev/repo/memkernel` (tag `v0.9.0`) and
   `/Users/gosha/dev/repo/code-copilot-team` (commit `00d49c0`); US2
   stops without them (FR-005).
2. On the evidence PR: review the labelling commit (US3) on its own (Q1);
   check the PR's commits are one per phase and the body carries the
   closing line from `pr.closes`; review and label; merge with a merge
   commit, never squash.
3. After the merge: file each drafted issue under `eval/patterns/issues/`
   (replacing its permalink placeholders), optionally comment on memkernel
   #57 with the report's D6 text; the hill chart by hand. No release
   (D7).

## Unattended run

The owner writes `specs/wiki-studio-patterns-54/automation.json` at
approval. This plan assumes 0.10.0's shape: profile `pr`, branch
`feature/wiki-studio-patterns-54` off `main`, seven phases
(`max_phases: 7`), the DeepSeek correctness reviewer gating (max 3 rounds
per phase), the test command of `specs/wiki-studio-0-10-0/automation.json`,
`pr.closes: [54]`, `merge.method: "merge"`. After the run, re-run the gate
on the branch head before trusting `landed`, and check no phase was
bypassed without a per-phase record (the known driver defects).

## Test strategy

- **The fixture is valid and traceable** (US2): structural lint on a
  temporary copy; the convention's sections and lines (the Y-statement
  paragraph's sentence count, `Chosen:` its own paragraph); no new key;
  prose lint clean on pattern pages; `superseded-still-indexed` for exactly
  the two superseded pages; the corpus copy and every background copy
  hash to their manifest entries; word counts recompute.
- **The freeze** (US3): sha256 pins in a test never edited after US3; the
  labels' structure (91 pairs, four dispositions, annotated pairs present);
  the questions' text verbatim in the corpus copy; the git history audit in
  US7.
- **Reproduction** (US4, US5): the trace, retrieval and duplicates
  regenerate their committed results; retrieval's `fts5` part skipped
  without FTS5; each records the input hashes it read.
- **No write under `eval/`**: a snapshot of `eval/patterns/` before and
  after each script.
- **Refusal**: duplicates exits 1 on a changed label in a temporary copy.
- **Staleness logic** (US6): a synthetic git repository, gated on `git`.
- **Shown commands**: every `wiki-studio …` and `python -m eval.patterns.…`
  line in the README, the report and `docs/patterns.md` parses with full
  flag spelling; `docs/patterns.md`'s commands also run in-process against
  the fixture.
- **Regression**: the existing suite untouched; coverage of `wiki_studio`
  unchanged at or above 92 percent (no package code changes).

## Risks

- **The labeller is a model that could anticipate the signals** (Q1).
  Mitigation: no signal code exists in US3 and the phase runs no overlap
  computation; the freeze test, the refusal and the history audit stop a
  later change; the owner reviews the labelling commit. Residual: a labeller
  that reasons about shared sources while labelling cannot be ruled out; the
  report says so.
- **The bar rests on few pairs** (reviewer note 2). The corpus annotates
  one conflict pair and few look-alikes; the counts are printed beside every
  verdict, and a pass only grounds a drafted issue (FR-024).
- **Links written from annotations inflate signal (a)** (fact 14). Mitigation:
  (a-path) has its own verdict, annotation-linked true pairs are marked,
  and a verdict resting only on them is flagged and not read as detection
  (FR-014, FR-024, FR-030).
- **Background pairs dominate the false column.** Linked background pages
  give signal (a) many background–background candidates, all false by rule;
  this is the honest result for a `findings` kind over a real wiki, and the
  table breaks false candidates down by category (FR-023).
- **Sibling checkouts unreadable in the session.** US2 cannot build pages
  without the pinned bytes; the build stops and reports rather than
  substituting (FR-005). Owner step 1 checks access first.
- **FTS5 rankings differ across SQLite versions.** The navigation evidence
  already reproduces across the CI matrix; the `fts5` comparison runs only
  where FTS5 exists and `ran_as` is recorded. A mismatch is reported, never
  hidden by loosening the comparison.
- **Background pages that fail lint.** A copied page that fails structural
  lint after the link rule is excluded and named (FR-009); the count of
  background pages may fall below 20.
- **A third review round on a phase.** Escalation to the owner, per the
  pitch's circuit breaker.

## Success criteria

1. `eval/patterns/report.md` answers issue 54's six questions with evidence
   and limits and ends in exactly one of the three outcomes.
2. Labels, gold, signals, thresholds and the pass bar are committed in US3,
   before any signal code, and never change after it.
3. The trace, retrieval and duplicates reproduce their committed results in
   CI (the `fts5` part where FTS5 exists); the corpus and background trace
   to recorded sha256 values.
4. Nothing under `src/wiki_studio/` changes; no schema, `findings`, lint,
   exit-code, MCP or dependency change; no release; memkernel and
   code-copilot-team only read.
5. The evidence PR keeps one commit per phase, merges with a merge commit
   and closes issue 54 through `pr.closes`; each proposed enhancement is a
   drafted issue for the owner to file.

## Open items for the spec review

Q1-Q5 were answered by the owner on 2026-11-18, every one by its default:
the build session labels (Q1); a distinct-by-precondition candidate counts
as false, in its own column (Q2); long summaries split for prose lint (Q3);
the close-keyword playbook page is not copied (Q4); the thresholds as fixed
(Q5). After the PR #115 review (head 41e62d8), Q3's split became the
three-sentence form (departure 8), and the owner kept the superseded pages
in `index.md` (departure 16).
