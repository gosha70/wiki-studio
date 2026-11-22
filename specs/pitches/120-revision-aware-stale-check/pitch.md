---
pitch_id: 120-revision-aware-stale-check
title: "A revision-aware check for a page's cited sources: measure candidate filters on the issue 54 study's 24 sources with labels frozen first, then ship an exact citation-error finding and, only if a candidate clears the frozen bar, a source-revision-changed finding that flags and still returns"
appetite: 4w
bet_status: shaped
cycle: ""
circuit_breaker: "Core is S1 (labels, candidates and bar frozen before any candidate code), S2 (the measurement, published whatever it shows, run with code-copilot-team's checkout as a source root), S3 (the exact source-not-at-revision finding, the repository matching across the root's repository and the source roots (D6), and the defined result when the check cannot run), S5's documents for what ships, and S6 (the release). S4 (source-revision-changed) ships only if a candidate clears the bar frozen in S1. Cut order, first to last, each with its trigger: (1) end of week 1, if S1's freeze has not landed: the candidate set narrows to C0, C1 and C2 (the Revisit-when token candidates C3 and C4 are dropped and named as unmeasured); (2) end of week 2, if S2 shows no candidate clearing the bar, or S2 has not run: S4 is cut, the release ships S3 only, and issue 120 stays open with the measurement as its evidence (D4); (3) end of week 3, if S4 is not downhill: S4 is cut the same way. End of week 4: S6 ships what is true; if the release cannot be cut, the change waits under [Unreleased]. Never, to save time: cut S3 down to the root's repository only (the owner chose source roots, D6); put a model on any path from findings, approve or review_state; read over the network, a partial clone's lazy blob fetch included; fetch into, or write to, a source root; pass a sha or path to git that is not validated, or through a shell; withdraw or alter an approval, or change what find returns; make lint --health --strict fail on a new kind; add a frontmatter key, a page type, a runtime dependency, an exit code or an MCP tool; bump findings_version; edit a label, a candidate definition or the bar after the run; edit eval/patterns' frozen files, memkernel or code-copilot-team; weaken or skip a test."
shaped_by: "pitch-shaper (Claude Code) for gosha70"
shaped_date: 2026-11-22
---

<!-- Shape-Up pitch. Origin: https://github.com/gosha70/wiki-studio/issues/120 (no comments on 2026-11-22), drafted by the issue 54 study at 25b9e13 (`eval/patterns/issues/revision-aware-stale-check.md`). Evidence: `eval/patterns/report.md` question 5, `eval/patterns/results/staleness.json`, `eval/patterns/README.md` "Revisit signals". Related: pitch 54-reusable-patterns (the study), memkernel #123 (flag, still return, on the runtime side). -->
<!-- This pitch shapes the issue; it does not replace it. It folds in the external reviewer's shaping points: the false-flag problem as the core design question, a measurement scope with labels fixed first, where the check runs, no network and a defined result without a checkout, flag-still-return, and the citation error as its own scope. -->

# Pitch: A revision-aware check for a page's cited sources

## Problem

A wiki page cites its evidence as `path:` + `sha:`: the file and the
commit the page was grounded at. When that file later changes in place,
nothing tells the curator. `stale-claim` checks only that the cited path
still exists, and `citation-rules.md` says outright that drift is "a
curator pass". So a pattern page whose spec gained a correction
superseding its decision stays clean, approved and returned by `find`,
and the curator learns about it only by re-reading every source by hand.

The issue 54 study measured the gap on 24 `path:` + `sha:` sources across
14 pattern pages. `stale-claim` flagged none of them, including the one
page that needed review. A plain "did the cited file change between its
`sha:` and the pin" check flagged 13 pages (15 sources): 1 true review,
12 false alarms under the pages' own `Revisit when:` lines, and no page
missed. It also surfaced one real citation error: the judge-statistics
page cites `spearman.py` at a commit that does not contain the file.

So the cheap check exists, and as it stands it is mostly noise. A finding
that is wrong 12 times in 13 teaches curators to ignore findings. Issue
120 asks for a specification that fixes what a flag means, how the false
flags are cut or explained, what the check costs, where it runs, and what
happens when a `sha:` is missing or unknown.

## Findings from the code

wiki-studio was read at main `ff30e34` (0.10.0 released, the issue 54
study merged) on 2026-11-22. These facts drive the scopes, decisions and
rabbit holes.

1. **`stale-claim` is path existence only, resolved against the root.**
   `_check_stale_claims` (`src/wiki_studio/health_lint.py` 110-155)
   resolves `paths.root / path` and flags a missing file. Its docstring
   says it does not compare `sha:` with git "(that would require shelling
   out)". It ignores `source_roots`.
2. **`stale-claim` also runs inside `lint --health`, the CI gate.**
   `lint_health` (`health_lint.py` 469, 496) runs it, and `findings`
   calls `lint_health(paths, backend=None)` (`findings.py` 198).
   `lint --health --strict` turns any health warning into a failing exit.
   A new check placed in `lint_health` would change that gate for every
   existing user; a check placed in `findings.py` would not.
3. **`findings` is the one place every reader already gets.**
   `api.findings(paths, *, pages=None)` (`api.py` 837) is what `nightly`
   calls (`nightly.py` 1063, `api.findings(paths)`) and what the MCP
   `findings` tool returns (`mcp_adapter/tools.py` 281-283,
   `.as_dict()`). A kind added there reaches the CLI, the nightly report
   and MCP without further work. `tests/test_findings.py` 160-162 pins
   the signature to `["paths", "pages"]` (the no-backend guard), so
   configuration that does not change the signature (the `WikiPaths`
   layout, or none) keeps that test as it is.
