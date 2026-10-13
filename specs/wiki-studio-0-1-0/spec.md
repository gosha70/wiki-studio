---
spec_mode: full
feature_id: wiki-studio-0-1-0
risk_category: feature
status: approved
date: 2026-10-13
---

# Spec: wiki-studio 0.1.0 — extract the LLM-wiki maintainer into a standalone package

<!-- Project constitution: shared/skills/ — copilot-conventions, coding-standards, safety -->

Design references (read before building): `CLAUDE.md`; the source tree being
extracted, `code-copilot-team/scripts/wiki_ingest/` (package, backends, tests,
fixtures), `code-copilot-team/knowledge/wiki/schema/*.md` and
`code-copilot-team/knowledge/wiki/scripts/lint-wiki.sh`; the consumers that
must keep working, `code-copilot-team/scripts/wiki`, `scripts/wiki-ingest`,
`tests/test-wiki-ingest.sh`, `.github/workflows/wiki-ingest-tests.yml`, and
`memkernel/src/memkernel/wiki/{pages,sync}.py` (pages written in the same schema).

## User Scenarios

### US1: The maintainer is an installable package (Priority: HIGH)

**Given** a developer with Python 3.11+ and no other dependency
**When** they run `pip install wiki-studio` (or `poetry install` in this repo) and then `wiki-studio --help`
**Then** the five verbs `ingest`, `promote`, `query`, `lint`, `audit-flush` are available with the same flags, help text and exit codes as `code-copilot-team/scripts/wiki`, the package imports only the standard library, and the moved test suite passes without network access through the deterministic `test` backend

### US2: The wiki lives anywhere, not only at `knowledge/wiki` (Priority: HIGH)

**Given** a project whose wiki is at a path of its choosing
**When** they run any verb with `--wiki-dir`, `--proposals-dir`, `--root`, or the matching `WIKISTUDIO_*` variables
**Then** every read and write resolves through one `WikiPaths` object, the structural linter runs in Python (no bash), nothing in the package reads `code-copilot-team`'s own files, and with no flags the defaults are byte-identical to the old layout so the old wrapper keeps working

### US3: Existing consumers keep working and the schema stays shared (Priority: MEDIUM)

**Given** code-copilot-team, memkernel and document-assistant as consumers
**When** code-copilot-team replaces `scripts/wiki` with `exec wiki-studio "$@"`, and memkernel's `WikiExporter` writes draft pages
**Then** code-copilot-team's `tests/test-wiki-ingest.sh` smoke path passes unchanged, memkernel's exported pages lint clean, and the public Python API (`wikistudio.api`) lets a library call ingest, promote, query and lint without the CLI

### US4: Release hygiene (Priority: LOW)

**Given** the extraction is complete
**When** the release is prepared
**Then** the version is `0.1.0`, the CHANGELOG lists what moved and what changed, the README documents verbs, flags, environment variables, exit codes and backends, CI runs lint, type check, tests with coverage and a build check on 3.11–3.13, and a tag `v0.1.0` publishes to PyPI through trusted publishing

## Requirements

