# Report: reusable engineering patterns with the pages wiki-studio has (issue 54)

This is the report of the issue 54 research spike. Its deliverable is one
recommendation, made at the end of this page, and every number here is
copied from the committed results **as recorded** there:

- `results/trace.json` — the lifecycle trace on a temporary copy, nineteen
  steps: the real verbs, two writes of a cited file, and the findings after
  each; no backend;
- `results/retrieval.json` — `api.find(question, paths, max_pages=5,
  ranker=r)` for the twelve frozen questions and both rankers, from a run
  with FTS5 available (Python 3.13.2, SQLite 3.48.0);
- `results/duplicates.json` — the five scored duplicate signals on the
  labels and thresholds frozen before any signal code existed;
- `results/staleness.json` — every `path:` + `sha:` source of the pattern
  pages against the code-copilot-team checkout at the manifest's pin.

The fixture is fourteen `decision` pages (twelve memkernel #57 records and
two successors), five of them issue 54's examples, beside twenty background
pages from code-copilot-team's wiki. `labels.json`, `questions.json`,
`protocol.json` and `tests/test_patterns_frozen.py` were committed in their
own phase, before any signal code existed, and were never edited after it.
No result depends on a model, and nothing under `src/wiki_studio/` changed.

## Question 1: Can current pages hold a pattern?

**Yes: six of the seven fields in existing slots, and the seventh — owner and
status — split between the approval record and the frontmatter.** The study
README's fit map is the evidence: intent in `## Decision`,
applicable constraints in `## Context`, the canonical implementation and the
validation evidence as `sources:` entries with `path:` and `sha:` (subject
text in `## Consequences`), rejected alternatives in `## Alternatives
considered`, revisit criteria as a `Revisit when:` line in `## Consequences`,
and `status:` in the frontmatter. The owner has no slot: the approval record
names the approver (`--by`), and nothing names a maintainer. `status:` never
approves a page.

All fourteen pages were written with existing keys only (`page_type`, `slug`,
`title`, `status`, `last_reviewed`, `sources`, `superseded_by`) and the four
existing `decision` H2s in template order. The trace's `lint` step reports the
promoted wiki at **36 pages, 0 violations**, and the fixture test asserts no
structural violation on the fixture. Prose lint reports no finding on a
pattern page.

**The Y-statement, weighed against the pitch.** The pitch proposed the
one-line form "In the context of …, we chose … over …, because …", sized for
memkernel's 200-character preview. That form breaks prose lint's 25-word
sentence limit on all twelve records, so the study wrote three sentences —
"In the context of <X>, we chose <Y>." / "We chose it over <Z>." / "The
reason: <W>." — one paragraph, the first paragraph of `## Decision`, each
sentence within the limit. `manifest.json` records 3 sentences for every
record page and 1 for each successor, whose statement is within 25 words in
total. The three-sentence form keeps what a preview needs (the choice and its
reason are the first two sentences) and passes the prose check; it costs two
sentence breaks, and a consumer that takes only "the first line" would take
just the context clause — so a pointer should take the whole paragraph
(question 6).

**Limits.** The convention is body text. Structural lint has no section rule
and prose lint is advisory, so a page missing `Applies when:` or `Revisit
when:` passes every check; the convention is enforced by review, not code. A
new required key would be a schema change and this study does not propose one.

## Question 2: How does an agent propose one, and what evidence must promotion see?

**The existing gate carries a candidate unchanged: propose, promote, approve.**
`propose --from` reads a directory laid out like the wiki and writes a pending
proposal with a `page_id` on every page; `promote` validates a staged copy
against the structural linter under the wiki lock and is the only writer;
`approve --revision` binds the sha256 the reviewer read. Promotion never
approves: the trace's `init` records `auto_approve_on_promote: false`, and the
promoted page reads `unapproved`.

The trace, as recorded: `propose-candidate` leaves P absent from the wiki with
the proposal written; `propose-broken` is accepted (proposing does not resolve
links); `promote-broken-refused` exits **9** and the wiki is unchanged, so
nothing broken reaches it; `promote-candidate` lands P unapproved with its
`page_id`; `lint` runs clean.

**What promotion must see is lint-clean bytes plus a curator's judgment on
five items**: the canonical implementation as `path:` + `sha:`; at least one
test or verification outcome; the originating spec, issue or PR; the rejected
options with their reasons; a revisit trigger. Nothing in code reads the five
— the linter checks frontmatter, placement, `sources:` presence and links.
Read from the five issue 54 example pages: the canonical implementation is
present 5 of 5, the rejected options 5 of 5, the originating spec 4 of 5, the
revisit trigger 3 of 5 (two pages say "not recorded in the source record"),
and a test or verification outcome 2 of 5. Sending a proposal back for a
missing item is therefore a curator decision, not a promotion failure.

