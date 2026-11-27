# Tasks: a duplicate audit in findings (issue 121, cycle 12)

<!-- status: draft -->
<!-- date: 2026-11-27 -->
<!-- One `## US<n>:` group = one auto-build phase = one commit. [US#]/FR tags trace to spec.md. The (S<n>) token in each heading is the pitch scope the phase moves. Run 1 (the evidence) is US1-US7, every phase ending at a pause; with `Development stage: stop` it ends at the pause after US3. The evidence PR is opened by hand. Run 2 is a fresh run with --start-phase 8: US8 (S6) always, unless trigger 1 cut it; US9-US11 only with a winner recorded by the spec amendment of FR-035. Every run-2 resume is `--resume --start-phase 8`. The build PR is opened by hand. -->
<!-- Read first: CLAUDE.md, spec.md, plan.md (facts, departures, "Runs, pauses and script runs", open items), specs/pitches/121-duplicate-audit/pitch.md, specs/wiki-studio-duplicates-121/spec.md (FR-004-FR-007, FR-013-FR-016: the extraction and labelling rules this cycle reuses), eval/similar/rank.py (153-232, 365-382, 546-548), eval/duplicates/extract.py (126, 231-277, 395-401, 517-543, 642-660), eval/duplicates/sample.py, eval/duplicates/corpus.json (1-210), eval/duplicates/protocol.json (84-116), src/wiki_studio/search_index.py (49-56, 130-278), src/wiki_studio/discovery.py (98-164, 268-296, 377-462, 471-543), src/wiki_studio/review.py (136-177), tests/test_duplicates_frozen.py, tests/test_similar_frozen.py. The labelling phase (US5) reads only what its own comment allows. Run 2 also: src/wiki_studio/paths.py (30-70, 250-444), src/wiki_studio/findings.py, src/wiki_studio/conflicts.py, src/wiki_studio/revisions.py (465-509), src/wiki_studio/cli.py (410-450, 875-886), src/wiki_studio/api.py (findings docstring), src/wiki_studio/mcp_adapter/trace.py (118-150), src/wiki_studio/querier.py (_extract_index_links), docs/knowledge-contract.md (372-560), docs/consumers.md (90-125), README.md (findings section, 420-425, 520-540, 580-595), tests/test_paths.py, tests/test_findings.py, tests/test_package_boundaries.py. -->
<!-- Run per phase: poetry run ruff check src/ tests/ eval/ examples/ conformance/ && poetry run ruff format --check src/ tests/ eval/ examples/ conformance/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=92 -->
<!-- Script runs are main-session steps (plan, "Runs, pauses and script runs", item 1): no phase runs audit.py, extract.py or sample.py to produce committed data. Those runs happen at the pauses below, in the main session, each committed as its own commit. Hashes a phase records come from a shell `shasum -a 256`. Sessions may run read-only git. -->
<!-- Each phase is reviewed on its own diff: every file a phase writes must be true at the end of that phase. No README, report, docstring, help text, doc, ADR or CHANGELOG line states later-phase work as done. Each behaviour is stated once, in its owning FR (spec, Constraints, "One owning FR per behaviour"); code comments and tests cite the FR. -->
<!-- Invariants: no model on any path from findings, approve or review_state; findings writes nothing (no search cache, no wiki file), takes no lock and exits 0 on a completed run; the kind never blocks promote or approve and never joins lint --health; no change to lint, lint --health, --strict, select, RankerConfig, DEFAULT_RANKER_CONFIG, ranker_config_hash, similar_pages, SearchIndex.rank or the cache format; findings_version stays 1; no new frontmatter key, page type, directory, exit code, capability, MCP tool or runtime dependency; no user-tunable k or threshold. Nothing is scored on either set before the owner's sign-off; no candidate runs on the held-out set before freeze.json; the labeller never opens audit code or results; nothing in the protocol, the labels or a verdict changes after its run. No edit to eval/duplicates/, eval/similar/ or eval/patterns/; nothing written to memkernel; no network read. Package modules spell none of tests/test_package_boundaries.py's forbidden layout strings. Every new .py file starts with the two-line EGOGE / Apache-2.0 header; from __future__ import annotations; type hints. Every shown command gets a real check. No closing keyword before an issue reference in any file, commit message or PR text; issue 121 is closed by no PR. No version bump, no CHANGELOG version section, no tag, no release in any phase (FR-050). No commit, push or branch change inside the session; the driver owns git. Never weaken or skip a test. -->

## US1: The protocol, frozen before any score (S1)

<!-- milestone -->
<!-- This phase writes no audit code and computes no rank, score, flag or count on either set: eval/duplicate_audit/audit.py does not exist. Hashes come from `shasum -a 256`; pins from read-only `git rev-parse` and `git ls-tree`. -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 1 | | `eval/duplicate_audit/__init__.py` (header only) and the README opening per FR-001 (issue 121, the pitch, the branch base's full hash, what is and is not measured, the three frozen studies read only, no model, everything else after sign-off). `CLAUDE.md` Layout gains `eval/duplicate_audit/     the duplicate-audit study (issue 121): protocol, audit script, held-out set, results, report` after the `eval/duplicates/` line (FR-001) | `eval/duplicate_audit/__init__.py`, `eval/duplicate_audit/README.md`, `CLAUDE.md` | build | [ ] |
| 2 | | With `shasum -a 256`, re-check `eval/duplicates/corpus.json` and `labels.json` against FR-002's values (stop if either differs) and compute `eval/similar/rank.py`'s. With read-only git: `git rev-parse --verify 04009eedfb25b5f27d898c5fdfd0bc4ee1bb1c86^{commit}`; `git -C ../memkernel rev-parse --verify main^{commit}` for memkernel's pin, then `git -C ../memkernel ls-tree --name-only <pin> -- specs/` shows both directories; `git show 04009ee:specs/wiki-studio-0-1-0/plan.md` and `…0-6-0/plan.md` show no `issue:` under `origin:` (FR-002, FR-008; plan, O2, O3) | `eval/duplicate_audit/README.md` | build | [ ] |
| 3 | | README protocol, in words: the index and query rule (FR-003); the candidates and the flag (FR-004); labels, the three restatement rules with O3 and the pair scopes (FR-005); the four bar conditions, selection, verdicts, winner lines (FR-006); the development stage, its stop rule and stage lines (FR-007); the held-out sources, both pins, the extraction rule by reference, slugs, `corpus.json` fields, families, `--wiki-studio-only` (FR-008); labelling, isolation, the sample and the freeze rule (FR-009); the time bound and its synthetic wiki (FR-010); the readings that are not binding, the caveat, post hoc (FR-011) | `eval/duplicate_audit/README.md` | build | [ ] |
| 4 | | `eval/duplicate_audit/protocol.json` per FR-012 (`development`, `index`, `ranker`, `query_rule`, `same_page_type`, `candidates`, `true_dispositions`, `restatement`, `pair_scopes`, `bar`, `selection`, `verdicts`, `winner_lines`, `held_out`, `time_bound`, `not_binding`, `caveat`); no score, rank or count (FR-012) | `eval/duplicate_audit/protocol.json` | build | [ ] |
| 5 | | `tests/test_duplicate_audit_frozen.py` (EGOGE header, unittest style): constants with the sha256 (shell) of the README and `protocol.json` as committed in this phase; each asserted; every `development.inputs` entry equals its file's sha256; `candidates` is k = 1, 3, 5 in order; `bar` holds 8, 3/4, `false <= true`, 2 (FR-013) | `tests/test_duplicate_audit_frozen.py` | build | [ ] |

**Checkpoint US1** — verify before continuing:
- [ ] `git status --porcelain` (this phase's changes) lists only `eval/duplicate_audit/__init__.py`, `README.md`, `protocol.json`, `tests/test_duplicate_audit_frozen.py` and `CLAUDE.md` (besides `specs/wiki-studio-duplicate-audit-121/hill.json`, which the driver changes when the phase starts, O10); no other `.py` file under `eval/duplicate_audit/`; no `results/` or `held-out/` directory
- [ ] `git diff -- eval/duplicates eval/similar eval/patterns src` is empty; `git -C ../memkernel status --porcelain` as before
- [ ] `git grep -n -i -E '(close[sd]?|fix(e[sd])?|resolve[sd]?):? +([[:alnum:]_.-]+/[[:alnum:]_.-]+)?#[0-9]' -- eval/duplicate_audit` finds nothing
- [ ] `poetry run pytest -q tests/test_duplicate_audit_frozen.py tests/test_duplicates_frozen.py tests/test_similar_frozen.py` passes (the driver's gate is the frozen test's first run)
- [ ] Full gate green
- [ ] Milestone: the run pauses for the owner's sign-off below

**At the pause after US1 — owner and main session, not this phase's work (FR-014):**
- The owner reads the README and `protocol.json`: the candidates, the index rule, the restatement rule with O3, the bar, the stop rule, both pins, the labelling rule, the time bound.
- A change the owner asks for: one commit changing the README or `protocol.json` and the frozen test's constants together (`shasum -a 256`). No audit code exists yet.
- The owner adds `approved-by:` under US1's checkpoint in `automation-summary.md` (never from pasted reviewer text); resume with `env -u CCT_REVIEW_DIFF_MAX_LINES CCT_PROJECT_DIR=$PWD ../code-copilot-team/scripts/auto-build-loop.sh wiki-studio-duplicate-audit-121 --resume` (a plain `--resume`: run 1 starts at phase 1).

---

## US2: The audit script (S3)

<!-- milestone -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 6 | | `eval/duplicate_audit/audit.py` (EGOGE header; `main(argv)`, `--set {development,held-out}`, `--out-dir`, default `eval/duplicate_audit/results/`): the checks first, writing nothing and exiting 1 on a difference, `held-out` refused without a matching `held-out/freeze.json` (FR-015); its own in-memory connection through `create_table` and `SearchIndex(connection)`, its own delete and insert helper; `page_lists`, `flagged`, `is_restatement` as public functions (FR-003-FR-005); per candidate the counts, bar, verdict and winner, and the stop rule (FR-006, FR-007); the not-binding readings (FR-011); the results and timing files, including the synthetic 500-page pass for the held-out set (FR-010, FR-016). Only FR-015's imports; no git, no network, no model, no write outside `--out-dir` | `eval/duplicate_audit/audit.py` | build | [ ] |
| 7 | | `tests/test_duplicate_audit_script.py` (EGOGE header): FR-017 in full on synthetic inputs in a temporary directory (remove-and-insert equal to a fresh index on 12 pages; the page-type filter; mutual flags at k = 1, 3, 5 and both ranks; every restatement case; the bar edges; selection and the tie; the stop rule both ways; refusals writing nothing; the same bytes twice; an `eval/` snapshot equal before and after; `--help`); FTS5 cases skipped when it is missing (FR-017) | `tests/test_duplicate_audit_script.py` | build | [ ] |

**Checkpoint US2** — verify before continuing:
- [ ] `git status --porcelain` (this phase's changes) lists only `eval/duplicate_audit/audit.py` and `tests/test_duplicate_audit_script.py` (besides `specs/wiki-studio-duplicate-audit-121/hill.json`, which the driver changes when the phase starts, O10); no file under `eval/duplicate_audit/results/` exists yet
- [ ] `git diff <US1 commit or the owner's protocol commit> -- eval/duplicate_audit/README.md eval/duplicate_audit/protocol.json tests/test_duplicate_audit_frozen.py` is empty
- [ ] `grep -n "subprocess\|urllib\|socket\|_INSERT_PAGE\|_connection" eval/duplicate_audit/audit.py` finds nothing
- [ ] `poetry run pytest -q tests/test_duplicate_audit_script.py tests/test_duplicate_audit_frozen.py` passes
- [ ] Full gate green
- [ ] Milestone: the run pauses for the development stage below

**At the pause after US2 — main session, not this phase's work (FR-018):**
- Run `python -m eval.duplicate_audit.audit --set development` once (the session sandbox cannot run Python). Commit `results/development.json` and `results/development-timing.json`, exactly as written, as their own commit.
- Read `stop_rule.outcome` (`go` or `stop`); note it for the pause after US3.
- Add `approved-by:` and resume with the plain `--resume` (same prefix as above).

---

## US3: The development stage, recorded (S1)

<!-- milestone -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 8 | | `eval/duplicate_audit/report.md`: how to rerun both sets; the development section per FR-019 (the table per candidate, the stop rule per candidate, exactly one `Development stage: go` or `Development stage: stop` line, the caveat, numbers "as recorded"); it says the held-out stage has not run; with `stop`, that the bet stops here and issue 121 stays open (FR-019) | `eval/duplicate_audit/report.md` | build | [ ] |
| 9 | | `tests/test_duplicate_audit_development.py` (EGOGE header): the development stage rerun into a temporary directory equals the committed `development.json` byte for byte; timing keys present; one stage line, equal to the file's outcome; the report's table equals the file's numbers; every `python -m eval.duplicate_audit.…` line parses; skipped with the reason when FTS5 is missing (FR-020) | `tests/test_duplicate_audit_development.py` | build | [ ] |
| 10 | | The development-stage audit (FR-021), against the run-1 base: `git diff <base> --stat` lists only FR-034's allowed paths; `git diff <base> -- src/ eval/duplicates eval/similar eval/patterns` empty; with `R=$(git log --diff-filter=A --format=%H -- eval/duplicate_audit/audit.py)`, `git log --format=%H $R^..HEAD -- eval/duplicate_audit/README.md eval/duplicate_audit/protocol.json tests/test_duplicate_audit_frozen.py` prints nothing and `git merge-base --is-ancestor $R $(git log --diff-filter=A --format=%H -- eval/duplicate_audit/results/development.json)` succeeds. Any other path is removed before the milestone, or the run stops | — | build | [ ] |

**Checkpoint US3** — verify before continuing:
- [ ] Task 10's audit passes
- [ ] The driver's gate runs `tests/test_duplicate_audit_development.py`, which reruns the development stage into a temporary directory (the session itself runs no Python); `git status --porcelain eval/` is clean
- [ ] Full gate green
- [ ] Milestone: the run pauses for trigger 0 below

**At the pause after US3 — main session and owner (FR-021; plan, owner step 4):**
- **`Development stage: stop`** (trigger 0): do not resume run 1. Run `pre-pr-check.sh --closes none`, open the evidence PR by hand (FR-034), confirm `closingIssuesReferences` is empty, review, label, merge with a merge commit. The amendment records `stop` (FR-035); US4-US7 and US9-US11 are cut; run 2 is US8 alone unless trigger 1 cut it.
- **`Development stage: go`**: add `approved-by:` and resume with the plain `--resume`.

---

## US4: The held-out extraction code (S2)

<!-- milestone -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 11 | | Read `results/development.json`'s `stop_rule.outcome`: if it is not `go`, stop and report: this phase does not run (FR-021) | — | build | [ ] |
| 12 | | `eval/duplicate_audit/extract.py` (EGOGE header; `main(argv)`; `--wiki-studio`, `--memkernel`, `--wiki-studio-only`, `--out`, default `eval/duplicate_audit/held-out/`): pins and the two memkernel directories as constants equal to `protocol.json`'s; cycle 10's functions imported read-only as FR-022 lists; the source lists (spec bundles, `specs/pitches/<id>/pitch.md`, memkernel's two directories), the slug rule, `origin_issue` from each bundle's `plan.md` at the pin, `source_kind`, `corpus.json` with `left_out` by id only (FR-008, FR-022) | `eval/duplicate_audit/extract.py` | build | [ ] |
| 13 | | `eval/duplicate_audit/sample.py` (EGOGE header; `main(argv)`, `--out`, default `held-out/review-sample.json`): the within-family false pairs, 20 as a fixed 16 from `wiki-studio` and 4 from `memkernel` (a family short of its share gives all it has, the rest from the other; O11), `random.Random(121)`, the labels' sha256 in the output (FR-023) | `eval/duplicate_audit/sample.py` | build | [ ] |
| 14 | | `tests/test_duplicate_audit_extract.py` (EGOGE header): FR-024 in full (slugs; `origin_issue` cases; `source_kind`; pitch paths; `--wiki-studio-only`; the closing-keyword item listed by id only; git reading on a temporary repository, git-gated, nothing written there; the imported functions are cycle 10's objects, or any reimplemented one rebuilds the six fixed pages of `tests/test_duplicates_extract.py` byte for byte; `sample.py` on synthetic labels; `--help` for both) (FR-024) | `tests/test_duplicate_audit_extract.py` | build | [ ] |

**Checkpoint US4** — verify before continuing:
- [ ] `git status --porcelain` (this phase's changes) lists only `extract.py`, `sample.py` and `tests/test_duplicate_audit_extract.py` (besides `specs/wiki-studio-duplicate-audit-121/hill.json`, which the driver changes when the phase starts, O10); no `held-out/` data file exists yet
- [ ] `git diff -- eval/duplicates` is empty; `git -C ../memkernel status --porcelain` as before
- [ ] `grep -n "shell=True" eval/duplicate_audit/extract.py` finds nothing
- [ ] `poetry run pytest -q tests/test_duplicate_audit_extract.py tests/test_duplicates_extract.py` passes
- [ ] Full gate green
- [ ] Milestone: the run pauses for the extraction run below

**At the pause after US4 — main session, not this phase's work (FR-025):**
- End of week 1: if the owner takes trigger 2, add `--wiki-studio-only` below.
- Run `python -m eval.duplicate_audit.extract` once. Commit `held-out/corpus/` and `held-out/corpus.json`, exactly as written, as their own commit. Check `git -C ../memkernel status --porcelain` is unchanged.
- Add `approved-by:` and resume with the plain `--resume`.

---

## US5: The held-out labels (S2)

<!-- milestone -->
<!-- The labelling session: read the protocol's labelling rule (eval/duplicate_audit/README.md, FR-009), specs/wiki-studio-duplicates-121/spec.md FR-013-FR-016, held-out/corpus.json and the pages under held-out/corpus/. Do not open eval/duplicate_audit/audit.py, eval/duplicate_audit/report.md, or any results/ directory under eval/; do not open eval/patterns/duplicates.py or eval/revisions/. Run no script; compute no token set, overlap, rank or score. Label from the pages' content only. A family's pages may be read with read-only shell commands (cat of its directory). Hashes from `shasum -a 256`. -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 15 | | Per family (`wiki-studio`, `memkernel`; only `wiki-studio` if trigger 2 was taken): read every page; group pages that answer the same question, each group named by its question; every in-group pair gets one disposition of six and a one-line reason naming the question, labelled once; a within-family pair outside every group is `unrelated`; a pitch decision and the spec decision it restates are labelled by content (FR-009, FR-026) | `eval/duplicate_audit/held-out/labels.json` | build | [ ] |
| 16 | | The summary of all families (one line per group, one per page in no group); one pass over it; the cross-repository pairs found, each read before labelling, with disposition and reason; unlisted cross pairs `unrelated` (FR-009, FR-026) | `eval/duplicate_audit/held-out/labels.json` | build | [ ] |
| 17 | | `labels.json` keys per FR-026 (`corpus_sha256` via `shasum -a 256`, `families`, `groups`, `pairs`, `summary`, `cross_pairs`, `defaults`, `true_pairs`). `held-out/README.md`, labelling section: the six dispositions, grouping by question, the defaults, how restated pitch and spec decisions are labelled, `true_pairs` beside the minimum of 8 (FR-026) | `eval/duplicate_audit/held-out/labels.json`, `eval/duplicate_audit/held-out/README.md` | build | [ ] |
| 18 | | `tests/test_duplicate_audit_labels.py` (EGOGE header): FR-027 in full (keys; groups within one family; in-group pairs labelled exactly once; no pair without a common group; dispositions and reasons; cross pairs across repositories; one summary line per group and per ungrouped page; `true_pairs` recomputed and equal to the README; `corpus_sha256`; the review sample's shape when it exists; the closing-keyword scan) (FR-027) | `tests/test_duplicate_audit_labels.py` | build | [ ] |

**Checkpoint US5** — verify before continuing:
- [ ] `git status --porcelain` (this phase's changes) lists only `held-out/labels.json`, `held-out/README.md` and `tests/test_duplicate_audit_labels.py` (besides `specs/wiki-studio-duplicate-audit-121/hill.json`, which the driver changes when the phase starts, O10)
- [ ] No file under `eval/duplicate_audit/` other than those three changed; `audit.py` unchanged since US2
- [ ] `poetry run pytest -q tests/test_duplicate_audit_labels.py` passes
- [ ] Full gate green
- [ ] Milestone: the run pauses for the steps below (FR-028)

**At the pause after US5 — main session and owner, not this phase's work (FR-028):**
- Run `python -m eval.duplicate_audit.sample` once and commit `held-out/review-sample.json` as its own commit, before any label changes.
- **The owner's review**: every true and `companion` label, every listed cross pair, the 20 sampled pairs. Change any label by a commit now, updating `true_pairs` and the README count with it; never after the freeze.
- End of week 2: if the freeze cannot land in time, the labels freeze as reviewed by now (trigger 3).
- Add `approved-by:` and resume with the plain `--resume`.

---

## US6: The freeze (S2)

<!-- milestone -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 19 | | `held-out/freeze.json` per FR-029 (`protocol_sha256`, `corpus_sha256`, `labels_sha256`, `review_sample_sha256` from `shasum -a 256`; `true_pairs`; `testable`; `owner_changed_labels_after_the_draw`; the `not testable` sentence when it applies). `held-out/README.md` corpus section from `corpus.json`: pages per repository, source kind and form; left-out items by id; badly extracted items; pitches and bundles with and without `origin_issue`; whether trigger 2 narrowed the base. No label changes (FR-029) | `eval/duplicate_audit/held-out/freeze.json`, `eval/duplicate_audit/held-out/README.md` | build | [ ] |
| 20 | | `tests/test_duplicate_audit_corpus.py` and `tests/test_duplicate_audit_heldout_frozen.py` (EGOGE headers): FR-030 in full (files equal entries; page hashes; `source_kind` and `origin_issue` agree with `spec_path`; README counts; structural lint on a temporary wiki with only listed violations; constants with the sha256 of `freeze.json`, `corpus.json`, `labels.json`, `review-sample.json`, `held-out/README.md` from a shell; `freeze.json`'s hashes and `protocol_sha256` match). The frozen test is written once, never edited after this phase (FR-030) | `tests/test_duplicate_audit_corpus.py`, `tests/test_duplicate_audit_heldout_frozen.py` | build | [ ] |

**Checkpoint US6** — verify before continuing:
- [ ] `git status --porcelain` (this phase's changes) lists only `held-out/freeze.json`, `held-out/README.md` and the two tests (besides `specs/wiki-studio-duplicate-audit-121/hill.json`, which the driver changes when the phase starts, O10)
- [ ] `git diff <the last label commit> -- eval/duplicate_audit/held-out/labels.json` is empty
- [ ] `poetry run pytest -q tests/test_duplicate_audit_corpus.py tests/test_duplicate_audit_heldout_frozen.py tests/test_duplicate_audit_labels.py` passes
- [ ] Full gate green
- [ ] Milestone: the run pauses for the held-out run below

**At the pause after US6 — main session, not this phase's work (FR-031):**
- Run `python -m eval.duplicate_audit.audit --set held-out` once. Commit `results/held-out.json` and `results/held-out-timing.json`, exactly as written, as their own commit.
- Add `approved-by:` and resume with the plain `--resume`.

---

## US7: The measurement and the evidence PR (S3)

<!-- milestone -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 21 | | `report.md` held-out section per FR-032: the table per candidate with each bar condition; exactly one winner line (`Winner: mutual-top-1`, `-3`, `-5` or `none`) and the verdict; the not-binding readings; the development section unchanged; the timings and whether the synthetic pass took over 10 s; the limits stated plainly; numbers "as recorded"; no post-hoc section unless FR-011 applies (FR-032) | `eval/duplicate_audit/report.md` | build | [ ] |
| 22 | | `tests/test_duplicate_audit_results.py` (EGOGE header): the held-out run rerun into a temporary directory equals the committed `held-out.json` byte for byte; timing keys; one winner line equal to the file's; the table equals the file's numbers; `paths` recompute with `slug_paths`; skipped with the reason when FTS5 is missing (FR-033) | `tests/test_duplicate_audit_results.py` | build | [ ] |
| 23 | | The evidence PR's scope and history audit (FR-034), against the run-1 base: task 10's checks; with `D`, `X`, `L`, `F`, `H` as FR-034 defines them (development results, corpus, labelling commit, freeze commit, held-out results), each an ancestor of the next (`git merge-base --is-ancestor`); `git show --stat L` lists only the three labelling files; `git log --format=%H F..HEAD -- eval/duplicate_audit/held-out/corpus eval/duplicate_audit/held-out/corpus.json eval/duplicate_audit/held-out/labels.json eval/duplicate_audit/held-out/review-sample.json eval/duplicate_audit/held-out/freeze.json eval/duplicate_audit/held-out/README.md tests/test_duplicate_audit_heldout_frozen.py` prints nothing. Any other path is removed before the milestone, or the run stops | — | build | [ ] |

**Checkpoint US7** — verify before continuing:
- [ ] Task 23's audit passes
- [ ] The driver's gate runs `tests/test_duplicate_audit_results.py` and `tests/test_duplicate_audit_development.py`; `git status --porcelain eval/` is clean
- [ ] The closing-keyword grep of US1's checkpoint still finds nothing
- [ ] Full gate green
- [ ] Milestone: run 1 ends here and is never resumed

**At the pause after US7 — main session and owner (FR-034, FR-035; plan, owner step 8):**
- Do not resume run 1 (a resume could reach the driver's own PR, which would name issue 121 for closure). If the driver opened a PR anyway, close it unmerged.
- Run `../code-copilot-team/scripts/pre-pr-check.sh --closes none --title <title> --body-file <file> --base main`; open the evidence PR by hand, its body naming issue 121 without a closing keyword; confirm `gh pr view <n> --json closingIssuesReferences` lists nothing; external review, the `reviewed` label after the review of its head, merge with a merge commit, never squash.
- A flaw found in review goes into a non-binding `post_hoc` block computed by `audit.py` and checked by the results test, plus a "Post hoc (not binding)" report section; nothing in the protocol, the labels or the winner line changes.
- The spec amendment: FR-035's slot, the triggers that fired, `DUPLICATE_K`, run 2's `automation.json`, re-approval. With `none` or `not testable` the kind is cut (trigger 4); run 2 is US8 alone unless trigger 1 cut it.

---

**Set by the spec amendment:** _pending (FR-035)._

## US8: Both constructors read the off switches (S6)

<!-- milestone -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 24 | | Read FR-035: if its slot still reads "to be set by the spec amendment", stop and report: this phase does not run (FR-035) | — | build | [ ] |
| 25 | | `paths.py`: one private helper that reads an on/off switch from a mapping as `resolve` reads `WIKI_STUDIO_SIMILAR_PAGES` today; `resolve` uses it, behaviour unchanged; `for_root` gains `env: Mapping[str, str] \| None = None` and reads the switch through the helper when `similar_pages` is None; an explicit argument wins; the docstrings say a bad value raises in library calls too (FR-036) | `src/wiki_studio/paths.py` | build | [ ] |
| 26 | | README: the `WIKI_STUDIO_SIMILAR_PAGES` row and the library example near `for_root`; `docs/consumers.md` beside its two `for_root` examples (memkernel's included: a mistyped value now fails every call that builds paths this way; how to pass it explicitly); `CHANGELOG.md` `[Unreleased]` **Changed**: one entry. Every changed shown command checked (FR-037) | `README.md`, `docs/consumers.md`, `CHANGELOG.md` | build | [ ] |
| 27 | | `tests/test_paths.py`: FR-038's cases for `for_root` (unset, empty, `off`, `OFF`, ` on `, an invalid value raising and naming the variable, an explicit value with an invalid variable not raising, the `env` mapping); `resolve`'s existing cases pass unedited; `with_wiki_dir` carries the field (FR-038) | `tests/test_paths.py` | build | [ ] |

**Checkpoint US8** — verify before continuing:
- [ ] `git diff <run-2 base> --stat -- src/` lists only `src/wiki_studio/paths.py`
- [ ] `WIKI_STUDIO_SIMILAR_PAGES=bogus poetry run wiki-studio findings` exits 1 as before; `poetry run pytest -q tests/test_paths.py tests/test_similar_pages.py` passes
- [ ] Full gate green
- [ ] Milestone: without a winner, run 2 ends here and is never resumed (build PR by hand, as at the pause after US11); with a winner, resume with `env -u CCT_REVIEW_DIFF_MAX_LINES CCT_PROJECT_DIR=$PWD ../code-copilot-team/scripts/auto-build-loop.sh wiki-studio-duplicate-audit-121 --resume --start-phase 8`, never a plain `--resume`

---

## US9: The audit rule in the package (S4)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 28 | | Read FR-035: if it names no winner, stop and report: this phase does not run (FR-035) | — | build | [ ] |
| 29 | | `search_index.py`, additions only: `SearchIndex.remove(path)` and `SearchIndex.add(document)` (FR-039) | `src/wiki_studio/search_index.py` | build | [ ] |
| 30 | | `src/wiki_studio/duplicates.py` (EGOGE header; standard library only; no forbidden layout string): `DUPLICATE_K` (the amendment's k), `COMPARED_PAGE_TYPES`, eligible pages as `select` reads them without the cache, one `build_in_memory` index, remove-rank-add per compared page under `DEFAULT_RANKER_CONFIG` with `similar_query`, the same-type filter, mutual flags, the conflict and related-line skips, `DuplicatePair`, `DuplicateCheck`, `duplicate_scan` (FR-040); the related-line parser reusing `conflicts.py`'s helpers, and `conflicts.py`'s "only importer" sentence naming `duplicates.py` too, no other line (FR-041). `CLAUDE.md` Layout gains `src/wiki_studio/duplicates.py   the possible-duplicate scan (mutual rank, the measured winner) and the related-line parser; reads only` after the `findings.py` line | `src/wiki_studio/duplicates.py`, `src/wiki_studio/conflicts.py`, `CLAUDE.md` | build | [ ] |
| 31 | | `paths.py`: `ENV_DUPLICATE_CHECK`, `WikiPaths.duplicate_check: bool = True` with its docstring entry, `for_root` and `resolve` taking `duplicate_check: bool \| None = None`, both reading it through US8's helper (only `resolve` if US8 was cut) (FR-042) | `src/wiki_studio/paths.py` | build | [ ] |
| 32 | | `tests/test_duplicate_scan.py` (EGOGE header): FR-043 in full (the replay on the frozen held-out pages against `held-out.json`'s winner pairs and ranks; remove-rank-add equal to a fresh index per page; `DUPLICATE_K`; the parser cases; the switch cases for both constructors; the filters) (FR-043) | `tests/test_duplicate_scan.py` | build | [ ] |

**Checkpoint US9** — verify before continuing:
- [ ] `git diff <run-2 base> -- src/wiki_studio/search_index.py | grep -c '^-[^-]'` prints 0 (additions only)
- [ ] `git diff <US8 commit> -- src/wiki_studio/findings.py src/wiki_studio/discovery.py src/wiki_studio/querier.py eval` is empty; `git diff <US8 commit> -- src/wiki_studio/conflicts.py` changes one docstring sentence
- [ ] `poetry run pytest -q tests/test_duplicate_scan.py tests/test_search_index.py tests/test_conflict_callouts.py tests/test_package_boundaries.py` passes
- [ ] Full gate green

---

## US10: The possible-duplicate kind (S4)

<!-- milestone -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 33 | | `findings.py`: `KIND_POSSIBLE_DUPLICATE` appended last to `FINDING_KINDS`; when the switch is on, one warning per pair through the conflict loop's scope rule, the description per FR-044 ending with the exact related line; `FindingsResult.duplicate_check` and its `as_dict` key after `revision_check`; off never calls the scan. `cli.py`: the `duplicate check:` line after the revision check line, the `findings` and `--json` help. `api.findings`' docstring and `findings.py`'s module docstring. `mcp_adapter/trace.py`: `TOOL_RESULT_KEYS[TOOL_FINDINGS]` gains `duplicate_check` (FR-044, FR-045) | `src/wiki_studio/findings.py`, `src/wiki_studio/cli.py`, `src/wiki_studio/api.py`, `src/wiki_studio/mcp_adapter/trace.py` | build | [ ] |
| 34 | | `tests/test_possible_duplicate.py` (EGOGE header): FR-046 in full (the line round trip on either page; brackets; conflict-joined pairs skipped and reported once as conflicts; a dangling related line; scope; switch off with a spy; FTS5 missing; strict lint, review state, `approve`, `find` unchanged; nightly lists and drafts nothing; the MCP result and trace key, gated on the extra; the no-backend and single-writer tests unedited; a snapshot of the wiki, proposals and cache location; the 10 s bound on the synthetic wiki). `tests/test_findings.py`: the fixture yields exactly one `possible-duplicate`; key sets expect the new entries; never by turning the switch off (FR-046) | `tests/test_possible_duplicate.py`, `tests/test_findings.py` | build | [ ] |

**Checkpoint US10** — verify before continuing:
- [ ] `git diff <run-2 base> -- src/wiki_studio/health_lint.py src/wiki_studio/lint.py src/wiki_studio/review.py src/wiki_studio/discovery.py src/wiki_studio/promoter.py src/wiki_studio/nightly.py src/wiki_studio/mcp_adapter/tools.py` is empty
- [ ] `grep -n "FINDINGS_FORMAT_VERSION = 1" src/wiki_studio/contract.py` still matches; `tests/test_info_contract.py` passes unedited
- [ ] On a temporary wiki with two near-identical decision pages linked from `index.md`, `poetry run wiki-studio findings --json` reports one `possible-duplicate` and `duplicate_check.state` `ran`; with `WIKI_STUDIO_DUPLICATE_CHECK=off` zero and `off`; the description's last line pasted into the first page makes it zero; `poetry run wiki-studio lint --health --strict` exits as before
- [ ] Full gate green
- [ ] Milestone: the run pauses for trigger 5 below

**At the pause after US10 — owner (FR-050; plan, owner step 9):**
- Middle of week 4 (trigger 5): if US9-US10 are not downhill or the time-bound test fails, cut US9-US11 (committed code removed by a follow-up commit, never an amend or force push). Otherwise resume with `env -u CCT_REVIEW_DIFF_MAX_LINES … --resume --start-phase 8`, never a plain `--resume`.

---

## US11: ADR-0006 and the documents (S5)

<!-- milestone -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 35 | | `docs/adr/0006-related-line.md`: the optional `> [!related]` body line (FR-041's rule), no frontmatter key, page type or schema version change, memkernel's bridge carrying the body; `not_duplicate_of:` weighed and refused (FR-047) | `docs/adr/0006-related-line.md` | build | [ ] |
| 36 | | Packaged `citation-rules.md`: a short section after "When sources disagree". `docs/knowledge-contract.md` Findings: the kind's row, the `duplicate_check` object, the switch, what was measured. README: the `findings` section names the kind; the environment table gains `WIKI_STUDIO_DUPLICATE_CHECK` (both constructors, or the limit stated if US8 was cut). `docs/patterns.md`: the three answers to a flag. Every changed shown command checked (FR-048) | `src/wiki_studio/schema/citation-rules.md`, `docs/knowledge-contract.md`, `README.md`, `docs/patterns.md` | build | [ ] |
| 37 | [P] | `CHANGELOG.md` `[Unreleased]`: **Added** `possible-duplicate`, `duplicate_check`, the related line and the switch, with one sentence on what was measured; **Docs** ADR-0006 and `docs/patterns.md`; no version section, no date, no closing keyword (FR-049) | `CHANGELOG.md` | build | [ ] |
| 38 | | Invariant audit (FR-050): the untouched-files `git diff` is empty; `git diff <base> --stat -- src/` lists only FR-050's files; `search_index.py` additions only; `FINDINGS_FORMAT_VERSION`, `SCHEMA_VERSION`, `CAPABILITIES`, `FORMATS` unchanged; `FINDING_KINDS` is the base tuple plus `possible-duplicate` last; exit codes unchanged (`tests/test_cli_contract.py`); no runtime dependency; the closing-keyword `git grep` finds nothing; no version bump, CHANGELOG version section or tag | — | build | [ ] |

**Checkpoint US11** — verify before continuing:
- [ ] Task 38's audit passes
- [ ] `poetry run wiki-studio findings --help` succeeds and names the kind; `poetry run wiki-studio --version` prints the run-2 base's version; `docs/compatibility.md` unchanged
- [ ] `poetry run pytest -q tests/test_schema_fingerprint.py tests/test_quickstart.py` passes
- [ ] Full gate green
- [ ] Milestone: run 2 ends here and is never resumed

**At the pause after US11 (or after US8 without a winner) — main session and owner (FR-050; plan, owner step 9):**
- Do not resume run 2. Re-run the gate on the branch head before trusting `landed`; check no phase was bypassed without its record.
- Run `../code-copilot-team/scripts/pre-pr-check.sh --closes none --title <title> --body-file <file> --base main`; open the build PR by hand, naming issue 121 without a closing keyword; confirm `closingIssuesReferences` lists nothing; external review, label after the review of its head, merge with a merge commit.
- Issue 121 stays open; the owner decides by hand. Any release only on the owner's explicit word.

---

## Final Verification

- [ ] Type checker: 0 errors; linter and formatter: 0 errors on `src/ tests/ eval/ examples/ conformance/`
- [ ] Full suite green with coverage at or above 92 percent; the git-gated tests ran in CI
- [ ] The protocol froze and was signed off before `audit.py` existed; the development stage ran before any held-out page was extracted; the labels were made without audit code, reviewed by the owner and frozen before the held-out run; every results file was produced by the main session at a pause and CI reproduces it byte for byte
- [ ] The evidence PR has one commit per phase and per main-session step, merged with a merge commit, never squashed, no change under `src/`, no closing keyword, opened by hand
- [ ] `WikiPaths.for_root` reads the switch and a bad value raises, documented for memkernel (unless trigger 1 cut it)
- [ ] With a winner: `possible-duplicate` reproduces the winner's pairs on the frozen held-out pages, is silenced by the related line, stays within 10 s on 500 pages and writes nothing; every place that documents it says only decision pages were measured
- [ ] No new exit code, frontmatter key, page type, capability, MCP tool or dependency; `findings_version` 1; `find`, the hint and `lint --health --strict` unchanged
- [ ] No version bump, CHANGELOG version section, tag or release from any run; issue 121 open, closed by no PR
