# The revision-check study (issue 120)

This directory holds the measurement that issue 120 asks for before a
revision-aware check for a page's cited sources is specified. The shaping
record is the pitch `specs/pitches/120-revision-aware-stale-check/pitch.md`;
the bundle is `specs/wiki-studio-0-11-0/`. It reads wiki-studio at commit
`a75a63a304f7353e241f5bda42dd3ba08cfac408`, the base of the branch this
directory was written on.

**What is measured.** Five model-free candidate filters, C0 to C4, on:

- their false alarms on the issue 54 study's 10 false pages and 11 source
  entries;
- whether each keeps the merge page's flag on the pre-successor copy;
- recall on the supplementary cases, as a count out of n;
- git processes and wall time.

**What is not measured.** A recall estimate; agent behaviour; any repository
other than code-copilot-team.

`eval/patterns/` (the issue 54 study) is read and never edited. No result
depends on a model: every label here was written by reading files and git
history, and every score will be computed by code from recorded text.

## Layout

```
README.md         this file: labels, cases, candidates, bar, selection, call plan
labels.json       the issue 54 study's 24 sources with needs_review and citation_error
protocol.json     the same protocol as fields: the 10 pages, the 11 entries, C0-C4, the bar
cases/            one directory per supplementary case: page.md and case.json
cases/keyword-quoting/   the three fenced cases (see "The fence")
pre-successor/    the merge page as it stood before its successor existed
```

This directory holds no candidate code. While the labels were written no
diff, token or anchor computation was run.

## The study's labels

`labels.json` lists the 14 pages of `eval/patterns/results/staleness.json` in
that file's order, and under each its sources (24 in all), each with:

- `path`, `sha` and `revision_check`, copied from `staleness.json`;
- `judgment`, the cell of the judgment column in `eval/patterns/README.md`'s
  per-pattern table for that row, verbatim, or `null` where the cell is "—";
- `needs_review`, true for exactly one entry: the merge page's
  `specs/auto-build-loop-merge-profile/spec.md` @ `a24a00e`, the one row whose
  judgment says the `Revisit when:` condition has arrived;
- `citation_error`, true for exactly one entry: the judge-statistics page's
  `scripts/benchmark_runner/calibration/spearman.py` @ `dafbc5b`, a commit
  that does not contain the file.

Each page carries `superseded`, true when its frontmatter under
`eval/patterns/wiki/` has `superseded_by`.

The judgments were made after the plain check ran and before any filter
existed. They were written for the issue 54 study, by reading the cited file
at the pin against each page's `Revisit when:` line; nothing in them was
written with a candidate in view, and they are copied here unchanged.

## From 13 flagged pages to 10

The plain check of the issue 54 study flagged 13 pages. The revision kind is
judged on 10 of them. The recipe, from the committed files' own fields:

1. select the sources with `revision_check == "changed"` in
   `eval/patterns/results/staleness.json`;
2. join each `page` to its frontmatter under `eval/patterns/wiki/` and drop
   the pages that carry `superseded_by`;
3. drop the `spearman.py` @ `dafbc5b` entry, which is absent at its `sha:`;
4. count source entries, page-and-file citations and pages.

| Step | Source entries | Page-and-file citations | Pages |
|---|---|---|---|
| `revision_check == "changed"` | 15 | 14 | 13 |
| less the pages whose frontmatter has `superseded_by`: the benchmark UI page (one entry) and the merge page (one file at two commits) | -3 | -2 | -2 |
| live pages with a changed source | 12 | 12 | 11 |
| less the judge-statistics `spearman.py` @ `dafbc5b` entry; the page's other source is unchanged, so the page drops too | -1 | -1 | -1 |
| left for the revision kind | 11 | 11 | 10 |

All 11 entries on those 10 pages are labelled no review. `protocol.json`
lists the 10 pages (`false_pages`) and the 11 entries (`false_entries`) by
page, path and sha. The one true entry, the merge page's `a24a00e` source, is
on a superseded page and is measured on the pre-successor copy below.

## The supplementary cases