**Limits.** One candidate page, one agent name, one sequential run. No
concurrent proposer, no backend, no judge of whether the evidence is true.

## Question 3: How does an agent find and cite approved patterns without treating them as binding?

**The sequence is find, then findings (or the MCP `review_state` tool), then
read `--json`, then the page's `Applies when:` and `Does not apply when:` lines
against the task.** `find` does not report review state, so approval is a
separate call; an `unapproved`, `approval-stale` or `approval-policy-changed`
page is a reason to stop. `read --json` returns the page's text and the sha256
of exactly those bytes — what an approval binds.

Retrieval, as recorded, for the twelve frozen questions at five pages:

| Ranker | Hit at 1 | Hit at 5 | Trap outranks | Superseded checked / violations |
|---|---|---|---|---|
| `index-first` | 9 of 12 | 12 of 12 | 1 | 2 / 0 |
| `fts5` | 10 of 12 | 12 of 12 | 1 | 2 / 0 |

Every gold page is returned within five by both rankers. The hit-at-1 misses
are the same kind of case: a background page or a sibling ranks first (the
trace-archive question puts the never-archive page first under `index-first`;
so do the benchmark-step and destructive-git questions; under `fts5` the
incident page tops the git-lock question and the recovery playbook tops the
destructive-git question). The false-reuse trap is real in both rankers: on
the config-redaction question the trap page (its own gold, per the frozen
gold rule) ranks first while the page to reuse is second under `index-first`
and fourth under `fts5` — "trap outranks" is 1 in each. Both superseded pages,
still linked from `index.md`, are listed ineligible with reason `superseded`
and never selected.

The trace runs each command: `find-approved` selects P after approval;
`find-after-supersession` lists P ineligible and selects the successor;
`findings` runs at three steps; `read` returns the revision that `approve`
then binds. **An approval is evidence that a curator saw those bytes, not that
the pattern applies** — the `Applies when:` line is the only place the page
says when it does not.

**Limits.** Twelve questions, one per record, are the records' own replay
tasks, not a stream of real tasks. Whether an agent obeys a `Does not apply
when:` line is not measured (issue 75).

## Question 4: Can existing lint, query or findings expose near-duplicates without merging anything?

**No existing check does, and none of the measured model-free signals clears
the frozen bar.** `FINDING_KINDS` lists twelve kinds and none compares two
pages for similarity; `_candidate_pairs` (a shared cited path or a direct
link) feeds only the model-checked contradiction pass, which this study does
not run. `query` ranks pages for a question; it is a retrieval ranker, not a
duplicate detector, and was not scored as one.

The five scored outputs, as recorded (scope: the 66 eligible pattern pairs,
the 240 eligible pattern–background pairs and the 190 eligible
background–background pairs; 32 eligible pages):

| Signal | Eligible labelled pairs found | Annotation-linked among found | True candidates | False candidates | Verdict |
|---|---|---|---|---|---|
| (a) | 3 of 3 | 1 | 3 | 36 | fail |
| (a-path) | 2 of 3 | 0 | 2 | 15 | fail |
| (b) | 2 of 3 | 1 | 2 | 1 | fail |
| (c) | 0 of 3 | 0 | 0 | 3 | fail |
| combined | 3 of 3 | 1 | 3 | 36 | fail |

False candidates by reason, as recorded: (a) 3 `distinct-by-precondition`, 0
`unrelated`, 33 background unlisted; (a-path) 2, 0, 13; (b) 0, 0, 1; (c) 0, 0,
3; combined 3, 0, 33. Missed pairs: (a) none; (a-path) the conflicting pattern
pair, which only a direct link joins; (b) the listed pattern–background pair;
(c) all three; combined none. The bar rests on those three eligible labelled
pairs — two pattern pairs and one listed pattern–background pair — and no
signal passes. (b) came closest: both pattern pairs found, one false candidate
(the background `overview` page against `use-llm-wiki-as-knowledge-layer`),
and the background pair missed.

