# The similar-pages study: report (issue 121)

This report gives the measurement that `README.md` in this directory defines
and that `protocol.json` freezes. The query rule, the title-slug paths, k, the
13 tries, the bar and the readings that are not binding were committed,
signed off by the owner and pinned by sha256 (`tests/test_similar_frozen.py`)
before the ranking script existed. Every figure here is copied from
`results/ranks.json` and `results/timing.json` as recorded. Nothing is
rounded by hand except the wall times, shown to three decimals.

## How the results were produced

At the pause after the ranking script, the main session ran it once and
committed its two files as written, as their own commit:

```
python -m eval.similar.rank
```

The script first checks every input `protocol.json` pins and every corpus
page against its `corpus.json` entry, and refuses to run, writing nothing,
on any difference. It runs no git, calls no model, opens no network
connection and reads nothing outside the repository, so CI reruns it:
`tests/test_similar_results.py` writes its output to a temporary directory
(`python -m eval.similar.rank --out-dir DIR`) and checks that `ranks.json`
equals the committed file byte for byte. `timing.json` is checked for its
keys only, since a rerun's wall time never matches.

The corpus holds 299 decision pages, each indexed under its title-slug path.
The frozen labels hold 8 true pairs, 5 `redundant` and 3 `supersedes`, which
give 13 tries: each `redundant` pair both ways, each `supersedes` pair once
with the later ruling as the query. The ranker configuration recorded at run
time is tokenizer `porter unicode61`, weights path 4, title 4, headings 2,
body 1, `min_match_tokens` 1, configuration hash
`c4b6576a6bc57e3c1b8c7f70ef6bb19b5dcf44d0ea0c30ab7dc0192965a43521`.

## Results

Each try with the partner's rank among the compared pages and whether it is
in the top 5 (paths under `eval/duplicates/corpus/`):

| # | Query | Partner | Disposition | Partner rank | Found |
|---|---|---|---|---|---|
| 1 | `code-copilot-team/routing/cct-routing-effective-endpoint-plan-01.md` | `code-copilot-team/routing/cct-routing-effective-endpoint-spec-01.md` | redundant | 1 | yes |
| 2 | `code-copilot-team/routing/cct-routing-effective-endpoint-spec-01.md` | `code-copilot-team/routing/cct-routing-effective-endpoint-plan-01.md` | redundant | 1 | yes |
| 3 | `code-copilot-team/routing/cct-routing-effective-endpoint-plan-02.md` | `code-copilot-team/routing/cct-routing-effective-endpoint-spec-02.md` | redundant | 1 | yes |
| 4 | `code-copilot-team/routing/cct-routing-effective-endpoint-spec-02.md` | `code-copilot-team/routing/cct-routing-effective-endpoint-plan-02.md` | redundant | 1 | yes |
| 5 | `code-copilot-team/routing/cct-routing-effective-endpoint-plan-03.md` | `code-copilot-team/routing/cct-routing-effective-endpoint-spec-03.md` | redundant | 1 | yes |
| 6 | `code-copilot-team/routing/cct-routing-effective-endpoint-spec-03.md` | `code-copilot-team/routing/cct-routing-effective-endpoint-plan-03.md` | redundant | 1 | yes |
| 7 | `code-copilot-team/routing/cct-routing-context-limit-plan-07.md` | `code-copilot-team/routing/cct-routing-context-limit-plan-08.md` | redundant | 1 | yes |
| 8 | `code-copilot-team/routing/cct-routing-context-limit-plan-08.md` | `code-copilot-team/routing/cct-routing-context-limit-plan-07.md` | redundant | 1 | yes |
| 9 | `code-copilot-team/routing/cct-routing-shadow-plan-07.md` | `code-copilot-team/routing/cct-routing-shadow-plan-11.md` | redundant | 4 | yes |
| 10 | `code-copilot-team/routing/cct-routing-shadow-plan-11.md` | `code-copilot-team/routing/cct-routing-shadow-plan-07.md` | redundant | 3 | yes |
| 11 | `code-copilot-team/pi/cct-pi-project-config-spec-01.md` | `code-copilot-team/pi/cct-pi-harness-adoption-plan-05.md` | supersedes | 6 | no |
| 12 | `memkernel/memkernel/mk-memkernel-0-14-capture-signals-spec-06.md` | `memkernel/memkernel/mk-memkernel-0-12-capture-core-spec-05.md` | supersedes | 3 | yes |
| 13 | `code-copilot-team/one-harness-home/cct-one-harness-home-spec-01.md` | `code-copilot-team/pi/cct-pi-harness-adoption-plan-05.md` | supersedes | 35 | no |