Seven candidates from code-copilot-team's history, read offline from the local
checkout beside this repository (`../code-copilot-team`) with read-only
`git rev-parse`, `git show` and `git log`. Nothing was fetched and nothing was
written there.

### The read rule

Each case has a **correcting commit**: the commit that corrected the page, or
for a spec case the commit that superseded the decision in the spec. Each has
a **read commit**, the commit that plays HEAD:

- `read_rule: "parent"`: the correcting commit's parent. Used when the cited
  source changed before the correcting commit.
- `read_rule: "correcting"`: the correcting commit itself. Used when the
  correcting commit also changed the cited source; its parent would predate
  the change, and no check could ever flag the case.

The page is always the page as it stood at the correcting commit's parent.

A case read at its correcting commit is **counterfactual**: it shows the
repository as if the source change had landed and the page had not been
updated in the same commit. The page is the parent's page and the cited `sha:`
stays as recorded or derived.

### The inventory

Every commit below is a full hash, resolved by hand. "Source" is the cited
path at the cited `sha:`.

| Case | Directory | Source | Read rule | `should_flag` |
|---|---|---|---|---|
| `pre-pr-strict-mode` | `cases/keyword-quoting/pre-pr-strict-mode/` | `scripts/pre-pr-check.sh` @ `33beb17` (derived) | correcting, counterfactual | true |
| `pre-pr-keyword-set` | `cases/keyword-quoting/pre-pr-keyword-set/` | `scripts/pre-pr-check.sh` @ `87bbc65` (derived) | correcting, counterfactual | true |
| `pre-pr-doc-audit` | `cases/keyword-quoting/pre-pr-doc-audit/` | `scripts/pre-pr-check.sh` @ `a9628e5` (derived) | parent | true |
| `vllm-backend-doc` | `cases/vllm-backend-doc/` | `benchmarks/backends/vllm.md` @ `c8b1f97` | correcting, counterfactual | false |
| `run-wiki-ingest-rules` | `cases/run-wiki-ingest-rules/` | `knowledge/wiki/schema/ingest-rules.md` @ `f6b1ee7` | parent | false |
| `provider-config-guarantee` | `cases/provider-config-guarantee/` | `specs/provider-config/spec.md` @ `840119f` | correcting, counterfactual | true |
| `benchmark-provider-id` | `cases/benchmark-provider-id/` | `specs/benchmark-adapters-backends/spec.md` @ `6529175` | correcting, counterfactual | true |

The commits of each case:

- `pre-pr-strict-mode`: page from `23fc078bfe0713236953dd8d5dda88e50a883865`;
  derived `sha:` `33beb17b242c12b2c91403a696c28703905a9efb`; source changed,
  page corrected and case read at
  `87bbc6515cf46051bef1c69653607303cdc5e63f`.
- `pre-pr-keyword-set`: page from
  `87bbc6515cf46051bef1c69653607303cdc5e63f`, which is also the derived
  `sha:`; source changed, page corrected and case read at
  `a9628e506177eb02110f3d7e007c898eda3b8480`.
- `pre-pr-doc-audit`: page from and case read at
  `69926b16efaa85e3ee64f5d767e96a8079b09982`; derived `sha:`
  `a9628e506177eb02110f3d7e007c898eda3b8480`; source changed in
  `d0e48c3962ddf18269d5859f25fa394c2beda3e7`,
  `34a752d8b162596ae6566f22d1601ce6e53ff25f` and
  `801309fa1910498416460cada4faaa1929daa196`; page corrected in
  `fc28fc3f257564da640a2a3c70b187974c189334`.
- `vllm-backend-doc`: page from `fe9c69098fe7ecb5a65af0d3bc707f6bc128691d`;
  cited `sha:` `c8b1f97d91333d7f4e82cf9de7f783e0089dc6cc`; source introduced
  in `9cbffbb9e7ad2baf59484ba7afd2e0d468a51001` and changed in
  `a9a3b1e43894017cc28353b96d78ada85e8f9ac7`, which also corrected the page
  and is the read commit.
