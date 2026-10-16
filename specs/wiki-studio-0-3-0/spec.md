---
spec_mode: full
feature_id: wiki-studio-0-3-0
risk_category: feature
status: approved
date: 2026-10-15
---

# Spec: wiki-studio 0.3.0 — navigation evidence (layer 1)

<!-- Project constitution: shared/skills/ — copilot-conventions, coding-standards, safety -->

Design references (read before building): `CLAUDE.md`; memkernel issue
[#17](https://github.com/gosha70/memkernel/issues/17) (the request for
agent-level evidence this feature mirrors for the wiki) and memkernel's
`specs/memkernel-0-5/spec.md` Track B (FR-011 to FR-018: the
`agent-memory-bench` adapter, preregistration, no judge); in this repository
`src/wiki_studio/querier.py` (`_select_query_candidates`: index-first page
selection by token overlap of the question with each index-linked page's slug,
path and first 400 characters, pages with zero overlap dropped, stable
tie-break by index order, `DEFAULT_MAX_QUERY_PAGES = 5`, no model call in
selection), `src/wiki_studio/api.py` (`ingest`, `query`), `src/wiki_studio/paths.py`
(defaults `knowledge/wiki` and `doc_internal/proposals` under the root unless
`WIKI_STUDIO_WIKI_DIR` / `WIKI_STUDIO_PROPOSALS_DIR` are set).

## Why

The README describes the wiki as cheaper to consult than raw sources
(index-first navigation, cited answers) but publishes no number. Issue #17
asked memkernel for execution-graded, preregistered, judge-free evidence with
a negative control; the same standard applies here. This release ships
**layer 1**: deterministic component metrics for the one part of `query`
that runs without a model, measured against a grep baseline, on a frozen
corpus and a wiki the tool itself produced. Agent-level evidence (**layer 2**,
an arm in `agent-memory-bench`) is tracked separately and depends on
memkernel's adapter run.

## User Scenarios

### US1: A frozen corpus and a wiki the tool produced from it (Priority: HIGH)

**Given** memkernel's documentation at tag `v0.4.0` as the raw corpus
**When** the maintainer runs `wiki-studio ingest` once per source document through the normal gate and commits the result
**Then** `eval/navigation/` holds the pinned sources, the frozen wiki, and a manifest recording the corpus commit, the backend, the model, the date and the per-document ingest cost the backend exposes; NOTICE attributes memkernel; CI never regenerates the wiki

### US2: A preregistered question set with gold assigned after freezing (Priority: HIGH)

**Given** the corpus, before any ingest has run
**When** the maintainer writes the question set from the sources and commits it
**Then** the questions are committed in a commit that precedes the frozen wiki, include questions whose answer is not in the corpus and questions where two pages compete, are not edited afterwards, and each question's gold page is assigned by reading the frozen wiki; questions with no gold page count toward ingest coverage, not the hit rate

### US3: Three numbers, each meaning one thing, reproduced in CI (Priority: HIGH)

**Given** the frozen fixture and the question set
**When** `python -m eval.navigation` runs (stdlib only, no model)
**Then** it reports ingest coverage, navigation hit rate at 1 and at `max_pages`, and words loaded by `query`'s page selection against the written-down grep rule over the raw sources; CI asserts the output equals the committed `results.json`, and the README states the numbers as component metrics specific to a vocabulary-aligned corpus

### US4: The gate measured by mutation, if it earns its place (Priority: LOW, may be dropped)

**Given** the archived patch-sets ingest produced for the frozen wiki
**When** mutation operators derive known-bad variants and the originals are replayed
**Then** the suite reports false accepts on mutants and false rejects on originals; if this cannot be built as a generated corpus, it is left out rather than hand-written

### US5: A clean second measurement gates the release (Priority: HIGH, amendment of 2026-10-16)

