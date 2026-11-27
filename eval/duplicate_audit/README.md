# The duplicate-audit study (issue 121)

Issue 121 asks for a way to tell a curator that two pages record the same
thing. The near-duplicate study in `eval/duplicates/` measured word overlap of
title and first paragraph and found 3 of 8 true pairs against a bar of 6, so
nothing was built. The similar-pages study in `eval/similar/` measured, and
cycle 11 shipped, a hint at writing time: `propose` lists the 5 most similar
existing pages of the same type. Nothing reports pairs already in the wiki.
This directory measures an after-the-fact audit for that: a model-free
`findings` kind that flags two same-type pages when each is in the other's
top k under the hint's own ranker (**mutual rank**). The bet pitch
`specs/pitches/121-duplicate-audit/pitch.md` shapes it, and
`specs/wiki-studio-duplicate-audit-121/` specifies it.

- **wiki-studio commit this protocol was written on**: the run-1 branch base,
  `d1338563fc067cd8d5079b05662806f942d1f72c` (`main` after the spec's
  approval).
- **What is measured**: for each of the three candidates below, the flagged
  pairs, the true pairs found out of n, and the false pairs, on the held-out
  set (binding); and the same counts on cycle 10's frozen corpus and labels
  (the development stage, which can stop the study and never decides a pass).
- **What is not measured**: a precision or recall estimate (recall is a count
  out of n); page types other than `decision` (every page of both sets is a
  decision page); curated pages (the pages are extracted spec and pitch
  decisions, not curated pages); curator behaviour.
- `eval/duplicates/`, `eval/similar/` and `eval/patterns/` are read and never
  edited.
- No result depends on a model. Nothing here calls one.
- The audit script (`audit.py`), the held-out set (`held-out/`) and the
  report (`report.md`) are written after the owner signs this protocol off.
  This README holds the protocol only and is frozen with `protocol.json` by
  `tests/test_duplicate_audit_frozen.py`. Held-out counts and labelling notes
  go into `held-out/README.md`, results into `report.md`.

## The development inputs (read-only, pinned)

Every input is checked against its sha256 before anything is ranked; a
difference stops the run with nothing written.

| Input | sha256 |
|---|---|
| `eval/duplicates/corpus.json` | `fc0f710ab994dd4a57a9bb23e700bd61b2ffde58f66a54bb30353c6cc5bbc4de` |
| every page under `eval/duplicates/corpus/` | its `corpus.json` entry's `sha256` |
| `eval/duplicates/labels.json` | `e1c34ca9533aedb39482d628fd8704752035fba3ca34f132d730f8a555082287` |
| `eval/similar/rank.py` | `4fcf98f8b231e3b0a605fc0690529e976a98ae10cb5e51715909b8976844cc80` |

The first and third values are the ones `tests/test_duplicates_frozen.py`
pins; they were re-checked with a shell sha256 tool when this protocol was
written and are unchanged. `rank.py`'s value was computed the same way. The
audit script imports `rank.py`'s `slug_paths`, so it is pinned as an input.

## The index and the query rule

The same rule on both sets.

**Paths.** Every page is indexed under its title-slug path
`decisions/<slug>.md`, given by `eval.similar.rank.slug_paths` over the set's
`corpus.json` entries in order. That is cycle 11's slug and collision rule,
imported and not restated here.

**One index.** One in-memory FTS5 table over every page of the set, rows in
`corpus.json` order, each row `search_index.build_document(<slug path>, <page
text>)`, tokenizer `DEFAULT_RANKER_CONFIG.tokenizer`.

**Each page's ranking.** For page A: A's row is deleted; then

```
SearchIndex.rank(similar_query(<A's text>),
                 order=<every other page's slug path, in corpus.json order>,
                 weights=DEFAULT_RANKER_CONFIG.weights,
                 min_match_tokens=DEFAULT_RANKER_CONFIG.min_match_tokens)
```

