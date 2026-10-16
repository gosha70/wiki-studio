# Tasks: wiki-studio 0.3.0 — navigation evidence (layer 1)

<!-- One `## US<n>:` group = one auto-build phase. [US#] tags trace to spec.md. -->
<!-- Run per phase: poetry run ruff check src/ tests/ eval/ && poetry run ruff format --check src/ tests/ eval/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=80 -->
<!-- US1 task 3 runs a model once, outside CI, by the maintainer; every other task is model-free. -->

## US1: Corpus, question set, frozen wiki

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 1 | | Copy `README.md` and `docs/**/*.md` from memkernel `v0.4.0` verbatim; write `manifest.json` (`corpus_repo`, `corpus_tag`, `corpus_commit`, `corpus_files` with sha256); NOTICE entry (FR-001) | `eval/navigation/corpus/**`, `eval/navigation/manifest.json`, `NOTICE` | build | [ ] |
| 2 | | Write `questions.json` (≥ 30; ≥ 5 `competing`; ≥ 5 `absent`; `source` path+heading) from the corpus and `stopwords.txt`; **commit these alone** and record `questions_commit` in the manifest (FR-002) | `eval/navigation/questions.json`, `eval/navigation/stopwords.txt`, `eval/navigation/manifest.json` | owner | [ ] |
| 3 | | One-time ingest: empty wiki under `eval/navigation/wiki` (index, log, packaged schema), then per corpus file in order `wiki-studio ingest --backend claude` + `wiki-studio promote`; record backend, model, date, version and per-document cost in the manifest; commit the tree with `.audit/` and `.applied/` (FR-003) | `eval/navigation/wiki/**`, `eval/navigation/manifest.json` | owner | [ ] |

**Checkpoint US1** — verify before continuing:
- [ ] `git merge-base --is-ancestor <questions_commit> HEAD` succeeds and `questions.json` is unchanged since it
- [ ] `wiki-studio lint --root eval/navigation` exits 0 on the frozen wiki
- [ ] NOTICE names memkernel and the copied paths

---

## US2 + US3: Gold, metrics, determinism test, README

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 4 | | Assign `gold.json` by reading the frozen wiki: `gold` (page containing the answer, `null` otherwise; `absent` → `null`), `reason` (heading or quoted sentence; for `null`, pages checked), `distractors` for `competing` (FR-004) | `eval/navigation/gold.json` | owner | [ ] |
| 5 | | `run.py` (stdlib): load fixture; one `count_words` for every count; call the querier's selection with `max_pages=5`; compute `ingest_coverage`, `hit_at_1`, `hit_at_max`, `distractor_outranks`, `absent_empty`, `absent_pages_loaded`, `wiki_words`, `grep_words` per the grep rule (stop list, ≥ 3 chars, whole-word case-insensitive, 2 lines context, merged ranges), medians/means/totals; write JSON to stdout (FR-005, FR-006) | `eval/navigation/run.py`, `eval/navigation/__init__.py` | build | [ ] |
| 6 | | Commit `results.json`; test asserts `run.py` output equals it; test that `questions.json` sha256 matches the manifest; exclude `eval/` from wheel (`pyproject` `exclude`) and from coverage (FR-007, FR-011) | `eval/navigation/results.json`, `tests/test_navigation_eval.py`, `pyproject.toml` | build | [ ] |
| 7 | [P] | README "Evidence" section: the three numbers with definitions, grep rule verbatim, component-metric and vocabulary-alignment caveats, ingest cost per document and amortised, link to the layer 2 issue; CHANGELOG `[0.3.0]`; version 0.3.0 (FR-008, FR-010) | `README.md`, `CHANGELOG.md`, `pyproject.toml`, `src/wiki_studio/__init__.py`, `tests/test_cli_contract.py` | build | [ ] |

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

## Final Verification

- [ ] Type checker: 0 errors; linter: 0 errors; coverage ≥ 80 percent with `eval/` excluded
- [ ] No model call anywhere in CI (`grep -rn "backend" tests/test_navigation_eval.py` shows none)
- [ ] `questions.json` unchanged since `questions_commit`
- [ ] README makes no claim beyond the three component numbers
