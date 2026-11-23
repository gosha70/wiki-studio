# Origin alignment check — wiki-studio-0-11-0

Gate: the bet pitch `specs/pitches/120-revision-aware-stale-check/pitch.md`
was reviewed over three rounds and merged in PR #124 (4cb7783). The owner
decided D1-D11 and D17-D19 on 2026-11-22 (D6 and D17 against the default);
D12-D16 and D20 were settled in review. The bet and cycle 09 start merged in
PR #125 (36a1661).

The spec bundle was reviewed on PR #126:
- The first review (b3b9892) requested two changes, both reproduced with git
  before the fix:
  - FR-021: git's stderr is read in order, with `is ambiguous` checked first,
    because an ambiguous prefix prints that line and then
    `Needed a single revision`;
  - FR-008 and FR-017: p4 is `diff-tree … --relative`, so that a root in a
    subdirectory of its repository gets paths that match the cited ones; FR-024
    tests it.
  The reviewer's two suggestions went in too: the contract states roughly how
  many distinct cited commits the call limit's default covers (FR-038), and
  both runs set `CCT_REVIEW_DIFF_MAX_LINES=6000` (plan, "Unattended run").
- Before the PR opened, the reviewer's notes on the draft added: FR-016's
  allowed paths for the evidence PR, with an audit (tasks.md task 14); the
  freeze test touched by exactly one commit; the counterfactual marking of the
  five cases read at their correcting commit, with a test before the freeze
  that each `should_flag` case's cited file differs between its `sha:` and its
  read commit, and one after the run that C0 flags n of n; one recorded-hunks
  file per fenced case.
- The reviewer approved f8d1d42. #126 merged as 24a0924 with the files still
  `status: draft`, so this approval follows in its own PR, as for the last
  three features.

The owner answered the bundle's open items on 2026-11-22: O1 two PRs (an
evidence run, US1-US3, then the spec amendment, then a build run, US4-US8); O2
git's commit-typed lookup for a short `sha:`; O3 `DEFAULT_GIT_CALL_LIMIT` in
`paths.py`, overridable by `WIKI_STUDIO_GIT_CALL_LIMIT`; the build session may
make temporary local clones of the sibling code-copilot-team checkout and run
`record.py`; O4-O9 take their defaults.

Checked on 2026-11-22 for owner step 1:
- `../code-copilot-team` is readable and holds the study's pin `00d49c0` and
  every case commit FR-004 names (`87bbc65`, `a9628e5`, `fc28fc3`, `a9a3b1e`,
  `5dc717d`, `6529175`, `e59f7cc`), checked offline with
  `git cat-file -e <sha>^{commit}`;
- `providers-health.sh --provider deepseek` reports the reviewer chain usable
  through `deepseek`.

This approval commit does four things:
- sets `spec.md`, `plan.md` and the `tasks.md` marker to approved, with no
  other text change;
- adds `automation.json` for **run 1 only**, copied from issue 54's with these
  fields changed: the branch `feature/wiki-studio-0-11-0-evidence`;
  `phases` from `tasks.md` with `milestone_every: 0` and `max_phases: 3`; and
  `pr` holding only a title, no `closes`. It keeps the `pr` profile, DeepSeek
  as the gating reviewer, the gate command of the spec's Constraints, two fix
  sessions per phase and the $150 / 12 h caps;
- adds this record;
- changes nothing else.

