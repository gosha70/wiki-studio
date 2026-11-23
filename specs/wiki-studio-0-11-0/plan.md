---
spec_mode: full
feature_id: wiki-studio-0-11-0
risk_category: feature
justification: "A measurement whose value rests on labels frozen before any candidate code and reviewed by the owner, built from real cases in another repository read offline and fenced for closing-keyword text; then a new git-reading path inside findings, the read surface every host and the nightly pass use, over configured repositories that are untrusted input (config-named programs, inherited GIT_ variables, ownership refusals, shallow and partial clones, ambiguous short shas); an additive key in a published JSON format and the MCP trace allowlist; a conditional kind that ships only if the frozen bar is cleared; documents and packaged schema text; and a release. A full spec pins the protocol, the command set, the environment, the ambiguity rule, the cap's provenance, the cut path and the per-phase truth rule before two unattended runs."
status: approved
date: 2026-11-22
collaboration_mode: single
origin:
  issue: 120
  urls:
    - https://github.com/gosha70/wiki-studio/blob/main/specs/pitches/120-revision-aware-stale-check/pitch.md
    - https://github.com/gosha70/wiki-studio/issues/120
    - https://github.com/gosha70/wiki-studio/pull/124
    - https://github.com/gosha70/wiki-studio/pull/125
    - https://github.com/gosha70/wiki-studio/issues/54
    - https://github.com/gosha70/wiki-studio/blob/main/eval/patterns/report.md
    - https://github.com/gosha70/wiki-studio/blob/main/eval/patterns/issues/revision-aware-stale-check.md
    - https://github.com/gosha70/memkernel/issues/123
  origin_claim: |
    Issue 120 (no comments on 2026-11-22), drafted by the issue 54 study
    (eval/patterns/issues/revision-aware-stale-check.md) and shaped by the
    bet pitch specs/pitches/120-revision-aware-stale-check/pitch.md (cycle
    09, building; reviewed in PR #124 over two rounds; bet and cycle start
    PR #125). Problem, as the pitch states it: a page cites its evidence as
    path: + sha:, and when the cited file changes in place nothing tells the
    curator; stale-claim checks only that the path exists. The issue 54
    study measured 24 sources: stale-claim flagged none; a plain revision
    check flagged 13 pages, 1 true review and 12 false alarms, and found one
    citation error (spearman.py cited at a commit that does not contain
    it). "A finding that is wrong 12 times in 13 teaches curators to ignore
    findings." Issue 120 asks for a specification that fixes what a flag
    means, how the false flags are cut or explained, what the check costs,
    where it runs, and what happens when a sha: is missing or unknown. Owner
    decisions (2026-11-22): D1 4w, the full project, knowing S4 ships only
    if a candidate clears the frozen bar; D2 the measurement lands as its
    own evidence PR before the spec names the winner or records "none"; D3
    candidates C0-C4 with three structural rules, labels copied from the
    issue 54 judgments, pass = at most 5 of the 10 false pages and the merge
    page's flag kept on a pre-successor copy, fewest false pages wins, ties
    to fewer git processes; D4 if nothing passes only source-not-at-revision
    ships and issue 120 stays open; D5 inside findings only, not lint
    --health; D6 (against the default) the root's repository plus the
    existing source roots, matched by commit, first usable wins and is
    named, skipped repositories reported and never fetched; D7 an additive
    revision_check object, a commit in no repository with all usable is
    source-not-at-revision, with one skipped not checked, a malformed sha:
    is source-not-at-revision, no sha: not checked; D8 the finding quotes
    Revisit when:, with ADR-0005; D9 on by default; D10 release 0.11.0; D11
    issue 120 is closed by the build PR only if source-revision-changed
    ships; D17 (against the default) label up to seven real cases from
    code-copilot-team's history first, reviewed by the owner and frozen
    before any candidate code; D18 at least 4 positives, keep at least three
    quarters rounded up; D19 keep the three pre-pr playbook cases, fenced
    off in their own directory, never quoted in a PR, commit message or
    issue. Settled: D12 no network; D13 flag, still return; D14 compare
    against each repository's HEAD; D15 kinds additive within
    findings_version 1, no capability; D16 the structural rules; D20 a
    clean git environment, a source root must be the top of its work tree,
    sha: at least 7 hex, an ambiguous prefix stops the search. The pitch
    review's three notes on the spec: D19's fence also covers the
    correcting commits' messages; one ambiguity-detection method, tested
    four ways; the call cap's default from S2's measured process count, in
    configuration.
---

# Plan: wiki-studio 0.11.0 — a revision-aware check for a page's cited sources

The bet pitch `specs/pitches/120-revision-aware-stale-check/pitch.md` is the
shaping record (reviewed on PR #124 in two rounds; owner decisions D1-D11 and
D17-D19 on 22 November 2026, D12-D16 and D20 settled; bet and cycle 09 start
PR #125). Its "Findings from the code" were re-checked against
main at 36a1661 (the merge of PR #125, the same tree as 140ae3c) on 22 November 2026 and hold with the
current line numbers in the spec's design references (findings 1-6, 10-14 and
16 in this repository; findings 15 and 17 rest on git history and the
code-copilot-team and memkernel checkouts, which the build re-reads). Issue
120's body was not re-fetched while this bundle was written (no shell in the
writing session); its words are taken from the pitch, and the
origin-alignment record at approval reads the issue itself. Facts found while
re-checking that shape the spec:

1. **The findings JSON key set and the every-kind test are pinned.**
   `tests/test_findings.py` 126 asserts the exact top-level key set, and the
   every-kind test (70-88) requires its fixture wiki to produce every kind in
   `FINDING_KINDS`. Adding `revision_check` and a kind therefore edits that
   test: the key set gains one key, and the fixture becomes a git repository
   that produces the new kinds (FR-029, FR-033). A kind that is cut must not
   enter `FINDING_KINDS`, because `counts` names every kind a build reports.
2. **The MCP trace pins the findings tool's keys.** Pitch finding 3 says a
   kind added in `findings` reaches MCP "without further work"; that holds
   for kinds, not for a new top-level key: `mcp_adapter/trace.py`'s
   `TOOL_RESULT_KEYS` (145) lists the tool's keys and
   `tests/test_mcp_adapter.py` 680 asserts results equal them. FR-026 adds
   `revision_check` there.
3. **The nightly pass is documented as never running git.** README 275 and
   `docs/nightly.md` 5 and 163 say so; with the revision check inside
   `findings`, the pass reads repositories. FR-040 corrects the three
   sentences.
4. **The package-boundary scan.** `tests/test_package_boundaries.py` 25-26
   forbids `code-copilot-team`, `shared/`, `specs/`, `doc_internal` and
   `knowledge/wiki` in every package module except `paths.py` and `cli.py`,
   docstrings included, and 74-92 allows only standard-library imports. The
   new module must respect both (Constraints).
5. **The project's configuration point for a tunable default.**
   `DEFAULT_LOCK_TIMEOUT = 30.0` (`paths.py` 59) with `ENV_LOCK_TIMEOUT` (36),
   parsed at 356-365 into `WikiPaths`; no packaged configuration file exists.
   The call cap follows that pattern, with its value tied to S2's measurement
   by a test (FR-022, O3).
6. **`rev-parse --verify --quiet` hides the ambiguity.** With `--quiet`, git
   suppresses the "short object ID … is ambiguous" message, so an ambiguous
   prefix and a missing commit look alike. A commit-typed lookup without
   `--quiet` (`rev-parse --verify <sha>^{commit}`) keeps git's own
   disambiguation by type (a blob sharing the prefix does not make it
   ambiguous) and reports a true ambiguity on stderr (FR-021, O2). The full
   commit it prints is used for every later call, so a short prefix never
   reaches `diff` or `diff-tree`, whose lookups are not commit-typed.
7. **The pitch's `diff-tree --name-only` cannot tell "added" from
   "modified".** The exact kind needs the path absent at the `sha:` and
   present at HEAD; `--name-status --no-renames` gives `A`, `D` and `M`
   (with `--relative`, so the printed paths match the cited paths when
   `--root` names a subdirectory), so
   one call per (repository, commit) serves both the exact kind and the
   structural rule (FR-023).
8. **C2's heading rule needs the source's lines.** The pitch's set reads no
   object content; the heading above a hunk needs the source at the cited
   commit (O4).
9. **The auto-build driver.** A `<!-- milestone -->` marker inside a
   `## US<n>:` group pauses after that phase until an `approved-by:` line is
   added; a phase that produces no diff parks the run ("produced no
   changes"); the build prompt says to write nothing outside the repository.
   So the owner's labelling review is a milestone after US1 (FR-009), S4's
   cut writes a CHANGELOG entry rather than nothing (FR-036), and
   `record.py`'s clones live in a temporary directory it removes (FR-012;
   owner step 1).
10. **CI has no code-copilot-team checkout.** Pins of the cited sources'
    bytes cannot be checked in CI without a fetch, which is forbidden;
    `record.py` verifies them against the local checkout before recording,
    and the US1 task verifies them by hand (FR-012, departure 6).
11. **Version places.** `pyproject.toml` 6, `__init__.py` 5, README 26,
    `docs/quickstart-memkernel.md` 27 and 38,
    `tests/integration/test_quickstart_memkernel.py` 58-59,
    `tests/test_cli_contract.py` 149. `CHANGELOG.md` `[Unreleased]` already
    holds two Docs entries (`docs/patterns.md`; the packaged `page-types.md`
    convention, issue 119), which ship in the 0.11.0 wheel (O6).

## Departures from the pitch

Each is recorded so the origin-alignment record at approval can cite it.

1. **The freeze is its own phase (US2).** The pitch's S1 has a labelling
   commit, the owner's review, then a freeze commit. One driver phase is one
   commit, so S1 is two phases with a milestone between them (FR-009,
   FR-011).
2. **D2's spec PR is this bundle's amendment.** The evidence run needs an
   approved spec to run under, so this bundle is written before the
   measurement, with FR-031's winner slot open. After the evidence PR merges,
   the owner's amendment sets the slot to the winner or `none` and
   re-approves; that amendment is the spec PR D2 orders after the evidence
   (FR-016, FR-031). The selection rule is frozen in S1 either way.
3. **Two driver runs, two PRs** (O1): run 1 is US1-US3 and ends with the
   evidence PR; run 2 is US4-US8 and ends with the build PR. The milestone
   marker after US3 makes a single run stop there too.
4. **S3 is two phases**: the hardened git layer (US4) and the finding with
   its run state (US5), so each review covers one concern.
5. **The read commit for a same-commit correction.** The pitch reads each
   case at "the one before the page or spec was corrected". When the
   correcting commit itself changed the cited source (the two pre-pr
   rewrites, the vLLM playbook, both spec supersessions), the commit before
   it predates the source change, and no candidate could ever flag the case.
   FR-004 reads such a case at the correcting commit, with the page from its
   parent and the cited `sha:` as recorded: a counterfactual fixture (the
   source change landed, the page was not updated), marked `read_rule:
   "correcting"` and said so in the README. FR-010 checks before the freeze,
   from the recorded hashes, that the cited file differs between the `sha:`
   and the read commit for every `should_flag` case, and FR-015 that C0 flags
   n of n.
6. **Source pins are verified by `record.py` and by hand, not by a CI test**
   (fact 10). The pitch has S1's frozen test verify the pins against the
   checkout's objects; CI has no checkout. CI checks what the committed files
   allow (`page.md`'s sha256, the inventory's shape, the full hashes).
7. **`protocol.json` beside the README**, frozen with it, so the scorer
   reads the 10 pages, the bar's numbers and the candidate list instead of
   restating them; and a residual tie-break, the lower-numbered candidate
   (O5), so the frozen rule always names one winner.
8. **The fence reaches the commit messages and the recorded hunks.** The
   pitch review's note 1: no text from the correcting commits' messages
   (`87bbc65`, `a9628e5`) outside the fenced directory. FR-012 also records
   the keyword-quoting cases' hunks under that directory, since the cited
   script's diffs may carry the same phrases.
9. **A closing-keyword file test over `eval/revisions/`**, excluding exactly
   the fenced directory (FR-010). D19 binds any such test; this one guards
   the fence the pitch relies on.
10. **One ambiguity method** (the pitch review's note 2; fact 6; O2): the
    commit-typed lookup, without `--quiet`, read under `LC_ALL=C`. The pitch
    counted any object type and offered `--disambiguate`.
11. **`diff-tree --name-status --no-renames --relative`** instead of `--name-only`
    (fact 7), and p1 combines `--show-toplevel --is-shallow-repository HEAD`
    in one call; FR-008 fixes the call plan for S2 and S3 alike.
12. **`cat-file blob` joins the read-only set** for C2's heading rule only
    (fact 8; O4), without `--textconv` or `--filters`.
13. **The cap and the timeout are derived by formula** (the pitch review's
    note 3; O3): ten times S2's recorded count for the shipped call plan,
    rounded up to a multiple of 100, and ten times the slowest recorded call
    (at least 10 s); a test recomputes both from the committed results.
14. **Two small result rules the pitch leaves open**: `revision_check`
    reports sources not checked as counts by reason (O9), and a path that
    escapes its directory is not checked, with no finding (O7).
15. **Existing tests and the MCP trace allowlist are edited** where they pin
    what this release extends (facts 1, 2).
16. **The "never runs git" sentences are corrected** (fact 3; FR-040).
17. **ADR-0005 lands with S4's code** (US6), only if S4 ships; the pitch
    lists it under S5.
18. **CLAUDE.md layout lines land with their code** (US1 for
    `eval/revisions/`, US4 for `revisions.py`), not in S5.
19. **CHANGELOG entries accumulate under `[Unreleased]`** with the phase
    that ships them (US5-US7), and US8 moves them, with the two existing Docs
    entries, under an undated `[0.11.0]`, as 0.10.0's build did; dating, the
    compatibility row, the tag and the release page are the owner's after
    the merge (FR-042, FR-044; O6).
20. **S4's cut is a CHANGELOG entry** (fact 9; FR-036), so the conditional
    phase ends as a recorded cut, not an empty phase.
21. **The `stale-claim` follow-up issue text lives in this plan**
    ("Follow-ups"), for the owner to file; the pitch asks only that it be
    recorded.
22. **The `findings` help text, `api.findings`' docstring and the nightly
    report's header list** name the new kind and the run state (FR-027);
    they enumerate kinds today, and the pitch asks for one line in the
    nightly report.
23. **The winner ships without fragment anchors** (spec amendment,
    2026-11-23; owner's decision after seeing the data). The external review
    of the evidence PR found that C2's frozen anchors include fragments (the
    last dotted part of backticked items such as `py` or `run`, and short or
    letterless items) matched anywhere in a changed line; two of C2's five
    false pages and the `run-wiki-ingest-rules` flag rest on them alone. The
    evidence PR added a non-binding `post_hoc` block measuring C2 without
    them: 3 of 10 false pages, the merge entry and all five positives kept.
    FR-032 ships that measured rule word for word and FR-034 replays it
    against the `post_hoc` figures, so the shipped behaviour is exactly what
    was measured. The preregistered verdict and winner stand unchanged; this
    departure changes only what ships. Two known limits are recorded in
    FR-032 and the contract, unmeasured: a bare file name's last dotted part
    (`toml`, `json`) stays an anchor, and an anchor can match inside a
    longer word.
24. **Run 1's phase 3 was finished by hand** (process, not scope). The
    auto-build's sessions could not run Python, so the record could not run
    in the phase and the phase parked. The build session ran `record.py` and
    `candidates.py` (owner step 1's fallback), committed the output, filled
    the report and had DeepSeek review the phase by hand (evidence PR #128).

Close target: issue 120, by run 2's merge (`pr.closes: [120]`) only when
`source-revision-changed` ships; otherwise it stays open with the measurement
as its evidence (FR-046, D4, D11). No other issue is closed; the pitch PR
(#124), the bet PR (#125), this spec PR, its amendment and the evidence PR use
no closing keyword.

## Architecture decisions

- **ADR-1: Measure, freeze, then build.** The study lives in
  `eval/revisions/`; labels, cases and the bar land before any candidate
  code, are reviewed by the owner, frozen by a test and by the history, and
  the build implements only what the frozen rule names.
- **ADR-2: One git layer, an allowlist in code.** `revisions.py` is the only
  place the check runs git: a fixed set of read-only plumbing shapes, a fixed
  prefix of overrides, a clean environment, a timeout and a counted cap; a
  request outside the set raises before a process starts.
- **ADR-3: Matching by commit, never by guess.** The `sha:` picks the
  repository; ambiguity and an unreadable repository yield "not checked",
  never a finding; the full commit is used once resolved.
- **ADR-4: The finding is a pure decision over collected facts.** The calls
  collect statuses and hunks; a pure function decides each kind, so the
  shipped rule can be replayed on the recorded hunks.
- **ADR-5: Each phase is true on its own diff.** Docs, the contract and the
  version move only when what they describe exists; the conditional kind
  brings its own ADR and CHANGELOG entry, or its cut entry.

## Files

| File | Phase | Change |
|---|---|---|
| `eval/revisions/__init__.py`, `README.md`, `labels.json`, `protocol.json` (new) | US1 (US2 for the cut-1 narrowing) | FR-001-FR-004, FR-008 |
| `eval/revisions/cases/**` (new) | US1 | Case fixtures and labels, FR-005, FR-006 |
| `eval/revisions/pre-successor/merge-require-green-ci-was-never-read.md` (new) | US1 | FR-007 |
| `CLAUDE.md` | US1, US4 | Layout lines for `eval/revisions/` and `revisions.py` |
| `tests/test_revisions_fixture.py` (new) | US1 | FR-010 |
| `tests/test_revisions_frozen.py` (new) | US2 | FR-011; never edited after |
| `eval/revisions/record.py`, `candidates.py` (new) | US3 | FR-012, FR-013 |
| `eval/revisions/results/hunks.json`, `results/candidates.json`, `cases/keyword-quoting/<id>/hunks.json`, one per case (new) | US3 | As recorded |
| `eval/revisions/report.md` (new) | US3 | FR-014 |
| `tests/test_revisions_eval.py` (new) | US3 | FR-015 |
| `src/wiki_studio/revisions.py` (new) | US4, US5, US6 | Layer (US4); source checks for the kind (US5); the winner's decision (US6) |
| `src/wiki_studio/paths.py` | US4, US7 | `git_call_limit`, `ENV_GIT_CALL_LIMIT`, `DEFAULT_GIT_CALL_LIMIT` (US4); source-roots comment and docstring (US7) |
| `tests/test_revisions.py` (new) | US4 | FR-024 |
| `src/wiki_studio/findings.py` | US5, US6 | The kinds and `revision_check` |
| `src/wiki_studio/api.py`, `cli.py`, `nightly.py`, `mcp_adapter/trace.py` | US5 | Docstring, help and text line, header line, trace key |
| `tests/test_revision_findings.py` (new) | US5, US6 | FR-029, FR-033, FR-034 |
| `tests/test_findings.py`, nightly tests pinning the header | US5, US6 | Key set; git fixture; header line |
| `docs/adr/0005-revisit-when-line.md` (new) | US6 | Only with a winner |
| `cli.py`, `mcp_adapter/config.py`, `schema/lint-rules.md`, `schema/citation-rules.md` | US7 | Source-roots help and text; drift sentence |
| `README.md`, `docs/knowledge-contract.md`, `docs/mcp-adapter.md`, `docs/patterns.md`, `docs/nightly.md`, `tests/test_nightly_recipe.py` | US7 | FR-037-FR-040 |
| `CHANGELOG.md` | US5-US8 | `[Unreleased]` entries; `[0.11.0]` in US8 |
| `pyproject.toml`, `src/wiki_studio/__init__.py`, `docs/quickstart-memkernel.md`, `tests/integration/test_quickstart_memkernel.py`, `tests/test_cli_contract.py` | US8 | Version |

## Interfaces

```python
# src/wiki_studio/paths.py
ENV_GIT_CALL_LIMIT = "WIKI_STUDIO_GIT_CALL_LIMIT"
DEFAULT_GIT_CALL_LIMIT = ...        # FR-022: S2's count for the shipped plan × 10, rounded up to a multiple of 100
# WikiPaths gains: git_call_limit: int = DEFAULT_GIT_CALL_LIMIT

# src/wiki_studio/revisions.py
SHA_MIN_LENGTH = 7
SHA_MAX_LENGTH = 40
KEPT_GIT_ENV = ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM")
GIT_CALL_TIMEOUT_SECONDS = ...      # FR-022
ROLE_ROOT = "root"; ROLE_SOURCE_ROOT = "source-root"
# reason constants of FR-019, FR-020, FR-021, FR-022

@dataclass(frozen=True)
class Repository:
    path: Path; role: str; status: str; reason: str | None; head: str | None

@dataclass(frozen=True)
class SourceCheck:                  # one cited source's outcome
    page: str; path: str; sha: str | None
    outcome: str                    # "not-at-revision" | "changed" | "unchanged" | "absent-at-head" | "not-checked"
    reason: str | None; repository: Repository | None; commit: str | None

@dataclass(frozen=True)
class RevisionCheck:
    state: str; reason: str | None; repositories: tuple[Repository, ...]
    sources: tuple[SourceCheck, ...]
    def as_dict(self) -> dict[str, Any]: ...   # FR-026's object (counts by reason)
    def summary(self) -> str: ...               # FR-027's line

class GitRunner:                    # FR-017, FR-018, FR-022: allowlist, prefix, environment, timeout, cap
    def __init__(self, limit: int) -> None: ...
    def run(self, directory: Path, args: Sequence[str], *, ceiling: Path | None) -> subprocess.CompletedProcess[str]: ...

def check_sources(paths: WikiPaths, pages: Sequence[str], *, runner: GitRunner | None = None) -> RevisionCheck: ...
# US6, with a winner:
def revision_flags(page_text: str, hunks: Sequence[Hunk], *, markdown_lines: Sequence[str] | None) -> bool: ...  # the winner, pure

# src/wiki_studio/findings.py
KIND_SOURCE_NOT_AT_REVISION = "source-not-at-revision"      # US5
KIND_SOURCE_REVISION_CHANGED = "source-revision-changed"    # US6, only with a winner
# FindingsResult gains: revision_check: RevisionCheck
```

Eval commands: `python -m eval.revisions.record --checkout PATH [--out PATH]`,
`python -m eval.revisions.candidates [--out PATH]`.

## Phases (one auto-build phase per `## US<n>:` group of tasks.md)

| Phase | Pitch scope | Run | What | Gate beyond the suite |
|---|---|---|---|---|
| US1 | S1 (labelling) | 1 | Labels, cases, pre-successor copy, README, protocol; structural test; **milestone: the owner reviews** | No `.py` under `eval/revisions/` but `__init__.py` |
| US2 | S1 (freeze) | 1 | sha256 pins; cut-1 narrowing if invoked | Only the freeze test (and the narrowing) in the diff |
| US3 | S2 | 1 | Record, score, report; **milestone: the evidence PR, then the amendment** | Scorer reproduces; nothing under `src/` |
| US4 | S3 | 2 | The hardened git layer and the cap | Hardening tests; formula test |
| US5 | S3 | 2 | `source-not-at-revision`, `revision_check`, surfaces | Snapshot equal; strict lint unchanged |
| US6 | S4 | 2 | The winner's kind and ADR-0005, or the recorded cut | Replay equals the committed scores |
| US7 | S5 | 2 | Contract, documents, the recipe | Shown commands checked |
| US8 | S6 | 2 | CHANGELOG `[0.11.0]`, version, audit | FR-045's audit |

Order follows the pitch: S1, S2 (the evidence PR), the spec amendment, then
S3, S4, S5, S6. S3 does not depend on S2's result except for the cap's value,
which US4 reads from the committed results.

## Owner-run steps

1. **Before run 1**: answer O1-O9; approve this bundle; in the approval PR,
   write the run configurations (O1) and the origin-alignment record. Confirm
   the code-copilot-team checkout the session reads (the sibling checkout
   `../code-copilot-team`, beside this repository; it must hold the study's pin
   `00d49c0` and every case commit of FR-004) and that the session may run
   git and Python and create temporary clones under the system temporary
   directory; if not, the owner runs `record.py` by hand in US3 and the
   session commits its output.
2. **Milestone after US1**: review the labelling commit on the pushed branch
   (the 24 labels, each case's `should_flag` and reason, the pre-successor
   edits, the bar). Change any label, case or bar by a commit on the branch;
   if the end of week 2 has passed, invoke cut 1 for US2. Add `approved-by:`
   under the checkpoint and resume.
3. **After US3**: review and label the evidence PR; merge with a merge
   commit, never squash. Then the spec amendment (D2): set FR-031 from
   `report.md`'s winner line, record trigger 2 if it fired, re-approve, and
   write run 2's configuration with `pr.closes: [120]` only when a winner is
   named.
4. **Run 2**: a review breaker or a stuck US6 is the pitch's escalation; a
   trigger-3 cut follows FR-036 (code removed by a follow-up commit, 120
   removed from `pr.closes` or the PR body). Check the build PR is open on the
   branch tip and its closing line matches the decision; review and label.
5. **After the merge**: the release PR (date `[0.11.0]`, the compatibility row
   naming the green `main` run), then the tag on the owner's word and the
   release page with the workflow's wheel and sdist, hash-checked against the
   package index, with relative links absolutized. Hill chart by hand.
6. File the follow-up issue below.

## Unattended run

The owner writes the configurations at approval. This plan assumes 0.10.0's
shape (profile `pr`, the DeepSeek correctness reviewer gating, max 3 rounds
per phase, the gate of the spec's Constraints, `merge.method: "merge"`), with:
run 1 on `feature/wiki-studio-0-11-0-evidence`, phases US1-US3, a pause after
US1 (and after US3, before the PR), no `pr.closes`; run 2 on
`feature/wiki-studio-0-11-0` from `main` after the amendment, phases US4-US8
(`--start-phase 4`), `pr.closes: [120]` only with a winner. How run 1 ends
after US3 with a PR (a phase list of three, or a phase cap) is settled with
O1; the driver honours the `<!-- milestone -->` markers only when phases come
from tasks.md. After each run, re-run the gate on the branch head before
trusting `landed`, check no phase was bypassed without a per-phase record, and
confirm an open PR exists (the known driver defects).

Both runs are started with `CCT_REVIEW_DIFF_MAX_LINES=6000` in the
environment while code-copilot-team's issue 504 is open (the driver's default
of 500 lines parked issue 54's data step as inconclusive). US1 commits seven
case pages with the labels, protocol, README and a test, and US3 the recorded
hunks: about 830 changed lines across the study's cited files alone, one file
539 of them.

**Run 2, as set by the spec amendment (2026-11-23).** `automation.json` now
holds run 2's settings: branch `feature/wiki-studio-0-11-0` from `main`
(after the amendment merges), phases from `tasks.md` with `milestone_every:
0` and `max_phases: 8`, started with `--start-phase 4` so US4-US8 run,
`pr.closes: [120]` (a winner ships), the build PR's title, and
`review.diff_max_lines: 6000`, which the driver freezes at launch. Run 1's
ledger (`.cct/auto-build/wiki-studio-0-11-0/`, parked at phase 3) is moved
aside before run 2 starts, so run 2 begins a fresh ledger. The driver runs
without an inherited `CCT_REVIEW_DIFF_MAX_LINES` (the owner's shell sets one,
which would override the frozen value). Run 2 ends with the driver's own PR,
whose closing line names issue 120.

## Test strategy

- **Measurement discipline** (US1-US3): the derivation recomputed from the
  committed files; the labels' and cases' structure; the fence scan; sha256
  pins in a test never edited after US2; the history audit; the scorer
  reproducing its committed output; the record's logic on a synthetic
  repository.
- **Hardening by attack** (US4): marker-writing fsmonitor, external-diff and
  textconv scripts that must never run; injected `GIT_` variables that must
  change nothing and never reach git; a promisor remote that must never be
  contacted; a source root inside another repository; an option-shaped and
  an uppercase `sha:`; escaping paths; ownership refusal; timeouts; the cap
  with a counting wrapper; an allowlist refusal.
- **The ambiguity rule** (note 2): four fixtures from fixed object contents
  with a verified 7-character collision: unique, ambiguous among commits,
  shared with a blob, too short.
- **Provenance of the defaults** (note 3): the cap and the timeout recomputed
  from `results/candidates.json`.
- **Read-only and unchanged neighbours** (US5, US6): a snapshot of the wiki,
  the proposals directory and every repository before and after; `lint
  --health --strict` unchanged; review state, `approve` and `find` unchanged
  on a flagged page; the backend-not-reached test unedited.
- **Replay** (US6): the shipped decision on the recorded hunks equals the
  committed scores for the winner.
- **Shown commands** (US3, US7): every `python -m eval.revisions.…` line
  parses; the recipe's workflows assert `fetch-depth: 0`; changed CLI lines
  get `--help` checks.
- **Regression**: coverage at or above 92 percent; existing tests edited only
  as FR-029 lists.

## Risks

- **Few positives, one author.** Even with seven cases the recall side is a
  count out of n from one repository, three cases one page at three moments
  and two built pages. Mitigation: frozen before scoring, owner-reviewed,
  reported with and without the built pages (FR-013, FR-014).
- **The labeller knows the candidates.** Mitigation: no candidate code and no
  diff computation in US1; labels only from recorded evidence with reasons;
  the owner's review at the milestone; the freeze and history audit.
- **The ambiguity rule reads a message.** git's text could change.
  Mitigation: `LC_ALL=C`, a substring present in every git release's wording
  ("is ambiguous"), the four real-git fixtures in CI, and fail-closed
  handling: an unrecognised failure skips the repository and yields no
  finding (FR-021).
- **The cap is sized on a small wiki.** Ten times a 14-page run may be low for
  a large wiki, which then reports sources not checked with the cap's reason.
  Mitigation: the reason is explicit and `WIKI_STUDIO_GIT_CALL_LIMIT` raises
  it; no finding is ever derived from an unchecked source.
- **Every `findings` call now spawns git** (at least p1 per repository), in
  CI, `nightly` and MCP. Mitigation: batching by repository and commit; the
  timeout; temporary roots in tests are not repositories and cost one call.
- **The session cannot read the checkout or run git and Python.** Patterns-54
  ran its git work in the session, but some sessions have blocked Python.
  Mitigation: owner step 1 checks access; the owner can run `record.py` by
  hand.
- **Cross-repository citations stay noisy on `stale-claim`**, which reads the
  root only (unchanged by D5). Mitigation: the follow-up issue.
- **Driver mechanics for two runs and a conditional phase.** Mitigation: the
  milestone markers stop a single run at the right places; the amendment
  decides US6's variant before run 2 starts; a trigger-3 cut is an owner
  escalation with FR-036 stating its end state.
- **A third review round on a phase.** Escalation to the owner, per the
  pitch's circuit breaker.

## Success criteria

1. The evidence PR publishes the frozen labels and cases, the scores of C0-C4
   and exactly one winner line, whatever they show; nothing under
   `src/wiki_studio/` changed in it. It changes only FR-016's allowed paths
   (`eval/revisions/**`, the three `tests/test_revisions_*.py` modules, the one
   `CLAUDE.md` Layout line, and the driver's run records under
   `specs/wiki-studio-0-11-0/`), checked by US3's scope audit (tasks.md task
   14), and `tests/test_revisions_frozen.py` is touched by exactly one commit,
   US2's.
2. `findings` reports `source-not-at-revision` exactly for the three causes
   of FR-025 (once on the study's data, for `spearman.py`) and a
   `revision_check` object that says when and why the check did not run.
3. `source-revision-changed` ships only with a winner, flags and still
   returns, and reproduces the committed scores; otherwise the cut is
   recorded and issue 120 stays open.
4. No marker script runs, no `GIT_` variable leaks, no network call is made,
   no write happens, and the cap and timeout trace to S2's numbers.
5. Version 0.11.0 in six places; no new exit code, frontmatter key, page
   type, capability, MCP tool or dependency; `findings_version` 1; gate green
   at 92 percent; `docs/compatibility.md` untouched by the build.

## Follow-ups

Issue text for the owner to file after the build PR merges (not built here;
the pitch's rabbit hole on `stale-claim`):

> **`stale-claim` should consult the repository that matched the cited
> `sha:`.** Since 0.11.0 the revision check matches a cited `sha:` across the
> root's repository and the configured source roots and reads the path in the
> repository that has the commit. `stale-claim` still resolves every cited
> `path:` against the root, so a page citing a file in a source root keeps a
> `stale-claim` beside a clean revision check. Proposal: when a source's
> `sha:` matched a source root, `stale-claim` checks the path there.
> Evidence: `eval/revisions/report.md` and the issue 54 fixture's
> `stale-claim` counts. Out of scope: any network source; a schema key naming
> the repository. Related: issue 120.

## Open items for the spec review

Draft defaults; the spec is written on them. The owner's answers are
recorded here before approval.

**Owner's answers (2026-11-22):** O1 two PRs (the default); O2 git's own
commit-typed lookup (the default); O3 `DEFAULT_GIT_CALL_LIMIT` in `paths.py`
with `WIKI_STUDIO_GIT_CALL_LIMIT` (the default); and, for owner-run step 1,
the build session may create the temporary local clones of the sibling
code-copilot-team checkout and run `record.py` itself. O4-O9 take their
defaults.

1. **O1 — How D2's PRs are produced.** Default: two driver runs from this
   bundle (run 1 US1-US3 ending in the evidence PR; the spec amendment; run 2
   US4-US8 ending in the build PR). Alternative: one run with milestone pauses
   after US1 and US3 and one PR, which merges evidence and build review and
   departs from D2's order.
2. **O2 — The short-`sha:` ambiguity method** (the pitch review's note 2).
   Default: git's commit-typed lookup, `rev-parse --verify <sha>^{commit}`
   without `--quiet`, stderr read under `LC_ALL=C` (`is ambiguous` stops the
   search; `Needed a single revision` moves on; anything else skips the
   repository). Reason: it is the lookup git itself applies when a commit is
   asked for, it costs one process, and it returns the full commit for later
   calls. Alternative: the pitch's any-object rule (`rev-parse
   --disambiguate=<prefix>`), stricter, with a type check per candidate.
3. **O3 — Where the call cap's default lives, and its headroom** (the pitch
   review's note 3). Default: `DEFAULT_GIT_CALL_LIMIT` in `paths.py` beside
   `DEFAULT_LOCK_TIMEOUT`, overridden by `WIKI_STUDIO_GIT_CALL_LIMIT` into
   `WikiPaths` (the project's existing configuration point; no configuration
   file exists), its value S2's count for the shipped plan × 10 rounded up to
   a multiple of 100, bound to the results by a test; the per-call timeout a
   constant derived the same way, with no variable (the pitch gives none).
   Alternative: a packaged defaults file read by `paths.py` (a new mechanism
   for one value), or a different headroom.
4. **O4 — `cat-file blob` for C2's heading rule.** Default: add
   `cat-file blob <commit>:./<path>` (no `--textconv`, no `--filters`) to the
   read-only set, used by S2's record and by S4 only if C2 or C4 wins.
   Alternative: read the lines from a full-context two-commit `diff`, keeping
   the pitch's set as listed.
5. **O5 — The residual tie-break.** Default: when false pages and git
   processes tie, the lower-numbered candidate wins.
6. **O6 — The existing `[Unreleased]` Docs entries.** Default: US8 moves them
   under `[0.11.0]` with the rest, since the packaged `page-types.md` change
   ships in that wheel.
7. **O7 — A cited path that escapes its directory.** Default: not checked,
   reason `path outside <dir>`, no finding.
8. **O8 — The read commit for a same-commit correction** (departure 5).
   Default: the correcting commit, with the page from its parent.
9. **O9 — `revision_check`'s unchecked sources.** Default: counts by reason,
   not a per-source list, so a shallow clone never makes the object large.