The summary, as recorded:

| Reading | Found | `supersedes` found | Pairs with a found try |
|---|---|---|---|
| the query rule (binding) | 11 of 13 | 1 of 3 | 6 of 8 |

The bar's two conditions: at least 10 of the 13 tries found (11, holds), and
at least 1 of the 3 `supersedes` tries found (1, holds, at the limit).

Verdict: pass

All 10 `redundant` tries find the partner, 8 of them at rank 1 and the two
`shadow-plan` tries at ranks 4 and 3. Of the `supersedes` tries, the memkernel
pair is found at rank 3. The two missed tries are both rulings that move where
a configuration lives, and both have the harness adoption plan as the partner:
the project-configuration ruling ranks it 6th, one place outside the list, and
the user-home ruling ranks it 35th. These are the location-only rulings the
pitch expected the hint to miss. Counted by pair, 6 of the 8 pairs have at
least one found try; the two `supersedes` pairs above have none.

## The noise (not binding)

Every other page in the 13 lists, by its label against the query (65 listed
pages, 11 of them the partner):

| Label | Pages |
|---|---|
| companion | 7 |
| unrelated | 47 |

No listed page other than a partner carries a true disposition against its
query. The 7 `companion` pages are in the `shadow-plan` lists (tries 9 and
10) and the two missed `supersedes` lists (tries 11 and 13); every other list
holds the partner and four `unrelated` pages. This is what a proposer would
read besides the partner: on these 13 tries, 54 pages of 65 listed.

## Two other query readings (not binding)

The same 13 tries ranked with the whole page as written (frontmatter
included) as the query, and with the body only (no title). The partner's rank
in each try, for the query rule and both readings:

| # | Query rule (binding) | Whole page | Body only |
|---|---|---|---|
| 1 | 1 found | 1 found | 32 missed |
| 2 | 1 found | 1 found | 6 missed |
| 3 | 1 found | 1 found | 1 found |
| 4 | 1 found | 1 found | 1 found |
| 5 | 1 found | 1 found | 1 found |
| 6 | 1 found | 1 found | 1 found |
| 7 | 1 found | 1 found | 1 found |
| 8 | 1 found | 1 found | 1 found |
| 9 | 4 found | 4 found | 9 missed |
| 10 | 3 found | 3 found | 5 found |
| 11 | 6 missed | 20 missed | 5 found |
| 12 | 3 found | 11 missed | 7 missed |
| 13 | 35 missed | 85 missed | 33 missed |

| Reading | Found | `supersedes` found | Pairs with a found try |
|---|---|---|---|
| whole page (not binding) | 10 of 13 | 0 of 3 | 5 of 8 |
| body only (not binding) | 8 of 13 | 1 of 3 | 5 of 8 |

Neither reading counts toward the verdict. The whole-page reading matches the
query rule on every `redundant` try and loses the memkernel `supersedes` try.
The body-only reading loses three `redundant` tries (1, 2 and 9) and finds the project-configuration ruling's partner at rank
5. The user-home ruling is missed under all three readings.

## The issue 54 fixture (not binding)

The curated issue 54 fixture (`eval/patterns/wiki/`), ranked as the hint would
rank it: the 32 pages linked from `index.md` once the 2 superseded pages are
left out (`decisions/benchmark-ui-was-backend-free-one-shot-and-studio-only.md`,
`decisions/merge-require-green-ci-was-never-read.md`), under their own paths,
without the query page, kept when of the query page's page type, k = 5:

| # | Query | Partner | Disposition | Partner rank | Found |
|---|---|---|---|---|---|
| 1 | `decisions/balanced-profile-denies-destructive-git-commands.md` | `decisions/destructive-git-commands-require-confirmation.md` | conflicting | 1 | yes |
| 2 | `decisions/destructive-git-commands-require-confirmation.md` | `decisions/balanced-profile-denies-destructive-git-commands.md` | conflicting | 1 | yes |
| 3 | `decisions/never-archive-raw-jsonl.md` | `decisions/trace-archive-reuses-the-ingest-redaction-path.md` | redundant | 1 | yes |
| 4 | `decisions/trace-archive-reuses-the-ingest-redaction-path.md` | `decisions/never-archive-raw-jsonl.md` | redundant | 1 | yes |

| Reading | Found | Pairs with a found try |
|---|---|---|
| the fixture (not binding) | 4 of 4 | 2 of 2 |

The fixture's third true pair as recorded,
`decisions/never-bypass-a-git-lock-with-an-alternate-index.md` (a decision)
and `incidents/git-safety-bypasses.md` (an incident), is a pair the hint never
lists: the two pages differ in page type, so the same-page-type rule keeps
one out of the other's list. It was not ranked.

## Collisions

Each slug that more than one corpus page's title gives, with its pages in
`corpus.json` order and the paths they were indexed under:

| Slug | Pages | Paths |
|---|---|---|
| `adds-no-runtime-authority` | `code-copilot-team/routing/cct-routing-eval-plan-10.md`, `code-copilot-team/routing/cct-routing-shadow-plan-11.md` | `decisions/adds-no-runtime-authority.md`, `decisions/adds-no-runtime-authority-2.md` |
| `scope` | `code-copilot-team/pi/cct-pi-team-controller-plan-01.md`, `memkernel/memkernel/mk-memkernel-0-7-release-b-exit-plan-03.md` | `decisions/scope.md`, `decisions/scope-2.md` |
| `stays-opportunistic` | `code-copilot-team/routing/cct-routing-effective-endpoint-plan-03.md`, `code-copilot-team/routing/cct-routing-effective-endpoint-spec-03.md` | `decisions/stays-opportunistic.md`, `decisions/stays-opportunistic-2.md` |

These are the three titles shared by two pages each; no two different titles
gave the same slug. Two of the collisions touch the tries: the
`effective-endpoint` pair of tries 5 and 6 shares its title, and
`shadow-plan-11` (tries 9 and 10) shares its title with its `companion`
`eval-plan-10`. A shared title puts the same words in both pages' path and
title, which the ranker weighs 4 each.

## Limits

Stated plainly, these bound what the verdict says:

- **Development data.** The 8 pairs are development data, and two readings
  were already run on them before the protocol was written (the pitch's
  finding 6), so a pass is weak evidence. There is no held-out set.
- **13 tries from 8 pairs.** The two tries of one `redundant` pair are not
  independent; 10 of the 13 tries come from 5 pairs.
- **Extracted, not curated.** The corpus is spec decisions extracted from two
  repositories, not curated wiki pages. The issue 54 fixture is the only
  curated reading, and it is not binding.
- **One family.** 7 of the 8 pairs sit within one spec family, where shared
  jargon helps the ranker; only the user-home pair crosses families, and it
  is missed.
- **Decision pages only.** Every corpus page is a decision page, so the
  same-page-type rule is unmeasured on the corpus.
- **Location-only rulings.** A ruling that only moves where something lives
  shares few words with the ruling it replaces. The user-home pair is missed
  at rank 35, and the project-configuration pair at rank 6.

## Timing

As recorded in `results/timing.json` (not reproduced by CI), with
`time.perf_counter`: the binding pass over the 13 tries took 0.099 s, the
whole-page reading 0.105 s, the body-only reading 0.098 s, and the fixture's 4
tries over its 32 pages 0.014 s.
