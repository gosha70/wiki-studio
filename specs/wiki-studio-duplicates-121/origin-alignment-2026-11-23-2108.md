# Origin alignment check — wiki-studio-duplicates-121

Gate: the bet pitch `specs/pitches/121-near-duplicate-finding/pitch.md` was
reviewed over two rounds and merged in PR #132 (f67dedd). The owner decided
D1-D10 on 2026-11-23: D2 against the default (memkernel's spec decisions join
the corpus) and D10 against the reviewer's recommendation (the shipped kind
compares same-type pairs of every content page type, with the docs saying
only decision pages were measured). Cycle 09 was closed in PR #133 (b18d852),
with the 0.11.0 release pending by the owner's choice. The bet and cycle 10
start merged in PR #134 (b05826a).

The spec bundle was reviewed on PR #135:
- **The first review** (ba6d386) requested three fixes and two small points:
  - B1's identifier rule missed most of the corpus's item labels; the owner
    chose the broader rule (plan departure 23);
  - a stopped run 2 is never resumed with a plain `--resume`;
  - every label-changing commit updates the README's true-pair count, and a
    test checks it;
  - the tag check fetches tags first;
  - the closing-keyword grep uses FR-007's full pattern.
- **The reviewer approved 37804a3.** #135 merged as 1faf70e with the files
  still `status: draft`, so this approval follows in its own PR, as for the
  last four features.
- **The owner's answers on the bundle (2026-11-23):** O1, two runs with four
  pauses; O2, a lint violation caused by an item's own text is listed, never
  fixed; O3-O12 take their defaults.

Checked on 2026-11-23 for owner step 1:
- `../code-copilot-team` holds `fd05256` and `../memkernel` holds `8279d76`,
  checked offline with `git cat-file -e`;
- `providers-health.sh --provider deepseek` reports the reviewer chain usable.

This approval commit does five things:
- sets `spec.md`, `plan.md` and the `tasks.md` marker to approved;
- applies the reviewer's two optional notes on #135:
  - departure 23 now says the broader rule drops about 164 more identifiers,
    since about 47 of the 211 the old rule kept are content words the new
    rule also keeps;
  - task 20 reads the local tag only, because the owner fetches tags before
    run 2 (owner step 7) and the session reaches no network;
- adds `automation.json` for **run 1 only**, copied from issue 120's run 2
  with these fields changed: the branch
  `feature/wiki-studio-duplicates-121-evidence`; `phases` from `tasks.md`
  with `milestone_every: 0` and `max_phases: 6`; `build.max_turns: 200`
  (O10); `review.diff_max_lines: 8000` (O10); and `pr` holding only a title,
  with no `closes`. It keeps the `pr` profile, DeepSeek as the gating
  reviewer, the gate command, two fix sessions per phase and the $150 / 12 h
  caps;
- adds this record;
- changes nothing else.

**How run 1 runs and ends.** The driver pauses at the four
`<!-- milestone -->` markers, after US1, US3, US5 and US6. At the first three,
the main session runs the scripts (extraction, then the extension rule if
needed and the review sample, then the scorer) and commits their output as
its own commits; the owner signs off and the run is resumed. Each resume
starts with `env -u CCT_REVIEW_DIFF_MAX_LINES`, and run 1 starts at step 1,
so a resume skips the finished steps. At the pause after US6, run 1 is never
resumed: the evidence PR is opened by hand after
`pre-pr-check.sh --closes none`. A resume would stop at `max_phases: 6`
before US7 and park without a PR. Run 2's settings come with the spec
amendment. Run 2 waits for the owner's own release of 0.11.0, which is not
part of this bundle.

Origin:
- **wiki-studio issue #121**, "Specify a near-duplicate finding based on
  titles and summaries" (no comments on 2026-11-23), filed by the owner from
  the issue 54 study's draft
  (`eval/patterns/issues/duplicate-title-summary-finding.md`). It asks for a
  separately specified investigation before any code:
  - re-run signal (b) on a larger, independently labelled corpus, with the
    labels frozen first;
  - settle how a decision page and its incident record are labelled;
  - only then decide whether a model-free `findings` kind is worth its false
    positives.

  The owner's preferred shape, if it passes: warn by default, silence a pair
  with a body line, an optional switch per wiki, every finding saying how to
  silence it, and findings only.
- **The issue 54 study:** `eval/patterns/report.md` (question 4 and the
  labels section), `results/duplicates.json`.

Issue 121 is to be closed only by run 2's build PR, through `pr.closes`, and
only if the kind ships. The pitch PR (#132), the bet PR (#134), the spec PR
(#135), this approval PR and the evidence PR use no closing keyword.

Working claim:
> An `eval/duplicates/` study extracts about 215 decision items, word for
> word by one written rule, from code-copilot-team's routing and pi specs and
> from memkernel's specs, excluding everything the issue 54 corpus was drawn
> from or overlaps. A session with no candidate code labels the pairs by
> question, and the owner reviews the labels before they are frozen with the
> candidates (B0, the study's signal (b) exactly, and B1, with one cleanup
> fixed in advance) and the bar (at least 8 true pairs, three quarters of
> them found, false candidates not outnumbering true ones). The measurement
> is then published whatever it shows.
>
> Only if a candidate clears the bar does the build ship `possible-duplicate`
> in `findings`, to the owner's design, with ADR-0006 for the related line.
> Otherwise issue 121 stays open with the evidence. No release is part of
> the build. Nothing changes in the page schema, exit codes, MCP tools,
> `findings_version`, `lint --health` or dependencies, and there is no model
> or network.

Origin items, mapped:
- The corpus (S1): FR-001 to FR-012, US1 and US2.
- The labels, candidates and bar, frozen (S2): FR-013 to FR-019, US3 and US4.
- The measurement and the evidence PR (S3): FR-020 to FR-026, US5 and US6.
- The kind (S4): FR-027 to FR-035, US7 and US8.
- ADR-0006, the contract and the docs (S5): FR-036 to FR-040, US9.
- The release (S6): not in the build, under the owner's release rule
  (departure 1).

Mismatches, each deliberate and recorded in plan.md's 23 "Departures from
the pitch": no release in the build; run 2 waits for the owner's 0.11.0
release; phases cut around the main-session script runs; B1's broader
identifier rule (owner, after review); and the rest as listed.

Verdict: aligned
Confidence: high