- `run-wiki-ingest-rules`: page from and case read at
  `d3179fd3b037df88f520a6428e1e1af1d826abfb`; cited `sha:`
  `f6b1ee77b0b4fba8dd0f176a7d589c019159c3f4`; source changed in
  `68bff413e829f706b6a732742a62fa219091a45a`; page edited in
  `5dc717d76e19ea80f40978ed861619394320116c`.
- `provider-config-guarantee`: decision text from and cited `sha:`
  `840119fa71783465b89df0b7b1c809c8dfbda8be`; spec superseded in place and
  case read at `652917572b604235778c23c7175d54de2d3cd51c`.
- `benchmark-provider-id`: decision text from and cited `sha:`
  `652917572b604235778c23c7175d54de2d3cd51c`; spec superseded in place and
  case read at `e59f7cc5ab8f835b2160d0d89626a0e8c76acaad`.

**Rejected candidates.** None of the seven was dropped as a fixture. Two are
labelled `should_flag: false`, with these reasons:

- `vllm-backend-doc`. The pitch expected a page whose text was edited after
  its cited document changed. The history shows otherwise: the cited file
  does not exist at the cited commit `c8b1f97` (it was introduced one commit
  later, in `9cbffbb`), and the correcting commit changed only the page's two
  `sha:` values. So the entry is a citation error, which the third structural
  rule sends to the exact kind, and no revision flag is due. Its
  `sha256.source_at_sha` is `null`, meaning "absent at that commit".
- `run-wiki-ingest-rules`. The cited rules file gained a section on writing
  style and kept the four-question gate the page cites it for. The page's
  edit answered the removal of two scripts and an environment variable that
  the page names, an uncited change. The change to the cited file did not
  call for the review that followed.

The pitch also names correction markers that are no revision event and were
never candidates: `docs/dgx-spark/vllm-qwen38.md` and the review-round
sections of several plans, each written in the same commit as the text it
corrects or before approval. memkernel adds no case: its two stale records
are already in the issue 54 study.

**The count.** Five cases are labelled `should_flag: true`: the three
keyword-quoting cases (one page at three moments) and the two built pages.
Without the two built pages the count is three.

### The fixtures

Each case directory holds `page.md` and `case.json`.

`page.md`:

- for the five wiki events, the page's bytes at the correcting commit's parent
  (`git show <parent>:knowledge/wiki/<path>`), verbatim. One exception: the
  three keyword-quoting pages cite their script as `path:` with no `sha:`, so
  each gains one line, a **derived** `sha:`, the commit of the page's previous
  revision. `case.json` says so (`sha_derived: true`, `sha_derivation`).
- for the two spec cases, a **built** `decision` page in the `docs/patterns.md`
  template, written for this study from the spec's decision text at the
  correcting commit's parent. Its backticked identifiers are only ones that
  text already backticks. It cites the spec as `path:` with `sha:` the
  correcting commit's parent. Its `Revisit when:` line says "not recorded in
  the spec", because the spec states no trigger and writing one now would be
  written with the correction in view.

`case.json` keys: `id`; `repository` (`code-copilot-team`); `page_origin`
(`verbatim` or `built`); `page_from` (the repository path and commit the page
bytes or the decision text came from); `path` and `sha` (the cited source);
`sha_derived` (with `sha_derivation` when true); `source_change_commits`;
`read_commit`; `read_rule`; `correcting_commit`; `sha256` (`page_md`,
`source_at_sha`, `source_at_read`); `evidence`; `negative`; `should_flag`;
`reason`.

`sha256.source_at_sha` and `sha256.source_at_read` are the sha256 of the bytes
`git show <commit>:<path>` prints, computed by hand in the checkout. CI has no
checkout and cannot recheck them; the measurement's record verifies them
against the checkout before it records anything. `evidence` names the
correcting commit (its message and its diff) and the paths read in that diff.
It quotes nothing.

### The labels

`should_flag` answers one question from the recorded correction evidence: did
the change to the cited file call for the review that followed? Each label
has a one-line `reason`. The labels come only from the page, the cited file at
the two commits, and the correcting commit's message and diff. No candidate
was consulted.

