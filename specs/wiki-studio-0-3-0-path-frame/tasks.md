# Tasks: one path frame for the ingest prompt, and `info` (issue #11)

<!-- One `## US<n>:` group = one auto-build phase. -->
<!-- Run per phase: poetry run ruff check src/ tests/ eval/ && poetry run ruff format --check src/ tests/ eval/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=80 -->

## US1: Prompt states the frame; parser strips exactly the label

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 1 | | `WikiPaths.strip_wiki_label(path)`: remove one leading `<wiki_label>/`, nothing else (FR-002) | `src/wiki_studio/paths.py` | build | [x] |
| 2 | | `DefaultMultiIngestor` applies it to every edit path before the validators (FR-002) | `src/wiki_studio/ingestor_multi.py` | build | [x] |
| 3 | [P] | Multi-page response instructions state the frame with the configured label; `description` on the schema's `path` (FR-001) | `src/wiki_studio/backends/copilot_cli.py`, `src/wiki_studio/prompt.py` | build | [x] |

## US2: `info`

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 4 | | `info` verb: layout default/custom, every location with its source (flag / env NAME / default), exists flags, schema copy; `--json`; added to `_VERBS` and the dispatch; parser description says six verbs (FR-003) | `src/wiki_studio/cli.py` | build | [x] |

## US3: Tests and docs

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 5 | | Tests: strip cases; stub-backend ingest with labels `wiki` and `knowledge/wiki` and the double prefix; rendered prompt with and without wiki state; `api.ingest` with a one-word label; `info` text and JSON, default and custom; contract tests gain `info` (FR-004) | `tests/test_path_frame.py`, `tests/test_cli_contract.py` | build | [x] |
| 6 | [P] | README (`info` under Verbs; Evidence paragraph: fixed in this release, run 1 measured on 0.2.0); CHANGELOG `[0.3.0]`: Fixed + Added (FR-005) | `README.md`, `CHANGELOG.md` | build | [x] |

## Final Verification

- [ ] Full gate green; CI green on 3.11–3.13
- [ ] `wiki-studio --version` prints only `0.3.0`; `wiki-studio info` exits 0 in an empty directory