**A pass resting only on annotation-linked pairs would not be evidence of
detection.** The corpus annotations are the source of both the labels and the
intra-wiki links the pages carry (the conflict callouts, the Consequences
links, the git-lock incident link); the build wrote those links, so (a)'s link
part can find a pair only because the build linked it. The frozen protocol
therefore marks such a true pair `annotation_linked`, and flags a verdict
whose found labelled pairs are all annotated. In this run the conflicting
pair carries the mark in every signal that finds it — `findings` already
reports it as `open-conflict`, and (a) also finds it through its callout
alone — but (a) also finds the other two true pairs without annotation links,
so `rests_on_annotation_links` is false for all five signals. **(a-path), (b)
and (c) are the measured detectors**: (a-path) has no links by construction,
(b) reads titles and the Y-statement paragraph, which the annotation links
never touch, and (c) subtracts the two pages' own slugs, so a mutual link
cannot create a candidate.

**No issue is drafted for a duplicate `findings` kind.** A pass would have
been grounds to draft one, not evidence that such a kind would work in
general; none passed, so the evidence supports keeping this as a throwaway
script, not shipping a check.

**Limits.** The bar rests on three pairs. (b)'s result (2 true, 1 false) is
the one a larger corpus could overturn; with only two eligible true pattern
pairs, no signal's precision or recall is estimated with any confidence.

## Question 5: How does a source or spec change mark a pattern for review?

**Today nothing does.** `stale-claim` checks that a cited `path:` exists, not
that the bytes at `sha:` are current, and it flagged **0 of the 24** cited
sources. The one page whose `Revisit when:` condition had arrived — the merge
page, whose spec carries the correction — was not flagged, because the path
exists. The study's revision check (a `git diff --quiet <sha> <pin> -- <path>`
between the cited commit and the pin) flagged **13 pages / 15 source entries**:
14 distinct page–file citations (the merge page cites one spec at two
commits), 1 true review, 12 false; 9 unchanged; none unknown. One of the 12
false flags is true for citation accuracy: the judge-statistics page names
`spearman.py` at `dafbc5b`, a commit that does not contain the file. So a
change is visible to a check that compares commits, but "the file changed" is
not "the pattern needs review": 12 of 13 flagged pages needed none under their
own `Revisit when:` line, and the one that did was the already-superseded
merge page, whose successor records the correction.

**"Flag, still return" fits the wiki as it stands.** A finding never
withdraws an approval and never changes eligibility — discovery's only
eligibility test is `superseded_by` — so a flagged page stays approved and
findable while a finding asks for review. The trace shows the two coexisting:
P carries `stale-claim` and `unapproved` findings at `findings-after-cited-file`
and is still selected by `find` at `find-approved`.

For the four triggers issue 54 names, what a `sources:` entry can carry and
what checks it today: a **changed source** can be carried as `path:` + `sha:`,
and `stale-claim` checks path existence only (the revision comparison is this
study's script, not a package check); a **new spec revision** is named by
`path:` + `sha:` and discussed by `issue:` or `pr:`, and nothing compares the
`sha:` or resolves the tickets; a **security finding** can be pointed at with
`issue:` or `url:`, and URLs are never fetched and issues never opened; a
**failed test** is named in the body as text or cited as `path:` + `sha:`, and
nothing runs a test. **No shipped check detects any of the four.**

**Limits.** The revision check is not a wiki-studio behaviour; it ran once,
by hand, against one checkout at one pin. The judgments under `Revisit when:`
were made after the run and live in the README as judgments, not in
`results/staleness.json`. A `sha:` that is not a commit of the checkout would
report unknown with a reason; none did.

## Question 6: What should memkernel keep to point at one?

**Text only; memkernel is untouched, and the owner may act on it (D6).** For
a pattern memkernel points at, it should keep:

- the page's `page_id`;
- the wiki path;
- the approved revision's sha256, taken from `read --json`;
- the Y-statement: the first paragraph of `## Decision`, which in this
  study's form is the three-sentence statement (a successor's may be one);
- `corrects:` on the wiki page naming the runtime record it replaces, as
  memkernel #57's research note says.

Each is a page fact the study can point at: `propose --from` assigns
`page_id` (`promote-candidate`), `read --json` returns the sha256 `approve`
then binds (`read`, `approve`), the Y-statement is the page's own summary
(question 1), and `corrects:` is an existing optional key
(`page-types.md` 43-44). The bridge carries title, body, single-line scalars
and `sources:`; the approval record does not cross it, which is why the
revision sha256 has to be kept beside the pointer rather than read from the
page.

**Limits.** No memkernel round trip ran in this study; the list is a
recommendation from the wiki side, consistent with the bridge's existing
round trip and memkernel #57's own research note.