**Matched negatives.** A matched negative would be a change to the same cited
file that the page's next revision did not answer, as its own case directory
(`<case-id>-negative`, `negative: true`, `should_flag: false`). None was
added. Every change to the script between two revisions of the keyword-quoting
page is one that the next revision answers, as far as the allowed evidence
shows, and the other cited files have no further change before their
correcting commits. `run-wiki-ingest-rules` is labelled false as a case in its
own right, not as a matched negative.

## The pre-successor copy

The study's one true entry sits on the merge page, which is superseded, and a
superseded page is skipped. The page has one commit in this repository and
was written already superseded, so "the page before its successor" cannot be
checked out. `pre-successor/merge-require-green-ci-was-never-read.md` is
`eval/patterns/wiki/decisions/merge-require-green-ci-was-never-read.md` with
exactly five edits. Each rests on memkernel #57's record of the decision,
`eval/patterns/corpus/decisions-57.md` lines 143-151:

| Edit | The record line it rests on |
|---|---|
| The `superseded_by` line is removed | 151: the decision is dated 2026-07-14 and is stale only since 2026-10-29, so on its date it had no successor |
| `status: deprecated` becomes `status: stable` | 151: the same dates; the record was a live decision until 2026-10-29 |
| The `e39969f` source is removed; only the `a24a00e` source stays | 149: `evidence` cites the spec at `a24a00e`, and names `e39969f` separately as the correction |
| The `Correction:` line is removed, with the blank line before it | 149: the correction is a later item, added when the decision went stale |
| `Confidence: high: …` becomes `Confidence: high.` | 149 and 151: the removed reason speaks of the correction, which did not exist yet; the level is kept |

No other line differs.

## The protocol

`protocol.json` records what follows as fields, so that the scoring reads the
candidates, the 10 pages and the bar from it.

### The three structural rules

They apply before any candidate.

1. A page whose frontmatter carries `superseded_by` is skipped.
2. A source whose path is missing at the matched repository's HEAD gets no
   revision kind.
3. A source whose path is missing at its `sha:` goes to the exact kind
   (`source-not-at-revision`) and gets no revision kind.

### Changed lines

The changed lines of a source are the `+` and `-` lines of the hunks of
`git diff -U0` between the cited `sha:` and HEAD. File headers and hunk
headers are excluded.

### The candidates

- **C0, plain change.** The path differs between the `sha:` and HEAD.
- **C1, change ignoring whitespace.** The path still differs under
  `-w --ignore-blank-lines`.
- **C2, anchor touch.** Either of:
  - a changed line contains one of the page's anchors. An anchor is a
    backticked identifier or a `file:line` reference, extracted from the page
    body with `wiki_studio.fact_diff`'s regexes unchanged (`_BACKTICK_RE`,
    normalized as that module does, and `_PATH_LINE_RE`, over the body with
    fenced code blanked). Each identifier also counts in its last dotted
    component (`correlate.run` also as `run`). "Contains" is a substring
    match.
  - a hunk of a Markdown source (a path ending in `.md`) lies under a heading
    whose text occurs in the page body, case-insensitive. The heading is the
    nearest ATX heading at or above the hunk's first old-side line, in the
    source at the cited `sha:`. For a pure insertion it is the line the
    insertion follows. A hunk with no heading above it does not fire this
    rule.

  A page with no anchor falls back to C1.
- **C3, Revisit-when tokens.** A changed line shares a token with the page's
  `Revisit when:` line. Tokens come from `wiki_studio.wiki_state._tokenise`,
  which drops its stop list. The `Revisit when:` line is the first body line
  outside fenced code whose text, after leading whitespace and an optional
  list marker, starts with `Revisit when:`; it is read to the end of that
  line. A page without one, or whose line says "not recorded", falls back to
  C1.
- **C4, both.** C2 and C3 both flag the source, each with its own fallback.

### The bar

A candidate passes only if all three conditions hold.

1. **False pages.** At most 5 of the 10 false pages are flagged. This
   condition binds in pages; the count of the 11 false entries flagged is
   reported beside it.
2. **The true entry.** The merge page's `a24a00e` flag is kept on the
   pre-successor copy.
