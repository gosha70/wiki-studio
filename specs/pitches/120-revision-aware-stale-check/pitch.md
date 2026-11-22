---
pitch_id: 120-revision-aware-stale-check
title: "A revision-aware check for a page's cited sources: measure candidate filters on the issue 54 study's 24 sources with labels frozen first, then ship an exact citation-error finding and, only if a candidate clears the frozen bar, a source-revision-changed finding that flags and still returns"
appetite: 4w
bet_status: shaped
cycle: ""
circuit_breaker: "Core is S1 (the supplementary set of real cases, its labels, the candidates and the bar, frozen before any candidate code, D17), S2 (the measurement, published whatever it shows, run with code-copilot-team's checkout as a source root), S3 (the exact source-not-at-revision finding, the repository matching across the root's repository and the source roots (D6), the git hardening and the per-run call cap, and the defined result when the check cannot run), S5's documents for what ships, and S6 (the release). S4 (source-revision-changed) ships only if a candidate clears the bar frozen in S1. S4 is the first scope at risk in 4w now that labelling comes first. Cut order, first to last, each with its trigger: (1) end of week 2 (moved from week 1 by D17), if S1's freeze has not landed: the candidate set narrows to C0, C1 and C2 (C3 and C4 dropped and named as unmeasured), and the supplementary set freezes with the cases labelled by then; below the minimum of D18 its recall condition is reported not testable; (2) start of week 3, if S2 shows no candidate clearing the bar, or S2 has not run: S4 is cut, the release ships S3 only, and issue 120 stays open with the measurement as its evidence (D4); (3) middle of week 4, if S4 is not downhill: S4 is cut the same way. End of week 4: S6 ships what is true; if the release cannot be cut, the change waits under [Unreleased]. Never, to save time: cut S3 down to the root's repository only (the owner chose source roots, D6); put a model on any path from findings, approve or review_state; read over the network, a partial clone's lazy blob fetch included; fetch into, or write to, a source root; run a git command outside S3's read-only plumbing set, without -c core.fsmonitor=false, core.hooksPath and protocol.allow=never, without --no-ext-diff --no-textconv on a diff, or past the per-run call cap; drop the hardening tests; pass a sha or path to git that is not validated, or through a shell; withdraw or alter an approval, or change what find returns; make lint --health --strict fail on a new kind; add a frontmatter key, a page type, a runtime dependency, an exit code or an MCP tool; bump findings_version; edit a label, a case, a candidate definition or the bar after the freeze; skip the owner's review of the labelling commit; add a case after the run; fetch a case's history over the network; quote text from the keyword-quoting case pages in a PR description, commit message or issue, or widen the closing-keyword exclusion beyond that directory (D19); let an inherited GIT_ variable other than GIT_CONFIG_GLOBAL, GIT_CONFIG_SYSTEM and GIT_CONFIG_NOSYSTEM reach git; accept a source root that is not the top of its own work tree; check a sha shorter than 7 characters, or move on to another repository after an ambiguous prefix; edit eval/patterns' frozen files, memkernel or code-copilot-team; weaken or skip a test."
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

   The arithmetic, from the committed file's own fields.
   `results/staleness.json` has `pages[]`, each with `page` and
   `sources[]`, each source with `path`, `sha` and `revision_check`. It
   carries no superseded marker: that is `superseded_by:` in each page's
   frontmatter under `eval/patterns/wiki/` (and `successor_of` in
   `manifest.json`), so the count joins the two.

   | Step | Source entries | Page-and-file citations | Pages |
   |---|---|---|---|
   | `revision_check == "changed"` | 15 | 14 | 13 |
   | less the pages whose frontmatter has `superseded_by`: the benchmark UI page (its benchmark-step `spec.md` @ `2325480`) and the merge page (`spec.md` @ `a24a00e` and @ `e39969f`) | -3 | -2 | -2 |
   | live pages with a changed source | 12 | 12 | 11 |
   | less the judge-statistics `spearman.py` @ `dafbc5b` entry, absent at its `sha:`, which `source-not-at-revision` reports; the page's other source is `unchanged`, so the page drops too | -1 | -1 | -1 |
   | **left for `source-revision-changed`** | **11** | **11** | **10** |

   All 11 entries on those 10 pages are labelled no review by the
   README's judgments. The 14 citations are fewer than the 15 entries
   because the merge page cites one `spec.md` at two commits. The true
   case is one entry: the merge page's `spec.md` @ `a24a00e`. Its
   `e39969f` entry is the correction's own commit and is labelled no
   further review. (The shaping agent computed every row from the file
   and the pages' frontmatter on 2026-11-22; the main session had
   verified the page counts 13, 2, 11, 1 and 10 the same day.)
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
15. **The merge page never existed without its successor in this
    repository.** `git log --follow` shows one commit for
    `eval/patterns/wiki/decisions/merge-require-green-ci-was-never-read.md`
    (`6d6b34c`, the study's corpus phase), and it already carries
    `superseded_by`, `status: deprecated`, the `e39969f` source and a
    `Correction:` line. The page as it stood before its successor exists
    only as memkernel #57's record (`eval/patterns/corpus/decisions-57.md`
    143-151: `evidence` cites `a24a00e`, the correction at `e39969f` came
    later). So "read as it stood before its successor" has to be a
    derived copy, built by stated edits and frozen in S1, not a checkout
    of an older commit.
16. **A configured repository is not trusted code.** A source root can
    be any clone, and its `.git/config` and `.gitattributes` can name
    programs git runs: `core.fsmonitor`, an external diff
    (`diff.external`, a `diff=<driver>` attribute with `command`), a
    `textconv` filter, a pager, hooks. Which of these fire depends on the
    command: tree-to-tree plumbing that never touches the index or the
    working tree runs none of them. Git also refuses a repository owned
    by another user unless `safe.directory` (system or global config)
    allows it. CI runners commonly add the workspace to the global
    `safe.directory` (the spec checks what `actions/checkout` does), so
    ignoring global config would break the nightly recipe's reads.