## Overhead

As recorded in `manifest.json` and the four results files:

| Measure | Value |
|---|---|
| Pattern pages written | 14 (12 record pages and 2 successors) |
| Words per page against the record | every record page is shorter than its record: 1,924 words across the 12 record pages against 2,579 in their records (75%); the two successors have no record and run 200 and 136 words; the page-by-page pairs follow the table |
| Y-statement sentences | 3 on every record page, 1 on each successor (a statement within 25 words stays one sentence) |
| Retrieval hits | `index-first` 9 of 12 at 1 and 12 of 12 at 5; `fts5` 10 of 12 at 1 and 12 of 12 at 5; trap outranks 1 per ranker; superseded checked 2, violations 0 |
| False candidates per signal | (a) 36 against 3 true; (a-path) 15 against 2; (b) 1 against 2; (c) 3 against 0; combined 36 against 3 |
| False staleness flags | `stale-claim`: 0 flags and 1 page that needed review missed; revision check: 13 pages flagged, 12 false and 1 true, 0 pages missed |
| Per-page conversion time | **not measured** |

Words per page (the body after the frontmatter) against the record (its
section in the corpus copy), as recorded in `manifest.json` `pages`:

| Page (under `decisions/`) | Words page / record |
|---|---|
| `trace-archive-reuses-the-ingest-redaction-path` | 155 / 209 |
| `benchmark-step-reuses-the-one-correlate-scan-seam` | 171 / 214 |
| `swe-bench-fetch-uses-the-stdlib-rows-api-not-parquet` | 152 / 199 |
| `judge-statistics-and-charts-stay-in-the-stdlib` | 169 / 199 |
| `never-bypass-a-git-lock-with-an-alternate-index` | 157 / 215 |
| `never-archive-raw-jsonl` | 154 / 197 |
| `benchmark-ui-was-backend-free-one-shot-and-studio-only` | 151 / 235 |
| `merge-require-green-ci-was-never-read` | 143 / 202 |
| `the-clusters-view-is-not-an-explorer` | 159 / 217 |
| `config-redaction-is-not-free-text-redaction` | 171 / 213 |
| `destructive-git-commands-require-confirmation` | 161 / 227 |
| `balanced-profile-denies-destructive-git-commands` | 181 / 252 |
| `benchmark-explains-itself-linking-runs-is-a-pipeline-step` (successor) | 200 / — |
| `merge-require-green-ci-was-never-read-and-was-removed` (successor) | 136 / — |

The four scripts and the fixture are the study's only artifacts; no package
code, dependency or schema changed, and no release was cut.

## The trace's assessment: approval, audit, revision, citation, containment and rollback

From the nineteen steps of `results/trace.json`:

- **Approval.** `promote-candidate` lands P unapproved; `read` returns its
  live bytes and sha256; `approve --revision` yields `review_state:
  approved` with no review kinds; the guarded update promoted by
  `promote-update` turns it `stale` with `approval-stale`; supersession turns
  it `superseded`. Approval binds the reviewed bytes, and promotion does not
  grant it.
- **Audit.** Every step records its argv, exit code and a deterministic
  observation; propose and approve carry `--by trace-agent`, and approve
  names the revision. Every wiki state change goes through a real verb — the
  trace has no shortcut into the wiki. The study did not test audit-tree
  tampering or the audit-format pass; that is lint's job, not this study's.
- **Revision.** The revision handle is the sha256 `read --json` prints:
  `propose-update` is guarded by it and `approve --revision` takes it. The
  trace shows the consequence of a later edit (approval stale); it does not
  include a refused approval for a stale revision, which is the code path's
  contract, not a measured step.
- **Citation.** `read --json` returns the page text with
  `content_matches_wiki_file: true` and a 64-hex sha256 — exactly what an
  approval binds and a citing agent records. The `sources:` entries are the
  upstream evidence: `findings-after-cited-file` shows `stale-claim` for the
  second cited path (absent under the temporary root) and none for the first
  once written; path existence only.
- **Containment.** P is absent from the wiki while its proposal is pending;
  the broken-link draft is refused at promotion (exit 9) and the wiki stays
  unchanged, so nothing broken reaches it; supersession lands the successor
  and the `superseded_by` update in one promotion; the wiki lints clean
  afterwards. Every write lands inside the temporary root.
- **Rollback.** The refused promotion is the rollback case the trace records:
  the patch-set is rejected as a whole and the wiki's state is what it was
  before. A mid-commit exception rollback inside the promoter is not
  exercised — it is internal to `promoter.py` and no step reaches it.

