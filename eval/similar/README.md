# The similar-pages study (issue 121)

Issue 121 asks whether wiki-studio can tell a curator that two pages record
the same decision. The near-duplicate study in `eval/duplicates/` measured a
model-free `findings` kind for it and found 3 of 8 true pairs against the 6
its bar needed, so nothing was built. This directory measures a different
place: the moment a page is proposed. For each new page, `propose` would list
the few existing pages most like it, ranked by the FTS5 ranker `find` already
uses, as a hint that never blocks. The bet pitch
`specs/pitches/121-similar-pages-at-propose/pitch.md` shapes it, and
`specs/wiki-studio-similar-121/` specifies it.

- **wiki-studio commit read**: the branch base,
  `ef1b07ff84de5bb17b234ee0e04bb78927877ac4` (`main` after the spec's
  approval).
- **What is measured**: in how many of the 13 tries below the partner page
  is in the top 5, and in how many of the 3 `supersedes` tries it is.
- **What is not measured**: a precision or recall estimate; page types other
  than `decision` (every corpus page is a decision page); curated pages (the
  corpus is extracted spec decisions, not curated pages); agent behaviour.
- `eval/duplicates/` and `eval/patterns/` are read and never edited.
- No result depends on a model. Nothing here calls one.
- The ranking script (`rank.py`) and the report (`report.md`) are written
  after the owner signs this protocol off. This README holds the protocol
  only and is frozen with `protocol.json` by `tests/test_similar_frozen.py`;
  the results and the script's command line go into `report.md`.

## Inputs (read-only, pinned)

Every input is checked against its sha256 before anything is ranked; a
difference stops the run with nothing written.

| Input | sha256 |
|---|---|
| `eval/duplicates/corpus.json` | `fc0f710ab994dd4a57a9bb23e700bd61b2ffde58f66a54bb30353c6cc5bbc4de` |
| every page under `eval/duplicates/corpus/` | its `corpus.json` entry's `sha256` |
| `eval/duplicates/labels.json` | `e1c34ca9533aedb39482d628fd8704752035fba3ca34f132d730f8a555082287` |
| `eval/patterns/labels.json` | `96da1b5a7553096ca38e7f0491692b61018c6735cc70d1dcf5c1afc478f39a7e` |
| `eval/patterns/manifest.json` | `1f1a4bf3b4908ec9549b3717685d772182858486e996f6aaa4250fd994360b29` |
| `eval/patterns/wiki/index.md` | `e832d71a742a7be65486ccf4864f4322e7b4a9e49966be85944a64fd9164f7e4` |
| the 34 fixture pages `index.md` links | each listed with its own sha256 in `protocol.json`'s `inputs` |

The first three values are the ones `tests/test_duplicates_frozen.py` and
`tests/test_patterns_frozen.py` pin; they were re-checked with a shell
sha256 tool when this protocol was written, and the others were computed the
same way. `index.md` decides which fixture pages are compared and the order
their ties are broken in. `manifest.json` holds no page hashes, so the fixture
pages are pinned one by one here, as `corpus.json` pins the corpus pages.

## The index each try ranks over

**Paths.** Every corpus page is indexed under `decisions/<slug>.md`, the path
a curated page would have (`schema/page-types.md`: the slug equals the
filename stem and is by convention the title in kebab-case), never under its
corpus path. The corpus paths carry the source spec's name, which a curated
page's path would not.

**The slug.** The page's `title` field in `corpus.json`, lowercased; every
run of characters outside `[a-z0-9]` replaced by one `-`; leading and
trailing `-` removed; `untitled` when nothing is left.

**Collisions.** Pages are taken in `corpus.json` order. The first page with a
slug keeps it; a later page with the same slug gets `<slug>-2`, then `-3`,
skipping any value another page already holds. Three titles are each shared
by two pages; a collision between different titles follows the same rule and
is reported, never tuned.

**The query page is left out.** Each try's index holds every corpus page
except the query page, as a proposed page is not yet in the wiki, in
`corpus.json` order. That order breaks bm25 ties, as `index.md` order breaks
them for the hint.