17. **Real review cases exist offline, and there are few of them.** Read
    on 2026-11-22 in the local checkouts (code-copilot-team at `2a60217`,
    memkernel at `a9d229c`), nothing fetched:
    - **memkernel adds none.** Its #57 corpus has two `stale` records
      (`eval/decisions-57/corpus.md`), and both are already in the
      study: the merge page (the true case) and the benchmark UI page
      (labelled no review, because its superseding spec already said so
      at the cited commit). Its other eval sets (`anti-rot-128`,
      `lifecycle-suite`, `repeat-mistakes`, `release-b-exit`) test
      memory supersession and hook behaviour, not a page whose cited
      file changed, so they carry no revision event.
    - **code-copilot-team's wiki history has five events.** Of the 22
      commits touching `knowledge/wiki/`, these revise a page right
      after, or in the same commit as, a change to a file it cites:
      1. `playbooks/pre-pr-close-keyword-audit.md`, cites
         `scripts/pre-pr-check.sh`; the script's strict mode (`87bbc65`)
         and the page rewritten in that commit;
      2. the same page and script, v3 with the full keyword set
         (`a9628e5`), page rewritten in that commit;
      3. the same page, last reviewed at `a9628e5`; the script then
         changed in `d0e48c3` (`--closes none`), `34a752d` and `801309f`
         (each `--closes` issue required in the PR body), and the page
         was corrected six months later in `fc28fc3` ("correct what the
         pre-2.1.0 documentation audit found stale"), describing exactly
         those changes;
      4. `playbooks/drive-claude-code-with-local-vllm.md`, cites
         `benchmarks/backends/vllm.md` @ `c8b1f97`; the doc changed in
         `a9a3b1e` and the page's `sha:` was bumped and its text edited
         in that commit;
      5. `workflows/run-wiki-ingest.md`, cites
         `knowledge/wiki/schema/ingest-rules.md` @ `f6b1ee7`; that file
         changed in `68bff41` and the page was edited in `5dc717d` and
         `2aa6ee5` the same day (whether the edit answered the cited
         change or an uncited one is for the labeller).
    - **code-copilot-team's specs have two in-place supersessions after
      approval:** `specs/provider-config/spec.md` (`6529175`, "retire the
      'records the selected provider' guarantee", issue #281) and
      `specs/benchmark-adapters-backends/spec.md` (`e59f7cc`, the
      `provider_id` decision marked "SUPERSEDED by #281"). These are real
      decisions corrected in place, but no wiki page cited them, so a
      case needs a decision page built from the spec text at the commit
      before, as issue 54 built its pages from records.
    - Other "Correction" markers (`docs/dgx-spark/vllm-qwen38.md`, the
      review-round sections of several plans) were written in the same
      commit as the text they correct, or before approval, so they are
      no revision event.
    So up to seven candidates: five verbatim historical pages (three of
    them one page at three moments) and two built pages. The pre-pr
    playbook quotes GitHub closing-keyword phrases: 9, 13, 18 and 18
    lines in its versions at `87bbc65^`, `87bbc65`, `a9628e5` and
    `fc28fc3^` (counted with `git show` and a case-insensitive
    `(close|fix|resolve)[sd]? +#<n>` match). The issue 54 study left this
    page out of its fixture for that reason (`eval/patterns/README.md`
    249). The owner kept the three cases, fenced off (D19). The pre-pr
    playbook cites `path:` without `sha:`; its cases take the commit of
    the page's previous revision as the derived `sha:`. Whether each
    candidate "should flag" is the labeller's call from the recorded
    evidence (S1); expect four to seven positives.

## Appetite

**4w** (D1, decided by the owner), one cycle. The work content for an
LLM executor is about 20.5-27 hours across six scopes. D6's repository
matching added about 1-1.5h to S3 and 0.5h to S5; the PR #124 review
added the frozen pre-successor copy to S1 (0.5h), the git hardening and
call cap to S3 (about 1h) and the full source-root documentation to S5
(0.5h); D17's supplementary set adds about 3-4h to S1 (the inventory,
seven case fixtures, two built pages, the labels) and 1h to S2 (the
cases' hunks):

| Scope | Estimate |
|-------|----------|
| S1 Real cases, labels, candidates and bar, frozen | 5-6.5h |
| S2 The measurement and its recommendation | 4-5h |
| S3 The exact finding, the repository matching and the git hardening | 4.5-6h |
| S4 The revision finding, by the winning candidate | 3-4h |
| S5 Contract, documents and the recipe | 3-4h |
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

Why not 6w: the content is about 27 hours at most, and if no candidate
clears the bar the cycle ends early with S3 shipped.

**Does 4w still hold after D17?** For the core, yes: S1-S3, S5 and S6
fit. The labelling commit now needs the owner's review before the
freeze, which moves the freeze to week 2 and the spec to the start of
week 3, so S3 and S4 share one week. **S4 is the first scope at risk.**
The cut order below drops C3 and C4 first, then S4; the supplementary
set itself is never cut, only frozen with what is labelled by the
trigger. If the owner wants S4 to ship with more certainty, the
alternative is 6w; the pitch is shaped on D1's 4w.

Planned order:

- **Week 1:** S1's inventory and case fixtures, the labelling commit
  (the 24 study sources and the supplementary cases), the owner's review
  of it.
- **Week 2:** the freeze commit; S2's run with the local
  code-copilot-team checkout as a source root; the evidence PR goes to
  review. Check trigger 1 at the end of the week.
- **Week 3:** the evidence PR merges; the spec PR names the winner or
  records "none" (check trigger 2 at the start of the week); S3 and S4
  built.
- **Week 4:** S4 finished (check trigger 3 at the middle of the week),
  S5, S6, the release.

## Solution shape

Two parts. First a short measurement under a new `eval/revisions/`
directory that picks the filter. Then a read-only check inside
`findings` that implements it, with an exact citation-error kind beside
it.

```
eval/revisions/
  README.md        protocol: the 24 sources, the supplementary cases, labels, candidates, bar, cost measure (S1, frozen)
  labels.json      per source: needs-review under Revisit when; citation error (S1, frozen, sha256-pinned)
  cases/<id>/      one real case each: page.md (before the correction), case.json (pins, labels) (S1, frozen, D17)
  cases/keyword-quoting/<id>/   the three pre-pr playbook cases, fenced off (D19)
  pre-successor/   the merge page as it stood before its successor (S1, frozen)
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
alone take 15 changed entries on 13 pages down to 11 entries on 10
pages, all false (finding 9's table names each one removed and why).

**Superseded pages in production.** The shipped check never examines a
superseded page: no revision kind is raised for a page carrying
`superseded_by`, as `find` never returns one. The superseded page was
reviewed when its successor was written.

**How the one true case is measured.** The merge page is superseded, so
the production rule would skip it. The bar's "keep the merge page's
flag" is measured on a derived copy of the page as it stood before its
successor (finding 15). It is the committed page with exactly these
edits: no `superseded_by`; `status: stable`; only the `a24a00e` source
(the `e39969f` correction did not exist yet); no `Correction:` line;
and the `Confidence:` line without its reference to the correction. The
copy is frozen in S1 with the labels, and each candidate runs on it with
the `a24a00e` entry's recorded hunks. In the study's own data the
recall side rests on this single entry, so the owner chose to label more
real cases first (D17).

**The supplementary set of real cases (D17).** Up to seven cases from
code-copilot-team's history (finding 17), each a page as it stood
before a cited source changed in a way that called for review, with its
`path:` + `sha:` and the commit that changed the source. They are
labelled and frozen before any candidate code, and give the bar a recall
condition: a candidate must keep at least the share D18 sets of the
cases labelled "should flag". With fewer positives than D18's minimum,
the recall condition is reported **not testable** and the bar is the
two study conditions alone, as before D17. Even at seven, the cases come
from one repository and one author, and three are one page at three
moments; the report says so.

**The bar, combined.** A candidate passes only when **all three** hold:
(1) it flags at most 5 of the study's 10 false pages (D3); (2) it keeps
the merge page's `a24a00e` flag on the pre-successor copy (D3); (3) it
keeps at least D18's share of the supplementary "should flag" cases
(D17, D18), or that condition is not testable. Among passing candidates
the fewest false pages wins, ties to the fewer git processes. Matched
negatives in the supplementary set are reported, not part of the bar.

The candidates, each run with S3's hardened command set:

- **C0, plain change:** whether the file differs between `<sha>` and
  HEAD (`git diff --quiet --no-ext-diff --no-textconv <sha> HEAD --
  <path>`). The baseline, as the study measured it.
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

Each is reported with pages and source entries flagged, the merge
page's `a24a00e` flag kept or lost (on the pre-successor copy), false
flags out of the 10 pages and out of the 11 entries, supplementary
positives kept out of n and negatives flagged, git processes per run and
wall time. The bar and the selection rule are frozen in S1 (D3, D17,
D18): the study's false side is binding in pages, as the owner decided
it; the entry counts are reported beside it.

**Where the repository comes from (D6, decided by the owner).** The
check looks in the root's own git repository and in the existing source
roots (`--source-root`, else `WIKI_STUDIO_SOURCE_ROOTS`; the flag
replaces the variable, as today). The `sha:` picks the repository; no
key is added to the source.

- **The candidate list.** The root's repository first, then each source
  root in the configured order. Each is classified once per run: a full
  clone is *usable*; a directory that is not a git work tree, a shallow
  clone or a partial clone is *skipped*, with its reason, and is never
  fetched into or written to. A source root must be the top of its own
  work tree (`git rev-parse --show-toplevel` resolves to it), else it is
  skipped as "not the top of a git work tree". Git missing from PATH
  skips them all. Every call runs with a clean environment (S3).
- **Matching.** A repository "has" a commit when
  `git -C <repo> cat-file -e <sha>^{commit}` succeeds there, which reads
  only local objects. The first usable repository in order that has the
  commit is the source's repository, and the finding names it (the root,
  or the source root's path). When more than one has it, the first wins;
  the match is by commit alone, and the path is then checked only in that
  repository. A `sha:` under 7 characters is not checked ("too short").
  A prefix ambiguous in a repository is not checked ("ambiguous in
  <repo>"), and the search for that source stops: it does not move on to
  the next repository.
- **Reading the path.** The cited `path:` is read relative to the matched
  directory: the root, as `stale-claim` reads it, or the source root as
  configured (so a source root for repo-relative citations is the
  repository's top directory). The existing containment rules hold: the
  path must be relative and stay inside that directory, and it reaches
  git only as `<sha>:./<path>` or after `--`.
- **No repository has the commit.** If every repository in the list was
  usable and none reported an ambiguity, the source is `source-not-at-revision` and the description
  lists the repositories searched. If at least one was skipped, the
  commit may be in a repository the check could not read: the source is
  *not checked*, counted with that reason in `revision_check`, and is not
  a finding. That matches D7: a shallow clone never floods the result.

No network: every git command is local, and a partial clone (which can
fetch blobs lazily) is skipped like a shallow one. Every git call runs
with S3's hardening (read-only plumbing, the `-c` overrides, a per-run
call cap), because a source root's own config is not trusted. `stale-claim` is
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

### S1: Real cases, labels, candidates and bar, frozen, ~5-6.5h

- **Labels.** `eval/revisions/labels.json`: one entry per source of
  `eval/patterns/results/staleness.json` (24), keyed by page, path and
  sha. Two labels each: `needs_review` (from the README's per-pattern
  judgment column, copied as written) and `citation_error` (the
  judge-statistics `spearman.py` entry only). Each page carries
  `superseded` from its frontmatter. The README states plainly that the
  judgments were made after the plain check ran and before any filter
  existed (finding 10).
- **The 13-to-10 derivation.** The README carries finding 9's table and
  the recipe for it: select `revision_check ==
  "changed"` in `results/staleness.json`, join each `page` to its
  frontmatter's `superseded_by`, drop those pages, drop the
  `spearman.py` entry, and count entries, citations and pages. The
  frozen test recomputes the table from the two files and asserts 15/14/13,
  12/12/11 and 11/11/10, so the bar's denominators cannot drift.
- **The supplementary cases (D17).** One directory per case under
  `eval/revisions/cases/<id>/`, built from the local code-copilot-team
  checkout, read-only and never fetched. The three pre-pr playbook cases
  live apart, under `eval/revisions/cases/keyword-quoting/<id>/`, by
  D19: their pages quote closing-keyword phrases verbatim, and that
  directory is the only one any closing-keyword file check excludes.
  The README, `case.json`, the labels and the report name those cases
  by id and path only and never quote their keyword lines:
  - `page.md`: the page as it stood before the correction. For the five
    wiki events (finding 17), the page's bytes at the commit before the
    correcting one, verbatim, except a derived `sha:` added to a `path:`
    citation that has none (the pre-pr playbook), named as derived. For
    the two spec supersessions, a `decision` page in the
    `docs/patterns.md` template built from the spec's decision text at
    the commit before the supersession, named as built.
  - `case.json`: the repository (code-copilot-team), the cited `path:`
    and `sha:` (as written, or derived and said so), the commit or commits
    that changed the source, the commit at which the case is read (the
    one before the page or spec was corrected, which plays HEAD), the
    correcting commit, the sha256 of `page.md`, of the source at `sha:`
    and of the source at the read commit, and where the evidence is (the
    correcting commit's message and diff).
  - **The inventory.** The README lists all seven candidates of finding
    17 with their commits, and the test checks the pins against the
    files; a candidate the labeller rejects stays listed with the reason.
- **Labels for the cases.** Each case is labelled `should_flag` (true or
  false) with a one-line reason drawn from the recorded correction
  evidence: did the change to the cited file call for the review that
  followed? A matched negative is labelled where the history offers one:
  a change to the same cited file that the page's next revision did not
  answer (for example a script change between two playbook revisions
  that the playbook never mentions), `should_flag: false`. Negatives are
  optional and reported, not part of the bar.
- **Who labels, and when.** The build session labels from the recorded
  evidence, in its own labelling commit that holds the case fixtures and
  every label (the 24 study sources and the cases) and no candidate
  code. The owner reviews that commit before the freeze, as the
  issue 54 labelling commit was reviewed. A label the owner changes is
  changed in that commit's PR, before the freeze, never after.
- **The minimum and the share (D18).** The README states the minimum
  number of `should_flag: true` cases for the recall condition to be
  tested and the share a candidate must keep; with fewer positives, the
  recall condition is "not testable" and the report says so.
- **The pre-successor copy.** `eval/revisions/pre-successor/merge-require-green-ci-was-never-read.md`,
  the merge page with the edits the solution shape lists, each edit
  named in the README beside memkernel #57's record it rests on.
- **Candidates and bar.** `eval/revisions/README.md` defines C0-C4
  exactly as above, the three structural rules, the fallback for a page
  with no anchor or no `Revisit when:` line, the bar in pages (binding)
  with the entry counts reported beside it, the recall condition on the
  supplementary set (D18), how the three conditions combine (all must
  hold), the selection rule (D3), and the cost measure (git processes
  and wall time).
- **The freeze.** Labels, the cases, the pre-successor copy, protocol
  and a test pinning them all by sha256 (as `tests/test_patterns_frozen.py`
  does) land after the owner's review of the labelling commit and before
  any candidate code exists. Nobody edits a label, a case or the bar
  after the freeze; no case is added after the run; a disagreement found
  later is reported, not patched.

### S2: The measurement and its recommendation, ~4-5h

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
  heading each hunk falls under). For each supplementary case it does the
  same with a second offline local clone detached at the case's read
  commit, so the case's `sha:` is compared with what HEAD was when the
  review was due. Written to `results/hunks.json`, as recorded. Argument
  lists, no shell, no network, S3's git hardening.
- **The scoring.** `eval/revisions/candidates.py` scores C0-C4 from the
  recorded hunks, the fixture pages (read-only from
  `eval/patterns/wiki/`), the pre-successor copy and the case pages,
  so a CI test reruns it without the checkout
  and checks the output equals `results/candidates.json`. It imports
  `wiki_studio.fact_diff` and `wiki_state._tokenise` read-only.
- **The report.** `eval/revisions/report.md`: per candidate, pages and
  entries flagged, the merge page's `a24a00e` flag kept or lost on the
  pre-successor copy, false flags of the 10 pages and of the 11 entries,
  supplementary positives kept out of n (or "not testable") and
  negatives flagged, git processes and time; the winner by the frozen rule, or "no
  candidate clears the bar". The limits are stated: in the study, one
  true case, one source entry, on a page the shipped check skips, read
  through a derived copy; in the supplementary set, a handful of
  positives from one repository and one author, three of them one page
  at three moments, two of them built pages; so the recall figure is a
  count out of n, not an estimate, and the report gives it as such.
- **The evidence PR (D2).** One commit per step, never squashed, as the
  0.8.0 and issue 54 evidence PRs were. It changes nothing under
  `src/wiki_studio/`.

### S3: The exact finding, the repository matching and the git hardening, ~4.5-6h

- **`revisions.py`.** A read-only git layer. It builds the repository
  list (the root's repository, then the source roots in configured
  order) and classifies each once per run: a git work tree or not, git
  on PATH, shallow (`git rev-parse --is-shallow-repository`) or partial,
  and its HEAD. It matches each `sha:` to the first usable repository
  that has the commit (`git cat-file -e <sha>^{commit}`), as the
  solution shape describes. A `sha:` must be 7-40 lowercase hex before
  it reaches git (7 is git's default abbreviation, and every `sha:` in
  the study has 7): a shorter one is *not checked*, reason "too short",
  and is not a finding; one that is not hex at all is
  `source-not-at-revision` (malformed). A prefix that is ambiguous in a
  repository (more than one object there starts with it) is *not
  checked*, reason "ambiguous in <repo>"; the search for that source
  stops there and does not move on to the next repository, and it never
  yields `source-not-at-revision`. The spec picks the detection
  (`rev-parse --disambiguate=<prefix>` or reading `rev-parse`'s error
  with `LC_ALL=C`); a `path:` must be relative and stay inside the
  matched directory, under the same containment rules as today's source
  roots. Every call uses an argument list with `--` before paths, no
  shell, and a bounded timeout. Calls are batched by repository and
  distinct `sha:`, so the process count grows with repositories times
  commits, not with sources.
- **Git hardening: a configured repository is not trusted code**
  (finding 16).
  - *Commands.* Only low-level, read-only, tree-to-tree commands:
    `rev-parse` (`--is-inside-work-tree`, `--is-shallow-repository`,
    `--verify --quiet <sha>^{commit}`, `HEAD`), `cat-file -e`,
    `config --get` (to detect a partial clone),
    `diff-tree -r --name-only --no-ext-diff --no-textconv`, and
    `diff --no-ext-diff --no-textconv` between two commits (`--quiet`,
    `-U0`, `-w --ignore-blank-lines`). Never a command that reads the
    index or the working tree (`status`, `diff` without two commits),
    so git refreshes no index and writes nothing.
  - *Overrides on every call:* `git --no-pager -c core.fsmonitor=false
    -c core.hooksPath=<os.devnull> -c protocol.allow=never -C <repo> …`.
    `core.fsmonitor=false` stops a configured monitor program;
    `core.hooksPath` points hooks nowhere (none of these commands runs
    one, so it costs nothing); `protocol.allow=never` makes any attempted
    transport, a partial clone's lazy fetch included, fail instead of
    reaching the network. Each is a `-c` on the command line.
  - *A clean environment for every call.* Git reads `GIT_DIR`,
    `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY` and their
    kin before `-C`, and git sets several of them when it runs a hook, so
    `findings` run from a pre-commit hook would check every `sha:`
    against the hook's repository. The git layer builds each call's
    environment from `os.environ` with a deny rule: **every variable
    whose name starts with `GIT_` is removed**, which covers the whole
    list `git rev-parse --local-env-vars` prints in git 2.53
    (`GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_CONFIG`,
    `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_COUNT`, `GIT_OBJECT_DIRECTORY`,
    `GIT_DIR`, `GIT_WORK_TREE`, `GIT_IMPLICIT_WORK_TREE`,
    `GIT_GRAFT_FILE`, `GIT_INDEX_FILE`, `GIT_NO_REPLACE_OBJECTS`,
    `GIT_REPLACE_REF_BASE`, `GIT_PREFIX`, `GIT_SHALLOW_FILE`,
    `GIT_COMMON_DIR`) plus `GIT_CONFIG_KEY_<n>`/`GIT_CONFIG_VALUE_<n>`,
    `GIT_EXTERNAL_DIFF`, `GIT_DISCOVERY_ACROSS_FILESYSTEM` and any
    variable a later git adds, **except three kept on purpose:**
    `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM` and `GIT_CONFIG_NOSYSTEM`,
    which only say where the user's own config lives (the reason system
    and global config are kept, below). The layer then sets
    `GIT_CEILING_DIRECTORIES` (next bullet), `GIT_TERMINAL_PROMPT=0` and
    `LC_ALL=C` (stable messages). Removing a variable or limiting
    discovery redirects nothing: no variable here points git at a
    different repository, index or lock.
  - *`paths.git_toplevel` is left as it is.* It resolves the default
    root for every verb and passes the environment through. Inside a
    hook `GIT_DIR` names the repository the hook runs in, so the root it
    finds is the right one, and changing it would change every verb's
    behaviour from hooks, which is outside this bet. The revision layer
    does not reuse it: it re-derives each repository from its directory
    with the clean environment.
  - *No search upward from a source root.* A plain directory inside
    another repository passes `--is-inside-work-tree` and would match
    against the enclosing repository. A source root is used only when
    `git rev-parse --show-toplevel`, resolved, equals the configured
    directory, resolved; otherwise it is skipped, reason "not the top of
    a git work tree". As a second guard, each call into a source root
    sets `GIT_CEILING_DIRECTORIES` to the directory's resolved parent, so
    git cannot look above it. The root keeps today's meaning (its
    repository is its git toplevel, as `default_root` finds it, and
    `--root` may name a subdirectory), so its calls set the ceiling to
    the parent of that resolved toplevel. The two guards do not conflict:
    the ceiling stops discovery above the directory, the equality check
    catches a directory that is not itself the top.
  - *System and global config are kept.* `GIT_CONFIG_NOSYSTEM=1` and
    `GIT_CONFIG_GLOBAL=/dev/null` are not used: those files are the
    user's own, not the configured repository's, and they carry
    `safe.directory`, which CI runners rely on (finding 16); ignoring
    them would make the nightly recipe's reads fail. The untrusted part
    is the repository's own config and attributes, which the command set
    and the overrides neutralise. A repository git refuses for ownership
    is skipped with that reason, never forced with a `safe.directory`
    override.
  - *A cap on git calls per run.* A default the spec fixes from S2's
    measured process count, overridable through a `WIKI_STUDIO_*`
    variable read into `WikiPaths`, as the lock timeout is. When the cap
    is reached, no further git call runs; every source not yet checked is
    *not checked* with the reason "git call limit (N) reached" in
    `revision_check`, and none of them is a finding. A call that times
    out skips its repository for the rest of the run, with that reason.
  - *Read-only.* `findings` writes nothing: not the wiki, not the
    proposals directory, not any repository. When git is not installed
    (`OSError` on the first call) `revision_check` says `state: off`,
    reason "git not found"; a root or source root that is not a work tree
    is listed as skipped, reason "not a git work tree" (D7).
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
  - a 6-character `sha:` is not checked, reason "too short", no finding;
  - a 7-character prefix ambiguous in the first repository and present
    as a commit in the second: not checked, reason "ambiguous in <first
    repository>", the second repository never consulted for it, no
    `source-not-at-revision`;
  - `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`,
    `GIT_ALTERNATE_OBJECT_DIRECTORIES` and `GIT_COMMON_DIR` set to a
    different repository (as a hook would): the result is identical to a
    run without them, and a spy on the subprocess call shows no `GIT_`
    variable reaches git except the three kept and the ones the layer
    sets;
  - a source root that is a subfolder of a repository is skipped, reason
    "not the top of a git work tree", and its commits are not matched;
  - a source root whose `.git/config` sets `core.fsmonitor` to a script,
    and whose config and `.gitattributes` set an external diff driver
    (`diff.external` and a `diff=<driver>` attribute with `command`) and
    a `textconv` filter, each script writing a marker file: after a
    `findings` run that checks a changed source there, no marker exists;
  - a source root with a partial-clone configuration and a reachable
    promisor remote: no network call happens (skipped, and
    `protocol.allow=never` as the second guard);
  - the call cap reached mid-run: the remaining sources are not checked
    with the cap's reason, no finding for them, and no git call after the
    cap (a counting wrapper around the subprocess call);
  - a timeout on one repository skips only that repository;
  - a repository git refuses for ownership is skipped with that reason;
  - `findings` leaves the wiki, the proposals directory and every
    repository byte-identical (a tree snapshot before and after);
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

### S5: Contract, documents and the recipe, ~3-4h

- **Source roots' second meaning, everywhere it is defined.** Today a
  source root is a directory pages may link into; from this release it
  is also a repository searched for cited commits. The spec states the
  rule (the D6 block: root's repository first, then source roots in
  configured order, the flag replacing the variable; a repository has a
  commit when `cat-file -e <sha>^{commit}` succeeds offline; the first
  usable one wins and is named; with no match, `source-not-at-revision`
  if every repository was usable, else not checked; skipped repositories
  and their reasons; read-only, hardened, never fetched), and each place
  that defines source roots says it in a sentence and points at the
  contract. Every place, from `git grep` at `ff30e34`:
  - `docs/knowledge-contract.md`: the full rule, the new kinds in the
    findings table, the `revision_check` object (D7) and the call cap;
  - README.md 49 (the layout table) and 502 (the environment table);
  - `docs/mcp-adapter.md` 35 (the MCP server's options), since the MCP
    `findings` tool runs the check with the server's source roots;
  - `src/wiki_studio/schema/lint-rules.md` 75 (packaged): the lint
    meaning is unchanged, plus one pointer to the second role;
  - `cli.py` 97-112 (`--source-root` help) and 959 (`info`'s
    "source-roots:" line, which reads "links stay inside the root" when
    none is set);
  - `mcp_adapter/config.py` 109-114 (its `--source-root` help);
  - `paths.py` 37 and 257-261 (the `ENV_SOURCE_ROOTS` comment and the
    `WikiPaths.source_roots` docstring).
  `lint.py`'s docstrings describe the lint boundary only and stay as
  they are; the CHANGELOG's history and ADR-0003's option list are
  history and are not edited.
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

- **Few true cases.** The study has one positive, and the supplementary
  set adds four to seven, three of them one page at three moments, so a
  filter can still be tuned to them by accident. *Workaround:* every
  case, label, candidate, fallback and the bar are frozen before any
  scoring code (S1); the report gives recall as a count out of n.
- **A search for cases that never ends.** "More real cases" invites
  digging through every repository. *Workaround:* the inventory is
  finding 17's seven candidates from the local checkouts, fixed in S1;
  no other repository, no network, no case added after the run. Fewer
  than D18's minimum positives makes the recall condition "not
  testable", not a reason to keep searching.
- **Labels that follow the hoped-for result.** The build session knows
  the candidates when it labels. *Workaround:* labels come only from the
  recorded correction evidence (the correcting commit's message and
  diff), with a reason per label; the owner reviews the labelling
  commit; no candidate code exists until the freeze.
- **Built pages that favour a candidate.** The two spec cases need
  pages written for them, and an author can put anchors where a filter
  will find them. *Workaround:* a built page copies the spec's decision
  text at the commit before, in the `docs/patterns.md` template, and
  its anchors are only identifiers that text already backticks; the
  report also gives the recall count without the built pages.
- **A configured repository's own config runs programs.** fsmonitor,
  external diff and textconv drivers, pagers and hooks can be named in a
  source root's `.git/config` or `.gitattributes`. *Workaround:* the S3
  command set (tree-to-tree plumbing, `--no-ext-diff --no-textconv`) and
  the per-call `-c` overrides; a test with marker-writing scripts proves
  none runs.
- **Ignoring global config would break CI.** Setting
  `GIT_CONFIG_GLOBAL=/dev/null` drops `safe.directory`, and the nightly
  runner's reads would fail. *Workaround:* keep system and global config
  (the user's own) and neutralise only what the repository can name; a
  repository git refuses for ownership is skipped with the reason.
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
  network on `git diff`. *Workaround:* detect both and report the
  repository as skipped with its reason; `-c protocol.allow=never` on
  every call is the second guard; the recipe asks for `fetch-depth: 0`.
  No environment variable that redirects git's state.
- **Option injection through a `sha:`.** A frontmatter value like
  `--output=/tmp/x` passed as a revision would be read as a git option.
  *Workaround:* validate hex before any call, `--` before paths, argument
  lists only; a test proves the refusal.
- **Cost on a large wiki, multiplied by source roots.** One process per
  source per call grows fast, and every source root can add a
  `cat-file` probe for every commit that was not matched earlier.
  *Workaround:* batch by repository and distinct `sha:`: classify each
  repository once, probe each distinct `sha:` in order and stop at the
  first match, then run one `git diff-tree -r --name-only <sha> HEAD`
  per (repository, `sha:`) to find the changed files; only those get a
  `-U0` diff. S2 records the process count; the spec sets a timeout and
  the per-run call cap from it (S3).
- **Cross-repository sources.** The study's pages cite another
  repository, and the schema cannot say which. *Workaround:* the `sha:`
  picks the repository among the root's and the source roots (D6). A
  `sha:` shorter than 7 characters is not checked ("too short"); a
  prefix ambiguous in a repository is not checked ("ambiguous in
  <repo>") and the search stops there, so an ambiguity can never turn
  into a wrong match in a later repository or a false
  `source-not-at-revision` (S3).
- **Inherited git variables and upward search.** `GIT_DIR` and its kin,
  set by a hook, would point every call at the hook's repository; a
  source root inside another repository would match against the
  enclosing one. *Workaround:* every `GIT_` variable but the user's
  three config-location variables is removed from each call's
  environment, a source root must be the top of its own work tree, and
  `GIT_CEILING_DIRECTORIES` stops discovery above it; a test covers each
  (S3).
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
- No git command in any repository outside S3's read-only, tree-to-tree
  set; none without `--no-pager`, `-c core.fsmonitor=false`,
  `-c core.hooksPath=<devnull>` and `-c protocol.allow=never`; none
  through a shell; no diff without `--no-ext-diff --no-textconv`; no
  `safe.directory` override; no git call past the per-run cap.
- No text from the pages under `eval/revisions/cases/keyword-quoting/`
  is ever quoted in a PR description, a commit message or an issue,
  because GitHub acts on closing keywords there (D19). The evidence and
  the report refer to those cases by id and path. No closing-keyword
  exclusion reaches beyond that one directory.
- No inherited `GIT_` variable reaches git except
  `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM` and `GIT_CONFIG_NOSYSTEM`; no
  source root that is not the top of its own work tree; no `sha:`
  shorter than 7 characters checked; no move to the next repository
  after an ambiguity.
- `findings` stays read-only: no write to the wiki, the proposals
  directory or any repository, and a missing git or a non-repository
  root is a `revision_check` reason, never an error exit.
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
contract, and are listed so the spec does not reopen them. D17 was added
after the external review of PR #124 (head `7fb2dc7`); the owner
**decided D17** on 2026-11-22 **against the default** (label more real
cases first). D18 follows from that answer; the owner **decided D18** on
2026-11-22 (the default). After the second external review of PR #124
(head `02fa871`) the owner decided D19 on 2026-11-22; D20 records that
review's git requirements as settled.

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
  superseded merge page's flag kept (finding 9). *Clarified after the
  PR #124 review, the bar unchanged:* the 10 pages are derived from the
  committed file in finding 9's table (15 entries / 13 pages, less 3 / 2
  superseded, less the 1 `spearman.py` citation error, leaving 11 / 10),
  and the frozen test recomputes it; the entry counts (at most 5 of 11
  would be the matching entry form) are reported beside the binding page
  bar, not added as a second condition, which would need the owner; the
  merge page's flag means its `a24a00e` entry on the frozen
  pre-successor copy (finding 15), and the recall side rests on that one
  entry. *After D17:* a third condition joins the two, the recall
  condition on the supplementary set (D18); all three must hold. Alternatives: a stricter bar (at most 2 of 10); a fresh
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
  the measurement, and S2 reports their effect separately. In
  production the check never examines a superseded page.
- **D17. Label more real cases before measuring (decided by the owner,
  2026-11-22: NOT the default).** Owner, 2026-11-22: **label more real
  cases first, frozen before any measuring.** How, worked out for the
  spec and settled by that answer:
  - *Source:* the seven candidates of finding 17, all read offline from
    the local code-copilot-team checkout: five wiki events (the pre-pr
    playbook three times, the vLLM playbook, the run-wiki-ingest
    workflow) and two spec supersessions under issue #281. memkernel
    adds none (its two `stale` records are already in the study). The
    expected count of positives is four to seven; the inventory, its
    commits and every pin are verified by S1's frozen test against the
    checkout's objects, never fetched.
  - *Fixture:* one directory per case: the page as it stood before the
    correction (verbatim for wiki events; built in the template from the
    spec text for the two spec cases, named as built), the cited `path:`
    + `sha:` (a derived `sha:` named as such where the page had none),
    the commits that changed the source, the read commit (playing HEAD)
    and the correcting commit, each file pinned by sha256, as the
    issue 54 corpus was pinned.
  - *Labels first:* `should_flag` per case, plus any matched negative,
    each with a reason from the correction evidence, in their own
    labelling commit with no candidate code; frozen with a sha256-pinning
    test; nobody edits them after the freeze.
  - *Who labels:* the build session, from the recorded evidence; the
    owner reviews the labelling commit before the freeze, as in issue 54.
  - *The bar:* a third condition, the recall share on the supplementary
    positives (D18), combined with the two study conditions by AND; if
    the positives fall below D18's minimum, that condition is reported
    "not testable" and the bar is the two study conditions.
  - *Schedule and cuts:* the week-1 trigger moves to the end of week 2,
    the "no winner" trigger to the start of week 3 and the "S4 not
    downhill" trigger to the middle of week 4. S1 grows by 3-4h and S2
    by 1h (20.5-27h in total); 4w holds for the core, and S4 is the first
    scope at risk.
  The default was **no; state the limit.** The bar's recall side rests
  on one source entry on a superseded page, and the report says so
  plainly. Finding more true cases means searching code-copilot-team's
  history, labelling and freezing before any candidate runs, as issue 54
  froze its labels: a study of its own, which pushes S4 later.
  Alternative, as chosen: a frozen supplementary set of real cases before
  S2 runs, with the week-1 trigger moved to the end of week 2.
- **D18. The recall condition's numbers (decided by the owner, 2026-11-22: the default).**
  Owner, 2026-11-22: the default. Default: **at least 4 cases labelled `should_flag: true` for the
  condition to be tested, and a candidate must keep at least three
  quarters of them, rounded up (3 of 4, 4 of 5, 5 of 6, 6 of 7).** A
  filter that drops more than a quarter of the real reviews hides the
  very thing the finding exists for; below four positives a single case
  moves the share by a third or more, so the result would say little.
  C0 keeps every positive by construction, so the condition only bites
  on the filters. Alternatives: keep every positive (strictest, one
  missed case fails a candidate); a minimum of 3 with two thirds kept;
  report the recall count without making it a condition.
- **D19. The pre-pr playbook cases quote closing keywords (decided by
  the owner, 2026-11-22: keep them, fenced off).** Owner, 2026-11-22:
  **keep the three cases**, with these rules:
  - their pages are stored verbatim in their own directory,
    `eval/revisions/cases/keyword-quoting/`, apart from the other cases;
  - the repository's closing-keyword check, and any "no closing keyword
    in any file" test the build adds, exclude exactly that directory and
    nothing else. Today no check in this repository scans files: the
    pre-PR check sessions run scans commit messages and the PR body
    (`scripts/pre-pr-check.sh`, from code-copilot-team), so the rule
    binds any file check that is added;
  - no text from those case pages is ever quoted in a PR description, a
    commit message or an issue, because GitHub acts on it (no-gos and
    the circuit breaker's "never" list);
  - the evidence and the report refer to those cases by id and path,
    never by quoting their keyword lines.
  Why it was a question: the issue 54 study excluded this page from its
  fixture for exactly this reason (`eval/patterns/README.md` 249), and
  the three cases are a large share of the supplementary set (finding
  17). The alternatives were to drop the three cases (leaving four
  candidates, near D18's minimum) or to redact the keyword lines (which
  would change the bytes the case is meant to preserve).
- **D20. The second review's git requirements (settled by the review of
  PR #124 at `02fa871`).** Every git call gets a clean environment: all
  `GIT_` variables removed except `GIT_CONFIG_GLOBAL`,
  `GIT_CONFIG_SYSTEM` and `GIT_CONFIG_NOSYSTEM`, then
  `GIT_CEILING_DIRECTORIES`, `GIT_TERMINAL_PROMPT=0` and `LC_ALL=C` set;
  `paths.git_toplevel` is left as it is. A source root must be the top of
  its own work tree (resolved `--show-toplevel` equals the resolved
  directory), else it is skipped as "not the top of a git work tree".
  A `sha:` must be at least 7 hex characters, else "not checked: too
  short"; an ambiguous prefix is "not checked: ambiguous in <repo>", the
  search stops there and never yields `source-not-at-revision`. S3 holds
  the detail and the tests.

## Circuit breaker

Core is S1 (with the supplementary set of real cases, labelled, reviewed by the
owner and frozen before any candidate code, D17), S2 (published whatever
it shows, run with code-copilot-team's checkout as a source root), S3 (the exact kind, the repository matching
across the root's repository and the source roots by D6, the git
hardening and call cap, and the `revision_check` result), S5's
documents for what ships, and S6. S4
ships only if a candidate clears the frozen bar, and since labelling
now comes first it is the first scope at risk in 4w. The source-root
matching and the supplementary set are the owner's decisions and are not
on the cut list; the set is frozen with what is labelled when trigger 1
fires.

The cut order, first to last, each with its trigger:

1. **End of week 2 (moved from week 1 by D17), if S1's freeze has not
   landed:** the candidates narrow to C0, C1 and C2 (C3 and C4 dropped
   and named as unmeasured), and the supplementary set freezes with the
   cases the owner has reviewed by then; below D18's minimum its recall
   condition is reported not testable.
2. **Start of week 3, if S2 shows no candidate clearing the bar, or S2
   has not run:** S4 is cut. The release ships S3, and issue 120 stays
   open with the measurement as its evidence (D4, D11).
3. **Middle of week 4, if S4 is not downhill:** S4 is cut the same way.

- **End of week 4.** S6 ships what is true. If the release cannot be
  cut, the change waits under `[Unreleased]`.
- **Never, to save time:** cut S3 down to the root's repository only
  (D6); put a model on any path from `findings`, `approve` or
  `review_state`; read over the network, a partial clone's lazy fetch
  included; fetch into, or write to, a source root; run a git command
  outside S3's read-only set, without its `-c` overrides, without
  `--no-ext-diff --no-textconv` on a diff, or past the call cap; drop
  the hardening tests; pass an unvalidated `sha:` or path to git, or use
  a shell; withdraw or alter an approval or change what `find` returns;
  make `lint --health --strict` fail on a new kind; add a frontmatter
  key, page type, runtime dependency, exit code or MCP tool; bump
  `findings_version`; edit a label, a case, a candidate or the bar after
  the freeze; skip the owner's review of the labelling commit; add a case
  after the run; fetch a case's history over the network; quote text
  from the keyword-quoting case pages in a PR description, commit
  message or issue, or widen the closing-keyword exclusion beyond that
  directory (D19); let an inherited `GIT_` variable other than the three
  config-location ones reach git, accept a source root that is not the
  top of its work tree, check a `sha:` under 7 characters, or move on to
  another repository after an ambiguity;
  edit `eval/patterns/`'s frozen files, memkernel or code-copilot-team;
  weaken or skip a test.

"Exhausted" means four working weeks have passed. A third review round
on one PR is an escalation to the owner, who chooses a fix session, a
cut from the list above, or a hold.

## Questions for the owner

D1-D11 were asked by the main session on 2026-11-22 and answered. The
owner chose the default for ten of the eleven and decided D6 against
it. D17, added after the external review of PR #124, was answered on
2026-11-22 against the default: label more real cases first, frozen
before any measuring. **D18 was answered on 2026-11-22 with the default**, following from it: at least 4
positives for the recall condition to be tested, and keep at least
three quarters of them, rounded up? Default: yes, those numbers.
After the second external review of PR #124, **D19 was answered on
2026-11-22**: keep the three pre-pr playbook cases, fenced off in their
own directory.

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
- D17 **not the default: label more real cases first**: finding 17's
  seven candidates from code-copilot-team's history, each a frozen
  fixture, labelled by the build session from the correction evidence,
  the labelling commit reviewed by the owner, frozen before any
  candidate code; a recall condition joins the bar (D18).
- D18 the default: at least 4 positives, keep at least three quarters,
  rounded up.
- D19 **keep the three pre-pr playbook cases, fenced off**: stored
  verbatim in `eval/revisions/cases/keyword-quoting/`, the only directory
  any closing-keyword file check excludes; never quoted in a PR
  description, commit message or issue; referred to by id and path.

## Bet log

| Date | bet_status | Note |
|------|------------|------|
| 2026-11-22 | shaping | Pitch drafted from wiki-studio issue 120 (no comments) and the external reviewer's shaping points. wiki-studio read at main ff30e34 (0.10.0): `health_lint.py`, `findings.py`, `api.py` (findings), `nightly.py`, `mcp_adapter/tools.py`, `contract.py`, `paths.py`, `audit_flush.py`, `review.py`, `discovery.py`, `fact_diff.py`, `schema/page-types.md`, `schema/citation-rules.md`, `docs/knowledge-contract.md`, `docs/nightly.md`, `docs/patterns.md`, `eval/patterns/` (report question 5, README revisit signals, `staleness.py`, `results/staleness.json`, the frozen-labels test). |
| 2026-11-22 | shaping → shaped | 6 scopes, 4w, work content 13-18h. Core: S1 (freeze), S2 (measurement), S3 (exact `source-not-at-revision`), S5, S6. S4 (`source-revision-changed`) only if a candidate clears the frozen bar. On the recorded data the three structural rules leave 10 flagged pages, all false, and the study's one true case sits on a superseded page. 16 decisions; D1-D11 open for the owner with defaults, not yet asked (AskUserQuestion was unavailable to the shaping agent). |
| 2026-11-22 | shaped (decided) | Owner answered D1-D11 in the main session (2026-11-22). Ten defaults; D6 against the default: the check also searches the existing source roots (`--source-root` / `WIKI_STUDIO_SOURCE_ROOTS`) after the root's repository, the `sha:` matched by `git cat-file -e <sha>^{commit}` offline, the first usable repository that has it wins and is named; no match with every repository usable is `source-not-at-revision`, with one skipped the source is not checked; non-repository, shallow or partial source roots are skipped with a reason and never fetched. D1: 4w, the full project, knowing S4 ships only if a candidate clears the bar. The main session verified finding 9 against `results/staleness.json` (13 pages with a changed source; 2 superseded, one of them the true case; of 11 live pages, 1 citation error and 10 false). Updated: frontmatter circuit breaker; findings 7, 8 and 9 (recall cannot be estimated); Appetite (14.5-20h; S3 3.5-5h, S5 2.5-3.5h); Solution shape (the repository matching and the per-repository `revision_check`); S2 (code-copilot-team's checkout as a source root, an offline local clone at the pin); S3 (matching and its tests); S4; S5 (source-root help and docs rows); rabbit holes (cost across roots, ambiguous short shas, `stale-claim` still root-only as a follow-up, thin source roots); no-gos; Decisions (intro, D1-D11, D14, D16); Circuit breaker (source-root matching not cuttable); Questions for the owner (answered). |
| 2026-11-22 | shaped (revised after review) | External review of PR #124 (head 7fb2dc7), four points, written before the reviewer read the pitch. (1) The bar is derived from the committed file: finding 9 gains a table from `results/staleness.json`'s fields joined to each page's `superseded_by` (15 changed entries / 14 citations / 13 pages, less 3 / 2 / 2 superseded, less the `spearman.py` citation error, leaving 11 / 11 / 10), recomputed by S1's frozen test; entry counts are reported beside the owner's page bar, which is unchanged. (2) The shipped check never examines a superseded page; the merge page's flag is measured on a frozen pre-successor copy (finding 15: the page has one commit and was born superseded, so no older commit exists) and the recall side rests on that one entry; D17 added, open, default no. (3) Git hardening in S3, no-gos and circuit breaker: read-only tree-to-tree plumbing, `--no-ext-diff --no-textconv`, `--no-pager -c core.fsmonitor=false -c core.hooksPath=<devnull> -c protocol.allow=never` on every call; system and global config kept, because they carry `safe.directory` (finding 16); a per-run call cap with "not checked" past it; `findings` read-only; tests with marker-writing fsmonitor, external diff and textconv scripts. (4) S5 lists every place that defines source roots (`git grep` at ff30e34): knowledge contract, README 49 and 502, `docs/mcp-adapter.md` 35, packaged `lint-rules.md` 75, `cli.py` help and `info`, `mcp_adapter/config.py` help, `paths.py` docstrings. Appetite 16.5-22h (S1 2-2.5h, S3 4.5-6h, S5 3-4h), still 4w. Updated: frontmatter circuit breaker; findings 9, 15, 16; Appetite; Solution shape; S1, S2, S3, S5; rabbit holes; no-gos; Decisions (intro, D3 clarified, D16, D17); Circuit breaker; Questions for the owner. |
| 2026-11-22 | shaped (decided, D17) | Owner answered D17 on 2026-11-22, against the default: label more real cases first, frozen before any measuring. Searched offline: memkernel at a9d229c adds none (its two #57 `stale` records are already the study's); code-copilot-team at 2a60217 has seven candidates (finding 17): the pre-pr playbook at 87bbc65, a9628e5 and fc28fc3 (script changes d0e48c3, 34a752d, 801309f), the vLLM playbook at a9a3b1e, the run-wiki-ingest workflow after 68bff41, and the #281 supersessions in `specs/provider-config/spec.md` (6529175) and `specs/benchmark-adapters-backends/spec.md` (e59f7cc). D17 records the source, fixtures, labels-first, who labels (build session, owner reviews the labelling commit), the bar's third condition combined by AND, and the schedule. D18 added, open: minimum 4 positives, keep at least three quarters rounded up. Appetite 20.5-27h (S1 5-6.5h, S2 4-5h), 4w holds for the core, S4 first at risk; triggers moved to end of week 2, start of week 3 and middle of week 4. Updated: frontmatter circuit breaker; finding 17; Appetite and planned order; Solution shape (the supplementary set, the combined bar); S1, S2; rabbit holes; Decisions (intro, D3 note, D17, D18); Circuit breaker; Questions for the owner. |
| 2026-11-22 | shaped (decided, D18) | Owner answered D18 on 2026-11-22 with the default: at least 4 real cases for the recall condition to be tested, and a candidate keeps at least three quarters of them, rounded up (3 of 4, 4 of 5, 5 of 6, 6 of 7). No decision remains open. |
| 2026-11-22 | shaped (revised after review 2) | External review of PR #124 at 02fa871 asked for small changes; the owner decided the one decision the same day. D19 added (owner): keep the three pre-pr playbook cases (their versions at 87bbc65^, 87bbc65, a9628e5 and fc28fc3^ quote closing-keyword phrases on 9, 13, 18 and 18 lines; issue 54 left the page out for that reason, `eval/patterns/README.md` 249), stored verbatim in `eval/revisions/cases/keyword-quoting/`, the only directory a closing-keyword file check excludes; never quoted in a PR description, commit message or issue; referred to by id and path. D20 added (settled by the review): every git call's environment drops all `GIT_` variables except `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM` and `GIT_CONFIG_NOSYSTEM` (covering git 2.53's `--local-env-vars` list) and sets `GIT_CEILING_DIRECTORIES`, `GIT_TERMINAL_PROMPT=0`, `LC_ALL=C`; `paths.git_toplevel` left as it is (inside a hook it finds the hook's own repository, and changing it would change every verb); a source root must equal its resolved `--show-toplevel`, else "not the top of a git work tree", with the ceiling as a second guard; `sha:` minimum 7 hex ("not checked: too short"), an ambiguous prefix is "not checked: ambiguous in <repo>" and stops the search. Updated: frontmatter circuit breaker; finding 17; Solution shape (layout, the candidate list, matching, no-commit rule); S1; S3 (sha rules, clean environment, top-of-work-tree check, tests for each); rabbit holes; no-gos; Decisions (intro, D19, D20); Circuit breaker; Questions for the owner. |
