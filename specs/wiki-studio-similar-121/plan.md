---
spec_mode: full
feature_id: wiki-studio-similar-121
risk_category: feature
justification: "A measurement whose value rests on a query rule, a slug rule, a direction rule and a bar frozen and signed off before any ranking code exists, run once on a corpus another cycle froze; then, only with a pass, an on-by-default hint on every create through api.propose, the CLI and the MCP propose tool, a new optional plan.json key archived into the wiki on promote, a WikiPaths switch read from the environment and an additive MCP result key. A full spec pins the protocol to the character, the per-phase truth rule, the main-session script run between phases, the hand-opened PRs that close nothing, and the cut path before two unattended runs."
status: approved
date: 2026-11-25
collaboration_mode: single
origin:
  issue: 121
  urls:
    - https://github.com/gosha70/wiki-studio/issues/121
    - https://github.com/gosha70/wiki-studio/blob/main/specs/pitches/121-similar-pages-at-propose/pitch.md
    - https://github.com/gosha70/wiki-studio/pull/140
    - https://github.com/gosha70/wiki-studio/pull/141
    - https://github.com/gosha70/wiki-studio/pull/143
    - https://github.com/gosha70/wiki-studio/blob/main/eval/duplicates/report.md
    - https://github.com/gosha70/wiki-studio/pull/137
    - https://github.com/gosha70/wiki-studio/pull/138
  origin_claim: |
    Issue 121 (filed by the owner on 2026-11-22, still open) asks whether
    wiki-studio can tell a curator that two pages record the same decision.
    Cycle 10 measured a model-free findings kind for it (evidence PR #137,
    eval/duplicates/report.md; spec amendment PR #138): word overlap of title
    and first paragraph found 3 of 8 true pairs against the 6 the bar needed,
    winner none, nothing built. The owner's comment on issue 121 of
    2026-11-24: a new candidate rule needs a new pitch, and the frozen corpus
    and labels in eval/duplicates/ can be reused to measure it. The bet pitch
    specs/pitches/121-similar-pages-at-propose/pitch.md (shaped and revised
    after review in PR #140, the owner's two points after its merge in
    PR #141, bet for cycle 11 in PR #143) proposes a
    hint instead of a finding: when a page is proposed, list the existing
    pages most like it, ranked by the FTS5 ranker find already uses,
    model-free, never blocking, measured first on the frozen corpus with the
    query rule and the bar fixed before the run. Owner decisions (2026-11-24,
    every default): D1 2w; D2 measure first, build only with a pass; D3 the
    query is the frontmatter title, a space, and the body after the
    frontmatter; D4 k = 5, no score floor; D5 same page type, superseded and
    non-index-linked pages excluded; D6 creates only; D7 a plan.json key, CLI
    stderr lines and an MCP propose result key; D8 no list without FTS5, one
    line saying why; D9 on by default, WIKI_STUDIO_SIMILAR_PAGES=off read
    into WikiPaths; D10 issue 121 stays open and the owner decides by hand.
    Review changes (2026-11-25): corpus pages indexed under title-slug paths
    decisions/<slug>.md, collisions numbered -2, -3 in corpus.json order
    (three titles are each shared by two pages); the bar is 10 of 13 tries
    and at least 1 of the 3 supersedes tries; finding 6 corrected (the
    reviewer's earlier check used the real corpus paths and is flattered too;
    under the 13-try rule its ranks give exactly 10 of 13); the issue 54
    fixture as a reading that is not binding, ranked as the hint would rank
    it (its 2 superseded pages left out, each query compared only with pages
    of its own page type). Settled S-1 to S-6: model-free and stdlib only; a
    hint never blocks; promoter.py stays the only wiki writer; superseded
    pages never listed; the frozen corpus and labels reused read-only; no
    release step, the owner alone decides releases.
---

# Plan: similar pages at propose (issue 121, cycle 11)

The bet pitch `specs/pitches/121-similar-pages-at-propose/pitch.md` is the
shaping record (owner decisions D1-D10 on 24 November 2026; review changes and
the two points after merge on 25 November; bet and cycle 11 start PR #143).
Its "Findings from the code and the evidence" were re-checked on `main` at
f3e87b3 and hold; the current line numbers are below. Issue 121 and its
comment of 2026-11-24 were not re-fetched (no shell in the writing session);
their words are taken from the pitch, and the origin-alignment record at
approval reads the issue itself.

## Facts (checked at f3e87b3, 25 November 2026)

1. **Where the CLI prints advisories.** `_do_propose` (`cli.py` 1026-1066)
   prints the proposal directory first on stdout, the edits, then calls
   `_print_fact_warnings(written)` (1051) before the optional promote (1052).
   `_print_fact_warnings` (628-647) reads `plan.json` and prints
   `fact-check:` lines to stderr; it is also called by `ingest` (672) and
   `query --file-back` (801), so the new printer is a separate function
   called by `_do_propose` only (FR-023).
2. **Where `api.propose` can rank outside the lock.** `api.propose`
   (`api.py` 600-703) validates the edits (653-672), then takes the
   `WikiLock` (680) around `write_patch_set_dir` (682-684) and the snapshot
   (696). The ranking goes between 672 and 680 (FR-020).
3. **Where `plan.json` entries are built.** `write_patch_set_dir`
   (`ingestor_multi.py` 209-262) fills entries in `_write_patch_set_files`
   (282-308); `fact_warnings` and `fact_check_error` are written at 290-307,
   and the comment at 299 records the rule that `plan.json` is archived into
   the wiki on promote, so an error records its kind, never a machine path.
   Its other callers are `ingest` (`api.py` 555) and `query --file-back`
   (1265); an optional keyword leaves both unchanged.
4. **Nightly never creates.** `nightly` calls `api.propose` (`nightly.py` 864)
   but refuses a `create` in a draft (632-633), so its proposals carry no
   list; it counts only `fact_warnings` (706-715).
5. **`select` is the reusable ranking path.** `select` (`discovery.py`
   375-460) reads `index.md`, normalises its links, skips `index.md` and
   `log.md`, classifies each page with `_read_eligible` (266-280: missing,
   not a regular file, not UTF-8, superseded), ranks with `_rank_fts5`
   (344-358, through `rank_cached`) and applies the page cap and byte budget
   after ranking (434-448). Its docstring and `validate_max_pages` (329-341)
   say `select` itself is uncapped. With FTS5 missing it falls back to
   `index-first` (398-402), which the hint must not do (D8), so the hint
   probes `fts5_available()` (158-162) first. `RankerConfig` and
   `DEFAULT_RANKER_CONFIG` (96-111): `porter unicode61`, weights path 4,
   title 4, headings 2, body 1, `min_match_tokens` 1, `max_pages` 5.
6. **What the index holds and how a query is built.** `build_document`
   (`search_index.py` 151-163): `path_words` from the path stem with `/` and
   `-` as spaces; `title` = `frontmatter_value(text, "title") or ""`;
   `headings`; `body` = the lines after the frontmatter (`_split_frontmatter`
   140-148) joined with `\n`. Frontmatter keys other than `title` are in no
   column. `build_query` (181-186) quotes the sorted `_tokenise` tokens and
   joins them with `OR`. `SearchIndex.rank` (211-239) returns only paths in
   `order`, best bm25 first, ties by position in `order`.
7. **The cache holds exactly the pages passed.** `_apply_diff` (537-553)
   deletes every stored row not in the call's pages, so ranking a page-type
   subset through the cache would churn it; the hint ranks over all eligible
   pages (as `find` does) and keeps its page type afterwards (departure 6).
   `rank_cached` (611-636) raises `ContractViolationError` for a cache inside
   the wiki (628) and otherwise falls back to memory with a warning that
   names the cache path (633).
8. **Titles keep single quotes.** `review.frontmatter_value` (136-154)
   removes one pair of double quotes only; the corpus pages' titles are
   single-quoted, so their title column carries the quotes. Tokens are
   unaffected (`wiki_state._TOKEN_RE` 43), and the slug rule drops them.
9. **The switch's pattern.** `ENV_GIT_CALL_LIMIT` (`paths.py` 38),
   `_NON_NEGATIVE_INTEGER_RE` (61), the `WikiPaths` fields (283-292),
   `for_root` (295-329), `resolve` reading the variable with `ValueError` on a
   bad value (388-396), and `with_wiki_dir` (408-419, `dataclasses.replace`,
   so a new field is carried). The MCP server resolves `WikiPaths` once at
   launch (`mcp_adapter/config.py` 173).
10. **The MCP surface.** `propose` (`mcp_adapter/tools.py` 169-201) returns
    `{name, proposal_dir, warnings}`; `trace.py`'s `TOOL_RESULT_KEYS`
    (120-137) lists each tool's result keys and counts any other as unknown,
    so it gains the key (FR-024); `docs/mcp-adapter.md` 110 documents the
    result. The conformance suite (`conformance/mcp/run.py`) does not check
    `propose`'s key set.
11. **The documents.** `docs/patch-set-format.md` 80-81 (the two fact keys,
    the precedent); `README.md` `propose --from` 385-408 and the
    environment-variables table 508-521; `schema/page-types.md` 14 (the slug
    equals the filename stem, kebab-case); `CHANGELOG.md` `[Unreleased]`
    empty at 7.
12. **The frozen inputs.** `tests/test_duplicates_frozen.py` 28-34 pins
    `corpus.json` (`fc0f710a…`) and `labels.json` (`e1c34ca9…`);
    `corpus.json`'s `pages` (from line 208) carry `page`, `title`, `sha256`;
    the labels' true pairs are 5 `redundant` (`labels.json` 911, 923, 929,
    935, 995) and 3 `supersedes` (1235, 1775, and the `cross_pairs` entry at
    2133), each reason naming the later ruling. `tests/test_patterns_frozen.py`
    28 pins `eval/patterns/labels.json` (`96da1b5a…`). `eval/patterns/wiki/`
    has an `index.md`; two pages carry `superseded_by`
    (`decisions/benchmark-ui-was-backend-free-one-shot-and-studio-only.md`,
    `decisions/merge-require-green-ci-was-never-read.md`); its true pairs are
    one `conflicting` (`labels.json` 4-5), one `redundant` (508-509) and the
    background decision/incident pair (551-553).
13. **The frozen-input check to copy.** `eval/duplicates/candidates.py`
    `check_frozen` (144-151) and its `--out-dir` (446).
14. **The driver** (carried from cycle 10's plan, fact 11, and its runs): a
    phase's review diff base is fixed when the phase starts, so a
    main-session commit at a pause is reviewed in the PR, not by the phase
    reviewer; `CCT_REVIEW_DIFF_MAX_LINES` in the environment overrides
    `review.diff_max_lines`; the driver falls back to `plan.md`'s origin
    issue when it opens a PR; `--resume` does not remember `--start-phase`, so
    a run 2 resume repeats `--start-phase 4`; the driver
    never updates `hill.json`.

## Departures from the pitch

Each is recorded so the origin-alignment record at approval can cite it.

1. **The query page is left out of each try's index** rather than indexed and
   filtered from the list (O2): a proposed page is not yet in the wiki, and
   bm25's statistics differ slightly between the two (FR-003).
2. **bm25 ties are broken by `corpus.json` order** in the measurement, as
   `index.md` order breaks them for the hint (FR-003).
3. **The later page of each `supersedes` pair is named in `protocol.json`**,
   read from the label reasons, and confirmed by the owner at sign-off (O3,
   FR-005).
4. **The README is frozen with the protocol in US1**, so it holds the
   protocol only; the script's command line and the results go into
   `report.md` (FR-001, FR-009, FR-015).
5. **The hint reuses `select` unchanged** (no cap, no budget) and keeps its
   page type afterwards; the pitch said "reusing the eligibility and the
   cached FTS5 path", and this is the smallest way to do it without touching
   `find` (fact 5, FR-019).
6. **The page-type filter runs after ranking**, over all eligible pages, as
   the cache must hold exactly them (fact 7). On the corpus every page is a
   decision page, so the measured rule and the shipped rule are the same;
   the fixture reading applies the same order of steps (FR-003, FR-007).
7. **"Did not run" is a second key, `similar_pages_error`**, as
   `fact_check_error` is beside `fact_warnings` (O4, FR-020).
8. **The CLI line carries the create's path**, `similar: <create>: <listed
   path>  <title>`, so a proposal with two creates is readable (O5, FR-023);
   the pitch wrote `similar: <path>  <title>`.
9. **Cache warnings stay out of `plan.json`** (they name the cache path) and
   are emitted as `DiscoveryWarning`; errors other than a missing FTS5 are
   recorded as `not computed: <class>` and never raised (S-2; FR-019,
   FR-020).
10. **The conformance suite is unchanged** (O6): it is adapter-agnostic and
    the key is optional; `trace.py`'s known-key list gains it (fact 10).
11. **Both runs end at a pause and both PRs are opened by hand** with
    `pre-pr-check.sh --closes none`, since the driver names the origin issue
    for closure and D10 keeps issue 121 open (FR-017, FR-028).
12. **Run 2 pauses after US4** so the owner can take cut 2 (drop the MCP key)
    before US5 starts (FR-024).
13. **The CHANGELOG entry lands in US6** with the documents, when every
    surface it names exists (FR-027).
14. **The 500-page time bound has a formula** from `results/timing.json` (O8,
    FR-022).
15. **`CLAUDE.md` layout lines land with their code** (US1 for
    `eval/similar/`, US4 for the `discovery.py` line).
16. **The verdict is pass** (spec amendment, 2026-11-26). The partner was in
    the top 5 in 11 of 13 tries and in 1 of the 3 `supersedes` tries
    (`eval/similar/report.md`, evidence PR #146). The two misses are the
    location-only rulings, at ranks 6 and 35. FR-019 to FR-029 apply, and
    FR-022's 500-page bound is 10 s. **Run 2's settings** (`automation.json`):
    branch `feature/wiki-studio-similar-121` from `main` after this amendment
    merges; `max_phases: 6`, started fresh with `--start-phase 4`, after run
    1's ledger (`.cct/auto-build/wiki-studio-similar-121/`) is moved aside;
    the markers pause after US4 (cut 2) and US6; `build.max_turns: 120`;
    `review.diff_max_lines: 6000`; no `pr.closes`; every start and resume
    with `env -u CCT_REVIEW_DIFF_MAX_LINES`, and the resume after US4 with
    `--resume --start-phase 4`, never a plain `--resume`, which would rebuild
    steps 1-3. Run 2 is not resumed after US6:
    its PR is opened by hand with `pre-pr-check.sh --closes none` (D10).
17. **Run 1's first sign-off cited a pasted review** (process). The sign-off
    after US1 credited "the external review at d3e6d23"; that review was
    pasted by the owner, not the external reviewer's. A correction line
    follows it in `automation-summary.md`, and the external reviewer later
    checked the protocol against this spec and found it matched (PR #146).

Close target: none. Issue 121 stays open whatever the verdict (D10); no PR,
commit message or artifact names it after a closing keyword, and no other
issue is closed.

## Architecture decisions

- **ADR-1: Protocol, sign-off, script, run, report.** The protocol and its
  frozen test land before any ranking code; the owner signs off; the script
  is written; the main session runs it once; the report publishes it.
- **ADR-2: Data is produced by a script the main session runs** at a pause,
  and CI reruns it byte for byte.
- **ADR-3: The hint is `find`'s ranker, not a new one.** `similar_pages`
  calls `select` unchanged; the only new logic is the query text, the
  page-type and proposal filters and k. A replay test binds it to `rank.py`.
- **ADR-4: One computation, many readers.** `api.propose` writes the list into
  `plan.json`; the CLI and the MCP tool read it from there.
- **ADR-5: Each phase is true on its own diff;** nothing is versioned.

## Files

| File | Phase | Change |
|---|---|---|
| `eval/similar/__init__.py`, `README.md`, `protocol.json` (new) | US1 (pause 1 only for an owner-asked change) | FR-001-FR-008 |
| `tests/test_similar_frozen.py` (new) | US1 | FR-009 |
| `CLAUDE.md` | US1, US4 | Layout line for `eval/similar/`; `discovery.py` line gains the hint |
| `eval/similar/rank.py` (new) | US2 | FR-011, FR-012 |
| `tests/test_similar_rank.py` (new) | US2 | FR-013 |
| `eval/similar/results/ranks.json`, `timing.json` (new) | pause 2 (main session) | FR-014, as written |
| `eval/similar/report.md` (new) | US3 | FR-015 |
| `tests/test_similar_results.py` (new) | US3 | FR-016 |
| `src/wiki_studio/discovery.py` | US4 | FR-019 (additions only) |
| `src/wiki_studio/api.py`, `ingestor_multi.py` | US4 | FR-020 |
| `src/wiki_studio/paths.py` | US4 | FR-021 |
| `tests/test_similar_pages.py` (new); tests whose fixtures now carry the key | US4, US5 | FR-022, FR-025 |
| `src/wiki_studio/cli.py` | US5 | FR-023 |
| `src/wiki_studio/mcp_adapter/tools.py`, `trace.py` | US5 (not with cut 2) | FR-024 |
| `docs/patch-set-format.md`, `docs/mcp-adapter.md`, `README.md` | US6 | FR-026 |
| `CHANGELOG.md` | US6 | FR-027, `[Unreleased]` only |

## Interfaces

```python
# eval/similar — run by the main session at pause 2, rerun by CI
#   python -m eval.similar.rank [--out-dir DIR]
def query_text(text: str) -> str: ...                      # FR-004
def slug_paths(entries: Sequence[Mapping[str, Any]]) -> dict[str, str]: ...   # FR-003: corpus page -> decisions/<slug>.md

# src/wiki_studio/discovery.py (additions only)
SIMILAR_PAGES_K = 5
SIMILAR_ERROR_NO_FTS5 = "FTS5 not available"

@dataclass(frozen=True)
class SimilarPage:
    path: str
    title: str

@dataclass(frozen=True)
class SimilarList:
    pages: tuple[SimilarPage, ...]
    error: str | None

def similar_query(text: str) -> str: ...                   # build_document title + " " + body
def similar_pages(paths: WikiPaths, text: str, *, exclude: frozenset[str]) -> tuple[SimilarList, tuple[str, ...]]: ...

# src/wiki_studio/ingestor_multi.py
def write_patch_set_dir(patch, output_dir, wiki_dir=None, *, on_collision=..., lock_timeout=None, lock=None,
                        similar: Mapping[int, SimilarList] | None = None) -> Path: ...

# src/wiki_studio/paths.py
ENV_SIMILAR_PAGES = "WIKI_STUDIO_SIMILAR_PAGES"
# WikiPaths gains: similar_pages: bool = True   (for_root/resolve: similar_pages: bool | None = None)
```

`plan.json`, for a `create` when the switch is on:

```json
{"path": "decisions/new-page.md", "action": "create", "rationale": "...", "preview": "preview/decisions/new-page.md",
 "similar_pages": [{"path": "decisions/old-page.md", "title": "Old page"}]}
```

or `"similar_pages_error": "FTS5 not available: no such module: fts5"` in
place of `similar_pages`. MCP `propose` result (unless cut 2):
`{"name", "proposal_dir", "warnings", "similar_pages": [{"path": "decisions/new-page.md", "pages": [{"path", "title"}]}]}`.
CLI stderr: `similar: decisions/new-page.md: decisions/old-page.md  Old page`.

## Phases (one auto-build phase per `## US<n>:` group of tasks.md)

Every phase's gate is the full gate of the spec's Constraints.

| Phase | Scope | Run | FRs | What | Phase tests | Pause after |
|---|---|---|---|---|---|---|
| US1 | S1 | 1 | FR-001-FR-010 | README, protocol.json, frozen test | `tests/test_similar_frozen.py`, `tests/test_duplicates_frozen.py`, `tests/test_patterns_frozen.py` | **yes**: the owner's review and sign-off (FR-010) |
| US2 | S2 | 1 | FR-011-FR-014 | rank.py on synthetic inputs | `tests/test_similar_rank.py`, `tests/test_similar_frozen.py` | **yes**: the ranking run (FR-014) |
| US3 | S2 | 1 | FR-015-FR-018 | report.md, results test, scope audit | `tests/test_similar_results.py`, `tests/test_similar_frozen.py` | **yes**: run 1 ends; evidence PR by hand |
| US4 | S3 | 2 | FR-019-FR-022 | similar_pages, plan.json keys, switch | `tests/test_similar_pages.py`, `tests/test_discovery.py`, `tests/test_search_index.py`, `tests/test_paths.py`, `tests/test_package_boundaries.py` | **yes**: trigger 2 (cut 2) |
| US5 | S4 | 2 | FR-023-FR-025 | CLI lines, MCP key, trace keys | `tests/test_similar_pages.py`, `tests/test_mcp_adapter.py`, `tests/test_cli_contract.py` | no |
| US6 | S5 | 2 | FR-026-FR-029 | docs, CHANGELOG, invariant audit | `tests/test_quickstart.py`, FR-028's audit | **yes**: run 2 ends; build PR by hand |

## Runs, pauses and script runs (the lessons of cycles 09 and 10, built in)

1. **Sessions cannot run Python.** No driver phase runs `rank.py`. The
   ranking run is a main-session step at the pause after US2 (FR-014),
   committed as its own commit. US1's hashes come from a shell
   `shasum -a 256`, and the driver's gate is the frozen test's first run;
   US2's tests use synthetic inputs; US3 checks the results commit.
2. **The driver cannot open a PR that closes nothing**: it falls back to
   `plan.md`'s origin issue. Run 1 ends at the milestone after US3
   (`max_phases: 3`) and is never resumed; the evidence PR is opened by hand
   after `../code-copilot-team/scripts/pre-pr-check.sh --closes none --title
   <title> --body-file <file> --base main`, and `gh pr view <n> --json
   closingIssuesReferences` must list nothing. Run 2 ends the same way after
   US6 (D10). If the driver opens a PR anyway, the owner closes it unmerged.
3. **`--resume` does not remember `--start-phase`.** Run 2 is a fresh run: run 1's
   ledger (`.cct/auto-build/wiki-studio-similar-121/`) is moved aside first,
   and run 2 starts with `--start-phase 4` on a new branch from `main` after
   the amendment merges. At its own pause after US4 it is resumed with
   `--resume --start-phase 4`, never a plain `--resume`: the driver does not
   remember `--start-phase` across a resume (`START_AT="${START_PHASE_ARG:-1}"`,
   `auto-build-loop.sh` 6510 at code-copilot-team 33fa492) and skips only
   steps its own ledger marks done, so a plain `--resume` would rebuild steps
   1-3 on the run 2 branch. With `--start-phase 4` it skips steps 1-3, skips
   step 4 as done, and builds step 5 (the external review of PR #147). A
   stopped run 2 is likewise resumed with `--resume --start-phase <the
   stopped step>`, or its ledger set aside and a fresh run started with
   `--start-phase <the stopped step>` on the same branch.
4. **The owner's shell sets `CCT_REVIEW_DIFF_MAX_LINES=4000`**, which
   overrides `review.diff_max_lines`. Every start and resume begins with
   `env -u CCT_REVIEW_DIFF_MAX_LINES`, and `automation.json` carries
   `review.diff_max_lines: 6000`. Size estimate: US1 about 500 lines, US2
   about 900 (script and tests), US3 about 400, the results commit about 900
   (299 path lines plus 13 tries and the readings; reviewed in the PR), US4
   about 900, US5 about 400, US6 about 150.
5. **The driver never updates `hill.json`**; the owner updates it by hand.
6. **Wall time lives in `results/timing.json`**, checked for keys only;
   `ranks.json` is reproduced byte for byte.
7. **A flaw found after the run is post hoc** (FR-007): never a change to the
   protocol or the verdict.

## Owner-run steps

1. **Before run 1**: answer O1-O9; approve this bundle; in the approval PR
   write run 1's `automation.json` and the origin-alignment record.
2. **Pause after US1**: review the README and `protocol.json` (the query rule,
   the slug rule, the 13 tries with the three later pages, the bar, the
   readings that are not binding); any change by one commit with the frozen
   test's constants (FR-010); `approved-by:`; resume with `env -u
   CCT_REVIEW_DIFF_MAX_LINES … --resume`.
3. **Pause after US2**: run `python -m eval.similar.rank` once; commit
   `results/ranks.json` and `results/timing.json` as written, as their own
   commit; `approved-by:`; resume.
4. **Pause after US3**: do not resume run 1. Run `pre-pr-check.sh --closes
   none`, open the evidence PR by hand (body names issue 121 without a
   closing keyword), confirm `closingIssuesReferences` is empty, send it to
   review, add the `reviewed` label after the review of its head, merge with
   a merge commit. Then the spec amendment: FR-018's verdict, the triggers
   that fired, FR-022's bound inputs, re-approval, and with a pass run 2's
   `automation.json`. With `fail` the cycle ends (trigger 1); update the hill
   chart by hand.
5. **Run 2** (with a pass): move run 1's ledger aside; start fresh with
   `--start-phase 4` and `env -u CCT_REVIEW_DIFF_MAX_LINES`. At the pause
   after US4, check trigger 2: to take cut 2, commit the cut to FR-024 and
   US5's MCP task, then resume with `env -u CCT_REVIEW_DIFF_MAX_LINES …
   --resume --start-phase 4`, never a plain `--resume` (item 3 of "Runs,
   pauses and script runs"). After US6, do not resume: re-run the gate on
   the branch head before trusting `landed`, check no phase was bypassed
   without its record, open the build PR by hand with `pre-pr-check.sh
   --closes none`, confirm `closingIssuesReferences` is empty, review and
   label.
6. **After the merge**: issue 121's fate is the owner's, by hand (D10); any
   release only on the owner's explicit word, outside the runs (FR-029).

## Unattended run

The owner writes the configurations at approval. This plan assumes cycle 10's
shape (profile `pr`, the DeepSeek correctness reviewer gating, max 3 rounds
per phase, two fix sessions per phase, the gate of the spec's Constraints,
`merge.enabled: false`, `merge.method: "merge"`), with:

- **Run 1**: branch `feature/wiki-studio-similar-121-evidence` from `main`
  after this bundle's approval merges; `milestone_every: 0`, `max_phases: 3`
  (the `<!-- milestone -->` markers pause after US1, US2 and US3);
  `build.max_turns: 120`; `review.diff_max_lines: 6000`; no `pr.closes`;
  started with
  `env -u CCT_REVIEW_DIFF_MAX_LINES CCT_PROJECT_DIR=$PWD ../code-copilot-team/scripts/auto-build-loop.sh wiki-studio-similar-121`
  and resumed at the pauses after US1 and US2 with the same prefix and
  `--resume`.
- **Run 2** (written by the amendment, only with a pass): branch
  `feature/wiki-studio-similar-121` from `main`; `max_phases: 6`, started
  fresh with `--start-phase 4`; markers pause after US4 and US6; resumed
  after US4 with `--resume --start-phase 4`, never a plain `--resume`; no
  `pr.closes`; `review.diff_max_lines: 6000`.

## Test strategy

- **Protocol pinned** (US1): sha256 of the README and `protocol.json`, the
  input hashes, the 13 tries' shape; the history audit of US3.
- **Script by construction** (US2): slug and collisions, the query text, the
  query page left out, the page-type filter, the tries, the bar at its edges,
  the noise labels, the refusal on changed inputs, determinism, no writes
  outside `--out-dir`.
- **Reproduction** (US3): `ranks.json` rerun byte for byte; one verdict line
  equal to the results'.
- **Replay** (US4): `similar_pages` gives `ranks.json`'s lists on the corpus
  and the fixture; `similar_query` equals `query_text` on every page; k and
  the configuration hash equal the measured ones.
- **Behaviour and neighbours** (US4-US5): filters, creates only, the switch,
  FTS5 missing, an unusable cache, caught errors, ranking before the lock,
  exit codes and promote unchanged, the wiki untouched, the 500-page bound,
  the CLI lines, the MCP key and the trace keys; `find`'s tests unedited.
- **Shown commands** (US3, US6): every `python -m eval.similar.…` line
  parses; changed docs lines get `--help` or a parse.
- **Regression**: coverage at or above 92 percent; existing tests edited only
  to expect the new key.

## Risks

- **The bar is not met.** The flattered earlier reading landed exactly on
  10 of 13 (pitch, finding 6); title-slug paths remove the spec names from
  the path column, so a fail is plausible. Mitigation: none in the rule; that
  is what the measurement is for, and the cycle ends early with the evidence
  published.
- **The pass is weak evidence.** Development data, 13 tries from 8 pairs.
  Mitigation: the report says so; the fixture reading is shown beside it.
- **Noise on every create.** Five mostly unrelated pages on every create may
  teach proposers to ignore the list. Mitigation: the report counts the
  noise by label; the switch; the README says it plainly.
- **Long queries.** A whole page is an OR of hundreds of tokens. Mitigation:
  `timing.json` on 299 pages and the 500-page bound in US4; a token cap only
  by a spec amendment applied to `rank.py` too.
- **Existing tests pin `plan.json`.** The on-by-default key appears in
  fixtures that propose a create. Mitigation: FR-022's rule, edit to expect
  it; US4's checkpoint runs the whole suite.
- **The cache during propose.** `propose` never touched the cache before.
  Mitigation: ranking before the lock through `select`'s cached path, which
  falls back to memory on a busy or broken cache; the lock is never taken
  twice.
- **The driver opens a PR at the end of a run.** Mitigation: milestones,
  `max_phases`, never resuming the last pause; any such PR is closed
  unmerged.
- **A third review round on one PR or phase.** Escalation to the owner, per
  the pitch's circuit breaker.

## Success criteria

1. The evidence PR publishes the protocol, the script, `ranks.json` and
   exactly one verdict line, whatever they show; it changes only FR-017's
   allowed paths, nothing under `src/`, and the history shows the protocol
   froze before `rank.py` and `rank.py` before any result.
2. `ranks.json` was produced by the main session at a pause and CI reproduces
   it byte for byte.
3. With a pass, every create's `plan.json` entry carries the list `rank.py`
   would give, the CLI and MCP surfaces show it, and
   `WIKI_STUDIO_SIMILAR_PAGES=off` turns it off; propose and promote exit as
   before.
4. No new exit code, frontmatter key, page type, capability, MCP tool or
   dependency; `find`, `RankerConfig` and the cache format unchanged; gate
   green at 92 percent; no version bump, CHANGELOG version section or tag;
   issue 121 open.

## Open items for the spec review

Draft defaults; the spec is written on them. **The owner accepted every
default on 2026-11-25 (O1-O9, asked by the build session before the spec
PR).** The alternatives stay recorded for the review.

1. **O1 — Phase structure.** Default: two runs from this bundle; run 1 is
   US1-US3 with pauses after each (sign-off, ranking run, end), ending with
   the evidence PR opened by hand; run 2 is US4-US6, fresh, only with a pass,
   pausing after US4 (cut 2) and after US6 (build PR by hand). Alternative:
   fold US3 into the pause after US2 (the main session writes the report),
   one phase fewer but a report the driver's reviewer never sees.
2. **O2 — The query page in its try's index.** Default: left out of the index,
   as a proposed page is not in the wiki yet, so bm25 sees what the hint
   sees. Alternative: index all 299 pages and drop the query page from the
   list, as the earlier checks did ("self excluded"); scores differ slightly.
3. **O3 — Which page of each `supersedes` pair is the later ruling.** Default,
   read from the label reasons: `cct-pi-project-config-spec-01` over
   `cct-pi-harness-adoption-plan-05`; `mk-memkernel-0-14-capture-signals-spec-06`
   over `mk-memkernel-0-12-capture-core-spec-05`; `cct-one-harness-home-spec-01`
   over `cct-pi-harness-adoption-plan-05` (the user-home pair). Alternative:
   the owner names them differently at sign-off.
4. **O4 — The `plan.json` shape.** Default: `similar_pages` (a list of
   `{path, title}`, possibly empty) on every create when the ranking ran;
   `similar_pages_error` (a string) instead when it did not; neither key when
   the switch is off. Alternative: one key holding an object
   `{"pages": [...], "error": null}`.
5. **O5 — The CLI lines.** Default: `similar: <create path>: <listed path>
   <title>` per listed page, `similar: <create path>: not computed (<reason>)`
   when it did not run, nothing for an empty list. Alternative: the pitch's
   `similar: <path>  <title>` without the create's path (ambiguous with two
   creates), or a `similar: <create path>: none` line for an empty list.
6. **O6 — The MCP key's shape and the conformance suite.** Default: a list in
   edit order, one `{path, pages}` or `{path, error}` per create, `[]` when
   off or no create; the conformance suite unchanged. Alternative: an object
   keyed by create path, and an optional conformance check that the key, when
   present, is a list.
7. **O7 — The switch's values.** Default: unset or empty means on; `on` or
   `off` in any case after stripping; anything else raises `ValueError`
   (exit 1), as a bad git call limit does. Alternative: anything but `off`
   means on (a typo such as `of` silently leaves it on).
8. **O8 — The 500-page time bound.** Default: `max(10, ceil(10 * t * 500 /
   298))` seconds for one create's list, `t` the binding pass's seconds per
   try from `results/timing.json`, recomputed by the test. Alternative: a
   fixed bound set by the amendment.
9. **O9 — Session and review limits.** Default: `build.max_turns: 120`,
   `review.diff_max_lines: 6000`, every start and resume with `env -u
   CCT_REVIEW_DIFF_MAX_LINES`. Alternative: cycle 10's 200 turns and 8,000
   lines.