ranks the rest; A's row is inserted back before the next page is ranked. So
A is absent while it is the query and present for every other page's
ranking, as a fresh index without A would rank (pitch, findings 3 and 12).
`similar_query` is the shipped `discovery.similar_query`: the frontmatter
title, one space, the body after the frontmatter. `rank` returns only pages
that match at least one query token, best bm25 first, ties by position in
`order`. At this commit the configuration is tokenizer `porter unicode61`,
weights path 4, title 4, headings 2, body 1, and `min_match_tokens` 1.

**The compared pages.** The ranked pages whose frontmatter `page_type` (read
with `review.frontmatter_value`) equals A's. Every page of both sets is a
decision page and none is superseded, so the filter keeps all of them; it is
applied so the measured path is the one that would ship.

**A's list** is the compared pages, best first. **A rank** is the 1-based
position in that list. A page not in A's list has no rank there. The lists
are computed once per set and every k is read from them.

## The candidates and the flag

One rule at three values of k, in this order:

| Candidate | k |
|---|---|
| `mutual-top-1` | 1 |
| `mutual-top-3` | 3 |
| `mutual-top-5` | 5 |

The unordered pair {A, B} is **flagged** at k when B is in A's first k and A
is in B's first k. Each flagged pair carries both ranks: B's in A's list and
A's in B's list. No score floor (bm25 scores are not comparable across
queries), and no other candidate.

## Labels, restatements and pair scope

**Labels.** A pair's label is its disposition in the set's `labels.json`
`pairs` or `cross_pairs`, else `unrelated`. True: `redundant`,
`conflicting`, `supersedes`. False: `companion`, `distinct-by-precondition`,
`unrelated`. **n** is the number of true pairs in the labels. A flagged pair
is true or false by its label; the **true pairs found** are the flagged true
pairs.

**A restatement** (the owner, 2026-11-27) is decided from the two pages'
`corpus.json` entries only, reading `repository`, `spec_path`, `source_kind`
and `origin_issue`:

- **(a)** Both pages come from the same spec directory: the same
  `repository` and the same directory part of `spec_path` (a directory in
  another repository is another directory).
- **(b)** One page comes from a pitch (`spec_path` is
  `specs/pitches/<id>/pitch.md`) and the other from a spec bundle of the same
  repository (`spec_path` is `specs/<name>/plan.md` or `specs/<name>/spec.md`)
  whose `origin_issue` is an integer equal to the leading number of the pitch
  id (the run of digits the id starts with; an id with none never meets (b)).
- **(c)** Both pages come from pitch files.

A pair that meets a rule is named by the first rule it meets, in the order
(a), (b), (c). Every other pair is not a restatement.

A spec bundle with no `origin_issue` never meets (b). On the held-out set that
is `wiki-studio-0-1-0` and `wiki-studio-0-6-0`, whose `plan.md` `origin:`
blocks hold no `issue:` at the wiki-studio pin (checked with `git show` in
this phase; plan, O3): a pitch paired with either is not a restatement. A
memkernel bundle never meets (b) either: its `origin_issue` is null, because
its `plan.md` `issue:` names a memkernel issue as a string, never an integer.
Cycle 10's corpus holds no pitch and no `source_kind` or `origin_issue`
fields (read as null), so only (a) can apply there.

**Pair scope** (reported, not binding): `one-feature` when (a) or (b) holds;
else `within-repository` when both pages share a repository; else
`cross-repository`.

## The bar, selection, the verdict and the winner line

On the held-out set only. A candidate **passes** when all four hold:

1. The frozen labels hold at least **8** true pairs (n >= 8); otherwise the
   verdict is `not testable`, never a pass.
2. It finds at least three quarters of the true pairs, rounded up, counted
   per true pair: `4 * found >= 3 * n`.
3. Its false pairs do not outnumber its true ones: `false <= true`, where
   true is the true pairs found.
4. At least **2** of its true pairs found are not restatements.

**Selection.** Among passing candidates, the fewest false pairs per true pair
wins: A beats B when `false_A * true_B < false_B * true_A`. A tie goes to the
smaller k.