How run 1 ends (the plan left this to O1). The driver pauses at the two
`<!-- milestone -->` markers, after US1 (the owner's review of the labelling
commit) and after US3, and pushes the branch after each phase. It cannot open
a pull request that closes nothing: with no `pr.closes` it falls back to the
plan's `origin.issue`, 120, which the evidence PR must not close (FR-016,
FR-046). So at the pause after US3 the evidence PR is opened by hand from the
pushed branch, after `pre-pr-check.sh --closes none`, and run 1 is never
resumed. If it were, `max_phases: 3` stops it before US4 and the driver parks
without opening or adopting a PR. The run is started with
`CCT_REVIEW_DIFF_MAX_LINES=6000` in its environment. Run 1's ledger is set
aside before run 2; run 2's settings (its branch from `main`, `--start-phase
4`, `pr.closes: [120]` only with a winner) come with the spec amendment.

Origin:
- wiki-studio issue #120, "Specify a revision-aware check for a pattern's
  cited sources" (no comments on 2026-11-22), drafted by the issue 54 study
  at 25b9e13
  (`eval/patterns/issues/revision-aware-stale-check.md`). It asks for a
  specification that fixes what a flag means, how the false flags are cut or
  explained, what the check costs, where it runs, and what happens when a
  `sha:` is missing or unknown.
- the issue 54 study: `eval/patterns/report.md` question 5,
  `eval/patterns/results/staleness.json`, `eval/patterns/README.md`
  "Revisit signals";
- the pitch's owner decisions, and memkernel #123 (flag, still return).

Issue 120 is to be closed only by the build PR, through run 2's
`pr.closes`, and only if `source-revision-changed` ships. The pitch PR
(#124), the bet PR (#125), the spec PR (#126), this approval PR and the
evidence PR use no closing keyword.

Working claim:
> wiki-studio 0.11.0 adds a revision-aware check of a page's cited sources,
> inside `findings` only, model-free and read-only.
>
> First, an `eval/revisions/` study labels the issue 54 study's 24 sources
> and seven real review cases from code-copilot-team's history, pauses for
> the owner's review of the labels, freezes them with the candidates and the
> bar, then measures five model-free filters and publishes the result,
> whatever it shows, with exactly one winner line. The bar: at most 5 of the
> 10 live false pages, the merge page's flag kept on a pre-successor copy,
> and at least three quarters of at least 4 real positives, all three
> holding.
>
> Then the build ships `source-not-at-revision` (a cited path absent at its
> commit, a commit no usable repository has, or a malformed `sha:`) over a
> hardened read-only git layer that searches the root's repository and the
> configured source roots, plus a `revision_check` object that says when and
> why the check did not run. `source-revision-changed`, which flags and
> still returns, ships only if a candidate cleared the frozen bar; otherwise
> the cut is recorded and issue 120 stays open with the measurement as its
> evidence. Release preparation for 0.11.0 happens either way.
>
> No change to `lint`, `lint --health --strict`, `stale-claim`, approvals,
> `find`, the page schema, exit codes, MCP tools, capabilities,
> `findings_version` or dependencies; no network; no model.

Origin items, mapped:
- The labels, real cases, candidates and bar, frozen first (S1): FR-001 to
  FR-011, US1 and US2.
- The measurement and its recommendation (S2): FR-012 to FR-016, US3.
- The exact finding, the repository matching and the git hardening (S3):
  FR-017 to FR-030, US4 and US5.
- The revision finding by the winner, or the recorded cut (S4): FR-031 to
  FR-036, US6.
- Contract, documents and the recipe (S5): FR-037 to FR-041, US7.
- Release preparation (S6): FR-042 to FR-046, US8; the tag and release page
  stay the owner's.
- The external reviewer's three notes on the pitch: FR-009 (the fence covers
  the correcting commits' messages), FR-021 (one ambiguity method, tested
  four ways), FR-022 (the call cap's default from S2's measured count).

Mismatches, each deliberate and recorded in plan.md's 22 "Departures from
the pitch":
- The freeze is its own phase after a milestone; D2's spec PR is an
  amendment of this bundle; two runs and two PRs; S3 is split in two.
- The same-commit read rule (departure 5): five cases are read at their
  correcting commit, marked counterfactual, so the plain change can flag
  them.
- `diff-tree --name-status --no-renames --relative` instead of `--name-only`;
  `cat-file blob` added for C2's heading rule; one ambiguity method.
- Two existing tests and the MCP trace allowlist are edited where they pin
  what the build extends; the "never runs git" sentences are corrected.
- The cut of S4 is recorded as a CHANGELOG entry.

Verdict: aligned
Confidence: high
