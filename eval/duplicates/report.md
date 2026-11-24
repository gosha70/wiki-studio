# The near-duplicate study: report (issue 121)

This report gives the measurement that `README.md` in this directory defines
and that `protocol.json` freezes. The corpus, the labels, the two candidates,
the threshold, the bar and the selection rule were committed, reviewed by the
owner and pinned by sha256 (`tests/test_duplicates_frozen.py`) before any
candidate code existed. Every figure here is copied from
`results/candidates.json` and `results/secondary.json` as recorded. Nothing is
rounded by hand except the wall times, shown to three decimals.

## How the results were produced

At the pause after the scorer, the main session ran the scorer once and
committed its three files as written, as their own commit:

```
python -m eval.duplicates.candidates
```

The scorer first checks that `corpus.json` and `labels.json` hash to the
values `protocol.json` records, and refuses to run otherwise. It runs no git,
calls no model and reads nothing outside the repository, so CI reruns it:
`tests/test_duplicates_results.py` writes its output to a temporary directory
(`python -m eval.duplicates.candidates --out-dir DIR`) and checks that
`candidates.json` and `secondary.json` equal the committed files byte for
byte. `timing.json` is not compared, since a rerun's wall time never matches.

The corpus holds 299 pages and 44551 pairs: 9754 within a family, 14799
across the families of one repository and 19998 across the two repositories.
The frozen labels hold 8 true pairs: 5 `redundant` and 3 `supersedes`, none
`conflicting`; 7 within a family, 1 across the families of code-copilot-team,
none across the repositories.

## Results

| Candidate | True pairs found | True candidates | False candidates | False per 100 pages | Bar |
|---|---|---|---|---|---|
| B0 | 3 of 8 | 3 | 3 | 1.00 | fail |
| B1 | 3 of 8 | 3 | 3 | 1.00 | fail |

The bar's three conditions:

| Candidate | At least 8 true pairs | Three quarters found | False not above true | Overall |
|---|---|---|---|---|
| B0 | yes | no | yes | fail |
| B1 | yes | no | yes | fail |

The labels hold exactly the minimum of 8 true pairs, so the bar is testable.
Three quarters of 8, rounded up, is 6; each candidate finds 3. Each
candidate's 3 false candidates do not outnumber its 3 true ones, so condition
3 holds at the limit. Recall decides: both fail.

**Verdict:** no candidate clears the bar.

Winner: none

False candidates by disposition:

| Candidate | companion | distinct-by-precondition | unrelated |
|---|---|---|---|
| B0 | 1 | 0 | 2 |
| B1 | 1 | 0 | 2 |

True and false candidates by pair scope:

| Candidate | within-family true | within-family false | cross-family true | cross-family false | cross-repository true | cross-repository false |
|---|---|---|---|---|---|---|
| B0 | 3 | 3 | 0 | 0 | 0 | 0 |
| B1 | 3 | 3 | 0 | 0 | 0 | 0 |

True and false candidates by repository:

| Candidate | code-copilot-team true | code-copilot-team false | memkernel true | memkernel false | cross-repository true | cross-repository false |
|---|---|---|---|---|---|---|
| B0 | 3 | 3 | 0 | 0 | 0 | 0 |
| B1 | 3 | 3 | 0 | 0 | 0 | 0 |

The candidate pairs, with each candidate's shared and union token counts
(paths under `corpus/`):

| Pair | Label | Scope | B0 | B1 |
|---|---|---|---|---|
| `code-copilot-team/llm-catalog/cct-llm-catalog-spec-05.md` and `code-copilot-team/llm-catalog/cct-llm-catalog-spec-13.md` | unrelated | within-family | 7/27 | 7/27 |
| `code-copilot-team/llm-catalog/cct-llm-catalog-spec-13.md` and `code-copilot-team/llm-catalog/cct-llm-catalog-spec-15.md` | unrelated | within-family | 6/23 | 6/22 |
| `code-copilot-team/routing/cct-routing-effective-endpoint-plan-01.md` and `code-copilot-team/routing/cct-routing-effective-endpoint-spec-01.md` | redundant | within-family | 4/10 | 3/7 |
| `code-copilot-team/routing/cct-routing-effective-endpoint-plan-02.md` and `code-copilot-team/routing/cct-routing-effective-endpoint-spec-02.md` | redundant | within-family | 33/66 | 31/64 |
| `code-copilot-team/routing/cct-routing-effective-endpoint-plan-03.md` and `code-copilot-team/routing/cct-routing-effective-endpoint-spec-03.md` | redundant | within-family | 15/34 | 15/33 |
| `code-copilot-team/routing/cct-routing-eval-plan-10.md` and `code-copilot-team/routing/cct-routing-shadow-plan-11.md` | companion | within-family | 21/56 | 19/53 |

Both candidates flag the same six pairs. B1's normalisation changes some
token counts but no pair's outcome, on either side of the threshold. All
three true pairs found are one spec directory's plan and spec recording the
same option ruling in nearly the same words (`routing-effective-endpoint`).
The `companion` false candidate is the routing pair whose label reads: E2
adds no execution authority over production routing and proves it the same
way E1 did, in nearly E1's words. The two
`unrelated` false candidates are pages of the `llm-catalog` extension family.
No candidate pair involves memkernel, and none crosses a family or the
repositories.