## Labels, cuts and what is unmeasured

### Labels

No label was edited, and no signal verdict depends on a disputed one. One
label the build would state differently if the set had a fifth disposition:
the two stale-page/successor pairs are labelled `distinct-by-precondition`,
while a successor replaces its stale page rather than splitting preconditions
with it. The four dispositions have no "supersedes" value, both pairs are
ineligible in the scope, and no verdict depends on them. Reported here, not
edited (FR-012).

Two further points come from the external review of the labelling commit
(`dbd8c60`). Both are reported here, and no label was edited (FR-012):

- **Two redundant labels rest partly on shared files, which (a-path)
  measures.** The never-archive-raw-JSONL / trace-archive pair's reason
  names "the same archive path calling `redact_text`". The git-lock page and
  `incidents/git-safety-bypasses.md` both cite
  `claude_code/.claude/rules/safety.md`. Both labels hold up on content (the
  same decision, issue and date; the incident quotes the rule). But when
  (a-path) finds these two pairs, it partly confirms how the labeller
  reasoned, not only what the pages say. This is the risk the plan named: a
  labeller reasoning about shared sources. (a-path)'s 2 of 3 should be read
  with that in mind; its verdict is a fail either way.
- **The background pair's "redundant" label is disputed.** A decision page
  and the incident record behind it are different page types that a curator
  keeps apart. FR-012 defines `unrelated` as "none of these, even when one
  page cites the other", which arguably fits this pair better. The effect on
  verdicts is small: (a-path) still cannot find the conflicting pair, whose
  two pages share no cited file, and every signal fails its bar with or
  without this pair.

The other 89 pattern pairs are not disputed.

### Cuts

**No cut was taken.** The pitch's three triggers, in its order, and the
evidence each did not fire: cut 1 (end of week 1, US2 not done) — the fixture
holds all fourteen pattern pages and the twenty background pages; cut 2
(start of week 2, US3 not landed) — the labels, questions and protocol landed
in their own commit before any signal code, and the full signal set ran; cut 3
(middle of week 2, US6 not run) — `results/staleness.json` is the output of a
real run against the code-copilot-team checkout. Nothing was removed by a
cut, so the README and this report have no reduced scope to declare.

### What is unmeasured

- Whether an agent chooses better with patterns in reach. That needs agent
  runs at historical commits and is issue 75; nothing here measures agent
  behaviour and no result depends on a model.
- Per-page conversion time (overhead, above).
- Anything a cut would have removed: nothing, since none was taken.
- A memkernel round trip: question 6 is text, and memkernel was only read.
- Concurrent writers against the wiki lock: the trace is one sequential run.
- An approval refused for a wrong `--revision`: the code path exists; the
  trace shows the approval going stale instead.

**0.10.0 shipped on 2026-11-18, before this branch's base commit, and nothing
here depends on it (D9).** The study uses no `nightly` code and no report from
it; every citation of package behaviour was read at the base commit.

## Recommendation

Recommendation: docs and a template.

The reasons:

- The template exists and works on real material with no package change:
  fourteen pages, lint-clean and prose-clean, with every one of the seven
  fields in an existing slot — six in the page's sections, and owner and
  status split between the approval record and the frontmatter's `status:`
  (question 1).
- The lifecycle needs no new verb: propose, promote, approve, read, find,
  findings and supersession carry a candidate from draft to approved page and
  out again (question 2, the trace).
- Retrieval returns every gold page within five under both rankers and keeps
  superseded pages out (question 3), so a documented convention is enough for
  an agent to find and cite a pattern without treating it as binding.
- What is missing is the convention written down where a team can follow it.
  `docs/patterns.md` carries the template, the evidence checklist, the find,
  findings and read sequence, the revisit guidance and what memkernel keeps;
  the study's measurements say what the convention can and cannot promise.
- Neither candidate enhancement is this deliverable. No duplicate signal
  passes its frozen bar, so no `findings` kind is proposed (question 4); the
  revision check is real but 12 of its 13 flags were false, so it needs its
  own specification before it ships (question 5). Both directions the
  evidence leaves open — carrying the template into the packaged
  `page-types.md` and a revision-aware stale check — are drafted beside this
  report as follow-up issues for the owner to file.
- Not "no change": without docs the convention stays invisible, and the study
  shows every element of it already works. Not "a separately specified
  enhancement": nothing measured justifies package code now; the two drafts
  are follow-ups, not the deliverable.