**Given** run 1 (measured on 0.2.0, one document in ten promoted, logs and wall time contaminated by a Stop hook) and the issue #11 fix merged
**When** the owner runs the one-time ingest again under a revised, recorded protocol: same frozen questions and corpus, a separate fixture directory, Claude hooks isolated from the backend and that isolation verified by a probe before any attempt is consumed, model and settings pinned, the one-attempt rule unchanged
**Then** run 2 is a completed, reproducible measurement published next to run 1 with both runs' denominators and caveats, run 1 is unchanged, and 0.3.0 is released only after that; the gate is the completed measurement, not any score

## Requirements

- **FR-001 (corpus)**: `eval/navigation/corpus/` MUST contain `README.md` and every `docs/**/*.md` of `gosha70/memkernel` at tag `v0.4.0`, copied verbatim with paths preserved; `eval/navigation/manifest.json` MUST record `corpus_repo`, `corpus_tag`, `corpus_commit` (the tag's commit SHA) and `corpus_files` (path and sha256 each). `NOTICE` MUST gain an entry naming memkernel, its Apache-2.0 licence and the copied paths. `v0.4.0` is the latest tag; no earlier tag predates the wiki bridge (every tag from `v0.2.0` carries ADR-008 and the same nine docs, all mentioning the wiki), so no choice of tag avoids the vocabulary alignment. A later feature may add a second, unrelated corpus; this one is reported as vocabulary-aligned (FR-010).
- **FR-002 (question set first)**: `eval/navigation/questions.json` MUST be written from the corpus and committed before the ingest of FR-003 runs, in two commits because a commit cannot contain its own hash: the first adds the question file together with its sha256 as `questions_sha256` in the manifest (a file checksum does not depend on the commit); the second, made before any ingest, records that first commit's hash as `questions_commit`. The frozen wiki's commit MUST be a descendant of `questions_commit`, and the file's checksum MUST still equal `questions_sha256`. Each entry has `id`, `question`, `kind` (`single`: one page should answer it; `competing`: two or more pages plausibly answer it, the gold is the one containing the answer; `absent`: the corpus does not answer it) and `source` (corpus path and heading the question was written from; `null` for `absent`). At least 30 questions, at least 5 `competing`, at least 5 `absent`. The file is never edited after that commit; corrections go in a new file with a new commit noted in the manifest.
- **FR-003 (frozen wiki)**: `eval/navigation/wiki/` MUST be produced by `wiki-studio ingest <doc> --backend <copilot-cli>` followed by `wiki-studio promote <proposal-dir>` for every corpus document, in corpus order, into an initially empty wiki (`index.md`, `log.md`, packaged schema), with all three locations set explicitly: `WIKI_STUDIO_ROOT=eval/navigation`, `WIKI_STUDIO_WIKI_DIR=eval/navigation/wiki`, `WIKI_STUDIO_PROPOSALS_DIR=eval/navigation/proposals` (the root alone would place the wiki under `knowledge/wiki` and the proposals under `doc_internal/proposals`, the path module's defaults). Promoted proposals therefore end up under `eval/navigation/proposals/.applied/<name>/` and the audit copies under `eval/navigation/wiki/.audit/proposals/<name>/`. **One attempt per document**: each document is ingested exactly once and its proposal promoted exactly once; no proposal, preview or wiki page is edited by hand, no document is re-run, and no backend setting changes between documents. The single exception is a failure before the backend returned anything (exit 2 backend not found, exit 3 backend failed with no proposal directory written: a network error, an expired login): such a failure cannot shape the wiki because no content was seen, so one retry is allowed and the manifest records it (`attempts: 2`, `transport_error` with the first attempt's exit code and stderr line); a second such failure stays recorded and the document counts as missing coverage. A run that produced a proposal, however bad, is never retried. A gate reject (empty patch-set) or a promote failure is recorded in the manifest as that document's `disposition` and `promote_error`, the document's questions then count as missing coverage (FR-004), and the run continues with the next document. The manifest MUST record `backend`, `model` (as the CLI reports it or as configured), `ingest_date`, `wiki_studio_version`, and per document: `attempts` (1 or 2), `transport_error` (`null` unless a retry happened), `proposal_dir`, `disposition`, `promote_error` (`null` on success), `pages_written`, `wall_seconds`, and `tokens_in`/`tokens_out` when the backend exposes them (`null` otherwise). The wiki, its `.audit/` tree and `eval/navigation/proposals/` (including `.applied/` and any rejected proposal) are committed; CI MUST NOT run ingest. The structural lint of the frozen wiki MUST pass as produced; if it does not, that is a finding recorded in the manifest and the README, not something to repair.
- **FR-004 (gold after freezing)**: `eval/navigation/gold.json` MUST hold, per question id, `gold` (the one wiki-relative page that contains the answer, assigned by reading the frozen wiki; `null` when no page contains it, and always `null` for `absent`), `reason` (the heading or a quoted sentence of that page that answers the question; for `null`, which pages were checked and why none answers), and for `competing` questions `distractors` (the other pages that plausibly answer it). Every assignment therefore carries a written reason a reviewer can check against the frozen tree. `ingest_coverage` = |non-`absent` questions with a gold page| / |non-`absent` questions|. Questions with `null` gold are excluded from the hit rates. Two edge cases: a gold page that `index.md` does not link is unreachable by the querier and counts as a miss at 1 and at max (reported separately as `gold_unreachable`, a fact about the ingested index, not excluded); a question whose answer is found only in `index.md` gets `gold: "index.md"`, is excluded from the hit rates because the index is always loaded, and is reported as `answered_by_index`.
- **FR-005 (navigation metric)**: `eval/navigation/run.py` (stdlib only) MUST call `wiki_studio.querier._select_query_candidates` (a private function; this is a deliberate dependency, and the determinism test of FR-007 is what exposes a rename or signature change) with the frozen wiki and `max_pages = 5` (the querier default, fixed here) and report, over questions with gold, `hit_at_1` (gold is the first selected page) and `hit_at_max` (gold is among the selected pages); the same two rules apply to `competing` questions (gold is the single page containing the answer; a distractor ranked first is a miss at 1), plus `distractor_outranks` (share of competing questions where any distractor is ranked above gold). For `absent` questions the selection is empty exactly when no index-linked page shares a token with the question, because the querier drops zero-overlap pages; report `absent_empty` (share with an empty selection) and `absent_pages_loaded` (mean pages selected), the latter being the navigation cost of a question the wiki cannot answer. Selection is deterministic; no backend is invoked.
- **FR-006 (words loaded)**: One function `count_words(text) = len(text.split())` is the unit for every count in this feature. For every question with gold, `wiki_words` = `count_words` of `index.md` plus the selected pages (what `query` would put in the prompt). `grep_words` = `count_words` of the grep rule's output over the corpus: lower-case the question and split it into words with the querier's own token pattern `[a-z0-9][a-z0-9-]*` (`wiki_state._TOKEN_RE`; so `export?` yields `export` and `page_type` yields `page` and `type`, exactly as the querier sees it), drop words in the committed stop list `eval/navigation/stopwords.txt` (a verbatim copy of the querier's `wiki_state._STOPWORDS`, so both sides drop the same common words, recorded as such in the manifest and fixed no later than the question set) and words shorter than 3 characters, run a case-insensitive whole-word match (`\b<word>\b`) of each remaining word over every corpus file, take every matching line with 2 lines of context before and after, merge overlapping ranges per file, concatenate. The rule is implemented in the script, not shelled out, and stated verbatim in the README. Questions whose grep output is empty (`grep_words == 0`) are reported by id as `grep_empty` and excluded from the ratio; over the rest report the median and mean of `wiki_words / grep_words` and both totals.
- **FR-007 (determinism gate)**: `eval/navigation/results.json` holds the script's output; `tests/test_navigation_eval.py` runs the script over the committed fixture and asserts equality with `results.json`. A change to the querier's selection that moves any number MUST update `results.json` in the same commit, which makes the change visible in review.
- **FR-008 (ingest cost)**: The README reports ingest cost per source document (primary) and amortised over the question set (secondary), from the manifest, in the units the backend exposed; when tokens were not exposed, wall time is reported and tokens are stated as unavailable.
- **FR-009 (mutation gate suite, conditional)**: If built, `eval/gate/mutate.py` derives from each archived patch-set under `eval/navigation/wiki/.audit/proposals/` one variant per operator (`drop-required-key`, `wrong-directory`, `slug-mismatch`, `empty-sources`, `broken-link`, `duplicate-create`, `path-escape`, `missing-update-target`) and reports `false_accepts` (variants `propose`+`promote --dry-run` accept) and `false_rejects` (originals replayed against the pre-promotion wiki state that are rejected); results are committed and asserted like FR-007. If the operators cannot be applied generically, US4 is dropped and the CHANGELOG says so.
- **FR-010 (README evidence section)**: `README.md` MUST gain an "Evidence" section stating the three numbers with their definitions, the unit stated next to them as whitespace-separated words (never "tokens", which would invite comparison with model tokens), labelled component metrics (not agent-level), noting the corpus is vocabulary-aligned with the wiki schema (memkernel's docs use "page", "wiki", "ingest", "export"), linking the mirror issue for layer 2, and making no claim about agent cost or quality. `CHANGELOG.md` gets `[0.3.0]`; version `0.3.0` in `pyproject.toml`, `__init__.py` and the version test.
- **FR-011 (hygiene)**: No runtime dependency; `eval/` is excluded from the wheel and from coverage; the script and tests carry the licence header; nothing under `eval/` reads this repository's own tree except the committed fixture.
- **FR-012 (ingest help text)**: The `ingest` verb's help in `cli.py` still says "Phase 0: requires --legacy-single-source … multi-page ingest lands in Phase 1" and calls the legacy flag required; multi-page ingest has been the default since 0.1.0 and the build runs that exact command. The two help strings MUST say that multi-page is the default and the flag selects the v1 single-source generator. Help text only; no flag, verb or exit code changes, and the CLI contract tests stay green.
- **FR-013 (run 2 fixture)**: `eval/navigation/run2/` MUST hold its own `wiki/`, `proposals/`, `manifest.json`, `gold.json`, `results.json`, `ingest-logs/` and `ingest-notes.md`. The corpus, `questions.json` and `stopwords.txt` are run 1's files in `eval/navigation/`, used in place and not copied; run 2's manifest MUST record their sha256 and a test MUST assert they equal run 1's manifest values. No file of run 1 changes.
- **FR-014 (hook isolation, verified before any attempt)**: The backend subprocess MUST be isolated from Claude Code user hooks by a recorded method (a dedicated `CLAUDE_CONFIG_DIR` whose settings define no hooks, or an opt-out variable the hook honours), and the isolation MUST be verified by a probe before the first ingest: one `claude -p` call with the run's exact environment and a trivial prompt, after which run 2's audit log, query log and proposals directory are byte-identical to before (or still absent) and no test-suite process was started. The probe's command, environment, output and verdict are recorded in the manifest as `isolation_probe`. A failed probe consumes no attempt: fix the isolation and probe again; only a passed probe may be followed by ingest.
- **FR-015 (pinned run)**: Run 2's manifest MUST record the wiki-studio commit the ingest ran from (a descendant of the issue #11 fix's merge commit) and version, the Claude Code version, the model (`ANTHROPIC_MODEL` set to a concrete model identifier when the CLI accepts one; otherwise the alias plus whatever the CLI reports), the backend timeout, every `WIKI_STUDIO_*` value and the command, all fixed before the first attempt and unchanged after it. FR-003's one-attempt rule applies unchanged, including its single retry for a failure that produced nothing. Document order and command are those of run 1 except the paths and one added flag: because run 2's root is `eval/navigation/run2/` while the shared corpus stays in `eval/navigation/corpus/`, every source lies outside the root and `ingest` would refuse it (`PathOutsideRootError`, exit 7) before calling the backend, so the pinned command carries `--allow-out-of-repo`; the manifest records the flag, and the audit records consequently carry `source_repo_relative: false` with the source path as given. The root stays inside `run2/` so the query log and audit log are run 2's own.
- **FR-016 (both runs published)**: `run.py` MUST accept `--shared <dir>` for the corpus, question set and stop list when the fixture directory lacks them; run 2's `results.json` is committed and asserted by the determinism test alongside run 1's. The README Evidence table MUST show run 1 and run 2 side by side with each run's denominators (answerable questions, questions with gold, questions in the ratio) and caveats; run 1's column and text are unchanged. The release gate is a completed, reproducible run 2 (manifest complete with a passed probe, one attempt per document, determinism test green), not any particular value.

## Constraints / What NOT to Build

- No LLM-as-judge, no rubric, no answer-quality score: the answer text needs a model and is out of layer 1.
- No benchmark runner, event schema or statistics code: layer 2 reuses `agent-memory-bench` at a pinned commit.
- No change to the querier's selection heuristic in this feature; the eval measures what 0.2.0 ships. Improvements come later with their effect visible through FR-007.
- No regeneration of the wiki in CI, no model call in CI.
- No efficiency claim in the README beyond the three component numbers and their caveats.
- No second corpus in this release; the vocabulary-alignment caveat is stated instead.
- Run 2 does not replace run 1 and is not rerun for a better score: one protocol, one run, published as it comes out. No change to code, prompt, settings or questions between the isolation probe and the last document.

## Key Entities

- **Corpus**: memkernel's documentation at `v0.4.0`, verbatim, attributed.
- **Frozen wiki**: the tree `ingest` and `promote` produced once from the corpus, with its audit trail.
- **Question set**: preregistered questions (`single`, `competing`, `absent`) written from the corpus before ingest.
- **Gold**: the frozen page containing a question's answer, assigned after freezing.
- **Grep rule**: the written-down deterministic baseline for "what an agent with grep would read".

## Success Criteria

1. `git log` shows `questions.json` committed before the frozen wiki; the manifest's `questions_commit` names the commit that added the file, is an ancestor of the wiki's commit, and the file's sha256 equals `questions_sha256`.
2. `python -m eval.navigation.run` prints ingest coverage, hit@1, hit@5, distractor-outranks, absent-empty, absent-pages-loaded, gold-unreachable, answered-by-index, grep-empty and the word ratio, equal to `results.json`; the test passes in CI on 3.11–3.13 with no network.
3. Every entry of `gold.json` has a non-empty `reason`, and a reviewer can confirm each `gold` against the frozen page it names.
4. The manifest lists every corpus document exactly once with `attempts` 1, or 2 only with a recorded `transport_error`, and the frozen wiki lints clean as produced (or the lint findings are recorded, unrepaired).
5. The README Evidence section states the numbers in words, the grep rule verbatim, the corpus caveat and the layer 2 link, and nothing else about efficiency.
6. NOTICE attributes memkernel; the wheel does not contain `eval/`.
7. Gate: ruff, format, mypy, coverage ≥ 80 percent (with `eval/` excluded) green.
8. Run 2: `eval/navigation/run2/manifest.json` records a passed `isolation_probe` dated before the first attempt, exactly one attempt per document (or two with a `transport_error`), a wiki-studio commit that descends from the #11 fix's merge, and the model and settings; run 1's files are byte-identical to their state before run 2.
9. `python -m eval.navigation.run eval/navigation/run2 --shared eval/navigation` reproduces run 2's `results.json`; the README shows both runs with their denominators and caveats; the tag is cut only after that.