## The true pairs' scores (not binding)

Each true pair with both candidates' shared and union token counts, found or
missed at the frozen threshold of one quarter:

| Pair | Label | Scope | B0 | B1 |
|---|---|---|---|---|
| `code-copilot-team/one-harness-home/cct-one-harness-home-spec-01.md` and `code-copilot-team/pi/cct-pi-harness-adoption-plan-05.md` | supersedes | cross-family | 1/52 missed | 1/51 missed |
| `code-copilot-team/pi/cct-pi-harness-adoption-plan-05.md` and `code-copilot-team/pi/cct-pi-project-config-spec-01.md` | supersedes | within-family | 2/44 missed | 2/43 missed |
| `code-copilot-team/routing/cct-routing-context-limit-plan-07.md` and `code-copilot-team/routing/cct-routing-context-limit-plan-08.md` | redundant | within-family | 4/74 missed | 3/73 missed |
| `code-copilot-team/routing/cct-routing-effective-endpoint-plan-01.md` and `code-copilot-team/routing/cct-routing-effective-endpoint-spec-01.md` | redundant | within-family | 4/10 found | 3/7 found |
| `code-copilot-team/routing/cct-routing-effective-endpoint-plan-02.md` and `code-copilot-team/routing/cct-routing-effective-endpoint-spec-02.md` | redundant | within-family | 33/66 found | 31/64 found |
| `code-copilot-team/routing/cct-routing-effective-endpoint-plan-03.md` and `code-copilot-team/routing/cct-routing-effective-endpoint-spec-03.md` | redundant | within-family | 15/34 found | 15/33 found |
| `code-copilot-team/routing/cct-routing-shadow-plan-07.md` and `code-copilot-team/routing/cct-routing-shadow-plan-11.md` | redundant | within-family | 8/92 missed | 7/89 missed |
| `memkernel/memkernel/mk-memkernel-0-12-capture-core-spec-05.md` and `memkernel/memkernel/mk-memkernel-0-14-capture-signals-spec-06.md` | supersedes | within-family | 4/32 missed | 4/27 missed |

The scores split in two. The three found pairs sit well above one quarter.
The five missed pairs share at most 8 tokens, and the highest of them, 4/32
under B0, is one eighth. All three `supersedes` pairs are missed. The two
missed `redundant` pairs are each two decisions of one plan recording the same
ruling, with unions of 74 and 92 tokens under B0. These scores are a
distribution, not a result; no threshold was varied.

## The secondary re-score (not binding)

B0 and B1 on the issue 54 fixture (`eval/patterns/wiki/`, 34 pages, 32
eligible after superseded pages, 496 pairs), read twice: with the labels as
recorded, and with the disputed pair
(`decisions/never-bypass-a-git-lock-with-an-alternate-index.md`,
`incidents/git-safety-bypasses.md`) read as `companion`. Counts only, with
no verdict.

| Reading | True pairs | B0 found | B0 false candidates | B1 found | B1 false candidates |
|---|---|---|---|---|---|
| as recorded | 3 | 2 | 1 | 0 | 2 |
| disputed pair as companion | 2 | 2 | 1 | 0 | 2 |

B0 as recorded reproduces the frozen issue 54 signal (b) counts (3 true
pairs, 2 found, 1 false candidate), as the protocol requires. The disputed
pair is the one B0 missed there, so reading it as `companion` leaves B0's
found and false counts unchanged and lowers n from 3 to 2. B1 finds neither of
the two pairs B0 finds and has one more false candidate. The fixture's pages
are curated wiki pages, the kind B1's template-word drop is meant for; which
of B1's rules moves these pairs is not examined here.

## Timing

As recorded in `results/timing.json` (not reproduced by CI): one scoring pass
over the 299 pages and 44551 pairs took 0.150 s for B0 and 0.156 s for B1
(`time.perf_counter`).

## Limits

- **Extracted spec decisions, not curated pages.** Every page is a decision
  item copied from a spec or plan by the frozen extraction rule (pitch
  finding 14). A curated wiki's decision pages may read differently.
- **Two repositories by one author.** code-copilot-team and memkernel, at
  one pin each.
- **The families measured.** The three base families (`routing`, `pi`,
  `memkernel`) with all eight steps of the extension order added, because the
  labels held fewer than 8 true pairs after each earlier step: `api`,
  `llm-catalog`, `wiki-studio-adoption`, `wiki-audit`,
  `memkernel-integration`, `one-harness-home`,
  `plugin-generate-from-sources` and `simplest-complete-change`. The
  extension order is used up; the eight added families brought no true pair
  of their own, and one true pair through the owner's review (the cross-family
  `one-harness-home` and `pi` pair).
- **Decision pages only.** The other content page types the shipped kind
  would compare (`concept`, `workflow`, `incident`, `playbook`) are
  unmeasured, and nothing is measured across page types.
- **B1's template-word drop is unmeasured here.** It is meant for curated
  template pages, which this corpus does not contain.
- **Recall is a count out of n, not an estimate.** n is 8, the minimum the
  bar allows; each candidate finds 3 of 8.
- **Cuts.** Cut 1 was not invoked; no family was narrowed. No other cut was
  taken in the measurement.