- **FR-001**: The repository MUST be a Poetry project named `wiki-studio` (import `wikistudio`, console script `wiki-studio`, PyPI distribution `wiki-studio`), Python `>=3.11,<3.14`, with **no `[tool.poetry.dependencies]` beyond `python`**; dev dependencies are `pytest`, `pytest-cov`, `ruff`, `mypy`.
- **FR-002**: Every module of `code-copilot-team/scripts/wiki_ingest/` MUST be moved under `src/wikistudio/` with its behaviour unchanged: `__main__.py` becomes `cli.py` (plus a two-line `__main__.py` calling `cli.main()`), the other modules keep their names, `backends/` keeps `copilot_cli.py`, `json_extract.py`, `test.py` and its registry. Relative imports are kept; the only edits in this move are the import paths, the licence header and what the other FRs name.
- **FR-003**: The six schema documents from `code-copilot-team/knowledge/wiki/schema/` MUST ship as package data under `src/wikistudio/schema/` and be loaded with `importlib.resources`; `load_schema_files()` MUST prefer `<wiki_dir>/schema/` when that directory exists (a project may carry its own copy) and fall back to the packaged files otherwise.
- **FR-004**: A new `src/wikistudio/paths.py` MUST define `WikiPaths` (`root`, `wiki_dir`, `proposals_dir`, `query_log`, `audit_log`, `schema_dir`) resolved from, in precedence order, CLI flags `--root`, `--wiki-dir`, `--proposals-dir`, environment `WIKISTUDIO_ROOT`, `WIKISTUDIO_WIKI_DIR`, `WIKISTUDIO_PROPOSALS_DIR`, then defaults (`root` = git toplevel of the current directory or the current directory; `wiki_dir` = `knowledge/wiki`; `proposals_dir` = `doc_internal/proposals`; `query_log` = `doc_internal/wiki-query-log.jsonl`; `audit_log` = `<wiki_dir>/.audit/ingest-log.md`). Every module that today takes `repo_root` and joins `knowledge/wiki` or `doc_internal` MUST take a `WikiPaths` instead; no other module may spell those directory names.
- **FR-005**: `src/wikistudio/lint.py` MUST implement the six structural checks of `lint-wiki.sh` in Python (frontmatter present and well-formed with required keys; `page_type` in the allowed set; `slug` equals the filename stem and is unique; `page_type` matches the directory; intra-wiki `[text](path.md)` links resolve; every page except `index` and `log` is reachable from `index.md`), skipping `schema/`, `scripts/` and `.audit/`, returning a list of violations; `lint` and `promote` MUST call it instead of `subprocess`-ing the bash script, which MUST NOT be shipped.
- **FR-006**: The backend registry MUST drop the `code-copilot-team`-specific capability lookup (`shared/capabilities/pi.yaml`); `pi` stays selectable by `--backend pi` and auto-detects only when `WIKISTUDIO_ENABLE_PI=1`. `WIKISTUDIO_BACKEND` MUST replace `WIKI_INGEST_BACKEND`, which stays accepted with a deprecation warning on stderr.
- **FR-007**: The CLI contract MUST be preserved exactly: verbs `ingest` (`--legacy-single-source`, `--backend`, `--dry-run`, `--output-dir`, `--no-redact`, `--allow-out-of-repo`, gate-only flag), `promote` (`--dry-run`, `--allow-out-of-repo`), `query` (`--file-back`, `--backend`, `--max-pages`, `--no-redact`, `--output-dir`), `lint` (`--health`, `--strict`, `--paths`, `--backend`), `audit-flush` (`--dry-run`); exit codes 0, 2, 3, 4, 5, 6, 7, 8 with their current meanings; `--help` text may only change where it names the old paths or the old wrapper.
- **FR-008**: `src/wikistudio/api.py` MUST expose `ingest(source, paths, backend=None, ...)`, `promote(proposal_dir, paths, dry_run=False)`, `query(question, paths, backend=None, ...)`, `lint(paths, health=False, strict=False, ...)` and `audit_flush(paths, dry_run=False)` returning typed results (dataclasses) and raising the existing `wikistudio.errors` exceptions; `cli.py` MUST be a thin argument parser over these functions and map exceptions to exit codes in one place.
- **FR-009**: The test suite (`code-copilot-team/scripts/wiki_ingest/tests/`, 240 test functions, plus the `wiki_audit` and sample fixtures) MUST move to `tests/` and pass under pytest; tests that located the old repo through `Path(__file__).parents[3]` MUST build their layout in a temporary directory via `WikiPaths`; tests that spawned `./scripts/wiki` MUST call `wikistudio.cli.main(argv)` in-process, except one subprocess smoke test of the installed `wikistudio` entry point; the shell-linter tests become tests of `wikistudio.lint`; the single-writer invariant test MUST scan `src/wikistudio/` and allow writes to the wiki directory only in `promoter.py`.
- **FR-010**: A fixture wiki under `tests/fixtures/wiki/` MUST contain one page of every page type plus `index.md` and `log.md`, and MUST include the draft pages memkernel 0.3's `WikiExporter` produces (one `decision`, one `concept`, one `workflow`, with `memkernel_ref` and `memory_type` extra frontmatter keys and a `memkernel://` source URL); `wikistudio.lint` MUST report zero violations on it, which pins schema compatibility with memkernel.
- **FR-011**: `docs/consumers.md` MUST give the three consumer recipes: code-copilot-team (`scripts/wiki` → `exec wiki-studio "$@"`, `scripts/wiki-ingest` → `exec wiki-studio ingest --legacy-single-source "$@"`, the workflow's install step, and deleting `scripts/wiki_ingest/` once pinned), memkernel (`MEMKERNEL_WIKI_DIR` plus `wiki-studio lint` after `wiki_export`), document-assistant (wiki at a custom path through `WIKISTUDIO_WIKI_DIR`).
- **FR-012**: `README.md` MUST document install, the five verbs with their flags, the environment variables, the exit-code table, the backends (claude, codex, cursor, pi, test) and how auto-detection orders them, the schema override rule, and the library API with one example; `CHANGELOG.md` MUST have a `[0.1.0]` section; `NOTICE` MUST state that the code was extracted from `gosha70/code-copilot-team`.
- **FR-013**: `.github/workflows/ci.yml` MUST run ruff check, ruff format check, mypy, pytest with coverage ≥ 80 percent and `poetry build` on Python 3.11, 3.12 and 3.13; `.github/workflows/release.yml` MUST publish to PyPI with trusted publishing on tags `v*` through an environment named `pypi` (same shape as memkernel's).
- **FR-014**: `pyproject.toml` version and `wikistudio.__version__` MUST be `0.1.0`; `wiki-studio --version` MUST print it.
- **FR-015**: Every source file MUST carry the `# Copyright (c) 2026 EGOGE` / `# SPDX-License-Identifier: Apache-2.0` header; `LICENSE` stays Apache-2.0.
- **FR-016**: Nothing in `src/wikistudio/` may reference `code-copilot-team`, `shared/`, `specs/`, `doc_internal` or `knowledge/wiki` except as the documented defaults inside `paths.py` and in help text; a test MUST grep the package for these strings outside `paths.py` and `cli.py`.

## Constraints / What NOT to Build

- No MCP server, no HTTP API: 0.1.0 is the CLI and the library API only. A `wiki-studio` MCP server is 0.2.0.
- No change to the page schema (frontmatter keys, page types, directory names, required sections): this is the contract memkernel and code-copilot-team already write to.
- No new backends and no LLM calls inside the package: backends shell out to CLIs as today; the `test` backend is the only one CI runs.
- No rewrite of ingest, promote, query or health-lint logic: move it, then change only what FR-004 to FR-008 name. Refactors beyond that are a later release.
- No runtime dependency, not even PyYAML: `yaml_lite.py` stays.
- No edits to code-copilot-team or memkernel in this feature; the consumer switch is documented (FR-011) and happens in their own repos.

## Key Entities

- **WikiPaths**: the resolved locations of the wiki, the proposals directory, the query log, the audit log and the schema directory; the single source of paths for every verb.
- **Proposal / patch-set**: the output of `ingest` under `proposals_dir`, applied atomically by `promote` after lint.
- **Backend**: a subprocess adapter (claude, codex, cursor, pi) or the in-process `test` backend that answers the ingest, query and health-lint prompts with JSON.
- **Structural lint**: the six deterministic checks on page shape and link integrity (Python in 0.1.0).
- **Health lint**: the four knowledge checks (contradictions through a backend, stale claims, weak orphans, missing cross-links).

## Success Criteria

1. US1 is demonstrable: in a clean virtual environment, `pip install dist/wiki_studio-0.1.0-py3-none-any.whl` then `wiki-studio --help` lists the five verbs; `pip check` reports no dependencies; `wiki-studio ingest tests/fixtures/sample-incident.md --backend test --output-dir <tmp>` exits 0 and writes a proposal.
2. US2 is demonstrable: `WIKISTUDIO_WIKI_DIR=<tmp>/kb wiki-studio lint` lints a wiki outside `knowledge/wiki`; `grep -rn "knowledge/wiki\|doc_internal\|shared/" src/wikistudio` matches only `paths.py` and help text in `cli.py`.
3. US3 is demonstrable: `wiki-studio lint --wiki-dir tests/fixtures/wiki` exits 0 on the fixture that includes memkernel-exported pages; the recipes in `docs/consumers.md` are copy-pasteable and the code-copilot-team wrapper lines are two `exec` commands.
4. All 240 moved test functions pass (renamed or re-homed tests are listed in the CHANGELOG); `poetry run pytest -q --cov=wikistudio --cov-fail-under=80`, `ruff check`, `ruff format --check` and `mypy src/` are clean; CI is green on the three Python versions.
5. `pyproject.toml` says `0.1.0`, `CHANGELOG.md` has `[0.1.0]`, `NOTICE` names the origin repository, and `release.yml` targets the `pypi` environment.
