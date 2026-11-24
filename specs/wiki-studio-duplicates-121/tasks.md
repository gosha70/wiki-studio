# Tasks: a near-duplicate finding from titles and summaries (issue 121)

<!-- status: draft -->
<!-- One `## US<n>:` group = one auto-build phase = one commit. [US#]/FR tags trace to spec.md. The (S<n>) token in each heading is the pitch scope the phase moves. Run 1 (the evidence) is US1-US6 and ends at the pause after US6; the evidence PR is opened by hand. Run 2 (the build) is US7-US9, a fresh run with --start-phase 7, only with a winner named by the spec amendment of FR-026 and only after the owner has released 0.11.0. -->
<!-- Read first: CLAUDE.md, spec.md, plan.md (facts, departures, "Runs, pauses and script runs", open items), specs/pitches/121-near-duplicate-finding/pitch.md, eval/patterns/duplicates.py (63-64, 85-137; read-only, imported by tests and the scorer, never by the labelling phase), eval/patterns/protocol.json, eval/patterns/labels.json (551-553), tests/test_revisions_frozen.py and tests/test_patterns_frozen.py (the pin pattern), src/wiki_studio/wiki_state.py (142-146), src/wiki_studio/schema/__init__.py (47-115), src/wiki_studio/lint.py (342-373), src/wiki_studio/yaml_lite.py (123-132). Run 2 also: src/wiki_studio/findings.py, src/wiki_studio/conflicts.py, src/wiki_studio/paths.py (30-70, 255-406), src/wiki_studio/review.py (default_review_pages, read_live_page, superseded_by), src/wiki_studio/cli.py (410-430), src/wiki_studio/api.py (835-860), tests/test_findings.py, tests/test_package_boundaries.py, tests/conftest.py. code-copilot-team and memkernel (read-only, offline, by commit): the sibling checkouts the owner confirmed (plan, owner step 1). -->
<!-- Run per phase: poetry run ruff check src/ tests/ eval/ conformance/ examples/ && poetry run ruff format --check src/ tests/ eval/ conformance/ examples/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=92 -->
<!-- Script runs are main-session steps (plan, "Runs, pauses and script runs", item 1): no phase runs extract.py, sample.py or candidates.py to produce committed data. Those runs happen at the milestone pauses below, in the main session, each committed as its own commit. A phase writes code, prose and tests whose checks pass on files it writes or on files an earlier commit holds. -->
<!-- Each phase is reviewed on its own diff: every file a phase writes must be true at the end of that phase. No README, report, docstring, help text, doc, ADR or CHANGELOG line states later-phase work as done. Each behaviour is stated once, in its owning FR (extraction FR-002-FR-007, review sample FR-008, labels FR-013-FR-015, who labels and the pause FR-016, candidates/bar/selection FR-018, freeze FR-019, scorer FR-020, post hoc and the amendment FR-026, winner FR-027, package rule FR-028, related line FR-029, switch FR-030, the kind FR-032, closure FR-039, release FR-040); code comments and tests cite the FR. -->
<!-- Invariants: no model on any path from findings, approve or review_state; nothing in lint, lint --health or --strict changes and the new kind never makes lint --health --strict fail; findings writes nothing and exits 0 on a completed run; no automatic merge, deletion, supersession, approval change or page rewrite; nightly drafts nothing for the kind. wiki_state._tokenise and ingest's candidate selection unchanged. No new exit code, frontmatter key, page type, directory, capability, MCP tool or runtime dependency; no findings_version or schema.version change; no user-tunable threshold. No candidate runs and no similarity is computed on the new corpus before US4's freeze; the labelling phase has no candidate code and runs nothing; no label, page, candidate, threshold or bar is edited after US4 and no page is added after the run. No edit to eval/patterns/'s frozen files, eval/navigation, eval/revisions, memkernel or code-copilot-team; no network read; nothing written to either checkout. Package modules spell none of code-copilot-team, shared/, specs/, doc_internal, knowledge/wiki (tests/test_package_boundaries.py). Every new .py file starts with the two-line EGOGE / Apache-2.0 header; from __future__ import annotations; type hints. Every shown command gets a real check. No closing keyword before an issue reference in any file, commit message or PR text (issue 121 is shut only through run 2's automation.json pr.closes, and only when the kind ships); no text from eval/revisions/cases/keyword-quoting/ anywhere. No version bump, no CHANGELOG version section, no tag, no release in any phase (FR-040). No commit, push or branch change inside the session; the driver owns git. Never weaken or skip a test. -->

