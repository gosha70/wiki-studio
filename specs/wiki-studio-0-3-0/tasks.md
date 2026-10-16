# Tasks: wiki-studio 0.3.0 — navigation evidence (layer 1)

<!-- One `## US<n>:` group = one auto-build phase. [US#] tags trace to spec.md. -->
<!-- Run per phase: poetry run ruff check src/ tests/ eval/ && poetry run ruff format --check src/ tests/ eval/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=80 -->
<!-- US1 task 3 runs a model once, outside CI, by the maintainer; every other task is model-free. -->

## US1: Corpus, question set, frozen wiki

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 1 | | Copy `README.md` and `docs/**/*.md` from memkernel `v0.4.0` verbatim; write `manifest.json` (`corpus_repo`, `corpus_tag`, `corpus_commit`, `corpus_files` with sha256); NOTICE entry; `stopwords.txt` generated verbatim from the querier's `_STOPWORDS` with its sha256 in the manifest (FR-001, FR-006) | `eval/navigation/corpus/**`, `eval/navigation/manifest.json`, `eval/navigation/stopwords.txt`, `NOTICE` | build | [x] |
| 2 | | Write `questions.json` (≥ 30; ≥ 5 `competing`; ≥ 5 `absent`; `source` path+heading) from the pinned corpus. **Two commits, before any ingest:** (a) the question file plus its sha256 as `questions_sha256` in the manifest, nothing else; (b) that commit's hash as `questions_commit` in the manifest (a commit cannot contain its own hash) (FR-002). The stop list is already frozen by task 1 and is not edited. | `eval/navigation/questions.json`, `eval/navigation/manifest.json` | owner | [x] |
| 3 | | One-time ingest with `WIKI_STUDIO_ROOT=eval/navigation WIKI_STUDIO_WIKI_DIR=eval/navigation/wiki WIKI_STUDIO_PROPOSALS_DIR=eval/navigation/proposals`: empty wiki (index, log, packaged schema), then per corpus file in order `wiki-studio ingest <file> --backend claude` + `wiki-studio promote <proposal-dir>`, **one attempt each (one retry only when the backend returned nothing, recorded as `attempts`/`transport_error`), nothing edited by hand, rejections and promote errors recorded and left as they are**; record backend, model, date, version and per-document cost in the manifest; commit `wiki/` (with `.audit/`) and `proposals/` (with `.applied/`) (FR-003) | `eval/navigation/wiki/**`, `eval/navigation/proposals/**`, `eval/navigation/manifest.json` | owner | [x] |

**Checkpoint US1** — verify before continuing:
- [x] `git merge-base --is-ancestor <questions_commit> HEAD` succeeds and `questions.json` is unchanged since it
- [x] `wiki-studio lint --root eval/navigation --wiki-dir eval/navigation/wiki` exits 0 on the frozen wiki as produced; if not, the findings are recorded in the manifest, not repaired
- [x] the manifest lists every corpus document exactly once
- [x] NOTICE names memkernel and the copied paths

Run finding: all ten documents were attempted once; one promoted, eight failed
path validation, and one timed out. Claude's inherited Stop hook ran tests
with the evaluation paths, contaminating the audit/query logs. All output is
preserved; the manifest marks the fixture `requires_review`. US1 execution is
complete. The owner approved proceeding with layer-1 metrics on this baseline
while retaining `requires_review` and its caveats; gold assignment is now
complete. See `eval/navigation/ingest-notes.md` before publication.

---

## US2 + US3: Gold, metrics, determinism test, README

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 4 | | Assign `gold.json` by reading the frozen wiki: `gold` (page containing the answer, `null` otherwise; `absent` → `null`), `reason` (heading or quoted sentence; for `null`, pages checked), `distractors` for `competing` (FR-004) | `eval/navigation/gold.json` | owner | [x] |
| 5 | | `run.py` (stdlib): load fixture; one `count_words` for every count; call `querier._select_query_candidates` with `max_pages=5`; compute `ingest_coverage`, `hit_at_1`, `hit_at_max`, `distractor_outranks`, `absent_empty`, `absent_pages_loaded`, `gold_unreachable`, `answered_by_index`, `wiki_words`, `grep_words` per the grep rule (question split by `[a-z0-9][a-z0-9-]*`, stop list, ≥ 3 chars, `\b` whole-word case-insensitive, 2 lines context, merged ranges), `grep_empty` ids excluded from the ratio, medians/means/totals; write JSON to stdout (FR-005, FR-006) | `eval/navigation/run.py`, `eval/navigation/__init__.py` | build | [x] |
| 6 | | Commit `results.json`; test asserts `run.py` output equals it; test that `questions.json` sha256 matches the manifest; exclude `eval/` from wheel (`pyproject` `exclude`) and from coverage (FR-007, FR-011) | `eval/navigation/results.json`, `tests/test_navigation_eval.py`, `pyproject.toml` | build | [x] |
| 7a | [P] | Fix the `ingest` help strings in `cli.py` (multi-page is the default; `--legacy-single-source` selects the v1 generator); help text only, CLI contract tests green (FR-012) | `src/wiki_studio/cli.py` | build | [x] |
| 7 | [P] | README "Evidence" section: the three numbers with definitions, grep rule verbatim, component-metric and vocabulary-alignment caveats, ingest cost per document and amortised, link to the layer 2 issue; CHANGELOG `[0.3.0]`; version 0.3.0 (FR-008, FR-010) | `README.md`, `CHANGELOG.md`, `pyproject.toml`, `src/wiki_studio/__init__.py`, `tests/test_cli_contract.py` | build | [x] |

**Checkpoint US2+US3** — verify before continuing:
- [ ] `poetry run python -m eval.navigation.run` output equals `results.json`; test green on 3.11–3.13
- [ ] `unzip -l dist/*.whl | grep eval/` matches nothing
- [ ] README states only the three numbers and their caveats

---

## US4: Mutation gate suite (conditional)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 8 | | `mutate.py`: for each archived patch-set, one variant per operator (drop-required-key, wrong-directory, slug-mismatch, empty-sources, broken-link, duplicate-create, path-escape, missing-update-target); replay originals against the pre-promotion state; report `false_accepts`, `false_rejects`; commit results; determinism test. **Drop US4 and say so in the CHANGELOG if the operators cannot be applied generically** (FR-009) | `eval/gate/mutate.py`, `eval/gate/results.json`, `tests/test_gate_eval.py` | build | [ ] |

---

## US5: Run 2 under the revised protocol (release gate)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 9 | | `run.py --shared <dir>`: corpus, questions and stop list from `<dir>` when the fixture lacks them; determinism and fixture tests parametrized over `eval/navigation` (run 1) and `eval/navigation/run2`; a test asserts run 2's manifest records the shared files' sha256 equal to run 1's (FR-013, FR-016) | `eval/navigation/run.py`, `tests/test_navigation_eval.py` | build | [x] |
| 10 | | Isolate hooks from the backend (recorded method), then the probe: one `claude -p` call with the run's environment, a trivial prompt, before/after byte comparison of run 2's logs and proposals dir, record `isolation_probe` in `run2/manifest.json`; repeat until it passes, consuming no attempt (FR-014) | `eval/navigation/run2/manifest.json` | owner | [ ] |
| 11 | | Pin and record commit (descendant of the #11 merge), versions, model, timeout, `WIKI_STUDIO_*` values and command; then the one-time ingest in run 1's order with `WIKI_STUDIO_ROOT=eval/navigation/run2 WIKI_STUDIO_WIKI_DIR=eval/navigation/run2/wiki WIKI_STUDIO_PROPOSALS_DIR=eval/navigation/run2/proposals` and the command `python -m wiki_studio ingest eval/navigation/corpus/<file> --backend claude --allow-out-of-repo` (the sources lie outside run 2's root; without the flag `ingest` exits 7 before any backend call), one attempt per document (FR-003 retry rule unchanged), nothing edited; commit `run2/wiki`, `run2/proposals`, `run2/ingest-logs`, `run2/ingest-notes.md`, manifest (FR-015) | `eval/navigation/run2/**` | owner | [ ] |
| 12 | | Assign `run2/gold.json` by reading the frozen run 2 wiki, a reason per entry; questions unchanged (FR-004) | `eval/navigation/run2/gold.json` | owner | [ ] |
| 13 | | Commit `run2/results.json`; README Evidence table with run 1 and run 2 side by side, denominators and caveats per run, run 1 text unchanged; CHANGELOG note (FR-016) | `eval/navigation/run2/results.json`, `README.md`, `CHANGELOG.md` | build | [ ] |

**Checkpoint US5** — verify before the tag:
- [ ] `run2/manifest.json`: `isolation_probe.passed` true and dated before the first attempt; one entry per document
- [ ] `git diff --stat <before-run-2>..HEAD -- eval/navigation/corpus eval/navigation/questions.json eval/navigation/stopwords.txt eval/navigation/wiki eval/navigation/gold.json eval/navigation/results.json` is empty
- [ ] determinism test green for both runs; README shows both

## Final Verification

- [ ] Type checker: 0 errors; linter: 0 errors; coverage ≥ 80 percent with `eval/` excluded
- [ ] No model call anywhere in CI (`grep -rn "backend" tests/test_navigation_eval.py` shows none)
- [ ] `questions.json` unchanged since `questions_commit`
- [ ] README makes no claim beyond the three component numbers
