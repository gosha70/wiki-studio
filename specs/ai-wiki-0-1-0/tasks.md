# Tasks: ai-wiki 0.1.0 — extraction

<!-- One `## US<n>:` group = one auto-build phase. [US#] tags trace to spec.md. -->
<!-- Run per phase: poetry run ruff check src/ tests/ && poetry run ruff format --check src/ tests/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=aiwiki --cov-fail-under=80 -->
<!-- Source tree to move: a sibling checkout of code-copilot-team (set CCT_SRC=/path/to/code-copilot-team; default ../code-copilot-team). Copy, never symlink. -->

## US1: Package scaffold and mechanical move

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 1 | | Create the Poetry project: name `aiwiki`, version `0.1.0`, `packages = [{include = "aiwiki", from = "src"}]`, console script `ai-wiki = "aiwiki.cli:main"`, no runtime deps, dev deps pytest/pytest-cov/ruff/mypy; ruff (line 120, E/F/W/I/N/UP/B/A/SIM/TCH), mypy (non-strict, `warn_unused_ignores`), pytest config (`testpaths = ["tests"]`) (FR-001) | `pyproject.toml`, `src/aiwiki/__init__.py`, `src/aiwiki/__main__.py` | build | [ ] |
| 2 | | Copy every module of `$CCT_SRC/scripts/wiki_ingest/` (except `tests/`) into `src/aiwiki/`; rename `__main__.py` to `cli.py` with `def main(argv: list[str] \| None = None) -> int`; keep relative imports; add the licence header to every file (FR-002, FR-015) | `src/aiwiki/*.py`, `src/aiwiki/backends/*.py` | build | [ ] |
| 3 | [P] | Copy the six schema files into `src/aiwiki/schema/`; make `prompt.load_schema_files()` read them through `importlib.resources` when the project override directory is absent (FR-003) | `src/aiwiki/schema/*.md`, `src/aiwiki/prompt.py` | build | [ ] |
| 4 | | Copy `scripts/wiki_ingest/tests/` to `tests/` (fixtures to `tests/fixtures/`); fix imports to `aiwiki`; replace `Path(__file__).parents[3]`-style repo discovery with a temporary layout per test (`<tmp>/knowledge/wiki`, `<tmp>/doc_internal`) built by a shared helper in `tests/conftest.py`; replace `./scripts/wiki` subprocess calls with `aiwiki.cli.main(argv)` in-process; keep exactly one subprocess smoke test (`python -m aiwiki --help`) (FR-009) | `tests/**` | build | [ ] |
| 5 | [P] | CI workflow: ruff check, ruff format check, mypy, pytest with `--cov-fail-under=80`, `poetry build`; matrix 3.11/3.12/3.13; cache Poetry (FR-013) | `.github/workflows/ci.yml` | build | [ ] |

**Checkpoint US1** — verify before continuing:
- [ ] `poetry run pytest -q` green with the moved suite (count reported)
- [ ] `poetry run ai-wiki --help` lists ingest, promote, query, lint, audit-flush
- [ ] `poetry run ruff check src/ tests/` and `poetry run mypy src/` clean

---

## US2: Paths, Python linter, backend decoupling

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 6 | | Add `WikiPaths` with `resolve(args, env)` implementing the flag > env > default precedence and the defaults from FR-004; add `--root`, `--wiki-dir`, `--proposals-dir` as global CLI options (FR-004) | `src/aiwiki/paths.py`, `src/aiwiki/cli.py`, `tests/test_paths.py` | build | [ ] |
| 7 | | Replace every `repo_root: Path` parameter and every joined `knowledge/wiki` / `doc_internal` / `.audit/ingest-log.md` with `WikiPaths` fields: `ingestor`, `ingestor_multi`, `promoter` (staging keeps symlinking sibling top-level dirs of `paths.root` so escape links resolve), `querier` (query log), `audit`, `audit_flush`, `audit_lint`, `health_lint`, `wiki_state`, `prompt`, `backends/copilot_cli` (rendered headings use `paths.wiki_dir` relative names) (FR-004) | `src/aiwiki/*.py`, `src/aiwiki/backends/copilot_cli.py` | build | [ ] |
| 8 | | Implement the structural linter in Python with the six checks and the three skipped directories; `lint` (default mode) and `promote` call it; delete any reference to `lint-wiki.sh`; port the old shell-linter tests to `aiwiki.lint` (FR-005) | `src/aiwiki/lint.py`, `src/aiwiki/cli.py`, `src/aiwiki/promoter.py`, `tests/test_lint.py` | build | [ ] |
| 9 | [P] | Backend registry: remove the `shared/capabilities/pi.yaml` lookup; `pi` auto-detects only with `AIWIKI_ENABLE_PI=1`; `AIWIKI_BACKEND` with `WIKI_INGEST_BACKEND` as a deprecated alias that warns on stderr (FR-006) | `src/aiwiki/backends/__init__.py`, `tests/test_backends.py` | build | [ ] |
| 10 | | Contract tests: every verb and flag in FR-007 parses; exit codes 0,2,3,4,5,6,7,8 map as before; an unflagged run from a temp root reproduces `knowledge/wiki` and `doc_internal/proposals`; boundary test greps `src/aiwiki` for `code-copilot-team`, `shared/`, `specs/`, `doc_internal`, `knowledge/wiki` and allows only `paths.py` and `cli.py` (FR-007, FR-016) | `tests/test_cli_contract.py`, `tests/test_package_boundaries.py` | build | [ ] |

**Checkpoint US2** — verify before continuing:
- [ ] `AIWIKI_WIKI_DIR=<tmp>/kb poetry run ai-wiki lint` lints a wiki outside the default path
- [ ] `grep -rn "knowledge/wiki\|doc_internal\|shared/" src/aiwiki` matches only `paths.py` and `cli.py`
- [ ] Full suite, ruff, mypy green

---

## US3: Library API, fixture wiki, consumer guide

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 11 | | Add `aiwiki.api` with `ingest`, `promote`, `query`, `lint`, `audit_flush` returning dataclass results and raising `aiwiki.errors` exceptions; make `cli.py` a thin parser over them with exit-code mapping in one function (FR-008) | `src/aiwiki/api.py`, `src/aiwiki/cli.py`, `tests/test_api.py` | build | [ ] |
| 12 | [P] | Fixture wiki with one page per page type, `index.md`, `log.md`, and three memkernel-exported draft pages (decision, concept, workflow; `memkernel_ref` and `memory_type` extra keys; `memkernel://` source URL); test that `aiwiki.lint` reports zero violations and that `query --backend test` answers over it (FR-010) | `tests/fixtures/wiki/**`, `tests/test_fixture_wiki.py` | build | [ ] |
| 13 | [P] | Write `docs/consumers.md` with the three recipes from FR-011; include the exact two `exec` lines for code-copilot-team and the install step for its workflow (FR-011) | `docs/consumers.md` | build | [ ] |

**Checkpoint US3** — verify before continuing:
- [ ] `poetry run ai-wiki lint --wiki-dir tests/fixtures/wiki` exits 0
- [ ] `python -c "import aiwiki.api"` works and `tests/test_api.py` covers all five functions
- [ ] Full suite, ruff, mypy green

---

## US4: Release hygiene

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 14 | | README: install, five verbs with flags, environment variables, exit-code table, backends and auto-detection order, schema override rule, library API example (FR-012) | `README.md` | build | [ ] |
| 15 | [P] | CHANGELOG `[0.1.0]` (moved from code-copilot-team at the source commit SHA; renamed tests; behaviour changes: WikiPaths, Python linter, AIWIKI_* variables, pi gating); NOTICE naming the origin repository; SECURITY.md with supported versions and private reporting (FR-012, FR-015) | `CHANGELOG.md`, `NOTICE`, `SECURITY.md` | build | [ ] |
| 16 | [P] | Release workflow: build on tag `v*`, smoke-install the wheel in a clean venv and run `ai-wiki --version`, publish with `pypa/gh-action-pypi-publish` through environment `pypi` (FR-013); `ai-wiki --version` prints `0.1.0` (FR-014) | `.github/workflows/release.yml`, `src/aiwiki/cli.py` | build | [ ] |

**Checkpoint US4** — verify before continuing:
- [ ] `poetry build` succeeds; wheel installs in a clean venv; `ai-wiki --version` prints 0.1.0; `pip check` clean
- [ ] `poetry run pytest -q --cov=aiwiki --cov-fail-under=80` green

---

## Final Verification

- [ ] Type checker: 0 errors
- [ ] Linter: 0 errors
- [ ] All moved tests pass; count equals the source suite or the CHANGELOG explains each difference
- [ ] No [NEEDS CLARIFICATION] markers remain in spec.md
- [ ] No runtime dependency in `pyproject.toml`