## US1: The extraction code, before any page exists (S1)

<!-- milestone -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 1 | | `eval/duplicates/__init__.py` (header only) and `README.md` opening per FR-001 (issue 121, the pitch, the branch base's full hash, what is and is not measured, pages extracted not curated, `eval/patterns/` read only, no model). `CLAUDE.md` Layout gains `eval/duplicates/          the near-duplicate study (issue 121): extracted corpus, labels, candidates, results, report` after the `eval/revisions/` line (FR-001) | `eval/duplicates/__init__.py`, `eval/duplicates/README.md`, `CLAUDE.md` | build | [ ] |
| 2 | | Read offline, with read-only `git -C <checkout> rev-parse`, `ls-tree`, `show` and `log -1 --format=%cs` only (nothing fetched, nothing written there): the full hashes and commit dates of `fd05256` and `8279d76`; code-copilot-team's `routing` and `pi` directory lists by FR-003's prefix rule, and each extension step's list; memkernel's spec directories with a decision section. README corpus-rule section: the sources and pins, each family's directory list beside the pitch's counts (routing 10, pi 5), the exclusions with their reasons and the checks that found them, the extension order, cut 1, and the closing-keyword left-out rule (FR-002, FR-003, FR-007) | `eval/duplicates/README.md` | build | [ ] |
| 3 | | `eval/duplicates/extract.py` (EGOGE header; `main(argv)`; `--code-copilot-team`, `--memkernel`, `--extend`, `--cut-1`, `--out`): the pins and family tables as named constants; the reading layer of FR-002 (argument lists, no shell, inherited `GIT_` variables dropped but the three config ones, `-c protocol.allow=never`, writes only under `--out`); decision sections and the three forms by precedence, `h3-adr` (FR-004); the title rule with FR-005's identifier pattern, trailing parenthetical and first-sentence fallback; the four-step body rule and the page bytes, slug and path (FR-006); `corpus.json` with per-page input counts and `left_out` (FR-007). A pure page-building function that tests can call on raw section text. README: the extraction rule in words, step by step | `eval/duplicates/extract.py`, `eval/duplicates/README.md` | build | [ ] |
| 4 | | `eval/duplicates/sample.py` (EGOGE header; `main(argv)`, `--out`): FR-008's population, largest-remainder split over the three base families, `SAMPLE_SEED = 121`, output `review-sample.json` with the seed, split, the labels' sha256 and the 20 pairs (FR-008) | `eval/duplicates/sample.py` | build | [ ] |
| 5 | | The six fixed items (one per form in each repository: code-copilot-team list item, bold paragraph, H3; memkernel list item, bold paragraph, `h3-adr`), none quoting closing-keyword text, each read with `git show <pin>:<path>`; the README names them by spec path and line span (FR-009; O12) | `eval/duplicates/README.md` | build | [ ] |
| 6 | | `tests/test_duplicates_extract.py` (EGOGE header, unittest style): FR-009 in full: forms and precedence, the title cases, each body step, the page bytes, the left-out item listed by id only, exclusions and the extension and cut-1 sets, git reading on a temporary repository (git-gated; `GIT_DIR` injected changes nothing; nothing written), `sample.py` on synthetic labels, `--help` for both scripts, the closing-keyword scan of `eval/duplicates/`; and **the six fixed items** as module constants (raw section text, expected title, expected paragraph written out by hand), each built by extract.py's page builder, asserting the title, the label absent from the body, and that `_first_paragraph` (imported read-only from `eval/patterns/duplicates.py`) equals **the first paragraph of each item's text after its label** (FR-009) | `tests/test_duplicates_extract.py` | build | [ ] |

**Checkpoint US1** — verify before continuing:
- [ ] `git status --porcelain` (this phase's changes) lists only `eval/duplicates/__init__.py`, `README.md`, `extract.py`, `sample.py`, `tests/test_duplicates_extract.py` and `CLAUDE.md`; no `corpus/`, `corpus.json` or any other data file exists yet
- [ ] `git -C ../code-copilot-team status --porcelain` and `git -C ../memkernel status --porcelain` are as before the phase
- [ ] `git grep -n -i -E '(close[sd]?|fix(e[sd])?|resolve[sd]?) +#[0-9]' -- eval/duplicates` finds nothing
- [ ] `poetry run pytest -q tests/test_duplicates_extract.py tests/test_patterns_frozen.py` passes
- [ ] Full gate green
- [ ] Milestone: the run pauses for the extraction run below

**At the pause after US1 — main session, not this phase's work (FR-010):**
- End of week 1: if the owner invokes cut 1, add `--cut-1` below (trigger 1).
- Run `python -m eval.duplicates.extract` once (the main session or the owner; the session sandbox cannot run Python). Commit `eval/duplicates/corpus/` and `eval/duplicates/corpus.json`, exactly as written, as their own commit. Check both checkouts' `git status --porcelain` is unchanged.
- Note the commit's size (`git show --stat`); it is outside US2's review diff (plan, fact 11).
- Add `approved-by:` under the checkpoint in `automation-summary.md` and resume with `env -u CCT_REVIEW_DIFF_MAX_LINES`.

---

## US2: The extracted corpus, checked (S1)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 7 | | README corpus section from `corpus.json` (FR-011): pages per repository, family and form, any difference from the pitch's counts reported and not tuned; the left-out items by id; the pages with an empty first paragraph, counted per repository and form and listed; min, median and max of `title_tokens` and `paragraph_tokens` per repository and form; the six fixed items by id; extracted not curated; B1's template-word drop unmeasurable on this corpus; the structural-lint violations that come from an item's own text, listed by page (O2) (FR-011) | `eval/duplicates/README.md` | build | [ ] |
| 8 | | `tests/test_duplicates_corpus.py` (EGOGE header): FR-012 in full: files equal entries, sha256 per page, input counts recomputed, README counts and lists equal `corpus.json`, the six fixed pages byte-equal to the builder's output for the raw texts imported from `tests.test_duplicates_extract` and their `_first_paragraph` equal to **the first paragraph of each item's text after its label**, no excluded spec, no label line in a body, the closing-keyword scan, the structural lint on a temporary wiki (pages as `decisions/<slug>.md`, an `index.md` linking all, a `log.md`) with only the README's listed violations (FR-012) | `tests/test_duplicates_corpus.py` | build | [ ] |

**Checkpoint US2** — verify before continuing:
- [ ] `git status --porcelain` (this phase's changes) lists only `eval/duplicates/README.md` and `tests/test_duplicates_corpus.py`; no file under `corpus/` or `corpus.json` changed
- [ ] No `.py` file under `eval/duplicates/` other than `__init__.py`, `extract.py` and `sample.py`
- [ ] `poetry run pytest -q tests/test_duplicates_corpus.py tests/test_duplicates_extract.py` passes
- [ ] Full gate green

---

## US3: The labels, for the owner's review (S2)

<!-- milestone -->
<!-- This phase has no candidate code and runs nothing (FR-016): eval/duplicates/candidates.py does not exist; do not open eval/patterns/duplicates.py, eval/patterns/results/ or eval/revisions/; compute no token set, overlap or score. Label from the pages' content only. A family's pages may be read with one read-only shell command (cat of its directory). -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 9 | | Per family (routing, pi, memkernel): read every page and group pages that answer the same question, each group named by its question; every in-group pair gets one disposition of the six and a one-line reason naming the question, labelled once even when two groups share it; a within-family pair outside every group is `unrelated`. README labelling section: the six dispositions, grouping by question and why, the within-family default, and the decision-and-incident rule (`companion`, false) with the two examples of FR-013 named by path only (FR-013) | `eval/duplicates/labels.json`, `eval/duplicates/README.md` | build | [ ] |
| 10 | | The summary of all families, one line per group (its question) and one per page in no group (its title); one pass over it; the cross-family and cross-repository pairs found, each read before labelling, with disposition and reason; unlisted cross pairs `unrelated` (FR-014) | `eval/duplicates/labels.json`, `eval/duplicates/README.md` | build | [ ] |
| 11 | | `labels.json` per FR-015 (`corpus_sha256` of `corpus.json` via `shasum -a 256`, `families`, `groups`, `pairs`, `summary`, `cross_pairs`, `defaults`, `true_pairs`); the README states `true_pairs` beside the minimum of 8 (FR-015) | `eval/duplicates/labels.json`, `eval/duplicates/README.md` | build | [ ] |
| 12 | | `tests/test_duplicates_labels.py` (EGOGE header): FR-017 in full (keys; groups within one family; in-group pairs labelled exactly once; no pair without a common group; dispositions and reasons; cross scopes; one summary line per group and per ungrouped page; `true_pairs` recomputed; `corpus_sha256`; when `review-sample.json` exists, 20 distinct pairs within the base families, split by FR-008's rule (8/1/11 on the full base); the closing-keyword scan) (FR-017) | `tests/test_duplicates_labels.py` | build | [ ] |

**Checkpoint US3** — verify before continuing:
- [ ] `git status --porcelain` (this phase's changes) lists only `eval/duplicates/labels.json`, `eval/duplicates/README.md` and `tests/test_duplicates_labels.py`
- [ ] No `.py` file under `eval/duplicates/` other than `__init__.py`, `extract.py` and `sample.py`
- [ ] `poetry run pytest -q tests/test_duplicates_labels.py tests/test_duplicates_corpus.py` passes
- [ ] Full gate green
- [ ] Milestone: the run pauses for the steps below (FR-016)

**At the pause after US3 — main session and owner, not this phase's work (FR-016, FR-008):**
- **Extension rule**, only if `true_pairs` is below 8: run `python -m eval.duplicates.extract --extend N` for the next step of FR-003's order and commit the added pages, `corpus.json` and the README's updated counts as one commit; start a fresh labelling session by hand (no candidate code, US3's instructions) to label the added family and redo the summary pass, committed as one commit; repeat until `true_pairs` is at least 8 or the order is used up.
- Run `python -m eval.duplicates.sample` once and commit `review-sample.json` as its own commit, before any label changes.
- **The owner's review (D3)**: every true and `companion` label, every listed cross pair, and the 20 sampled false pairs. Change any label by a commit on the branch now; never after the freeze.
- End of week 2: if the freeze cannot land in time, the labels freeze as reviewed by now (trigger 2).
- Add `approved-by:` and resume with `env -u CCT_REVIEW_DIFF_MAX_LINES`.

---

## US4: The freeze (S2)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 13 | | `protocol.json` and the README protocol section per FR-018: pages and pair scopes; the label rule; B0; B1's two text patterns and four token rules exactly as FR-018 writes them, the template words; the threshold as `4 * shared >= union` with a non-empty union; the bar's three conditions; selection with the tie to B0; the verdicts and the winner line forms; `corpus_sha256`, `labels_sha256`; the review sample's seed and split; the issue 54 disputed pair; the reporting splits; if cut 1 was invoked, the narrowed families named. No other content change (FR-018) | `eval/duplicates/protocol.json`, `eval/duplicates/README.md` | build | [ ] |
| 14 | | `tests/test_duplicates_frozen.py` (EGOGE header): constants with the sha256 (shell `shasum -a 256`) of `corpus.json`, `labels.json`, `protocol.json`, `review-sample.json` and `README.md` as they will be committed in this phase; each asserted; every page checked against its `corpus.json` entry and the pages present equal to the entries; `protocol.json`'s two hashes and `labels.json`'s `corpus_sha256` equal the frozen files'. Written once, never edited after this phase (FR-019) | `tests/test_duplicates_frozen.py` | build | [ ] |

**Checkpoint US4** — verify before continuing:
- [ ] `git status --porcelain` (this phase's changes) lists only `eval/duplicates/protocol.json`, `eval/duplicates/README.md` and `tests/test_duplicates_frozen.py`
- [ ] No `.py` file under `eval/duplicates/` other than `__init__.py`, `extract.py` and `sample.py`
- [ ] `poetry run pytest -q tests/test_duplicates_frozen.py tests/test_duplicates_labels.py tests/test_duplicates_corpus.py` passes (the driver's gate is the frozen test's first run)
- [ ] Full gate green

---

## US5: The scorer (S3)

<!-- milestone -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 15 | | `eval/duplicates/candidates.py` (EGOGE header; `main(argv)`, `--out-dir`): the refusal unless `corpus.json` and `labels.json` hash to `protocol.json`'s values; B0 and B1 read from `protocol.json`, importing `_tokenise`, `_first_paragraph` and `_title` read-only; every pair, integer threshold; `results/candidates.json` with every figure of FR-020, `candidate_pairs` and `true_pair_scores` one string per pair (O9), the verdict and the winner; `results/secondary.json` per FR-021 (both readings, counts only); `results/timing.json` (wall time per candidate, pages, pairs). Deterministic except `timing.json`; runs no git (FR-020, FR-021) | `eval/duplicates/candidates.py` | build | [ ] |
| 16 | | `tests/test_duplicates_eval.py` (EGOGE header): FR-022 in full on a synthetic corpus, labels and protocol in a temporary directory (each B1 rule alone; the threshold at one quarter, below it, empty sets; every bar edge; selection and the tie; scopes and repositories; the refusal writing nothing; an `eval/duplicates/` snapshot equal before and after; `--help`) (FR-022) | `tests/test_duplicates_eval.py` | build | [ ] |

**Checkpoint US5** — verify before continuing:
- [ ] `git status --porcelain` (this phase's changes) lists only `eval/duplicates/candidates.py` and `tests/test_duplicates_eval.py`; no file under `eval/duplicates/results/` exists yet
- [ ] `git log --format=%H <US4 commit>..HEAD` over the pinned files (FR-026's list) prints nothing
- [ ] `grep -n "shell=True\|subprocess" eval/duplicates/candidates.py` finds nothing
- [ ] `poetry run pytest -q tests/test_duplicates_eval.py tests/test_duplicates_frozen.py` passes
- [ ] Full gate green
- [ ] Milestone: the run pauses for the scoring run below

**At the pause after US5 — main session, not this phase's work (FR-023):**
- Run `python -m eval.duplicates.candidates` once (the main session or the owner). Commit `results/candidates.json`, `results/secondary.json` and `results/timing.json`, exactly as written, as their own commit.
- Add `approved-by:` and resume with `env -u CCT_REVIEW_DIFF_MAX_LINES`.

---

## US6: The report and the evidence PR (S3)

<!-- milestone -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 17 | | `eval/duplicates/report.md` per FR-024: the table per candidate; exactly one winner line (`Winner: B0`, `Winner: B1` or `Winner: none`) and the verdict; the true pairs' score distribution; the secondary re-score with both readings, no verdict; the limits stated plainly (extracted spec decisions; two repositories by one author; the families measured; decision pages only, so the other content page types are unmeasured and nothing across page types; B1's template-word drop unmeasured; recall a count out of n; cuts taken); numbers "as recorded"; no post-hoc section unless FR-026 applies (FR-024) | `eval/duplicates/report.md` | build | [ ] |
| 18 | | `tests/test_duplicates_results.py` (EGOGE header): the scorer's output equals the committed `candidates.json` and `secondary.json` byte for byte; `timing.json` keys present, values not compared; one winner line equal to the results' winner; secondary B0 as recorded equals the frozen issue 54 signal b counts; every `python -m eval.duplicates.…` line in the README and the report parses with its script's parser (FR-025) | `tests/test_duplicates_results.py` | build | [ ] |
| 19 | | The evidence PR's scope audit (FR-026), against the run-1 branch base: `git diff <base> --stat` lists only FR-026's allowed paths; `git diff <base> -- src/` empty; `git diff <base> -- CLAUDE.md` adds exactly FR-001's line; `git log --format=%H <base>..HEAD -- tests/test_duplicates_frozen.py` prints exactly US4's commit; `git log --format=%H <US4 commit>..HEAD -- eval/duplicates/corpus eval/duplicates/corpus.json eval/duplicates/labels.json eval/duplicates/protocol.json eval/duplicates/review-sample.json eval/duplicates/README.md` prints nothing; the commit that added `eval/duplicates/candidates.py` has US4's commit as an ancestor (`git merge-base --is-ancestor`). Any other path is removed before the milestone, or the run stops | — | build | [ ] |

**Checkpoint US6** — verify before continuing:
- [ ] Task 19's audit passes
- [ ] `poetry run python -m eval.duplicates.candidates --out-dir <tmp>` writes files equal to the committed `candidates.json` and `secondary.json`, and `git status --porcelain eval/` is clean afterwards
- [ ] The closing-keyword grep of US1's checkpoint still finds nothing
- [ ] Full gate green
- [ ] Milestone: run 1 ends here and is never resumed

**At the pause after US6 — main session and owner (FR-026; plan, owner steps 5-6):**
- Do not resume run 1 (a resume could reach the driver's own PR, which would name issue 121 for closure). If the driver opened a PR anyway, close it unmerged.
- Run `scripts/pre-pr-check.sh`; open the evidence PR by hand, its body naming issue 121 without a closing keyword; confirm `gh pr view <n> --json closingIssuesReferences` lists nothing; review, label after the review of its head, merge with a merge commit, never squash.
- A flaw found in review after the freeze goes into a non-binding `post_hoc` block computed by `candidates.py` and checked by `tests/test_duplicates_results.py`, plus a "Post hoc (not binding)" report section; no label, bar, verdict or winner line changes.
- The spec amendment: FR-027's winner (`B0`, `B1` or `none`), the triggers that fired, FR-035's time bound from `results/timing.json`, re-approval, and with a winner run 2's `automation.json`. With `none` the cycle ends (trigger 3) and issue 121 stays open.
- Run 2 waits for the owner's 0.11.0 release (tag and release page); no session acts toward it.

---

## US7: The winning rule in the package (S4)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 20 | | Read FR-027: the winner is the amended value; if it is `none`, or no 0.11.0 tag exists (`git tag --list '*0.11.0*'` prints nothing), stop and report: this phase does not run (FR-027) | — | build | [ ] |
| 21 | | `paths.py`: `ENV_DUPLICATE_CHECK = "WIKI_STUDIO_DUPLICATE_CHECK"` beside `ENV_GIT_CALL_LIMIT`; `WikiPaths.duplicate_check: bool = True` with its docstring entry; `for_root` and `resolve` taking `duplicate_check: bool | None = None`; `resolve` reading the variable per FR-030 (unset or empty on; `off`/`on` in any case after stripping; else `ValueError`) (FR-030) | `src/wiki_studio/paths.py` | build | [ ] |
| 22 | | `src/wiki_studio/duplicates.py` (EGOGE header; standard library only; no forbidden layout string): `first_paragraph` reimplementing eval's `_body`, `_decision_section` and `_first_paragraph`; the title from `yaml_lite.parse_frontmatter`; `page_tokens` with `_tokenise` imported unchanged (and, for B1, FR-018's normalisation as named constants equal to `protocol.json`'s); `similar` with `4 * shared >= union > 0`; the related-line parser (`RELATED_MARKER`, `RELATED_MARKER_RE`, `related_targets`) reusing `conflicts.py`'s `_body_lines`, `_marker_target`, `_resolve_target` and the prose fence rules; `conflicts.py`'s "only importer" docstring sentence updated, no other line. `CLAUDE.md` Layout gains `src/wiki_studio/duplicates.py   the possible-duplicate rule (title and first paragraph, the measured winner) and the related-line parser; reads only` after the `revisions.py` line (FR-028, FR-029) | `src/wiki_studio/duplicates.py`, `src/wiki_studio/conflicts.py`, `CLAUDE.md` | build | [ ] |
| 23 | | `tests/test_duplicates_rule.py` (EGOGE header): FR-031 in full: the replay over the frozen corpus equal to the winner's `candidate_pairs`; `first_paragraph` and tokens equal eval's on every corpus page and every `eval/patterns/wiki/` page; B1 constants equal `protocol.json` (if B1 won); the parser cases; the switch cases (FR-031) | `tests/test_duplicates_rule.py` | build | [ ] |

**Checkpoint US7** — verify before continuing:
- [ ] `git diff <run-2 base> -- src/wiki_studio/findings.py src/wiki_studio/wiki_state.py src/wiki_studio/health_lint.py src/wiki_studio/lint.py eval` is empty
- [ ] `git diff <run-2 base> -- src/wiki_studio/conflicts.py` changes one docstring sentence only
- [ ] `poetry run pytest -q tests/test_duplicates_rule.py tests/test_package_boundaries.py tests/test_conflict_callouts.py` passes
- [ ] Full gate green

---

## US8: The possible-duplicate kind (S4)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 24 | | `duplicates.duplicate_pairs(paths)`: the whole default review set through `read_live_page`; the five page types of FR-032 only, superseded pages skipped, same type only; pairs joined by a conflict callout either way (`scan_callouts`) or a related line either way skipped; one `DuplicatePair` per remaining similar pair with its related line (second page's title without brackets, else its stem; link by `posixpath.relpath` from the first page's directory). `findings.py`: `KIND_POSSIBLE_DUPLICATE` appended last to `FINDING_KINDS`; when `paths.duplicate_check` is on, one warning per pair through the same scope rule as the conflict loop, the description per FR-032 ending with the exact line; when off, never called. `api.findings`' signature unchanged (FR-032, FR-033) | `src/wiki_studio/duplicates.py`, `src/wiki_studio/findings.py` | build | [ ] |
| 25 | | Surfaces: `findings.py`'s module docstring, `cli.py`'s `findings` description and `api.findings`' docstring name the kind, what it compares and the switch (FR-034) | `src/wiki_studio/findings.py`, `src/wiki_studio/cli.py`, `src/wiki_studio/api.py` | build | [ ] |
| 26 | | `tests/test_possible_duplicate.py` (EGOGE header): FR-035 in full (the line round-trip on either page; brackets in a title; concept and workflow pairs compared, concept-decision and glossary not; superseded skipped; open and one-sided conflict pairs skipped and reported once as conflicts; a dangling related line; scope; the switch off with a spy; strict lint unchanged; review state, `approve`, `find` unchanged; nightly lists and drafts nothing; MCP carries it, gated on the extra; snapshot equal; the 500-page bound recomputed from `results/timing.json`). Existing tests edited only as FR-035 lists: `tests/test_findings.py`'s fixture produces exactly one `possible-duplicate`; any test whose fixture now yields the kind expects it, never by switching it off (FR-035) | `tests/test_possible_duplicate.py`, `tests/test_findings.py`, other tests as FR-035 requires | build | [ ] |
| 27 | [P] | `CHANGELOG.md` `[Unreleased]` **Added**: `possible-duplicate`, the `> [!related]` line and `WIKI_STUDIO_DUPLICATE_CHECK=off`, with the measured-only sentence (decision pages only; concept, workflow, incident and playbook pages compared by the same rule, false-alarm rate unmeasured); no closing keyword; no version section (FR-034, FR-040) | `CHANGELOG.md` | build | [ ] |

**Checkpoint US8** — verify before continuing:
- [ ] `git diff <run-2 base> -- src/wiki_studio/health_lint.py src/wiki_studio/lint.py src/wiki_studio/review.py src/wiki_studio/discovery.py src/wiki_studio/promoter.py src/wiki_studio/wiki_state.py src/wiki_studio/nightly.py src/wiki_studio/mcp_adapter` is empty
- [ ] `grep -n "FINDINGS_FORMAT_VERSION = 1" src/wiki_studio/contract.py` still matches; `tests/test_info_contract.py` passes unedited
- [ ] On a temporary wiki with two similar decision pages, `poetry run wiki-studio findings --json` reports one `possible-duplicate`; with `WIKI_STUDIO_DUPLICATE_CHECK=off` it reports zero; the description's last line pasted into the first page makes it zero; `poetry run wiki-studio lint --health --strict` exits as before
- [ ] Full gate green

---

## US9: ADR-0006, the contract and the documents (S5)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 28 | | `docs/adr/0006-related-line.md`: the optional `> [!related]` body line `findings` reads (FR-029's rule), no frontmatter key, page type or schema version change, memkernel's bridge carrying the body; `not_duplicate_of:` weighed and refused (FR-036) | `docs/adr/0006-related-line.md` | build | [ ] |
| 29 | | Packaged `citation-rules.md`: a short section after "When sources disagree" on marking two pages deliberately separate. `docs/knowledge-contract.md` Findings: the kind's row and a subsection (what is compared, skips, the last line, the switch, what was measured: decision pages only, the other four types unmeasured). README: the `findings` section names the kind; the environment table gains `WIKI_STUDIO_DUPLICATE_CHECK`. `docs/patterns.md`: the three actions on a flag and the measured-only sentence (FR-037) | `src/wiki_studio/schema/citation-rules.md`, `docs/knowledge-contract.md`, `README.md`, `docs/patterns.md` | build | [ ] |
| 30 | [P] | `CHANGELOG.md` `[Unreleased]`: **Changed** the packaged `citation-rules.md` section; **Docs** ADR-0006 and `docs/patterns.md`. Every command a changed page shows gets its check (FR-038) | `CHANGELOG.md` | build | [ ] |
| 31 | | Invariant audit (FR-039, FR-040): the untouched-files `git diff` of FR-039 is empty (including `pyproject.toml`, `src/wiki_studio/__init__.py`, `eval` and `docs/compatibility.md`); `git diff <base> --stat -- src/` lists only FR-039's files; `FINDINGS_FORMAT_VERSION`, `SCHEMA_VERSION`, `CAPABILITIES`, `FORMATS` unchanged; `FINDING_KINDS` is the 0.11.0 tuple plus `possible-duplicate` last; exit codes unchanged (`tests/test_cli_contract.py`); no runtime dependency; the closing-keyword `git grep` of FR-039 finds nothing; no version bump, no CHANGELOG version section, no tag | — | build | [ ] |

**Checkpoint US9** — verify before continuing:
- [ ] `poetry run wiki-studio --help` and `poetry run wiki-studio findings --help` succeed and the `findings` help names the kind
- [ ] `poetry run pytest -q tests/test_schema_fingerprint.py tests/test_frozen_runs.py tests/test_quickstart.py` passes
- [ ] `poetry run wiki-studio --version` still prints 0.11.0; `docs/compatibility.md` unchanged
- [ ] Full gate green

---

## Final Verification

- [ ] Type checker: 0 errors; linter and formatter: 0 errors on `src/ tests/ eval/ conformance/ examples/`
- [ ] Full suite green with coverage at or above 92 percent; the git-gated tests ran in CI
- [ ] Every committed data file under `eval/duplicates/` was produced by a main-session script run at a pause, each its own commit, and is reproduced (results) or pinned (corpus, labels, sample) by CI
- [ ] The evidence PR has one commit per phase and per main-session step, merged with a merge commit, never squashed, no change under `src/`, no closing keyword, opened by hand
- [ ] The corpus rule landed before any page; the labels before the freeze, made without candidate code and reviewed by the owner; nothing pinned changed after US4
- [ ] `possible-duplicate` ships only with a winner and after the 0.11.0 release; it reproduces the winner's pairs on the frozen corpus; every place that documents it says only decision pages were measured
- [ ] No new exit code, frontmatter key, page type, capability, MCP tool or dependency; `findings_version` 1; `_tokenise` unchanged; `lint --health --strict` unchanged
- [ ] No version bump, CHANGELOG version section, tag or release from any run; release preparation only on the owner's word
- [ ] The build PR's body carries the closing line from `pr.closes: [121]` only when the kind ships; the session closed no issue