**The verdict** is `winner` when a candidate passes; `no candidate clears the
bar` when n >= 8 and none passes; `not testable` when n < 8.

**The winner line** of `report.md` is exactly one line, one of:

```
Winner: mutual-top-1
Winner: mutual-top-3
Winner: mutual-top-5
Winner: none
```

`Winner: none` goes with the verdicts `no candidate clears the bar` and `not
testable`. Nothing else counts toward the verdict.

## The development stage and its stop rule

Before any held-out page is extracted, the three candidates run once on cycle
10's frozen corpus and labels (the development inputs above) under the index
and query rule above. Counts are taken as on the held-out set.

**The stop rule** (trigger 0): the held-out stage goes ahead only if at least
one candidate's false pairs on that corpus do not outnumber its true pairs
found there (`false <= true`); otherwise the bet stops. The development stage
line of `report.md` is exactly one line, one of:

```
Development stage: go
Development stage: stop
```

Its counts never decide a pass. They are reported as committed, and the
candidates are not run on that corpus again for any reading; a CI test may
only reproduce the committed bytes.

## The held-out set

### Sources and pins

| Repository | Pin | Commit date | Default checkout |
|---|---|---|---|
| wiki-studio | `04009eedfb25b5f27d898c5fdfd0bc4ee1bb1c86` | 2026-11-27 | this repository |
| memkernel | `5984ee7a0ebd47044f2da617e46a7535285da5b4` | 2026-11-27 | `../memkernel` |

Both pins were resolved in this phase with read-only git:
`git rev-parse --verify 04009eedfb25b5f27d898c5fdfd0bc4ee1bb1c86^{commit}`
for wiki-studio (`main` after the pitch merged, before this bundle existed;
plan, O2), and `git -C ../memkernel rev-parse --verify main^{commit}` for
memkernel (the commit its local `main` pointed to when this phase ran). The
dates come from `git log -1` on each pin.

- **wiki-studio**: every `specs/<name>/plan.md` and `specs/<name>/spec.md`
  (plan before spec) and every `specs/pitches/<id>/pitch.md` at the pin, with
  no exclusion.
- **memkernel**: only the directories
  `memkernel-0-17-supersede-and-canonical-hash` and
  `memkernel-0-18-imported-page-collapse`, which exist at the pin (checked
  with `git -C ../memkernel ls-tree --name-only <pin> -- specs/`).
- **code-copilot-team** contributes nothing (pitch, finding 8).

Nothing is fetched, and nothing is written to either repository.

### The extraction rule

