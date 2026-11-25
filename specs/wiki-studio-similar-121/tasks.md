# Tasks: similar pages at propose (issue 121, cycle 11)

<!-- status: draft -->
<!-- date: 2026-11-25 -->
<!-- One `## US<n>:` group = one auto-build phase = one commit. [US#]/FR tags trace to spec.md. The (S<n>) token in each heading is the pitch scope the phase moves. Run 1 (the evidence) is US1-US3 and ends at the pause after US3; the evidence PR is opened by hand. Run 2 (the build) is US4-US6, a fresh run with --start-phase 4, only with a pass recorded by the spec amendment of FR-018; it pauses after US4 (cut 2) and ends at the pause after US6; the build PR is opened by hand. -->
<!-- Read first: CLAUDE.md, spec.md, plan.md (facts, departures, "Runs, pauses and script runs", open items), specs/pitches/121-similar-pages-at-propose/pitch.md, src/wiki_studio/search_index.py (140-186, 211-278), src/wiki_studio/discovery.py (96-162, 266-280, 344-460), src/wiki_studio/review.py (136-177), src/wiki_studio/querier.py (_extract_index_links 85), eval/duplicates/corpus.json, eval/duplicates/labels.json, eval/duplicates/candidates.py (check_frozen 144-151), tests/test_duplicates_frozen.py, tests/test_patterns_frozen.py, eval/patterns/manifest.json, eval/patterns/labels.json, eval/patterns/wiki/index.md. Run 2 also: src/wiki_studio/api.py (600-703), src/wiki_studio/ingestor_multi.py (209-308), src/wiki_studio/paths.py (30-70, 244-423), src/wiki_studio/cli.py (551-578, 628-647, 1026-1066), src/wiki_studio/mcp_adapter/tools.py (169-201), src/wiki_studio/mcp_adapter/trace.py (118-145), docs/patch-set-format.md (68-87), docs/mcp-adapter.md (100-120), README.md (385-421, 508-521), tests/test_mcp_adapter.py, tests/test_package_boundaries.py. -->
<!-- Run per phase: poetry run ruff check src/ tests/ eval/ examples/ conformance/ && poetry run ruff format --check src/ tests/ eval/ examples/ conformance/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=92 -->
<!-- Script runs are main-session steps (plan, "Runs, pauses and script runs", item 1): no phase runs eval/similar/rank.py to produce committed data. The ranking run happens at the pause after US2, in the main session, committed as its own commit. Hashes a phase records are computed with a shell `shasum -a 256`. -->
<!-- Each phase is reviewed on its own diff: every file a phase writes must be true at the end of that phase. No README, report, docstring, help text, doc or CHANGELOG line states later-phase work as done. Each behaviour is stated once, in its owning FR (inputs FR-002, index and slug FR-003, query rule FR-004, tries FR-005, list and bar FR-006, readings and post hoc FR-007, frozen test FR-009, sign-off FR-010, script FR-011, results FR-012, evidence PR FR-017, verdict FR-018, ranking function FR-019, plan.json FR-020, switch FR-021, CLI FR-023, MCP FR-024, documents FR-026, issue 121 FR-028, release FR-029); code comments and tests cite the FR. -->
<!-- Invariants: no model on any path; the hint never blocks propose or promote and never changes an exit code, review_state, an approval or what find returns; no findings kind, no lint change. promoter.py stays the only wiki writer; the hint writes only the proposal directory (through api.propose) and the search cache (through search_index.py). No change to select, RankerConfig, DEFAULT_RANKER_CONFIG, ranker_config_hash, search_index.py or the cache format. No new frontmatter key, page type, directory, exit code, capability, MCP tool or runtime dependency. Nothing is scored on the corpus before the protocol is signed off; nothing in the protocol changes after the run. No edit to eval/duplicates/ or eval/patterns/. Package modules spell none of tests/test_package_boundaries.py's forbidden layout strings. Every new .py file starts with the two-line EGOGE / Apache-2.0 header; from __future__ import annotations; type hints. Every shown command gets a real check. No closing keyword before an issue reference in any file, commit message or PR text; issue 121 is never closed by a PR (D10). No version bump, no CHANGELOG version section, no tag, no release in any phase (FR-029). No commit, push or branch change inside the session; the driver owns git. Never weaken or skip a test. -->

## US1: The protocol, frozen before anything is scored (S1)

<!-- milestone -->
<!-- This phase writes no ranking code and computes no rank, score or token set on the corpus: eval/similar/rank.py does not exist. Hashes come from `shasum -a 256`. -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 1 | | `eval/similar/__init__.py` (header only) and the README opening per FR-001 (issue 121, the pitch, the branch base's full hash, what is and is not measured, `eval/duplicates/` and `eval/patterns/` read only, no model, the script and report written after sign-off). `CLAUDE.md` Layout gains `eval/similar/             the similar-pages study (issue 121): protocol, ranking script, results, report` after the `eval/duplicates/` line (FR-001) | `eval/similar/__init__.py`, `eval/similar/README.md`, `CLAUDE.md` | build | [ ] |
| 2 | | Re-check the three pinned input hashes and compute `eval/patterns/manifest.json`'s with `shasum -a 256`; stop if a pinned value differs. README: the inputs, read-only (FR-002) | `eval/similar/README.md` | build | [ ] |
| 3 | | README protocol, in words: the title-slug index, the slug rule and collisions, the query page left out, `corpus.json` order, the ranker configuration, the page-type filter (FR-003); the query rule to the character (FR-004); the true pairs, the direction rule, the three later pages, the 13 tries in order, and that they come from 8 pairs (FR-005); k = 5, no floor, found, the partner's rank, the bar, the verdict lines (FR-006); the readings that are not binding (the noise, the issue 54 fixture as the hint would rank it, the whole-page and body-only readings), the development-data caveat and the post-hoc rule (FR-007) | `eval/similar/README.md` | build | [ ] |
| 4 | | `eval/similar/protocol.json` per FR-008: `inputs` (every issue 54 fixture page the reading reads with its own sha256, FR-002), `index`, `ranker`, `query_rule`, `k`, `score_floor`, `same_page_type`, `true_dispositions`, `tries` (13, in FR-005's order), `bar`, `verdict_lines`, `not_binding`, `caveat`; no score, rank or count computed on the corpus (FR-008) | `eval/similar/protocol.json` | build | [ ] |
| 5 | | `tests/test_similar_frozen.py` (EGOGE header, unittest style): constants with the sha256 (shell `shasum -a 256`) of the README and `protocol.json` as committed in this phase; each asserted; every `inputs` entry equals its file's sha256; `tries` holds 10 `redundant` (5 pairs, both ways) and 3 `supersedes` entries, each pair a true pair of `labels.json` (FR-009) | `tests/test_similar_frozen.py` | build | [ ] |

**Checkpoint US1** — verify before continuing:
- [ ] `git status --porcelain` (this phase's changes) lists only `eval/similar/__init__.py`, `README.md`, `protocol.json`, `tests/test_similar_frozen.py` and `CLAUDE.md`; no `.py` file under `eval/similar/` other than `__init__.py`; no `results/` directory
- [ ] `git diff -- eval/duplicates eval/patterns src` is empty
- [ ] `git grep -n -i -E '(close[sd]?|fix(e[sd])?|resolve[sd]?):? +([[:alnum:]_.-]+/[[:alnum:]_.-]+)?#[0-9]' -- eval/similar` finds nothing
- [ ] `poetry run pytest -q tests/test_similar_frozen.py tests/test_duplicates_frozen.py tests/test_patterns_frozen.py` passes (the driver's gate is the frozen test's first run)
- [ ] Full gate green
- [ ] Milestone: the run pauses for the owner's review below

**At the pause after US1 — owner and main session, not this phase's work (FR-010):**
- The owner reads the README and `protocol.json`: the query rule, the slug rule, the 13 tries and the three later pages (plan, O3), the bar, the readings that are not binding.
- A change the owner asks for: one commit changing the README or `protocol.json` and `tests/test_similar_frozen.py`'s constants together (hashes from `shasum -a 256`). No ranking code exists yet.
- Add `approved-by:` under US1's checkpoint in `automation-summary.md` (the sign-off) and resume with `env -u CCT_REVIEW_DIFF_MAX_LINES … --resume`.

---

## US2: The ranking script (S2)

<!-- milestone -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 6 | | `eval/similar/rank.py` (EGOGE header; `main(argv)`, `--out-dir`, default `eval/similar/results/`): the frozen-input check first, writing nothing and exiting 1 on a difference (FR-011); `slug_paths` and `query_text` as public functions (FR-003, FR-004); per try, an in-memory index of every corpus page but the query page in `corpus.json` order, ranked with `DEFAULT_RANKER_CONFIG`, filtered by page type, k from `protocol.json`; the tries, found, ranks, summary and verdict (FR-005, FR-006); the noise, the two other readings and the fixture pass (FR-007); `ranks.json` with `indent=2`, `sort_keys=True`, `ensure_ascii=False` and one final newline, and `timing.json` (FR-012). Only the imports FR-011 names; no git, no network, no model, no write outside `--out-dir` | `eval/similar/rank.py` | build | [ ] |
| 7 | | `tests/test_similar_rank.py` (EGOGE header): FR-013 in full on a synthetic corpus, labels and protocol in a temporary directory (slug and collisions; `query_text` cases; the query page absent from its index; the page-type filter; tries from labels; the bar at 9/13, 10/13 with 0 `supersedes`, 10/13 with 1; noise labels; the refusal writing nothing; the same bytes twice; an `eval/` snapshot equal before and after; `--help`), FTS5 cases skipped when it is missing (FR-013) | `tests/test_similar_rank.py` | build | [ ] |

**Checkpoint US2** — verify before continuing:
- [ ] `git status --porcelain` (this phase's changes) lists only `eval/similar/rank.py` and `tests/test_similar_rank.py`; no file under `eval/similar/results/` exists yet
- [ ] `git diff <US1 commit or the owner's protocol commit> -- eval/similar/README.md eval/similar/protocol.json tests/test_similar_frozen.py` is empty
- [ ] `grep -n "subprocess\|urllib\|socket" eval/similar/rank.py` finds nothing
- [ ] `poetry run pytest -q tests/test_similar_rank.py tests/test_similar_frozen.py` passes
- [ ] Full gate green
- [ ] Milestone: the run pauses for the ranking run below

**At the pause after US2 — main session, not this phase's work (FR-014):**
- Run `python -m eval.similar.rank` once (the main session or the owner; the session sandbox cannot run Python). Commit `eval/similar/results/ranks.json` and `eval/similar/results/timing.json`, exactly as written, as their own commit.
- Add `approved-by:` and resume with `env -u CCT_REVIEW_DIFF_MAX_LINES … --resume`.

---

## US3: The report and the evidence PR (S2)

<!-- milestone -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 8 | | `eval/similar/report.md` per FR-015: how to rerun; the table of the 13 tries; the summary and exactly one verdict line (`Verdict: pass` or `Verdict: fail`); the noise by label; the two other readings and the issue 54 fixture, each marked not binding; the collisions; the limits stated plainly (development data, 13 tries from 8 pairs, extracted not curated, 7 of 8 pairs within one family, decision pages only, location-only rulings, no held-out set); numbers "as recorded"; no post-hoc section unless FR-007 applies (FR-015) | `eval/similar/report.md` | build | [ ] |
| 9 | | `tests/test_similar_results.py` (EGOGE header): `rank.py` with `--out-dir` in a temporary directory equals the committed `ranks.json` byte for byte; `timing.json` keys present, values not compared; one verdict line equal to `ranks.json`'s; `paths` and `collisions` recompute with `slug_paths`; every `python -m eval.similar.…` line in the report parses with the script's parser; skipped with the reason when FTS5 is missing (FR-016) | `tests/test_similar_results.py` | build | [ ] |
| 10 | | The evidence PR's scope audit (FR-017), against the run-1 branch base: `git diff <base> --stat` lists only FR-017's allowed paths; `git diff <base> -- src/ eval/duplicates eval/patterns` empty; `git diff <base> -- CLAUDE.md` adds exactly FR-001's line; with `R=$(git log --diff-filter=A --format=%H -- eval/similar/rank.py)`, `git log --format=%H $R^..HEAD -- eval/similar/README.md eval/similar/protocol.json tests/test_similar_frozen.py` prints nothing and `git merge-base --is-ancestor $R $(git log --diff-filter=A --format=%H -- eval/similar/results/ranks.json)` succeeds. Any other path is removed before the milestone, or the run stops | — | build | [ ] |

**Checkpoint US3** — verify before continuing:
- [ ] Task 10's audit passes
- [ ] The driver's gate runs `tests/test_similar_results.py`, which reruns `rank.py` into a temporary directory and compares `ranks.json` byte for byte (the session itself runs no Python); `git status --porcelain eval/` is clean
- [ ] The closing-keyword grep of US1's checkpoint still finds nothing
- [ ] Full gate green
- [ ] Milestone: run 1 ends here and is never resumed

**At the pause after US3 — main session and owner (FR-017, FR-018; plan, owner step 4):**
- Do not resume run 1 (a resume could reach the driver's own PR, which would name issue 121 for closure). If the driver opened a PR anyway, close it unmerged.
- Run `../code-copilot-team/scripts/pre-pr-check.sh --closes none --title <title> --body-file <file> --base main`; open the evidence PR by hand, its body naming issue 121 without a closing keyword; confirm `gh pr view <n> --json closingIssuesReferences` lists nothing; review, label after the review of its head, merge with a merge commit, never squash.
- A flaw found in review goes into a non-binding `post_hoc` block computed by `rank.py` and checked by `tests/test_similar_results.py`, plus a "Post hoc (not binding)" report section; the protocol and the verdict line never change.
- The spec amendment: FR-018's verdict (`pass` or `fail`), the triggers that fired, FR-022's bound inputs from `results/timing.json`, re-approval, and with a pass run 2's `automation.json`. With `fail` the cycle ends (trigger 1), nothing under `src/` changes, no CHANGELOG entry, and issue 121 stays open.

---

## US4: The hint in the library and in plan.json (S3)

<!-- milestone -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 11 | | Read FR-018: if the verdict is not `pass`, stop and report: this phase does not run (FR-018) | — | build | [ ] |
| 12 | | `paths.py`: `ENV_SIMILAR_PAGES = "WIKI_STUDIO_SIMILAR_PAGES"` beside `ENV_GIT_CALL_LIMIT`; `WikiPaths.similar_pages: bool = True` with its docstring entry; `for_root` and `resolve` taking `similar_pages: bool | None = None`; `resolve` reading the variable per FR-021 (unset or empty on; `on`/`off` in any case after stripping; else `ValueError`) (FR-021) | `src/wiki_studio/paths.py` | build | [ ] |
| 13 | | `discovery.py`, additions only: `SIMILAR_PAGES_K`, `SIMILAR_ERROR_NO_FTS5`, the no-cap and no-budget constants, `SimilarPage`, `SimilarList`, `similar_query`, `similar_pages` per FR-019 (probe first, no index-first fallback; `select` unchanged with no cap and no budget; page-type and `exclude` filters after ranking; first k; titles as `build_document` reads them; `ContractViolationError` and `sqlite3.Error` caught as `not computed: <class>`; no lock, no model). `CLAUDE.md`'s `discovery.py` Layout line gains `, the similar-pages hint` (FR-019) | `src/wiki_studio/discovery.py`, `CLAUDE.md` | build | [ ] |
| 14 | | `api.propose`: after validation and before the `WikiLock`, when `paths.similar_pages` is on, `similar_pages` once per create with `exclude` the proposal's normalised paths; cache warnings emitted as `DiscoveryWarning`; results passed to `write_patch_set_dir(..., similar=...)`. `ingestor_multi.py`: the optional `similar` keyword (`SimilarList` imported under `TYPE_CHECKING` only, FR-020); `_write_patch_set_files` writes `similar_pages` (list of `{path, title}`) or `similar_pages_error`; docstring updated; `ingest` and file-back unchanged (FR-020) | `src/wiki_studio/api.py`, `src/wiki_studio/ingestor_multi.py` | build | [ ] |
| 15 | | `tests/test_similar_pages.py` (EGOGE header): FR-022 in full: the replay on the corpus (13 tries, query page absent) and on a copy of the fixture against `ranks.json`; `similar_query` equals `query_text` on every page; k and the configuration hash equal the measured ones; filters (superseded, other type, not index-linked, same proposal); creates only; two creates; the switch cases and the spy; FTS5 missing; an unusable cache; caught errors; ranking before the lock; exit codes and promote unchanged; the wiki snapshot; the 500-page bound recomputed from `results/timing.json`. Existing tests edited only where their fixtures now carry the key, to expect it, never by turning it off (FR-022) | `tests/test_similar_pages.py`, tests whose fixtures carry the key | build | [ ] |

**Checkpoint US4** — verify before continuing:
- [ ] `git diff <run-2 base> -- src/wiki_studio/search_index.py src/wiki_studio/promoter.py src/wiki_studio/querier.py src/wiki_studio/nightly.py src/wiki_studio/cli.py src/wiki_studio/mcp_adapter eval` is empty
- [ ] `git diff <run-2 base> -- src/wiki_studio/discovery.py | grep -c '^-[^-]'` prints 0 (additions only)
- [ ] `poetry run pytest -q tests/test_similar_pages.py tests/test_discovery.py tests/test_search_index.py tests/test_paths.py tests/test_package_boundaries.py` passes
- [ ] Full gate green
- [ ] Milestone: the run pauses for trigger 2 below

**At the pause after US4 — owner (FR-024; plan, owner step 5):**
- Middle of week 2 (trigger 2): to take cut 2, commit the cut to FR-024 and US5's task 17 (marked cut), then resume. Otherwise resume as is, with `env -u CCT_REVIEW_DIFF_MAX_LINES … --resume`.

---

## US5: The CLI and MCP surfaces (S4)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 16 | | `cli.py`: `_print_similar_pages(patch_dir)` per FR-023, called by `_do_propose` only, right after `_print_fact_warnings(written)`; `similar: <edit path>: <listed path>  <title>` per listed page, `similar: <edit path>: not computed (<error>)`, nothing for an empty list, all on stderr; `propose`'s help gains one sentence on the lines and the switch (FR-023) | `src/wiki_studio/cli.py` | build | [ ] |
| 17 | | Unless cut 2: the MCP `propose` result gains `similar_pages` read from the written `plan.json` (one `{path, pages}` or `{path, error}` per create, in edit order; `[]` when off or no create); the tool docstring says so; `trace.py`'s `TOOL_RESULT_KEYS[TOOL_PROPOSE]` gains `similar_pages`; no argument, no tool, conformance unchanged (FR-024) | `src/wiki_studio/mcp_adapter/tools.py`, `src/wiki_studio/mcp_adapter/trace.py` | build | [ ] |
| 18 | | Tests in `tests/test_similar_pages.py` per FR-025: the CLI lines in-process (a listed page, two creates, not computed, empty prints nothing, after `fact-check:` and before `applied`, stdout's first line unchanged, exit 0); unless cut 2 the MCP key (a create, update-only `[]`, switch off `[]`, not computed), gated on the `mcp` extra; the trace's known key (FR-025) | `tests/test_similar_pages.py` | build | [ ] |

**Checkpoint US5** — verify before continuing:
- [ ] On a temporary wiki with two similar decision pages, `poetry run wiki-studio propose --from <dir>` with one new decision page prints `similar:` lines on stderr and exits 0; with `WIKI_STUDIO_SIMILAR_PAGES=off` it prints none
- [ ] `poetry run wiki-studio propose --help` succeeds and names the switch
- [ ] `poetry run pytest -q tests/test_similar_pages.py tests/test_mcp_adapter.py tests/test_cli_contract.py` passes
- [ ] Full gate green

---

## US6: Documents and CHANGELOG (S5)

<!-- milestone -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 19 | | `docs/patch-set-format.md`: the `edits[].similar_pages` and `edits[].similar_pages_error` rows after `fact_check_error`. `docs/mcp-adapter.md` (unless cut 2): the `propose` row's result and its shape. `README.md`: one paragraph in the `propose --from` section (a hint, noise on every create, location-only rulings likely missed, measured on development data, `eval/similar/report.md`, the switch) and the `WIKI_STUDIO_SIMILAR_PAGES` row in the environment table. Every changed shown command checked (`--help`, a JSON parse) (FR-026) | `docs/patch-set-format.md`, `docs/mcp-adapter.md`, `README.md` | build | [ ] |
| 20 | [P] | `CHANGELOG.md` `[Unreleased]` **Added**: similar pages at propose (the `plan.json` keys, the `similar:` lines, the MCP key unless cut 2, advisory, `WIKI_STUDIO_SIMILAR_PAGES=off`), one sentence on the measurement and the location-only limit; no version section, no date, no closing keyword (FR-027, FR-029) | `CHANGELOG.md` | build | [ ] |
| 21 | | Invariant audit (FR-028, FR-029): the untouched-files `git diff` of FR-028 is empty; `git diff <base> --stat -- src/` lists only FR-028's files; `discovery.py` additions only; exit codes unchanged (`tests/test_cli_contract.py`); no runtime dependency; the closing-keyword `git grep` of FR-028 finds nothing; no version bump, no CHANGELOG version section, no tag | — | build | [ ] |

**Checkpoint US6** — verify before continuing:
- [ ] Task 21's audit passes
- [ ] `poetry run wiki-studio --version` still prints the version at the run-2 base; `docs/compatibility.md` unchanged
- [ ] `poetry run pytest -q tests/test_quickstart.py` passes
- [ ] Full gate green
- [ ] Milestone: run 2 ends here and is never resumed

**At the pause after US6 — main session and owner (FR-028; plan, owner step 5):**
- Do not resume run 2. Re-run the gate on the branch head before trusting `landed`; check no phase was bypassed without its record.
- Run `../code-copilot-team/scripts/pre-pr-check.sh --closes none --title <title> --body-file <file> --base main`; open the build PR by hand, naming issue 121 without a closing keyword; confirm `closingIssuesReferences` lists nothing; review, label after the review of its head, merge with a merge commit.
- Issue 121 stays open; the owner decides by hand (D10). Any release only on the owner's explicit word.

---

## Final Verification

- [ ] Type checker: 0 errors; linter and formatter: 0 errors on `src/ tests/ eval/ examples/ conformance/`
- [ ] Full suite green with coverage at or above 92 percent
- [ ] The protocol froze and was signed off before `rank.py` existed; `ranks.json` was produced by the main session at a pause and CI reproduces it byte for byte
- [ ] The evidence PR has one commit per phase and per main-session step, merged with a merge commit, never squashed, no change under `src/`, no closing keyword, opened by hand
- [ ] With a pass: every create's `plan.json` entry carries the list `rank.py` would give; the CLI and (unless cut 2) MCP surfaces show it; the switch turns it off; propose and promote exit as before
- [ ] No new exit code, frontmatter key, page type, capability, MCP tool or dependency; `find`, `RankerConfig` and the cache format unchanged
- [ ] No version bump, CHANGELOG version section, tag or release from any run; issue 121 open, closed by no PR