**The ranker.** The index is built with
`search_index.build_document(<slug path>, <page text>)` for each page and
`search_index.build_in_memory(..., tokenizer=DEFAULT_RANKER_CONFIG.tokenizer)`,
and ranked with `SearchIndex.rank(query, order=<the index's paths in
corpus.json order>, weights=DEFAULT_RANKER_CONFIG.weights,
min_match_tokens=DEFAULT_RANKER_CONFIG.min_match_tokens)`. At this commit that
configuration is tokenizer `porter unicode61`, weights path 4, title 4,
headings 2, body 1, and `min_match_tokens` 1.

**The page-type filter.** The pages compared are the ranked pages whose
frontmatter `page_type` (read with `review.frontmatter_value`) equals the
query page's. Every corpus page is a decision page and none is superseded, so
on the corpus the filter keeps everything; it is applied so the measured path
is the one that would ship.

## The query rule

For a page whose text is `text`, with `doc = build_document(path, text)`:

```
query = doc.title + " " + doc.body
```

- `doc.title` is the frontmatter `title` as `review.frontmatter_value` reads
  it, the empty string when absent.
- one space.
- `doc.body` is the page's lines after the frontmatter joined with `\n`, or
  all the page's lines when there is no closed frontmatter block.

No other frontmatter key is in the query (`slug`, `sources:` and the rest
describe where a page came from, not what it says). The query reaches FTS5
only through `search_index.build_query`: its `_tokenise` tokens, sorted, each
quoted, joined by `OR`.

## The tries (the direction rule)

The true pairs are the entries of `eval/duplicates/labels.json`'s `pairs` and
`cross_pairs` whose disposition is `redundant`, `conflicting` or
`supersedes`. The frozen labels hold 5 `redundant`, 3 `supersedes` and 0
`conflicting`.

The hint runs when the second page of a pair is proposed. A `redundant` pair
could be proposed in either order, so it is tried both ways, each page once as
the query with the other as the partner. A `supersedes` pair is tried once,
the later ruling as the query. The later page of each `supersedes` pair, read
from its label's reason:

| Later page (the query) | Earlier page (the partner) |
|---|---|
| `code-copilot-team/pi/cct-pi-project-config-spec-01.md` | `code-copilot-team/pi/cct-pi-harness-adoption-plan-05.md` |
| `memkernel/memkernel/mk-memkernel-0-14-capture-signals-spec-06.md` | `memkernel/memkernel/mk-memkernel-0-12-capture-core-spec-05.md` |
| `code-copilot-team/one-harness-home/cct-one-harness-home-spec-01.md` | `code-copilot-team/pi/cct-pi-harness-adoption-plan-05.md` |

5 x 2 + 3 = **13 tries**, in this fixed order (corpus paths, relative to
`eval/duplicates/corpus/`):

| # | Query | Partner | Disposition |
|---|---|---|---|
| 1 | `code-copilot-team/routing/cct-routing-effective-endpoint-plan-01.md` | `code-copilot-team/routing/cct-routing-effective-endpoint-spec-01.md` | `redundant` |
| 2 | `code-copilot-team/routing/cct-routing-effective-endpoint-spec-01.md` | `code-copilot-team/routing/cct-routing-effective-endpoint-plan-01.md` | `redundant` |
| 3 | `code-copilot-team/routing/cct-routing-effective-endpoint-plan-02.md` | `code-copilot-team/routing/cct-routing-effective-endpoint-spec-02.md` | `redundant` |
| 4 | `code-copilot-team/routing/cct-routing-effective-endpoint-spec-02.md` | `code-copilot-team/routing/cct-routing-effective-endpoint-plan-02.md` | `redundant` |
| 5 | `code-copilot-team/routing/cct-routing-effective-endpoint-plan-03.md` | `code-copilot-team/routing/cct-routing-effective-endpoint-spec-03.md` | `redundant` |
| 6 | `code-copilot-team/routing/cct-routing-effective-endpoint-spec-03.md` | `code-copilot-team/routing/cct-routing-effective-endpoint-plan-03.md` | `redundant` |
| 7 | `code-copilot-team/routing/cct-routing-context-limit-plan-07.md` | `code-copilot-team/routing/cct-routing-context-limit-plan-08.md` | `redundant` |
| 8 | `code-copilot-team/routing/cct-routing-context-limit-plan-08.md` | `code-copilot-team/routing/cct-routing-context-limit-plan-07.md` | `redundant` |
| 9 | `code-copilot-team/routing/cct-routing-shadow-plan-07.md` | `code-copilot-team/routing/cct-routing-shadow-plan-11.md` | `redundant` |
| 10 | `code-copilot-team/routing/cct-routing-shadow-plan-11.md` | `code-copilot-team/routing/cct-routing-shadow-plan-07.md` | `redundant` |
| 11 | `code-copilot-team/pi/cct-pi-project-config-spec-01.md` | `code-copilot-team/pi/cct-pi-harness-adoption-plan-05.md` | `supersedes` |
| 12 | `memkernel/memkernel/mk-memkernel-0-14-capture-signals-spec-06.md` | `memkernel/memkernel/mk-memkernel-0-12-capture-core-spec-05.md` | `supersedes` |
| 13 | `code-copilot-team/one-harness-home/cct-one-harness-home-spec-01.md` | `code-copilot-team/pi/cct-pi-harness-adoption-plan-05.md` | `supersedes` |