4. **New kinds are additive within `findings_version: 1`.**
   `docs/knowledge-contract.md` 401-403: "Kinds may be added within
   `findings_version: 1`"; `counts` names every kind and a consumer
   treats an unknown kind as an unclassified warning. The three conflict
   kinds (ADR-0004) were added this way, with no capability in
   `contract.py`'s `CAPABILITIES` (112-125). A new top-level key in the
   findings JSON is not covered by that sentence and needs care (D7).
5. **A finding never withdraws an approval or changes eligibility.**
   Approval is an immutable record bound to the page's bytes
   (`review.py` 1-20); `findings` reads only. Discovery's only content
   eligibility test is `superseded_by` (`discovery.py` 278). So "flag,
   still return" is already how every finding behaves; the study's trace
   showed a page carrying findings and still selected by `find`.
6. **git is already on the read path, and only one module commits.**
   `paths.git_toplevel` (`paths.py` 91-105) runs `git rev-parse` on every
   default root resolution and treats `OSError` as "no repository".
   `audit_flush.py` reads with `git show HEAD:./<path>` and
   `git hash-object` (89, 115) and is the only module that runs
   `git commit`. A read-only `git cat-file` / `git diff` from `findings`
   follows these precedents. No git call reaches a model.
7. **The source schema has no repository key.** `page-types.md` 18-20
   and `citation-rules.md` 21-24: `path` is "repo-relative" and `sha` is
   "the commit SHA at which the page was grounded". A cited file in
   another repository has nothing that names that repository. Adding a
   key is a published-contract change with memkernel and needs an ADR
   (CLAUDE.md). `source_roots` (`paths.py` 257-261, `--source-root`,
   `WIKI_STUDIO_SOURCE_ROOTS`, the flag replacing the variable) is today a
   lint boundary for local links (`lint.py` 309), not a list of
   repositories. The owner chose to use it as one (D6): the cited `sha:`,
   which names one commit, picks the repository, so no key is added.
8. **The comparison target is the checkout's HEAD; there is no recorded
   pin.** The study compared against a pin in its own `manifest.json`. A
   wiki has nowhere to record a pin without a schema change, so the only
   revision a check can read offline is the commit each repository's
   checkout is at.
9. **The study's true case is on a page that is already superseded.**
   13 pages have a changed source. Two of them carry `superseded_by`: the
   benchmark UI page, and the merge page
   (`merge-require-green-ci-was-never-read`), which is the one true
   review case, and whose successor already records the correction. Of
   the 11 live pages, judge-statistics is the missing-at-`sha:` citation
   error, and the other **10 are all false** under their own `Revisit
   when:` lines (from `results/staleness.json` and the README's
   judgments; the main session checked these counts on 2026-11-22). On
   the pages a curator would act on, the study holds no true review
   case, so **recall cannot be estimated**. A candidate is judged on two
   things only: how many of those 10 false alarms it removes, and whether
   it keeps the superseded merge page's flag when that page is read as it
   stood before its successor existed.
10. **The labels exist, and were written after the plain check ran.**
    The per-source judgments live in `eval/patterns/README.md`'s
    per-pattern table (made after the run, against each `Revisit when:`
    line), not in `results/staleness.json`. They were written before any
    filter existed, so they can be frozen as labels for the candidates
    now, and the README says so honestly.
11. **The study's anchors are free text, and an extractor already
    exists.** The pages carry their anchors in the body, mostly on a
    `Chosen:` line: backticked identifiers (`redact_text`,
    `correlate.run`, `api/server.py:_correlate`) and section names
    ("the Confirmation Required Before section"). No page carries a line
    range. `fact_diff.py` (28-33, 123) already extracts backticked
    identifiers, `file:line` references and body `path:` citations from
    a page for the patch-set `fact_warnings`. An anchor candidate can
    reuse it with no new convention.
12. **Reading a body line in `findings` is a registered convention.**
    ADR-0001 (`avoid:`) and ADR-0004 (the conflict callout) register a
    body form that `findings` parses. A finding that quotes the page's
    `Revisit when:` line, or filters on it, makes that line a parsed
    convention, which by this precedent takes a short ADR (D8). Generic
    extraction of backticked identifiers is not a convention.
13. **The nightly CI recipe makes a shallow clone.** `docs/nightly.md`
    116 and 146 use `actions/checkout@v4` with no `fetch-depth`, so the
    runner has one commit and every cited `sha:` is unknown there. A
    revision check in that recipe needs `fetch-depth: 0` and a defined
    result for a shallow clone. `tests/test_nightly_recipe.py` parses
    those blocks.
14. **The study is frozen.** `tests/test_patterns_frozen.py` pins
    `labels.json`, `questions.json` and `protocol.json` by sha256, and
    `eval/patterns/` is the record of issue 54. A new measurement reads
    its fixture and results without editing them.

## Appetite

**4w** (D1, decided by the owner), one cycle. The work content for an
LLM executor is about 14.5-20 hours across six scopes; D6's repository
matching adds about 1-1.5h to S3 and 0.5h to S5:

| Scope | Estimate |
|-------|----------|
| S1 Labels, candidates and bar, frozen | 1.5-2h |
| S2 The measurement and its recommendation | 3-4h |
| S3 The exact finding and the repository matching | 3.5-5h |
| S4 The revision finding, by the winning candidate | 3-4h |
| S5 Contract, documents and the recipe | 2.5-3.5h |
| S6 Release | 1-1.5h |

Why 4w and not 2w: the measurement has to come before the build, and it
fixes an order the work cannot compress. The labels and the bar land in
their own commit before any candidate code (S1), the measurement goes
through review as an evidence PR (S2), and only then can the spec name
the candidate the build implements (D2). That is three review-gated PRs
in sequence (evidence, spec, build) before the release, each with its
own external review round. The owner weighed the 2w alternative (S1-S3
only, S4 as a follow-up bet) and chose the full project, knowing S4
ships only if a candidate clears the frozen bar.

Why not 6w: the content is about 20 hours at most, and if no candidate
clears the bar the cycle ends early with S3 shipped.

Planned order:

- **Week 1:** S1 lands (the freeze commit); S2's run with the local
  code-copilot-team checkout as a source root; the evidence PR goes to
  review. Check trigger 1.
- **Week 2:** the evidence PR merges; the spec PR names the winner or
  records "none"; S3 starts. Check trigger 2.
- **Week 3:** S3 and S4 built. Check trigger 3.
- **Week 4:** S5, S6, the release.

## Solution shape

Two parts. First a short measurement under a new `eval/revisions/`
directory that picks the filter. Then a read-only check inside
`findings` that implements it, with an exact citation-error kind beside
it.

```
eval/revisions/
  README.md        protocol: the 24 sources, labels, candidates, bar, cost measure (S1, frozen)
  labels.json      per source: needs-review under Revisit when; citation error (S1, frozen, sha256-pinned)
  candidates.py    every candidate scored from recorded hunks (S2)
  record.py        by hand, once: the -U0 hunks of each changed source against the checkout (S2)
  results/         hunks.json (as recorded), candidates.json (S2)
  report.md        the table, the winner by the frozen rule or "none", the limits (S2)

src/wiki_studio/revisions.py   read-only git: repository list and states, sha-to-repository matching, validated sha/path, cat-file, diff (S3, S4)
src/wiki_studio/findings.py    two kinds: source-not-at-revision (S3), source-revision-changed (S4)
```

**What a flag means.** `source-revision-changed` says: "a file this page
relies on changed in a way the filter says may matter; read the page's
`Revisit when:` line against the change." It is a reason to look, not a
verdict. It never withdraws an approval and never changes what `find`
returns (finding 5). The finding's description names the cited `sha:`,
the repository that matched it, that repository's HEAD and, by D8,
quotes the page's `Revisit when:` line, so the curator has the trigger
in front of them.

