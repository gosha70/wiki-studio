---
spec_mode: full
feature_id: wiki-studio-0-4-0
risk_category: feature
justification: "Three new CLI verbs that another repository's evaluation harness will drive; specified so the arm proposal and the verbs agree."
status: approved
date: 2026-10-16
collaboration_mode: single
origin:
  issue: 10
  urls:
    - https://github.com/gosha70/wiki-studio/issues/10
    - https://github.com/gosha70/memkernel/issues/17
  origin_claim: |
    Issue #10, layer 2: agent-level evidence that consulting the wiki helps an
    agent, as an arm next to memkernel's in an execution-graded harness with a
    files-plus-grep control, preregistered, no judge. The owner chose route B
    on 2026-10-16: wiki-studio builds what an agent needs to use it from a
    shell without a model, plus a ready arm proposal; the owner adopts the arm
    in memkernel's lifecycle suite and runs the benchmark there.
---

# Plan: wiki-studio 0.4.0 — an agent can use the wiki from a shell (issue #10, layer 2)

## Findings (memkernel main d189f2b, read 2026-10-16)

- memkernel's lifecycle suite is merged and not yet run. It is fixed at six
  arms in its spec and code; adding one is a memkernel change.
- Its five `lc-wiki-*` tasks need nothing from memkernel: session 0 records a
  decision under `knowledge/wiki/`, session 1 (second namespace) sees only
  that wiki, and a hidden oracle grades the code. The fixture has `index.md`
  but no `log.md`.
- Three wiki-studio gaps stop an agent from using it there: no CLI to create
  the scaffold (`promote` needs index and log); no CLI to save a page the
  agent wrote without a model (`propose` was library-only, `ingest` calls a
  backend); no CLI lookup without a model (`query` starts a second model whose
  tokens the receipts cannot see).

## Architecture decisions

- **ADR-1: `init` lives in `promoter.py`.** The single-writer invariant (only
  `promoter.py` writes into the wiki directory) is kept: `api.init` calls
  `promoter.init_wiki`, which creates `index.md`/`log.md` only when absent.
- **ADR-2: `propose --from DIR` maps a directory to edits.** Files sit at their
  wiki paths; `index.md`/`log.md` in DIR are lines to append (one edit per line,
  frontmatter refused, matching #15's rule); any other file is a content page,
  `update` when the wiki has it, otherwise `create`. Validation and writing are
  `api.propose`'s; `--promote` applies it at once.
- **ADR-3: `find` is a verb, not `query --no-backend`.** It returns paths and
  titles, writes no query log and has no answer field, so a separate verb keeps
  `query`'s contract unchanged.
- **ADR-4: the arm proposal is documentation here, code there.** `docs/agent-arm/`
  holds the config and a length-matched instruction (within 5 percent of
  memkernel's block, its placebo rule) plus the list of memkernel changes;
  nothing in memkernel's repository is changed from this repository.

## Scope

1. `wiki-studio init [--title]`, `api.init`.
2. `wiki-studio propose --from DIR [--name] [--rationale] [--promote]`,
   `api.edits_from_dir`.
3. `wiki-studio find "<question>" [--max-pages] [--json]`, `api.find`,
   `FindResult`, `FoundPage`.
4. `docs/agent-arm/` (README, `config.frozen.json`, `instruction.md`).
5. Tests (`tests/test_agent_verbs.py`), CLI contract verb list, README Verbs,
   CHANGELOG `[0.4.0]`, version 0.4.0, banner pinned to `v0.4.0`, SECURITY 0.4.x.

Not in scope: running any agent harness; changes in memkernel's repository;
model backends inside the arm; a new evaluation run here.

## Success criteria

1. On an lc-wiki-shaped workspace (index, no log): `init` creates the log only;
   `propose --from <draft> --promote` lands a decision page with its index and
   log lines; `find` returns that page for a question about it; `lint` passes.
2. `propose --from` refuses an index or log file with frontmatter and an invalid
   page with exit 4 and writes nothing; an existing page becomes an update;
   `glossary/index.md` is a content page.
3. `find` calls no backend and writes no query log.
4. The arm instruction is within 5 percent of memkernel's 1,832 bytes.
5. The single-writer test, the CLI contract tests and both evaluation runs'
   determinism tests stay green; full gate green; CI green.