The `redundant` pairs come in `labels.json` order, each with its sorted-first
page as the first query; then the three `supersedes` tries in `labels.json`
order (`pairs` before `cross_pairs`). **The two tries of one `redundant` pair
are not independent: the 13 tries come from 8 pairs.**

## The list and the bar

- **The list**: the first **k = 5** compared pages for the query, best first.
  No score floor (bm25 scores are not comparable across queries).
- **Found**: the partner's title-slug path is in the list.
- **The partner's rank**: its 1-based position among all compared pages that
  match at least one query token, or none when it matches none.
- **The bar**, both conditions:
  1. the partner is found in at least **10 of the 13 tries**, and
  2. the partner is found in at least **1 of the 3 `supersedes` tries**.
- **The verdict** is `pass` when both hold, else `fail`. The report's verdict
  line is exactly one line, either `Verdict: pass` or `Verdict: fail`.
- Below either condition the hint is not built. Nothing else counts toward
  the verdict.

## Reported, never binding

These are reported beside the verdict and are never part of it:

1. **Ranks**: the partner's rank in every try, and how many of the 8 pairs
   have at least one found try.
2. **The noise**: every other page in each of the 13 lists, by its label
   against the query (`eval/duplicates/labels.json`'s disposition for that
   pair, else `unrelated`), counted by label. It is what a proposer would read
   besides the partner.
3. **The issue 54 fixture, ranked as the hint would rank it.** The pages
   linked from `eval/patterns/wiki/index.md` (each link normalised; `index.md`
   and `log.md` never; a link whose file is missing, is not a regular file or
   is not UTF-8 skipped, as `discovery.select` skips it), under their own
   paths, without the 2 pages that carry `superseded_by`
   (`decisions/benchmark-ui-was-backend-free-one-shot-and-studio-only.md`,
   `decisions/merge-require-green-ci-was-never-read.md`), without the query
   page, in `index.md` link order; ranked with the configuration and the query
   rule above, then kept only when of the query page's page type; k = 5. Of
   its 3 true pairs as recorded (`redundant` or `conflicting` in
   `eval/patterns/labels.json`'s `pattern_pairs` and `background_pairs`), the
   2 whose pages share a page type are tried both ways, 4 tries:
   - `decisions/balanced-profile-denies-destructive-git-commands.md` and
     `decisions/destructive-git-commands-require-confirmation.md`
     (`conflicting`);
   - `decisions/never-archive-raw-jsonl.md` and
     `decisions/trace-archive-reuses-the-ingest-redaction-path.md`
     (`redundant`).

   The third, the background pair whose pages differ in page type
   (`decisions/never-bypass-a-git-lock-with-an-alternate-index.md`, a
   decision; `incidents/git-safety-bypasses.md`, an incident), is reported as
   a pair the hint never lists, without ranking.
4. **Two other query readings** on the 13 tries, with found counts and ranks:
   the whole page as written (frontmatter included), and the body only
   (`doc.body`, no title).

**Stated plainly.** The 8 pairs are development data. Two readings were
already run on them (the pitch's finding 6), so a pass is weak evidence.
There is no held-out set. The issue 54 fixture, never run through this
ranker, is the only curated reading, and it is not binding.

**Post hoc.** Anything found after the run goes into a `post_hoc` block of
`results/ranks.json` marked `"binding": false`, computed by `rank.py` from the
committed inputs with its rule in one constant, and into a "Post hoc (not
binding)" section of the report. It never changes the query rule, k, the
slug rule, the direction rule, the bar or the verdict line.