**The candidates (S1, S2).** Each is model-free and judged on the 24
sources. Three structural rules apply to every candidate, because each
is right on its own merits: a superseded page is skipped (its review has
happened, and `find` already treats it as ineligible); a source whose
path is missing at the matched repository's HEAD gets no revision kind
(the file is gone, which is `stale-claim`'s question); a source missing
at its `sha:` goes to the exact kind. On the recorded data those rules
alone leave 10 flagged pages, all false (finding 9). Recall cannot be
estimated, so the measurement counts false alarms removed and whether
the superseded merge page's flag is kept when the page is read as it
stood before its successor. The candidates:

- **C0, plain change:** `git diff --quiet <sha> HEAD -- <path>`. The
  baseline, as the study measured it.
- **C1, ignoring whitespace:** the same with `-w --ignore-blank-lines`.
  Same cost as C0.
- **C2, anchor touch:** flag only when a changed line (`git diff -U0`)
  touches one of the page's anchors: a backticked identifier or
  `file:line` reference that `fact_diff.py` already extracts, or, for a
  Markdown source, a hunk under a heading of the source whose text
  appears in the page body. A page with no anchor falls back to C1.
- **C3, Revisit-when tokens:** flag only when a changed line shares a
  content token (`wiki_state._tokenise` and its stop list, as the issue 54 protocol used them) with the page's
  `Revisit when:` line. A page without one, or with "not recorded",
  falls back to C1.
- **C4, both:** C2 and C3 must both fire.

Each is reported with pages flagged, the merge page's true flag kept or
lost, false flags out of the 10, git processes per run and wall time.
The bar and the selection rule are frozen in S1 (D3).

**Where the repository comes from (D6, decided by the owner).** The
check looks in the root's own git repository and in the existing source
roots (`--source-root`, else `WIKI_STUDIO_SOURCE_ROOTS`; the flag
replaces the variable, as today). The `sha:` picks the repository; no
key is added to the source.

- **The candidate list.** The root's repository first, then each source
  root in the configured order. Each is classified once per run: a full
  clone is *usable*; a directory that is not a git work tree, a shallow
  clone or a partial clone is *skipped*, with its reason, and is never
  fetched into or written to. Git missing from PATH skips them all.
- **Matching.** A repository "has" a commit when
  `git -C <repo> cat-file -e <sha>^{commit}` succeeds there, which reads
  only local objects. The first usable repository in order that has the
  commit is the source's repository, and the finding names it (the root,
  or the source root's path). When more than one has it, the first wins;
  the match is by commit alone, and the path is then checked only in that
  repository.
- **Reading the path.** The cited `path:` is read relative to the matched
  directory: the root, as `stale-claim` reads it, or the source root as
  configured (so a source root for repo-relative citations is the
  repository's top directory). The existing containment rules hold: the
  path must be relative and stay inside that directory, and it reaches
  git only as `<sha>:./<path>` or after `--`.
- **No repository has the commit.** If every repository in the list was
  usable, the source is `source-not-at-revision` and the description
  lists the repositories searched. If at least one was skipped, the
  commit may be in a repository the check could not read: the source is
  *not checked*, counted with that reason in `revision_check`, and is not
  a finding. That matches D7: a shallow clone never floods the result.

No network: every git command is local, and a partial clone (which can
fetch blobs lazily) is skipped like a shallow one. `stale-claim` is
unchanged and still reads the root only, so a source matched in a source
root whose path does not exist under the root keeps its existing
`stale-claim` beside any revision kind (rabbit holes).

**When the check cannot run (D7).** No repository in the list is usable
(no git work tree, git not on PATH, shallow or partial clones only): no
revision kinds are reported, and the run says so. The JSON carries a
`revision_check` object with the `state`, its `reason`, one entry per
repository (path, root or source root, used or skipped with its reason,
its HEAD) and the counts of sources checked and not checked; the text
output and the nightly report carry one line. A `path:` with no `sha:`
is not checked and is not a finding.

## Scopes

Build order: S1, then S2 (the evidence PR). The spec follows S2. Then
S3, S4, S5, S6. S3 does not depend on S2's result.

### S1: Labels, candidates and bar, frozen, ~1.5-2h

- **Labels.** `eval/revisions/labels.json`: one entry per source of
  `eval/patterns/results/staleness.json` (24), keyed by page, path and
  sha. Two labels each: `needs_review` (from the README's per-pattern
  judgment column, copied as written) and `citation_error` (the
  judge-statistics `spearman.py` entry only). Each page carries
  `superseded` from its frontmatter. The README states plainly that the
  judgments were made after the plain check ran and before any filter
  existed (finding 10).
- **Candidates and bar.** `eval/revisions/README.md` defines C0-C4
  exactly as above, the three structural rules, the fallback for a page
  with no anchor or no `Revisit when:` line, the bar and the selection
  rule (D3), and the cost measure (git processes and wall time).
- **The freeze.** Labels, protocol and a test pinning both by sha256 (as
  `tests/test_patterns_frozen.py` does) land in one commit before any
  candidate code exists. A label or bar is never edited after the run; a
  disagreement found later is reported, not patched.

### S2: The measurement and its recommendation, ~3-4h

- **The record.** `eval/revisions/record.py`, run by hand once, in the
  study's own setup: the wiki-studio checkout as the root and the local
  code-copilot-team checkout as a source root (D6), with that source
  root's HEAD at the study's pin `00d49c0`. So that code-copilot-team is
  never edited, the source root is an offline local clone of the
  checkout in a scratch directory, detached at the pin. The record uses
  the D6 matching order and records, for each source, which repository
  matched its `sha:` (all 24 are expected in the source root; any match
  in wiki-studio's repository is reported, not hidden), presence at HEAD
  and at its `sha:`, and for each changed source the
  `git diff -U0 <sha> HEAD -- <path>` hunks (plus the
  `-w --ignore-blank-lines` variant and, for Markdown sources, the
  heading each hunk falls under). Written to `results/hunks.json`, as
  recorded. Argument lists, no shell, no network.
- **The scoring.** `eval/revisions/candidates.py` scores C0-C4 from the
  recorded hunks and the fixture pages (read-only from
  `eval/patterns/wiki/`), so a CI test reruns it without the checkout
  and checks the output equals `results/candidates.json`. It imports
  `wiki_studio.fact_diff` and `wiki_state._tokenise` read-only.
- **The report.** `eval/revisions/report.md`: per candidate, pages
  flagged, the merge page kept or lost, false flags of the 10, git
  processes and time; the winner by the frozen rule, or "no candidate
  clears the bar". The limits are stated: one true case, and it sits on
  a superseded page; 24 sources from one repository; no recall estimate
  is possible, so the table reports false alarms removed out of 10 and
  the merge page kept or lost, nothing more.
- **The evidence PR (D2).** One commit per step, never squashed, as the
  0.8.0 and issue 54 evidence PRs were. It changes nothing under
  `src/wiki_studio/`.

### S3: The exact finding and the repository matching, ~3.5-5h

- **`revisions.py`.** A read-only git layer. It builds the repository
  list (the root's repository, then the source roots in configured
  order) and classifies each once per run: a git work tree or not, git
  on PATH, shallow (`git rev-parse --is-shallow-repository`) or partial,
  and its HEAD. It matches each `sha:` to the first usable repository
  that has the commit (`git cat-file -e <sha>^{commit}`), as the
  solution shape describes. A `sha:` must match 4-40 lowercase hex
  before it reaches git; a `path:` must be relative and stay inside the
  matched directory, under the same containment rules as today's source
  roots. Every call uses an argument list with `--` before paths, no
  shell, and a bounded timeout. Calls are batched by repository and
  distinct `sha:`, so the process count grows with repositories times
  commits, not with sources.
- **`source-not-at-revision`.** Raised when a page's `path:` exists at
  the matched repository's HEAD but not at its `sha:`; or the `sha:` is
  a commit in no repository and every repository in the list was usable
  (the description lists those searched); or the `sha:` is malformed.
  One finding per source, severity `warning`, the description saying
  which case and naming the repository. On the study's data it fires
  once, for `spearman.py` at `dafbc5b`.
- **The run state (D7).** The `revision_check` object: the state, its
  reason, one entry per repository (used, or skipped with its reason),
  and the sources not checked with theirs. When no repository is usable,
  no revision kind appears.
- **Tests.** Temporary git repositories for each case:
  - the three cases of the kind, in the root's repository;
  - the commit only in a source root (it matches there, and the finding
    names that source root);
  - the commit in the root's repository and a source root, and in two
    source roots (the first in order wins and is named);
  - flag order against `WIKI_STUDIO_SOURCE_ROOTS` order (the flag
    replaces the variable);
  - the commit in no repository with all of them usable
    (`source-not-at-revision`, listing them) and with one skipped (not
    checked, counted with the reason, no finding);
  - a source root that is not a work tree, one that is shallow, and one
    with a partial-clone configuration (each skipped with its reason; no
    git command that could fetch runs there);
  - the root not a repository while a source root is one (the check runs
    on the source root);
  - no usable repository at all, and git missing (patched `OSError`);
  - an option-shaped `sha:` (`--output=x`) refused before git; a path
    escaping the root or a source root refused;
  - the existing backend-not-reached test still passing.

### S4: The revision finding, by the winning candidate, ~3-4h

Built only if S2 names a winner (D4).

- **`source-revision-changed`.** The winning candidate, with the three
  structural rules. One finding per page and changed source, severity
  `warning`. The description names the `sha:`, the matched repository,
  that repository's HEAD and, by D8, the page's `Revisit when:` line,
  quoted. A scoped run
  (`--paths`) checks only the pages in scope.
- **Flag, still return.** Tests that a flagged page's `review_state` is
  unchanged, `approve` still works on it, and `find` still selects it;
  that `nightly`'s report and JSON list the kind; that the MCP
  `findings` tool carries it; and that `lint --health --strict` is
  unaffected (D5).
- **The study replayed.** One test builds a small repository from the
  recorded hunks' shape (or uses the scoring module directly) and shows
  the shipped rule gives the same flags as `results/candidates.json`
  for the winner.

### S5: Contract, documents and the recipe, ~2-3h

- `docs/knowledge-contract.md`: the new kinds in the findings table and
  the `revision_check` object (D7), and the second role of source roots:
  the repositories a cited `sha:` is matched in, in order (D6).
- `cli.py`'s `--source-root` help text and the rows that describe it and
  `WIKI_STUDIO_SOURCE_ROOTS` (README.md 49 and 502, `docs/mcp-adapter.md`
  35): a source root is also searched for cited commits, read-only and
  offline.
- `src/wiki_studio/schema/citation-rules.md`: replace "The lint script
  does not auto-detect drift" with what `findings` now checks and what
  it does not (packaged document, so it ships in the release).
- `docs/patterns.md` "Revisiting and superseding": what the finding
  means and how to read it against `Revisit when:`.
- `docs/nightly.md`: both workflows gain `with: fetch-depth: 0`, with one
  sentence on why; `tests/test_nightly_recipe.py` follows.
- `docs/adr/0005-...md`, only by D8: `Revisit when:` as an optional body
  line `findings` reads, no frontmatter key, memkernel unaffected (the
  bridge carries the body unchanged).
- `CHANGELOG.md` `[Unreleased]`; CLAUDE.md's layout line for
  `revisions.py`. Every command a changed page shows gets its check.

### S6: Release, ~1-1.5h

0.11.0 by D10: version bumped in `pyproject.toml` and `__init__.py`
together, the CHANGELOG dated, the compatibility row, the release page
with the workflow's wheel and sdist. The build PR closes issue 120 by
D11.

## Rabbit holes

- **One true case.** With a single positive, any candidate that keeps it
  "has full recall", and a filter can be tuned to the 10 false pages by
  accident. *Workaround:* candidates, fallbacks and bar are frozen before
  any scoring code (S1); the report says no recall estimate is possible;
  a new labelled corpus is a separate study, not this bet.
- **Anchors that are not exact.** Backticked text includes things that
  are not identifiers (`status: stable`), qualified names
  (`session_analytics.ingest.redaction.redact_text`) may appear in the
  source only as `redact_text`, and section names are written in prose.
  *Workaround:* C2 uses `fact_diff`'s extraction unchanged, plus the last
  dotted component as a second form, and the heading rule only for
  Markdown sources. Anything finer is out; the measurement decides
  whether that is enough.
- **A shallow or partial clone in CI.** The nightly recipe's default
  checkout has one commit; a partial clone can fetch blobs over the
  network on `git diff`. *Workaround:* detect both and report the check
  as off with its reason; the recipe asks for `fetch-depth: 0`. No
  environment-variable tricks to suppress lazy fetching.
- **Option injection through a `sha:`.** A frontmatter value like
  `--output=/tmp/x` passed as a revision would be read as a git option.
  *Workaround:* validate hex before any call, `--` before paths, argument
  lists only; a test proves the refusal.
- **Cost on a large wiki, multiplied by source roots.** One process per
  source per call grows fast, and every source root can add a
  `cat-file` probe for every commit that was not matched earlier.
  *Workaround:* batch by repository and distinct `sha:`: classify each
  repository once, probe each distinct `sha:` in order and stop at the
  first match, then run one `git diff --name-only <sha> HEAD` per
  (repository, `sha:`) to find the changed files; only those get a `-U0`
  diff. S2 records the process count, and the spec sets a timeout.
- **Cross-repository sources.** The study's pages cite another
  repository, and the schema cannot say which. *Workaround:* the `sha:`
  picks the repository among the root's and the source roots (D6). A
  short `sha:` that is ambiguous in a repository fails `cat-file` there
  and counts as not found in it; the spec says how the description
  reports it.
- **`stale-claim` still reads the root only.** A source matched in a
  source root whose path does not exist under the root keeps today's
  `stale-claim`, so cross-repository citations stay noisy on that kind.
  *Workaround:* leave `stale-claim` unchanged in this bet (it is the CI
  gate's kind, D5) and record "make `stale-claim` consult the matched
  repository" as a follow-up issue text, not built here.
- **Source roots that are not repositories, or are thin ones.** An
  existing user may have set a source root for lint links that is a
  plain directory, a shallow clone or a partial clone. *Workaround:*
  each is skipped with its reason in `revision_check`, never fetched,
  and the lint boundary meaning of source roots is unchanged.

## No-gos

- No model on any path from `findings`, `approve` or `review_state`.
- No network access: no fetch, no URL read, no issue lookup, no lazy
  blob fetch; no scheduled job is added. Nothing is written to or
  fetched into the root's repository or a source root.
- No change to `stale-claim` or to what source roots mean for lint's
  link boundary.
- No automatic approval withdrawal, re-review, page rewrite or
  supersession; a flag never changes `find` or `query` eligibility.
- No frontmatter key, page type or directory; no repository key on a
  source (finding 7). An optional body line read by `findings` gets an
  ADR (D8), as ADR-0004 did.
- No `findings_version` bump, no new capability, no new exit code, no
  MCP tool; `findings` exits 0 on a completed run as today.
- No change to `lint`, `lint --health` or `--strict` (D5).
- No edit to `eval/patterns/`'s frozen files, `eval/navigation`'s frozen
  runs, memkernel or code-copilot-team.
- No runtime dependency; git is a subprocess, as `paths.py` and
  `audit_flush.py` already use it.

## Decisions

The owner **decided D1-D11** on 2026-11-22 in the main session. D6 went
against the recommended default (source roots are searched too, not the
root's repository only); the other ten took the default. Each item keeps
the default, its reason and the alternatives, so the record shows what
was weighed. D12-D16 are *settled* by the issue, the code or the
contract, and are listed so the spec does not reopen them.

- **D1. Appetite (decided by the owner, 2026-11-22: the default).**
  Owner, 2026-11-22: **4w, the full project**, knowing S4 ships only if a
  candidate clears the frozen bar. The default was **4w**, one cycle. The
  measurement must precede the build and goes through its own review
  (D2), so three review-gated PRs run in sequence before the release.
  Alternative: **2w**, S1-S3 only (the measurement and the exact kind),
  with `source-revision-changed` as a follow-up bet that starts from S2's
  winner.
- **D2. When the measurement lands (decided by the owner, 2026-11-22:
  the default).** Owner, 2026-11-22: the default. The default was **its own evidence
  PR (S1 and S2) before the spec PR; the spec names the winner or
  records "none".** The auto-build driver needs a fixed spec, and the
  issue asks the spec to fix how the false flags are cut. Alternative:
  measurement inside the build, with the spec fixing only the
  preregistered selection rule.
- **D3. The candidates, the labels and the bar (decided by the owner,
  2026-11-22: the default).** Owner, 2026-11-22: the default. The
  default was **C0-C4 as described, with the three structural rules; labels copied
  from the issue 54 README's per-pattern judgments; a candidate passes
  when it keeps the merge page's `a24a00e` flag (evaluated as if not
  superseded) and flags at most 5 of the 10 false pages; among passing
  candidates the fewest false flags wins, ties to the fewer git
  processes.** Halving is the least that changes how a curator reads the
  finding; the judgments are the only labels that exist and predate
  every filter. With no true case among the live pages, recall cannot be
  estimated, so the bar measures only false alarms removed and the
  superseded merge page's flag kept (finding 9). Alternatives: a stricter bar (at most 2 of 10); a fresh
  blind relabelling by another reader before the freeze; fewer
  candidates (C0-C2).
- **D4. What ships if no candidate clears the bar (decided by the
  owner, 2026-11-22: the default).** Owner, 2026-11-22: the default. The
  default was **S3 ships alone; `source-revision-changed` does not ship; issue 120
  stays open with the measurement as its evidence.** A kind that is
  wrong in most flags trains curators to ignore findings. Alternative:
  ship C0 behind an opt-in, documented as "a reason to look", with its
  measured false-flag rate in the docs.
- **D5. Where the check runs (decided by the owner, 2026-11-22: the
  default).** Owner, 2026-11-22: the default. The default was **inside `findings`
  only, so the CLI, the `nightly` report and the MCP `findings` tool get
  it; not in `lint --health`.** `lint --health --strict` is the CI gate,
  and a new warning there would fail existing pipelines (finding 2).
  Alternatives: also in `lint --health` (strict gate affected); a
  separate verb.
- **D6. Which repository a cited path belongs to (decided by the owner,
  2026-11-22: NOT the default).** Owner, 2026-11-22: **the check also
  looks in other local repositories, found through the existing source
  roots (`--source-root` / `WIKI_STUDIO_SOURCE_ROOTS`, `paths.py`), plus
  the root's own repository.** What that means, worked out for the spec:
  - *Matching:* the root's repository first, then each source root that
    is a git work tree, in the configured order (the flag replaces the
    variable, as today). A repository has the commit when
    `git cat-file -e <sha>^{commit}` succeeds there, offline. The first
    usable repository that has it is the source's repository; when more
    than one has it, the first wins and the finding names it. The path is
    then read relative to that directory and checked only there.
  - *No repository has the commit:* with every repository usable,
    `source-not-at-revision`, listing the repositories searched; with at
    least one skipped, the source is not checked, counted with that
    reason in `revision_check`, and is not a finding (consistent with
    D7).
  - *Skipped repositories:* a source root that is not a git work tree, is
    shallow or is partial is skipped with its reason in the
    `revision_check` object, and is never fetched into or written to.
  - *Containment:* the existing rules for source roots hold; a cited path
    must be relative and stay inside the matched directory.
  - *Measurement:* S2 runs with code-copilot-team's checkout as a source
    root (an offline local clone detached at the pin), which is exactly
    the study's setup.
  - *Cost:* batched by repository and commit (rabbit holes); S3 grows by
    about 1-1.5h and S5 by about 0.5h.
  The default was **the root's own git repository only**, the path read
  relative to the root as `stale-claim` reads it. That is
  code-copilot-team's own case (its wiki cites its own files) and needs
  no new configuration. Alternatives: the source roots, as the owner
  chose (widens what `source_roots` means); a new `WIKI_STUDIO_*`
  variable listing repositories.
- **D7. The result when the check cannot run, and when a `sha:` is
  missing or unknown (decided by the owner, 2026-11-22: the default, as
  D6 extends it).** Owner, 2026-11-22: the default. With D6 the object
  lists each repository (used, or skipped with its reason, and its HEAD),
  and "unknown in a full clone" reads "a commit in no repository, every
  repository usable"; with one skipped, the source is not checked rather
  than a finding. The default was **no work tree, git missing, a
  shallow or a partial clone: no revision kinds and an additive
  `revision_check` object (`state` on/off, `reason`, the compared HEAD)
  in the findings JSON, mirroring `nightly`'s `drafting` object, plus one
  text line; a `sha:` unknown in a full clone or malformed:
  `source-not-at-revision`; a `path:` with no `sha:`: not checked, not a
  finding.** A silent skip is indistinguishable from "clean", and a
  per-source finding in a shallow clone would flood. Alternatives: a
  `source-revision-unchecked` finding instead of the new key (no JSON
  shape change, but a run-level fact dressed as a page finding); a silent
  skip.
- **D8. The finding quotes `Revisit when:` (decided by the owner,
  2026-11-22: the default).** Owner, 2026-11-22: the default. The
  default was **yes, and
  ADR-0005 registers the line as an optional body form `findings`
  reads.** The issue says the `Revisit when:` line, not the changed file,
  is the review trigger; putting it in the finding is how the curator
  reads the flag. Alternative: no quote and no ADR, the description
  points at the page (required anyway if C3 or C4 wins, since they parse
  the line).
- **D9. On by default (decided by the owner, 2026-11-22: the
  default).** Owner, 2026-11-22: the default; with D6, the check is on
  whenever the root's repository or any source root is a usable full
  clone. The default was **on whenever the root is a full git clone; no
  flag.** The cost is bounded by distinct commits and
  measured in S2, and an opt-in kind is one nobody turns on.
  Alternative: opt-in through a `WIKI_STUDIO_*` variable read into
  `WikiPaths` (keeps `api.findings`' signature).
- **D10. Release (decided by the owner, 2026-11-22: the default).**
  Owner, 2026-11-22: the default, 0.11.0. The default was **0.11.0**, a minor release: new
  kinds and an edited packaged `citation-rules.md`. Alternative: hold
  under `[Unreleased]` for a later release.
- **D11. How issue 120 closes (decided by the owner, 2026-11-22: the
  default).** Owner, 2026-11-22: the default. The default was **the build PR closes
  issue 120 when `source-revision-changed` ships; if D4 applies, the
  build PR names issue 120 without a closing keyword and the issue stays
  open.** The pitch, evidence and spec PRs use no closing keyword.
- **D12. No network (settled by the issue).**
- **D13. Flag, still return (settled by the issue and finding 5).** A
  finding never touches an approval or eligibility.
- **D14. Compare against HEAD (settled by finding 8).** Each matched
  repository's HEAD; uncommitted working-tree changes are ignored; the
  compared commit is reported.
- **D15. Kinds are additive within `findings_version: 1`, with no new
  capability (settled by finding 4 and the ADR-0004 precedent).**
- **D16. The three structural rules (settled).** Superseded pages are
  skipped; a source whose path is missing at the matched repository's
  HEAD gets no revision kind (`stale-claim`, unchanged, reports a
  root-relative missing path as today); a source missing at its `sha:`
  gets the exact kind only. Each is right without
  the measurement, and S2 reports their effect separately.

## Circuit breaker

Core is S1, S2 (published whatever it shows, run with code-copilot-team's
checkout as a source root), S3 (the exact kind, the repository matching
across the root's repository and the source roots by D6, and the
`revision_check` result), S5's documents for what ships, and S6. S4
ships only if a candidate clears the frozen bar. The source-root
matching is the owner's decision and is not on the cut list.

The cut order, first to last, each with its trigger:

1. **End of week 1, if S1's freeze has not landed:** the candidates
   narrow to C0, C1 and C2; C3 and C4 are dropped and named as
   unmeasured.
2. **End of week 2, if S2 shows no candidate clearing the bar, or S2
   has not run:** S4 is cut. The release ships S3, and issue 120 stays
   open with the measurement as its evidence (D4, D11).
3. **End of week 3, if S4 is not downhill:** S4 is cut the same way.

- **End of week 4.** S6 ships what is true. If the release cannot be
  cut, the change waits under `[Unreleased]`.
- **Never, to save time:** cut S3 down to the root's repository only
  (D6); put a model on any path from `findings`, `approve` or
  `review_state`; read over the network, a partial clone's lazy fetch
  included; fetch into, or write to, a source root; pass an unvalidated
  `sha:` or path to git, or use a shell; withdraw or alter an approval or change what `find` returns;
  make `lint --health --strict` fail on a new kind; add a frontmatter
  key, page type, runtime dependency, exit code or MCP tool; bump
  `findings_version`; edit a label, candidate or the bar after the run;
  edit `eval/patterns/`'s frozen files, memkernel or code-copilot-team;
  weaken or skip a test.

"Exhausted" means four working weeks have passed. A third review round
on one PR is an escalation to the owner, who chooses a fix session, a
cut from the list above, or a hold.

## Questions for the owner

Asked by the main session on 2026-11-22; all answered. The owner chose
the default for ten of the eleven and decided D6 against it.

- D1 **4w, the full project**, knowing S4 ships only if a candidate
  clears the frozen bar.
- D2 the measurement lands as its own evidence PR before the spec, and
  the spec names the winner or records "none".
- D3 candidates C0-C4 with the three structural rules; labels copied
  from the issue 54 judgments; pass = keep the superseded merge page's
  flag (read as it stood before its successor) and flag at most 5 of the
  10 false pages; fewest false flags wins, ties to fewer git processes.
- D4 if nothing passes, only `source-not-at-revision` ships and issue
  120 stays open.
- D5 inside `findings` only, not `lint --health`.
- D6 **not the default: the root's own repository plus the existing
  source roots**, the `sha:` matched in order (root first, then each
  source root that is a git work tree), the first that has the commit
  wins and is named, skipped repositories reported in `revision_check`
  and never fetched; S2 runs with code-copilot-team's checkout as a
  source root.
- D7 the additive `revision_check` object (now per repository); a commit
  in no repository with all usable is `source-not-at-revision`, with one
  skipped it is not checked; a malformed `sha:` is
  `source-not-at-revision`; no `sha:` is not checked.
- D8 the finding quotes `Revisit when:`, with ADR-0005.
- D9 on by default whenever the root's repository or a source root is a
  usable full clone.
- D10 release 0.11.0.
- D11 the build PR closes issue 120 only if `source-revision-changed`
  ships.

## Bet log

| Date | bet_status | Note |
|------|------------|------|
| 2026-11-22 | shaping | Pitch drafted from wiki-studio issue 120 (no comments) and the external reviewer's shaping points. wiki-studio read at main ff30e34 (0.10.0): `health_lint.py`, `findings.py`, `api.py` (findings), `nightly.py`, `mcp_adapter/tools.py`, `contract.py`, `paths.py`, `audit_flush.py`, `review.py`, `discovery.py`, `fact_diff.py`, `schema/page-types.md`, `schema/citation-rules.md`, `docs/knowledge-contract.md`, `docs/nightly.md`, `docs/patterns.md`, `eval/patterns/` (report question 5, README revisit signals, `staleness.py`, `results/staleness.json`, the frozen-labels test). |
| 2026-11-22 | shaping → shaped | 6 scopes, 4w, work content 13-18h. Core: S1 (freeze), S2 (measurement), S3 (exact `source-not-at-revision`), S5, S6. S4 (`source-revision-changed`) only if a candidate clears the frozen bar. On the recorded data the three structural rules leave 10 flagged pages, all false, and the study's one true case sits on a superseded page. 16 decisions; D1-D11 open for the owner with defaults, not yet asked (AskUserQuestion was unavailable to the shaping agent). |
| 2026-11-22 | shaped (decided) | Owner answered D1-D11 in the main session (2026-11-22). Ten defaults; D6 against the default: the check also searches the existing source roots (`--source-root` / `WIKI_STUDIO_SOURCE_ROOTS`) after the root's repository, the `sha:` matched by `git cat-file -e <sha>^{commit}` offline, the first usable repository that has it wins and is named; no match with every repository usable is `source-not-at-revision`, with one skipped the source is not checked; non-repository, shallow or partial source roots are skipped with a reason and never fetched. D1: 4w, the full project, knowing S4 ships only if a candidate clears the bar. The main session verified finding 9 against `results/staleness.json` (13 pages with a changed source; 2 superseded, one of them the true case; of 11 live pages, 1 citation error and 10 false). Updated: frontmatter circuit breaker; findings 7, 8 and 9 (recall cannot be estimated); Appetite (14.5-20h; S3 3.5-5h, S5 2.5-3.5h); Solution shape (the repository matching and the per-repository `revision_check`); S2 (code-copilot-team's checkout as a source root, an offline local clone at the pin); S3 (matching and its tests); S4; S5 (source-root help and docs rows); rabbit holes (cost across roots, ambiguous short shas, `stale-claim` still root-only as a follow-up, thin source roots); no-gos; Decisions (intro, D1-D11, D14, D16); Circuit breaker (source-root matching not cuttable); Questions for the owner (answered). |
