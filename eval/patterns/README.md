# Reusable engineering patterns: a research spike (issue 54)

This is a study for [issue 54](https://github.com/gosha70/wiki-studio/issues/54).
It is a research spike, and its deliverable is a recommendation — docs and a
template, a separately specified enhancement, or no change — not a schema, a
page type or a deduplication service.

The inventory below reads wiki-studio at the build branch's base commit,
`43aab76000ccb7acf8d5cda1ae5cdd929e452f72` (0.10.0 released). Every file and
line it cites is that commit's, and each opens at the line cited.

## What the study measures, and what it does not

It measures what wiki-studio already does with a reusable pattern:

- whether a `decision` page, unchanged, has a slot for each of issue 54's
  seven fields — intent, applicable constraints, canonical implementation
  link, rejected alternatives, validation evidence, owner and status, and
  revisit criteria;
- what the real verbs do while a candidate pattern travels from a pending
  proposal, through a lint-gated promotion, to an approval bound to the bytes
  a reviewer saw, and what a later edit does to that approval;
- whether `find` puts the right pattern page in front of a reader for the
  task the pattern claims to help with, with each of the two rankers;
- whether the existing model-free pair signals expose near-duplicate
  patterns, with no merge and no edit;
- what the existing checks report when a pattern's cited source changes or
  the pattern itself is superseded.

It does **not** measure whether an agent chooses better with patterns in
reach. That needs agent runs at historical commits and is the subject of
issue 75; nothing here measures agent behaviour, and no result depends on a
model — every claim is computed from code and files.

Nothing under `src/wiki_studio/` changes: no verb, flag, exit code, MCP
tool, `findings` kind, lint rule, prompt, persona, packaged schema document,
frontmatter key or page type is added or changed.

## Fit map: issue 54's seven fields against today's `decision` page

A pattern record, as issue 54 defines it, has seven fields. The table maps
each to the existing `decision` template — its four H2 sections and the
universal frontmatter (`page-types.md` 104-121 and 11-25) — and says what
checks the field, if anything, and what a round trip through memkernel's
wiki bridge carries. The bridge keeps a page's title, body, single-line
frontmatter scalars and `sources:`; the approval record is not page text and
does not cross it.

File references are repository-relative; `page-types.md` abbreviates
`src/wiki_studio/schema/page-types.md`.

| Issue 54 field | Where it can live today | What checks it | What reaches memkernel |
|---|---|---|---|
| Intent | `## Decision`, the section's prose (`page-types.md` 109) | No content check. Prose lint advises on sentence length only (`src/wiki_studio/prose_lint.py` 22-27); approval binds the bytes the approver saw but checks nothing about their content (`src/wiki_studio/review.py` 1-21) | Body |
| Applicable constraints | `## Context` (`page-types.md` 110) | Nothing: structural lint has no body-section rule (`src/wiki_studio/lint.py` 5-23) | Body |
| Canonical implementation link | A `sources:` entry with `path:` and `sha:` (`page-types.md` 18-20); a body link where the evidence has no commit | Structural lint requires `sources:` (`lint.py` 372-373); `stale-claim` checks that the path exists, never that `sha:` is current (`src/wiki_studio/health_lint.py` 110-155) | `sources:`; a body link only as body text |
| Rejected alternatives | `## Alternatives considered`, one bullet per option (`page-types.md` 111) | Nothing | Body |
| Validation evidence | `## Consequences` prose — the tests and confidence stated there — and `sources:` entries | Only `sources:` presence (`lint.py` 372-373) and the path-existence check (`health_lint.py` 110-155) | Body and `sources:` |
| Owner and status | Owner: the approver named in the approval record by `--by` (`src/wiki_studio/api.py` 783-789; `src/wiki_studio/cli.py` 322) — there is no maintainer slot. Status: the frontmatter `status:` scalar, `draft`, `stable` or `deprecated` (`page-types.md` 16) | Approval names who approved which bytes, not a maintainer (`review.py` 1-21); `findings` reports the review state (`src/wiki_studio/findings.py` 70-83). `status:` never approves a page (`page-types.md` 46-49) | The `status:` scalar; the approver is not a page field and does not cross |
| Revisit criteria | A `## Consequences` body line (`page-types.md` 112) | Nothing: neither lint nor `findings` reads it | Body |

## Behaviour inventory

One paragraph per behaviour, with file and line at the commit above. The
paragraphs describe what the code does; none quotes it.

**Page types and the `decision` template.** Every page carries exactly one
page type, and the type names the directory the page lives in; the
structural linter checks the placement (`page-types.md` 3-5; `lint.py`
349-370). A `decision` page lives under `decisions/` and has four required
H2 sections — `## Decision`, `## Context`, `## Alternatives considered` and
`## Consequences` — with status and date in the frontmatter rather than in
`## Status` or `## Date` H2s (`page-types.md` 104-121). Those four sections
are the only body slots a pattern convention can use without a schema
change, and no code requires them (see structural lint, below).

**`propose --from` and `promote`.** `propose --from DIR` reads a directory
laid out like the wiki and writes a pending proposal, adding a `page_id` to
every page it creates (`cli.py` 542-568, `--from` at 550; `page-types.md`
36-39); `api.propose` is at `api.py` 600. `promote` (`api.py` 721) validates
a patch-set against a staged copy of the wiki — per-edit semantics and the
structural linter — under the wiki lock, and it is the only code path that
writes into the wiki directory: it commits only the paths the patch-set
names and rolls back on an exception (`src/wiki_studio/promoter.py` 5-14,
22-33). A candidate pattern is therefore a pending proposal first, and it
enters the wiki only when a promotion passes validation.

**Approval and `review_state`.** An approval is one immutable record per
decision under `<wiki>/.audit/approvals/`, keyed by the page key, the sha256
of the reviewed revision and the policy hash (`review.py` 1-21).
`approve --revision` takes the sha256 that `read --json` printed and refuses
a page whose live bytes differ (`api.py` 783-811; `cli.py` 302-322,
`--revision` at 315-320). `review_state` reads the verified records only —
it takes no lock and calls no model — and reports a page approved, stale,
policy-changed, superseded or unapproved from bytes; frontmatter never makes
a page approved (`api.py` 818-834; `review.py` 19-20).

**Citations.** `sources:` is required on every page except `index` and `log`
(`page-types.md` 27). An entry is `path:` with `sha:`, or `issue:`, or
`url:` with `retrieved:` (`page-types.md` 18-23). The structural linter
checks only that the list is present and non-empty (`lint.py` 372-373); the
`path:` entries are what `stale-claim` later looks for on disk, below.

**Structural lint (no section rule) and prose lint (advisory, 25-word
limit).** Structural lint runs six checks — frontmatter present and
well-formed, a known `page_type`, a matching unique slug, directory
placement, `sources:` presence, and link resolution with reachability
(`lint.py` 5-23); the rules page lists the same checks and no
body-section rule (`page-types.md` 196-212), so nothing in code requires a
`## Decision` or any other H2. Prose lint is a separate advisor: checks 1-5
cover sentence length, semicolons, filler phrases, `## Summary` and
`## Key ideas` length, and the glossary avoid-term lock
(`src/wiki_studio/prose_lint.py` 22-27). A sentence is limited to 25 words
(`src/wiki_studio/schema/__init__.py` 119), counted by `count_words`
(`prose_lint.py` 618-620), and check 4 reads only `## Summary` and
`## Key ideas` (`prose_lint.py` 644). Its findings are advisory: a body
convention costs nothing in lint, and nothing enforces it either.

**`stale-claim` checks path existence only.** `_check_stale_claims`
(`health_lint.py` 110-155) resolves each cited `path:` against the project
root (`health_lint.py` 141) and reports a page whose path does not exist. It
says in the code that it does not compare `sha:` with git and does not fetch
URLs (`health_lint.py` 115-119), so a source that changed in place is
reported by nothing.

**`findings`: twelve kinds, none for similarity.** `FINDING_KINDS`
(`findings.py` 70-83) lists twelve: `stale-claim`, `weak-orphan`,
`missing-cross-link`, `avoid-format`, `unapproved`, `approval-stale`,
`approval-policy-changed`, `superseded-still-indexed`, `no-page-id`,
`open-conflict`, `conflict-one-sided` and `conflict-dangling`. None compares
two pages for similarity. `findings` reads only — no lock, no backend, no
model (`findings.py` 188; `api.py` 837-839; `cli.py` 420).

**Discovery: index-linked candidates, two rankers, the FTS5 fallback,
superseded pages ineligible.** `index.md` is read first, and the candidates
are the pages it links (`src/wiki_studio/discovery.py` 4-7, 410-424), so a
page the index does not link is never considered. Two rankers order the
eligible pages, `index-first` and `fts5` (`discovery.py` 49-52); without
FTS5 in this Python's SQLite the `fts5` ranker falls back to `index-first`
and says why (`discovery.py` 12-13; the probe is `Fts5Probe` 150-155 and
`fts5_available` 158-162). A page carrying `superseded_by` is ineligible
with reason `superseded` (`discovery.py` 278, 78). `find` runs the
selection only — no backend, nothing written (`api.py` 1158-1207;
`cli.py` 587-598).

**Supersession.** `superseded_by` is an optional frontmatter key naming the
wiki-relative page that replaces this one; the target must exist and must
not itself be superseded (`page-types.md` 40-42; `lint.py` 268-289, 388).
`review.superseded_by` reads the key (`review.py` 175), discovery drops the
page from every result (`discovery.py` 278), and `findings` reports
`superseded-still-indexed` for a superseded page that `index.md` still links
(`findings.py` 157-184).

**The conflict callout.** A page may mark a disagreement with another page
by a body callout: a blockquote whose marker line names the other page, in
the form `> [!conflict] Disagrees with [<title>](<path>)`, with no new
frontmatter key, page type or directory (`docs/adr/0004-conflict-callout.md`
40-62; the form at 46-52). `findings` has three kinds that read it:
`open-conflict`, `conflict-one-sided` and `conflict-dangling`
(`findings.py` 66-68, 80-82).

## Compatibility

Three coordination issues are closed, and this study changes none of their
contracts. #38 (closed 2026-10-30) and #51 (closed 2026-10-28) are
wiki-studio's release tracks, and memkernel #48 (closed) is the wiki-bridge
side.
Revision preconditions, containment, citations, locking, receipts and the
human gates stay as released: the study adds no package code, no schema
change and no ADR.

memkernel #57 (closed by gosha70/memkernel#117) and memkernel #123 (closed
by gosha70/memkernel#127) are the runtime side. #57 is memkernel's own
research spike on preserving and retrieving implementation decisions; #123
is its revalidation rule, which flags a decision that cites a changed file
and still returns it. The study compares wiki-studio's reporting against
that rule and does not change memkernel.

## Corpus

The pattern corpus is memkernel #57's twelve decision records, read at tag
`v0.9.0` and copied byte for byte:

- tag: `v0.9.0`
- commit: `7f260123d28d3594c83d6ebdb4b4433195bd0023`
- source path: `eval/decisions-57/corpus.md`
- sha256: `10e61af7bca5dfd764443908b040f8581c4d5de4c8aa774c9dce324b663ca503`

The copy is `eval/patterns/corpus/decisions-57.md`, and it is unchanged: the
hash above is the hash of the committed copy. It was read with
`git -C <memkernel> show v0.9.0:eval/decisions-57/corpus.md`, and the commit
with `git -C <memkernel> rev-parse v0.9.0^{commit}`.

The background is code-copilot-team's `knowledge/wiki/` at commit
`00d49c0a9eb51e9bf234cee70490889b151cd550` (the short `00d49c0` resolved).
Every commit the corpus cites is an ancestor of that pin, checked with
`git -C <code-copilot-team> merge-base --is-ancestor <sha> <pin>`: 76beab2,
c776632, 2325480, 13eb704, dafbc5b, 5ce94f2, 37e8417, a24a00e, e39969f,
15438b2, 8dbceaf and 88931a3.

The two repositories were read, never edited. The git commands used are the
ones the study allows: `rev-parse`, `show`, `cat-file`, `merge-base`,
`diff --quiet` and `ls-tree`.

### The pattern pages

Fourteen `decision` pages under `eval/patterns/wiki/decisions/`: one per
corpus record plus a successor for each of the two stale records. Words are
whitespace-separated tokens: the page body after the frontmatter, and the
record's section in the corpus copy from its heading to the next heading.

| Page | Record | Kind | Issue 54 example | Words page / record |
|---|---|---|---|---|
| `trace-archive-reuses-the-ingest-redaction-path` | reuse: Trace archive reuses the ingest redaction path | reuse | reuse a helper | 155 / 209 |
| `benchmark-step-reuses-the-one-correlate-scan-seam` | reuse: Benchmark step reuses the one correlate scan seam | reuse | — | 171 / 214 |
| `swe-bench-fetch-uses-the-stdlib-rows-api-not-parquet` | native-vs-dependency: SWE-bench fetch uses the stdlib rows API, not Parquet | native-vs-dependency | native feature over a dependency | 152 / 199 |
| `judge-statistics-and-charts-stay-in-the-stdlib` | native-vs-dependency: Judge statistics and charts stay in the stdlib | native-vs-dependency | — | 169 / 199 |
| `never-bypass-a-git-lock-with-an-alternate-index` | rejected-for-safety: Never bypass a git lock with an alternate index | rejected-for-safety | reject a shorter solution that weakens safety | 157 / 215 |
| `never-archive-raw-jsonl` | rejected-for-safety: Never archive raw JSONL | rejected-for-safety | — | 154 / 197 |
| `benchmark-ui-was-backend-free-one-shot-and-studio-only` | stale: Benchmark UI was backend-free, one-shot and Studio-only | stale | supersede after a change | 151 / 235 |
| `merge-require-green-ci-was-never-read` | stale: merge.require_green_ci was never read | stale | — | 143 / 202 |
| `the-clusters-view-is-not-an-explorer` | false-reuse-trap: The clusters view is not an explorer | false-reuse-trap | — | 159 / 217 |
| `config-redaction-is-not-free-text-redaction` | false-reuse-trap: Config redaction is not free-text redaction | false-reuse-trap | keep two similar patterns distinct | 171 / 213 |
| `destructive-git-commands-require-confirmation` | conflict: Destructive git commands require confirmation | conflict | — | 161 / 227 |
| `balanced-profile-denies-destructive-git-commands` | conflict: Balanced profile denies destructive git commands | conflict | — | 181 / 252 |
| `benchmark-explains-itself-linking-runs-is-a-pipeline-step` | successor of the Benchmark UI record | successor | supersede after a change | 200 / — |
| `merge-require-green-ci-was-never-read-and-was-removed` | successor of the merge.require_green_ci record | successor | — | 136 / — |

`manifest.json` records the same table as `pages`, with each page's
`y_statement_sentences` (three for a record page, one for a successor) and
its `successor_of` link.

### The background pages

Every `.md` file of code-copilot-team's `knowledge/wiki/` at the pin outside
`schema/`, except `index.md`, `log.md` and
`playbooks/pre-pr-close-keyword-audit.md`, is copied by
`git show <pin>:knowledge/wiki/<path>` to the same path under
`eval/patterns/wiki/`. Twenty pages are copied. One transformation is
applied: an inline link whose target leaves the copied set — a `../` target
outside the wiki, a `schema/` page, or an excluded page — is rewritten to
`https://github.com/gosha70/code-copilot-team/blob/<pin>/<repo path>`.
Nothing else changes. `manifest.json` `background` lists each copy with
its `sha256_at_pin` (the bytes `git show` printed), its `sha256` (the
committed copy) and its `links_rewritten` count. Thirty-two links were
rewritten in all.

The exclusions are named here: `index.md` and `log.md` (the fixture has its
own), `playbooks/pre-pr-close-keyword-audit.md` (its text quotes GitHub
closing-keyword phrases, which no file of this study may carry), the
`schema/` pages (not copied, so their links are rewritten), and the
non-page files `open-questions/.gitkeep` and `scripts/lint-wiki.sh`. No
`scripts/` directory exists in the fixture. No copied page failed
structural lint, so no page was excluded for a violation.

`eval/patterns/wiki/index.md` has `page_type: index` and links every fixture
page in its "Patterns" and "Background" sections, the two superseded pages
included. `eval/patterns/wiki/log.md` has `page_type: log` and one line per
pattern page in the form `- YYYY-MM-DD — add <slug> (decision): <why>`,
dated from the record.

### What the fixture reports

On the fixture as a wiki, three findings are expected and none of them is a
defect:

- `superseded-still-indexed` for exactly the two superseded pages, because
  `index.md` keeps their entries. That is deliberate: `find` considers only
  the pages `index.md` links, so keeping them indexed is what lets the study
  observe a superseded page become ineligible rather than invisible.
- `stale-claim` for every `path:` source of a code-copilot-team file, because
  those paths do not exist under this repository's root. This is the
  path-existence check of `health_lint.py` 110-155, not a claim that the
  cited files are gone from code-copilot-team.
- `no-page-id` on the fixture's pages, which carry none: `propose --from`
  assigns one, and the fixture is copied in, not proposed.

No page has an approval record, so the review kinds report the pages
unapproved as well.

## Protocol: labels, gold and signals, frozen before any signal runs

`eval/patterns/labels.json`, `eval/patterns/questions.json` and
`eval/patterns/protocol.json` were written in US3, the phase after the
corpus, and were committed before any signal or retrieval code existed in
the repository. They are frozen: nothing after that phase edits them,
`protocol.json` records the sha256 of the other two, and
`tests/test_patterns_frozen.py` pins all three.

### Labels

`labels.json` labels all 91 unordered pairs of the 14 pattern pages. Each
entry carries the sorted pair, a disposition, a one-sentence reason drawn
from the two pages, and `annotation`: the corpus line that names the pair (a
`partner:`, a seed, or the git-lock record's `incident:` evidence), or null.
The four pairs the corpus annotates are listed first. The dispositions are:

- `redundant`: a merge candidate — the pages record the same decision, with
  the same implementation and the same evidence;
- `conflicting`: a `[!conflict]` case — the two conflict records that name
  the same destructive git commands at different layers;
- `distinct-by-precondition`: the pages agree, or state the same decision
  shape, but their stated preconditions or scopes differ, so both stand;
- `unrelated`: none of these, even when one page cites the other.

The 91 pairs are one `redundant`, one `conflicting`, eleven
`distinct-by-precondition` and seventy-eight `unrelated`.

`background_pairs` lists only the pattern-background pairs a corpus record
names; one is named, the git-lock record and
`incidents/git-safety-bypasses.md`, and it is labelled `redundant`. Every
pair that involves a background page and is not listed is a false candidate
by rule.

### Questions and gold

`questions.json` holds the twelve records' replay questions in corpus
order. Each entry's `question` is the record's `later-task:` text verbatim
and its `record` is the record's corpus heading. `gold` follows the record's
`seed:` line: "this record" gives the record's page; "this record and its
partner" gives both conflict pages; "this record and the trace-archive reuse
record" gives the config-redaction page and the trace-archive page, its
trap; "this record and the superseding record" and "this record and the
correction" give the successor page only, with the stale page in
`superseded`. `reuse_target` is the page to reuse — the record's page, the
successor for a stale record, the trace-archive page for the config-redaction
question; `trap` is the look-alike page a seed names, which only the
config-redaction question has; `superseded` is the stale page that must stay
ineligible.

### Signals and thresholds

`protocol.json` fixes five scored outputs: (a), (a-path), (b), (c) and
`combined`.

- (a) is `health_lint._candidate_pairs`' rule: two eligible pages are a
  candidate when they share at least one cited `sources[].path` or one
  links directly to the other, and the output records which part fired.
- (a-path) is (a)'s shared-path part on its own, scored with its own verdict
  and counts.
- (b) is the Jaccard similarity of `wiki_state._tokenise(title + " " + the
  first paragraph of the Decision section)` between two pages, at least
  0.25; a background page without a `## Decision` section contributes its
  title and its first body paragraph.
- (c) is shared entity mentions as `missing-cross-link` counts them: the
  entity vocabulary is every fixture page's slug except `index`, `log` and
  `overview`, mentions are found with `health_lint._entity_mentions` in the
  body after the frontmatter with the per-file glossary aliases
  `prose_lint.load_avoid_map` gives, and the intersection less the two
  pages' own slugs must reach 2.
- `combined` is the union of (a), (b) and (c).

An eligible page is one that carries no `superseded_by`, as `find` treats
it; the two stale pages are ineligible. The scope is every eligible pattern
pair (66 of the 91), every eligible pattern-background pair and every
eligible background-background pair; the 91-pair table is reported as
secondary.

### Annotation-linked pairs

The corpus annotations are the source of both the labels and the intra-wiki
links the pages carry (the conflict callouts, the Consequences links and the
git-lock incident link). A true candidate is marked `annotation_linked` when
the only part of its signal that fired is such a link, or when `findings`
already reports the pair as `open-conflict`. The mark exists because a link
the study wrote from an annotation cannot be evidence that a signal detects
duplicates. Signal (c) is unaffected: a mutual link puts each page's slug in
the other's body, and (c) subtracts the two pages' own slugs. (b) reads
titles and the Y-statement paragraph, which the annotation links never
touch, and (a-path) has no links by construction.

### True, false and the pass bar

A candidate is true when its label is `redundant` or `conflicting`; it is
false when its label is `distinct-by-precondition` or `unrelated`, and a
pair involving a background page is false unless `background_pairs` lists it
with a true disposition. A signal passes when it finds every eligible pair
labelled `redundant` or `conflicting` and its false candidates do not
outnumber its true ones across the whole scope. With no such labelled pair
the bar is "not testable", never a pass. The eligible true pairs number two,
so any verdict rests on those two pairs; a pass is grounds to draft an issue
for a `findings` kind, not evidence that such a kind would work in general.

### Retrieval

Each question is asked with `api.find(question, paths, max_pages=5,
ranker=r)` for each ranker (`index-first`, `fts5`). Hit at 1 means the top
page is a gold page; the config-redaction question's gold includes its trap
page, so a top-ranked trap is a hit at 1 there, and "trap outranks" — the
trap above the `reuse_target`, or the target absent while the trap is
present — is the metric that shows it. Hit at 5 means every gold page is in
the five. For a question with a `superseded` page, that page (still linked
from `index.md`) must be listed ineligible with reason `superseded` and
never selected.

## The lifecycle trace

```
python -m eval.patterns.trace --out <PATH>
```

Without `--out` the command prints the same JSON. It copies
`eval/patterns/wiki` into a temporary root, removes one issue 54 example
page **P** and its index line from the copy, and then runs the real verbs
in-process through `wiki_studio.cli.main`. P is
`decisions/swe-bench-fetch-uses-the-stdlib-rows-api-not-parquet.md`, the
native-feature example: no other fixture page links to it, so removing it
leaves no dangling link. Every verb receives `--root`, `--wiki-dir` and
`--proposals-dir` pointing into the temporary root, and propose, promote
and approve receive `--by trace-agent`. Each step records its argv with the
temporary root written `<root>` and the reviewed revision written
`<sha256>`, its exit code, and a deterministic observation; no timestamp,
page id, sha256 value or generated proposal path is recorded, so the
output is the same on every run. The committed output is
`results/trace.json`.

| Step | What it shows |
|---|---|
| `init` | The manifest's policy: `auto_approve_on_promote` is false, so nothing is approved by promotion |
| `propose-candidate` | P, its index line and a log line travel as a pending proposal; P is absent from the wiki |
| `propose-broken` | A draft whose body links a missing page is accepted as a proposal (`propose` does not resolve links) |
| `promote-broken-refused` | The staged-tree linter refuses it: exit 9, nothing broken reaches the wiki |
| `promote-candidate` | P enters the wiki unapproved, with the `page_id` `propose --from` assigned |
| `lint` | The promoted wiki is structurally clean |
| `cited-file-written` | A file appears at P's first cited `path:`, inside the temporary root |
| `findings-after-cited-file` | P is `unapproved`; the path just written is no longer a `stale-claim`, the second cited path still is |
| `read` | P's live text and the sha256 of exactly those bytes |
| `approve` | The approval names the revision that was read; P is then in no review kind |
| `find-approved` | `find` with P's later-task question selects P |
| `propose-update` | An update of P, guarded by the revision `read` printed, is pending; the live bytes do not change |
| `promote-update` | P's approval no longer matches the live bytes: `approval-stale` |
| `propose-supersession` | A successor page and an update of P adding `superseded_by`, proposed together |
| `promote-supersession` | Both land in one promotion; P reads `superseded` |
| `find-after-supersession` | The same `find` lists P ineligible with reason `superseded` and selects the successor |
| `findings-after-supersession` | P is `superseded-still-indexed` while its index line stays, and the review kind is gone |
| `cited-file-changed` | The cited file's bytes change again |
| `findings-after-source-change` | P's findings are exactly what they were: nothing reports a changed source (`health_lint.py` 110-155) |

The trace calls no backend, writes only inside its temporary root, and
leaves `eval/patterns/` untouched (a test snapshots the tree before and
after it runs).

## Retrieval results

```
python -m eval.patterns.retrieval --out <PATH>
```

The command copies the fixture into a temporary root — so the `fts5`
search cache, which lives beside the wiki's lock, is written there — and
asks each of the twelve questions in
`questions.json` with `api.find(question, paths, max_pages=5, ranker=r)`
for every ranker in `discovery.RANKERS`. Per question and ranker it
records the selected pages in rank order, the ranker that ran (`ran_as`,
so an FTS5 fallback is visible), hit at 1, hit at 5, whether the trap
outranks the reuse target (null where the question names no trap), and for
a question with a superseded page whether that page is listed ineligible
with reason `superseded` and absent from the selection. It also records
`questions_sha256` and the Python and SQLite versions of the run. The
navigation runner under `eval/navigation` needs a `corpus/` and
`stopwords.txt` for its grep control, which this fixture does not have; it
is neither used nor edited.

The committed output is `results/retrieval.json`, the output of a run with
FTS5 available: Python 3.13.2, SQLite 3.48.0. The per-question entries and
the totals by ranker are recorded there, and the test suite compares every
`index-first` entry on any machine and every `fts5` entry wherever this
Python's SQLite has FTS5.

## The evidence checklist

Before a curator promotes a pattern proposal, the candidate should carry
five items:

1. the canonical implementation as a `sources:` entry with `path:` and
   `sha:`;
2. at least one test or verification outcome;
3. the originating spec, issue or PR;
4. the rejected options with their reasons;
5. a revisit trigger.

Read from the five issue 54 example pages, marked `present`, `absent`, or
`not recorded in the source record` where the page says so:

| Issue 54 example | Canonical `path:` + `sha:` | Test or verification outcome | Originating spec, issue or PR | Rejected options with reasons | Revisit trigger |
|---|---|---|---|---|---|
| Reuse a helper (`trace-archive-reuses-the-ingest-redaction-path`) | present | present | present | present | present |
| Native feature over a dependency (`swe-bench-fetch-uses-the-stdlib-rows-api-not-parquet`) | present | absent | present | present | present |
| Reject a shorter solution that weakens safety (`never-bypass-a-git-lock-with-an-alternate-index`) | present | absent | absent | present | not recorded in the source record |
| Supersede after a change (`benchmark-explains-itself-linking-runs-is-a-pipeline-step`) | present | present | present | present | not recorded in the source record |
| Keep two similar patterns distinct (`config-redaction-is-not-free-text-redaction`) | present | absent | present | present | present |

A missing item is a reason to send a proposal back — curator guidance, not
a check in code: nothing in lint, `findings` or approval reads any of the
five.

## Citing without binding

An agent uses a found pattern without treating it as binding in four
steps:

```
wiki-studio find "<question>" --json
wiki-studio findings --json
wiki-studio read <page> --json
```

The first returns the pages `query` would put in front of a model; the
second keeps only pages whose review state is `approved` (the MCP
`review_state` tool answers the same question without a model, and an
`unapproved`, `approval-stale` or `approval-policy-changed` page is a
reason to stop); the third returns the page's text and the sha256 of the
bytes being cited, which is what an approval binds. The reader then checks
the page's `Applies when:` and `Does not apply when:` lines against the
task. An approval is evidence that a curator saw those bytes, not that the
pattern applies.

The trace runs each command: `find` at `find-approved` and
`find-after-supersession`, `findings` at three steps, and `read` at `read`
before the approval.

The corpus has cases where a found pattern must not be reused:

- the two false-reuse traps: `config-redaction-is-not-free-text-redaction`
  (its helper redacts configuration values by key name, not free text —
  reuse `trace-archive-reuses-the-ingest-redaction-path` for free text) and
  `the-clusters-view-is-not-an-explorer` (a minimal read-only view is not
  an explorer, so filtering, drill-down and graph work is not a reuse);
- the two superseded pages, `benchmark-ui-was-backend-free-one-shot-and-studio-only`
  and `merge-require-green-ci-was-never-read`: their successors are the
  live pages, and `find` lists the stale pages ineligible with reason
  `superseded` (the trace's `find-after-supersession` shows it).

None of this is enforced: a `find` result is a candidate list, and the
`Applies when:` line is the only place the page says when it does not
apply.