3. **Recall on the supplementary cases.** With at least 4 cases labelled
   `should_flag: true` (matched negatives excluded), the candidate keeps at
   least three quarters of them, rounded up: 3 of 4, 4 of 5, 5 of 6, 6 of 7.
   With fewer than 4, this condition is "not testable" and the bar is
   conditions 1 and 2.

Matched negatives are reported and are not part of the bar.

**The two cases labelled `should_flag: false`** (`run-wiki-ingest-rules`, a
real change to a cited file that called for no review, and
`vllm-backend-doc`, a citation error that belongs to the exact kind) are
reported too. For each candidate the report says whether it flags each of
them. They are reported only and are not part of the bar.

### Selection and the winner line

Among the candidates that pass, the one with the fewest false pages wins. A
tie goes to the fewer git processes on the study run. A remaining tie goes to
the lower-numbered candidate. If none passes there is no winner.

The report states the result on exactly one line, in one of two forms:
`Winner: C<n>` or `Winner: none`.

### The cost measure and the call plan

Cost is git processes and wall time per run, counted on this call plan:

| Step | When | Command |
|---|---|---|
| p1 | per repository, once | `rev-parse --show-toplevel --is-shallow-repository HEAD` |
| p2 | per repository, once, when p1 succeeds and the repository is not shallow | `config --get extensions.partialclone` |
| p3 | per distinct `sha:`, repository by repository in order until the first match or ambiguity | `rev-parse --verify <sha>^{commit}` |
| p4 | per matched (repository, full commit) | `diff-tree -r --name-status --no-renames --relative`, limited to the cited paths |
| p5 | per changed cited path, only as a candidate needs it: C1 and the C1 fallbacks | `diff --quiet -w --ignore-blank-lines` |
| p6 | per changed cited path, only as a candidate needs it: C2, C3 and C4 | `diff -U0` |
| p7 | per changed cited Markdown path, only as a candidate needs it: the heading rule of C2 and C4 | `cat-file blob <commit>:./<path>` |

p4 carries `--relative` because git takes the path filter relative to the
directory it runs in, but prints paths relative to the repository's top
unless told otherwise. With it the printed paths match the cited paths even
when the root is a subdirectory of its repository.

### Points this protocol settles beyond the spec's wording

Three details are the labeller's reading, written down before any candidate
code so that the owner can change them at the review:

- an anchor matches a changed line as a substring;
- a hunk with no heading above it does not fire C2's heading rule;
- "says not recorded" means the `Revisit when:` line contains the words "not
  recorded", in any letter case.

## Who labelled, the review and the freeze

The build session wrote every label in this directory in one labelling phase,
with no candidate code present. The owner reviews that commit. A label, a
case or the bar that the owner changes is changed by a commit on the branch
before the freeze, never after it. The freeze then pins `labels.json`,
`protocol.json`, this README, the pre-successor copy and every case file by
sha256.

**Cut 1.** If the end of week 2 of the cycle passes without the freeze and the
owner invokes the cut at the review, the freeze phase first narrows the
candidates to C0, C1 and C2 and names C3 and C4 as unmeasured. With fewer
positives than the minimum of 4, condition 3 reads "not testable".

**No case is added after the run.** A disagreement with a label found later is
reported in the study's report and is never patched here.

## The fence

Three cases, `pre-pr-strict-mode`, `pre-pr-keyword-set` and
`pre-pr-doc-audit`, live apart under `cases/keyword-quoting/`. Their pages
quote closing-keyword phrases verbatim, and two of their correcting commits
carry such phrases in their messages. The rules:

- no text from those pages, and no text from those commits' messages, appears
  outside `cases/keyword-quoting/`: not in a label reason, this README,
  `labels.json`, `protocol.json`, a results file, a report, a commit message,
  pull request text or an issue;
- this README, `labels.json` and `protocol.json` name those cases by id and
  path only; their labels and reasons are in their own `case.json` files, in
  the labeller's own words, quoting nothing;
- anything recorded from those cases later (source hunks included) is stored
  under that directory;
- any closing-keyword file check excludes exactly
  `eval/revisions/cases/keyword-quoting/` and nothing else.
  `tests/test_revisions_fixture.py` runs such a check over the rest of this
  directory.
