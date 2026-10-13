# ai-wiki — project instructions

Standalone, stdlib-only implementation of the Karpathy-pattern **LLM wiki**:
a curated markdown knowledge base (`index.md`, `log.md`, typed pages with cited
sources) that agents ingest into, query from and lint. The code is extracted
from `code-copilot-team/scripts/wiki_ingest` (same author); the page schema is
shared with `memkernel`'s wiki bridge and `code-copilot-team/knowledge/wiki`.
The current feature spec lives in `specs/<feature-id>/` (spec-driven
development, one `## US<n>:` group in `tasks.md` per build phase).

## Commands

```bash
poetry install                                   # once
poetry run pytest -q -p no:cacheprovider          # unit + e2e (test backend, no network)
poetry run ruff check src/ tests/ && poetry run ruff format --check src/ tests/
poetry run mypy src/
poetry run pytest -q --cov=aiwiki --cov-fail-under=80
poetry run ai-wiki --help                        # the CLI
poetry build                                     # wheel + sdist
```

Format with `poetry run ruff format src/ tests/` before finishing.

## Layout

```
src/aiwiki/cli.py          verb dispatcher: ingest | promote | query | lint | audit-flush (exit codes 0,2..8 are a contract)
src/aiwiki/paths.py        WikiPaths: root, wiki_dir, proposals_dir, query log, audit log (the only place paths are resolved)
src/aiwiki/ingestor*.py    single-source and multi-page ingest (proposal generation; never writes the wiki)
src/aiwiki/promoter.py     THE ONLY MODULE THAT WRITES INTO THE WIKI DIRECTORY (atomic, lint-gated)
src/aiwiki/querier.py      index-first question answering over wiki pages
src/aiwiki/lint.py         structural linter (frontmatter, page_type, slug, placement, links, reachability)
src/aiwiki/health_lint.py  knowledge-health checks (contradictions, stale claims, weak orphans, cross-links)
src/aiwiki/audit*.py       ingest log, audit tree validation, audit flush (git)
src/aiwiki/prompt.py, proposal.py, wiki_state.py, yaml_lite.py, errors.py
src/aiwiki/backends/       copilot_cli (claude, codex, cursor, pi), json_extract, test (deterministic, for CI)
src/aiwiki/schema/*.md     page-types, ingest, citation, lint, audit rules, WIKI_MAINTAINER (package data)
tests/                     unittest-style tests run by pytest; fixtures under tests/fixtures/
```

## Conventions that CI enforces

- Python 3.11–3.13; `from __future__ import annotations`; type hints on new code; `mypy src/` clean (not strict in 0.1.x).
- **No runtime dependencies.** The package imports only the standard library; backends shell out to CLIs.
- Ruff: line length 120, rule sets E/F/W/I/N/UP/B/A/SIM/TCH.
- Every source file starts with `# Copyright (c) 2026 EGOGE` / `# SPDX-License-Identifier: Apache-2.0`.
- CLI exit codes are stable: 0 ok, 2 backend not found, 3 backend failed, 4 contract violation, 5 source missing, 6 output write failure, 7 path outside root, 8 not implemented.
- `promoter.py` is the single writer into the wiki directory; a test scans the package for violations.
- Defaults reproduce `code-copilot-team`'s layout (`knowledge/wiki`, `doc_internal/proposals`) so its wrapper is `exec ai-wiki "$@"`; every path is overridable by flag and `AIWIKI_*` environment variable.
- The page schema (frontmatter keys, page types, directories) is a published contract shared with memkernel's `WikiExporter`/`WikiImporter`; changing it needs a decision record in `docs/adr/`.
- Coverage ≥ 80 percent; CLI tests call `aiwiki.cli.main(argv)` in-process except one subprocess smoke test.

## Working rules

- Read `specs/<feature-id>/spec.md` and `plan.md` before changing behaviour; keep each change to one phase of `tasks.md`; do not edit `specs/` except artifacts the phase owns.
- Do not commit, push, or change branches inside an auto-build session; the driver owns git.
- Update `CHANGELOG.md` under `[Unreleased]` for user-visible changes; bump `pyproject.toml` and `src/aiwiki/__init__.py` together.
- Report test failures and skipped steps plainly; never skip or weaken a test to get green.