Cycle 10's rule, unchanged and not tuned: decision sections, the three item
forms and `h3-adr`, the title rule, the four-step body rule, the page form,
and the closing-keyword left-out rule, as `specs/wiki-studio-duplicates-121/spec.md`
FR-004 to FR-007 and `eval/duplicates/README.md` ("The extraction rule, step
by step", "Items left out for closing-keyword text") state them. It is
applied through `eval/duplicates/extract.py`'s own functions, imported
read-only. An item extracted badly is kept as written and listed in
`held-out/README.md`. An item left out still takes its ordinal.

### Slugs, pages and `corpus.json`

- **Page slugs** (the corpus path, not the index path):
  `ws-<spec name>-<plan|spec>-<nn>` and `ws-pitch-<pitch id>-<nn>` for
  wiki-studio, `mk-<spec name>-<plan|spec>-<nn>` for memkernel; `nn` is the
  item's 1-based ordinal in its file, two digits.
- **Pages** at `held-out/corpus/<repository>/<slug>.md`; an entry's `page` is
  that path relative to `held-out/corpus/`.
- **`held-out/corpus.json`** records both pins and commit dates, the options
  (`wiki_studio_only`), and each page's `page`, `repository`, `spec_path`,
  `line_start`, `line_end`, `form`, `title`, `sha256`, `source_kind` (`spec`
  or `pitch`) and `origin_issue`, and the items under `left_out` by id only.
  Pages are listed sorted by `page`, as cycle 10's `corpus.json` lists them.
- **`origin_issue`**: for a spec page, the integer on the `issue:` line inside
  the `origin:` block of its bundle's `plan.md` frontmatter at the pin, else
  null; for a pitch page, null.
- **Families**: one per repository, `wiki-studio` and `memkernel` (plan, O6).
- **Narrowing** (trigger 2): run with `--wiki-studio-only`, memkernel is
  dropped and `wiki_studio_only` is recorded as true.

### Labelling

As cycle 10 (`specs/wiki-studio-duplicates-121/spec.md` FR-013 to FR-016),
per family:

- The labeller reads every page of the family, groups pages that answer the
  same question, and gives each in-group pair one disposition of the six
  (`redundant`, `conflicting`, `supersedes` true; `companion`,
  `distinct-by-precondition`, `unrelated` false) with a one-line reason that
  names the question.
- A within-family pair outside every group is `unrelated`.
- One summary pass over all families (one line per group, one line per page
  in no group) lists the cross-repository pairs, each read before it is
  labelled. An unlisted cross pair is `unrelated`.
- A pitch decision and the spec decision it restates are labelled by content
  like any pair (usually `redundant`).

**Isolation.** The labeller never opens `eval/duplicate_audit/audit.py`,
`eval/duplicate_audit/results/`, `report.md`, or any `results/` directory
under `eval/`, and runs no script (plan, O6). Labels are by content only.

**The review sample.** 20 pairs drawn by `eval/duplicate_audit/sample.py`
with seed 121 from the within-family pairs whose label is false: a fixed 16
from `wiki-studio` and 4 from `memkernel` (the owner, O11). If a family has
fewer false pairs than its share, it gives all it has and the rest come from
the other family. Within each family the draw is
`random.Random(121).sample(sorted(population), k)`. It is drawn once, from the
labelling commit's labels, before any owner change, and never re-drawn.

**The owner's review.** The owner reviews every true and `companion` label,
every listed cross pair and the 20 sampled pairs; changes land as commits
before the freeze.

**The freeze.** With fewer than 8 true pairs the verdict is `not testable`,
stated in `held-out/freeze.json` before any candidate runs on the set; the
audit still runs and is published. No candidate runs on the held-out set
before `freeze.json` exists. No source is added after labelling starts.

## The time bound

With the switch on, the kind adds at most **10 s** to `findings` on the CI
runner on a 500-page synthetic wiki.

**The synthetic wiki.** The frozen held-out pages in `corpus.json` order,
cycled to 500: for i = 0 to 499, page i is held-out page `i mod N` (N the
number of held-out pages). Copy `c = i div N` sits at the page's title-slug
path, with `-c<c>` appended to the stem for `c >= 1`. An `index.md` links all
500 in that order; a `log.md` is present.

**Measured** as the wall time of one `findings` run with the switch on minus
one with it off, on that wiki (plan, O12). The audit script records its own
pass time on this wiki as an early sign, and the kind's test checks the
bound. If the frozen rule misses it, the kind is cut (trigger 5), never
replaced by a faster rule.

## Reported, never binding

Reported beside the verdict and never part of it:

1. Per candidate, the counts per 100 pages (two decimals).
2. False pairs by disposition.
3. Flagged pairs by pair scope, and by restatement or not.
4. The groups with at least one flagged true pair (pitch, finding 11: groups
   cap recall).
5. The true pairs found that are not restatements and involve
   `wiki-studio-0-1-0` or `wiki-studio-0-6-0`, listed (plan, O3), so a reader
   can see whether condition 4 rests on them.
6. The development stage's counts, copied as committed.
7. The wall times.

**Stated plainly.** Cycle 10's 8 true pairs have been read by three cycles and
are development data. The pitch's finding 7 did arithmetic on published ranks
while shaping. The held-out set is the only binding evidence.

**Post hoc.** Anything found after a run goes into a `post_hoc` block of that
run's results file marked `"binding": false`, computed by `audit.py` with its
rule in one constant, and into a "Post hoc (not binding)" section of the
report. It never changes a candidate, k, the index rule, the restatement
rule, the bar, a label or a verdict line.
