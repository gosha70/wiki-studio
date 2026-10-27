# wiki-studio — project instructions

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
poetry run ruff check src/ tests/ conformance/ && poetry run ruff format --check src/ tests/ conformance/
poetry run mypy src/
poetry run pytest -q --cov=wiki_studio --cov-fail-under=92
poetry run wiki-studio --help                        # the CLI
poetry run wiki-studio-mcp --help                    # the MCP server (the `mcp` extra)
poetry run python -m conformance.mcp.run --server-cmd "wiki-studio-mcp --root {root}"   # MCP conformance suite
poetry run python -m eval.navigation.discovery --help    # discovery evaluation runner
poetry build                                     # wheel + sdist
```

Format with `poetry run ruff format src/ tests/` before finishing.

## Layout

```
src/wiki_studio/cli.py          verb dispatcher: init | ingest | propose | promote | approve | read | query | find | lint | findings | audit-flush | info (exit codes 0,2..11 are a contract)
src/wiki_studio/api.py          the public library API every verb calls (additive changes with defaults only)
src/wiki_studio/paths.py        WikiPaths: root, wiki_dir, proposals_dir, query log, audit log (the only place paths are resolved)
src/wiki_studio/contract.py     root manifest (.wiki-studio.json) read side, contained schema loader, fingerprint, drift, info formats and capabilities
src/wiki_studio/review.py       page keys, approval-record verification and review_state (read side; promoter.py writes records)
src/wiki_studio/findings.py     model-free findings: deterministic health kinds plus review, superseded-still-indexed and no-page-id kinds
src/wiki_studio/ingestor*.py    single-source and multi-page ingest (proposal generation; never writes the wiki)
src/wiki_studio/promoter.py     THE ONLY MODULE THAT WRITES INTO THE WIKI DIRECTORY (lint-gated, scoped commit, receipt protocol)
src/wiki_studio/wikilock.py     WikiLock: the OS advisory lock beside the resolved wiki that serialises cooperating writers
src/wiki_studio/querier.py      index-first question answering over wiki pages
src/wiki_studio/discovery.py    rankers (index-first, fts5), eligibility, the byte budget, the FTS5 probe, RankerConfig
src/wiki_studio/search_index.py the FTS5 index in memory and the on-disk search cache beside the lock (its only writer)
src/wiki_studio/mcp_adapter/    wiki-studio-mcp: the optional MCP server (the only place `mcp` is imported, behind the extra)
src/wiki_studio/lint.py         structural linter (frontmatter, page_type, slug, placement, links, reachability)
src/wiki_studio/health_lint.py  knowledge-health checks (contradictions, stale claims, weak orphans, cross-links)
src/wiki_studio/audit*.py       ingest log, audit tree validation, audit flush (git)
src/wiki_studio/prompt.py, proposal.py, wiki_state.py, yaml_lite.py, errors.py
src/wiki_studio/backends/       copilot_cli (claude, codex, cursor, pi), json_extract, test (deterministic, for CI)
src/wiki_studio/schema/*.md     page-types, ingest, citation, lint, audit rules, WIKI_MAINTAINER (package data)
tests/                     unittest-style tests run by pytest; fixtures under tests/fixtures/
conformance/mcp/           adapter-agnostic MCP conformance suite (run.py, fixture/, scenario.md); conformance/runs/ host runs
eval/navigation/           frozen runs 1-2 (never edited), discovery.py runner, run3/ development set, heldout/ protocol
```

## Conventions that CI enforces

- Python 3.11–3.13; `from __future__ import annotations`; type hints on new code; `mypy src/` clean (not strict in 0.1.x).
- **No runtime dependencies.** The package imports only the standard library; backends shell out to CLIs.
- Ruff: line length 120, rule sets E/F/W/I/N/UP/B/A/SIM/TCH.
- Every source file starts with `# Copyright (c) 2026 EGOGE` / `# SPDX-License-Identifier: Apache-2.0`.
- CLI exit codes are stable: 0 ok, 1 fatal lint, 2 backend not found, 3 backend failed, 4 contract violation, 5 source missing, 6 output write failure, 7 path outside root, 8 not implemented, 9 promote validation or approve refused, 10 promote apply failed, 11 audit-flush error.
- No code path from `findings`, `approve` or `review_state` reaches a model; `WikiLock` is not reentrant.
- `promoter.py` is the single writer into the wiki directory; a test scans the package for violations.
- Defaults reproduce `code-copilot-team`'s layout (`knowledge/wiki`, `doc_internal/proposals`) so its wrapper is `exec wiki-studio "$@"`; every path is overridable by flag and `WIKI_STUDIO_*` environment variable.
- The page schema (frontmatter keys, page types, directories) is a published contract shared with memkernel's `WikiExporter`/`WikiImporter`; changing it needs a decision record in `docs/adr/`.
- Coverage ≥ 80 percent; CLI tests call `wiki_studio.cli.main(argv)` in-process except one subprocess smoke test.

## Working rules

- Read `specs/<feature-id>/spec.md` and `plan.md` before changing behaviour; keep each change to one phase of `tasks.md`; do not edit `specs/` except artifacts the phase owns.
- Do not commit, push, or change branches inside an auto-build session; the driver owns git.
- Update `CHANGELOG.md` under `[Unreleased]` for user-visible changes; bump `pyproject.toml` and `src/wiki_studio/__init__.py` together.
- Report test failures and skipped steps plainly; never skip or weaken a test to get green.
