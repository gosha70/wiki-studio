---
spec_mode: full
feature_id: wiki-studio-0-1-0
risk_category: feature
justification: "An extraction across 15 modules, 240 tests and three consumers; a full spec pins the CLI and schema contracts so the unattended build cannot drift."
status: approved
date: 2026-10-13
collaboration_mode: single
origin:
  urls:
    - https://github.com/gosha70/wiki-studio
    - https://github.com/gosha70/memkernel/blob/main/docs/roadmap.md
    - https://github.com/gosha70/code-copilot-team/blob/master/specs/wiki-ingest-pipeline/spec.md
    - https://github.com/gosha70/memkernel/blob/main/docs/adr/ADR-008-llm-wiki-as-semantic-layer.md
  origin_claim: |
    Create a new repository for extracting and enhancing the LLM Wiki
    (owner decision, confirmed in the memkernel planning session and
    recorded as step 2 of memkernel's docs/roadmap.md): move
    code-copilot-team's knowledge/wiki/schema, its linter and
    scripts/wiki_ingest (ingest, promote, query, health-lint, 240 tests,
    stdlib-only) into gosha70/wiki-studio as a standalone package that
    code-copilot-team, memkernel and document-assistant consume. Build it
    the fastest, most automated way with code-copilot-team's build loop
    and DeepSeek as the code reviewer. The repository was created as
    ai-wiki and renamed wiki-studio because `ai-wiki` is taken on PyPI,
    `wikiforge` is too similar to the existing `wiki-forge`, and
    the name should say knowledge, not memory (memkernel is the memory
    layer). 0.1.0 is the extraction with the
    paths decoupled; an MCP server and memkernel's extra come later.
---

# Implementation Plan: wiki-studio 0.1.0 — extraction

**Branch**: `feature/wiki-studio-0-1-0`
**Input**: specs/wiki-studio-0-1-0/spec.md

## Summary

code-copilot-team hosts a working Karpathy-pattern wiki maintainer under
`scripts/wiki_ingest` (5,691 lines, standard library only, 240 tests) with the
page schema under `knowledge/wiki/schema` and a bash structural linter. memkernel
writes pages in that schema without importing anything, and document-assistant
wants the same tool. 0.1.0 moves the code into this repository as the `wiki_studio`
package with a `wiki-studio` CLI, replaces the hard-coded `knowledge/wiki` and
`doc_internal` paths with one `WikiPaths` object, ports the bash linter to Python,
removes the two code-copilot-team couplings (the `pi` capability file and the
`PYTHONPATH` wrapper), and adds a library API, a consumer guide, CI and a PyPI
release workflow. Behaviour, flags and exit codes do not change.

## Technical Context

**Language/Version**: Python 3.11–3.13, Poetry, standard library only at runtime
**Primary Dependencies**: none at runtime; dev: pytest, pytest-cov, ruff, mypy
**Source being moved**: `code-copilot-team/scripts/wiki_ingest/**` (modules, backends, tests, fixtures), `code-copilot-team/knowledge/wiki/schema/*.md`, the checks of `knowledge/wiki/scripts/lint-wiki.sh`
**Testing**: `poetry run pytest -q -p no:cacheprovider` (unittest-style tests under pytest; `test` backend; temporary wiki layouts built through `WikiPaths`)
**Constraints**: no runtime dependency; CLI contract and exit codes frozen; page schema frozen; `promoter.py` is the only writer into the wiki; coverage ≥ 80 percent; ruff line length 120; mypy clean (not strict in 0.1.x)

## Constitution Check

| Rule file | Concern | Status |
|-----------|---------|--------|
| `coding-standards.md` | No magic strings, lint-clean, typed | OK — paths live in `paths.py`; exit codes are module constants |
| `safety.md` | No secrets, inputs validated, no writes outside the project | OK — `--allow-out-of-repo` gate kept; promoter stays the single writer; stderr redaction kept |
| `copilot-conventions.md` | One logical change per commit, repo is source of truth | OK — one phase per driver commit |

## Architecture Decisions

### ADR-1: Move first, then decouple

**Context**: The code is tested and in production use inside code-copilot-team; a rewrite would lose that.
**Decision**: US1 moves modules and tests with only import-path and header edits and gets them green; US2 makes the behavioural changes the spec names. No refactor beyond FR-004 to FR-008.
**Consequences**: the US1 diff is large but mechanical; the reviewer can diff against the source tree.

### ADR-2: One `WikiPaths` object replaces `repo_root`

**Context**: Eleven functions take `repo_root` and join `knowledge/wiki` or `doc_internal` themselves; the bash wrapper set `PYTHONPATH`.
**Decision**: `paths.py` resolves flags, `WIKI_STUDIO_*` variables and defaults once; every function takes `WikiPaths`. Defaults equal the old layout, so an unflagged run is byte-identical.
**Consequences**: code-copilot-team's wrapper becomes `exec wiki-studio "$@"`; memkernel can point the tool at `MEMKERNEL_WIKI_DIR`.

### ADR-3: Structural lint in Python, bash script not shipped

**Context**: `lint` and `promote` shell out to `lint-wiki.sh`, which needs bash and a path into the repo; wheels do not carry executable scripts well.
**Decision**: `lint.py` implements the six checks; `promote` calls it in-process on the staged tree.
**Consequences**: identical rules, one fewer process, testable without a shell. code-copilot-team may keep its bash copy until it switches.

### ADR-4: Schema is package data with a project override

**Context**: `prompt.py` reads the schema files from the repository at runtime.
**Decision**: the six files ship inside the wheel; `<wiki_dir>/schema/` wins when present.
**Consequences**: a bare `pip install wiki-studio` works on an empty wiki; projects that customise the schema keep doing so.

### ADR-5: Distribution `wiki-studio`, CLI `wiki-studio`

**Context**: the repository started as `ai-wiki`; `ai-wiki`, `llmwiki`, `agent-wiki` and `memforge` are taken on PyPI, a memory-flavoured name would collide with memkernel's role, and PyPI rejects `wikiforge` as too similar to the existing `wiki-forge` (another LLM-wiki project). `wiki-studio` is free on PyPI in every spelling, matches `rlm-studio`, and names the knowledge layer agents build.
**Decision**: repository, distribution and console script are `wiki-studio`; the import name is `wiki_studio` because module names cannot contain hyphens; the PyPI name is held by a `0.0.1` placeholder release until 0.1.0 replaces it.
**Consequences**: `pip install wiki-studio`, `import wiki_studio`, `wiki-studio <verb>`; one name everywhere except the import.

## Project Structure

```
pyproject.toml                       — poetry, wiki-studio 0.1.0, console script wiki-studio, no runtime deps
src/wiki_studio/__init__.py               — __version__
src/wiki_studio/__main__.py               — python -m wiki_studio
src/wiki_studio/cli.py                    — verb parser, exit-code mapping (from __main__.py)
src/wiki_studio/api.py                    — ingest/promote/query/lint/audit_flush as functions
src/wiki_studio/paths.py                  — WikiPaths
src/wiki_studio/lint.py                   — structural linter (from lint-wiki.sh)
src/wiki_studio/{ingestor,ingestor_multi,promoter,querier,proposal,prompt,wiki_state,yaml_lite,errors}.py
src/wiki_studio/{audit,audit_flush,audit_lint,health_lint}.py
src/wiki_studio/backends/{__init__,copilot_cli,json_extract,test}.py
src/wiki_studio/schema/*.md               — package data
tests/                               — moved suite + test_paths.py, test_lint.py, test_api.py, test_package_boundaries.py
tests/fixtures/{sample-incident.md,stub-backend.sh,stub-backend-fail.sh,wiki_audit/,wiki/}
docs/consumers.md                    — recipes for code-copilot-team, memkernel, document-assistant
.github/workflows/{ci,release}.yml
README.md, CHANGELOG.md, NOTICE, SECURITY.md, LICENSE
```

## Scope

### Task 1: Package scaffold and mechanical move (US1)

**Files**: `pyproject.toml`, `src/wiki_studio/**`, `tests/**`, `.github/workflows/ci.yml`
**Acceptance criteria**:
- [ ] FR-001, FR-002, FR-003 (packaging part), FR-009 (move part), FR-013 (ci.yml), FR-015
- [ ] `poetry run pytest -q` passes with every moved test
- [ ] `wiki-studio --help` lists the five verbs

### Task 2: Paths, Python linter, backend decoupling (US2)

**Files**: `src/wiki_studio/paths.py`, `src/wiki_studio/lint.py`, `src/wiki_studio/backends/__init__.py`, every module that took `repo_root`, tests
**Acceptance criteria**:
- [ ] FR-004, FR-005, FR-006, FR-007, FR-016 implemented
- [ ] Boundary test passes; unflagged run reproduces the old layout

### Task 3: Library API, fixture wiki, consumer guide (US3)

**Files**: `src/wiki_studio/api.py`, `src/wiki_studio/cli.py`, `tests/fixtures/wiki/**`, `tests/test_api.py`, `docs/consumers.md`
**Acceptance criteria**:
- [ ] FR-008, FR-010, FR-011 implemented
- [ ] memkernel-shaped pages lint clean

### Task 4: Release hygiene (US4)

**Files**: `README.md`, `CHANGELOG.md`, `NOTICE`, `SECURITY.md`, `.github/workflows/release.yml`, `pyproject.toml`, `src/wiki_studio/__init__.py`
**Acceptance criteria**:
- [ ] FR-012, FR-013 (release.yml), FR-014 satisfied
- [ ] `poetry build` and a clean-venv smoke run pass; coverage ≥ 80 percent

## Risks

- **Coverage below 80 percent after the move** because the old e2e tests ran the CLI in a subprocess. Mitigation: FR-009 requires in-process `main(argv)` calls.
- **mypy noise on legacy code**. Mitigation: non-strict mypy in 0.1.x; strict is a 0.2 goal.
- **Hidden path assumptions** in promoter staging (symlinks to sibling top-level dirs so escape links resolve). Mitigation: `WikiPaths.root` keeps that behaviour; a promote test with an escape link is in the moved suite.
