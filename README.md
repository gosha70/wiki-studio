<p align="center">
  <img src="docs/assets/wiki-studio-banner.png" alt="Wiki-Studio — Turn information into living knowledge." width="760">
</p>

Karpathy-pattern LLM wiki maintainer: a curated markdown knowledge base
(`index.md`, `log.md`, typed pages with cited sources) that agents ingest
into, query from and lint. Standard library only; the LLM backends are
copilot CLIs the tool shells out to.

The code was extracted from
[gosha70/code-copilot-team](https://github.com/gosha70/code-copilot-team)
(see `NOTICE`); the page schema is shared with
[memkernel](https://github.com/gosha70/memkernel)'s wiki bridge.

## Install

```bash
pip install wiki-studio          # Python 3.11–3.13, no runtime dependencies
wiki-studio --help
wiki-studio --version           # 0.2.0
```

From a checkout: `poetry install`, then `poetry run wiki-studio --help`.

## Layout

With no flags and no variables `wiki-studio` reproduces the original
code-copilot-team layout under the git toplevel of the current directory:

| Location | Default | Flag | Variable |
|---|---|---|---|
| root (confines sources and proposals; anchors `path:` citations) | git toplevel of the current directory, else the current directory | `--root` | `WIKI_STUDIO_ROOT` |
| wiki directory | `<root>/knowledge/wiki` | `--wiki-dir` | `WIKI_STUDIO_WIKI_DIR` |
| proposals directory | `<root>/doc_internal/proposals` | `--proposals-dir` | `WIKI_STUDIO_PROPOSALS_DIR` |
| query log | `<root>/doc_internal/wiki-query-log.jsonl` | | |
| ingest audit log | `<wiki-dir>/.audit/ingest-log.md` | | |
| schema override | `<wiki-dir>/schema/` (used when present) | | |

Flags beat variables, variables beat defaults. The three flags are accepted
before or after the verb. Relative flag and variable values are taken from
the current directory.

## Verbs

### `wiki-studio ingest <source>`

Runs the four-question gate over a source file and writes a patch-set
(`plan.json` plus `preview/<page>.md` for every page it would create or
update) under `<proposals-dir>/<date>-<source-stem>/`, then appends one
line to the ingest audit log.

| Flag | Effect |
|---|---|
| `--legacy-single-source` | v1 single-page proposal: one `<date>-<slug>.md` file instead of a patch-set |
| `--backend NAME` | `claude`, `codex`, `cursor`, `pi` or `test` (see Backends) |
| `--dry-run` | gate only, no draft body (legacy) / audit record marked as a dry run (multi-page) |
| `--check` | run the gate with zero filesystem side effects; exit 0 accept, 1 reject. Mutually exclusive with `--dry-run` |
| `--output-dir DIR` | write the proposal somewhere other than the proposals directory |
| `--allow-out-of-repo` | accept a source outside the root (otherwise exit 7) |
| `--debug-unsafe-output` | show raw backend stderr instead of a redacted fingerprint |

### `wiki-studio promote <proposal-dir>`

Applies a patch-set to the wiki atomically. The staged tree is validated
page by page and by the structural linter before anything is written; on
success the proposal directory moves to `<proposals-dir>/.applied/` and
the accepted proposal is archived under `<wiki-dir>/.audit/proposals/`.
This is the only code path that writes into the wiki.

| Flag | Effect |
|---|---|
| `--dry-run` | build and validate the staged tree, change nothing |
| `--allow-out-of-repo` | accept a proposal directory outside the root (otherwise exit 7) |

### `wiki-studio query "<question>"`

Reads `index.md` first, loads the most relevant linked pages, asks the
backend, and prints the answer; citations and the pages loaded go to
stderr and the pages-loaded set is appended to the query log.

| Flag | Effect |
|---|---|
| `--backend NAME` | as for ingest |
| `--max-pages N` | cap on pages loaded into the prompt (default 5) |
| `--file-back` | also ingest the question + answer as a source and write a patch-set the curator can promote |
| `--output-dir DIR` | with `--file-back`, where to write that patch-set |
| `--debug-unsafe-output` | as for ingest |

### `wiki-studio lint`

Structural lint of every page: frontmatter present and well formed with
the required keys; `page_type` known; `slug` equals the file name and is
unique; the page lives in its type's directory; intra-wiki links resolve;
every page except `index.md` and `log.md` is reachable from `index.md`.
The audit tree under `.audit/` is always checked against
`schema/audit-rules.md` as well.

| Flag | Effect |
|---|---|
| `--health` | add the knowledge-health checks: stale `path:` sources, weak orphans, missing cross-links and, with a backend, contradictions |
| `--strict` | audit-format and health findings become fatal (structural violations always are) |
| `--paths P [P ...]` | with `--health`, scope the findings to these wiki-relative pages |
| `--backend NAME` | with `--health`, the backend for the contradiction check (skipped when omitted) |

### `wiki-studio audit-flush`

Commits pending lines of the ingest audit log. The only verb that runs
`git commit`; never invoked automatically.

| Flag | Effect |
|---|---|
| `--dry-run` | report the pending line count and blob SHA without committing |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | success (for `lint`: no fatal findings; for `ingest --check`: gate accepted) |
| 1 | `ingest --check` rejected; fatal lint findings; a rejected flag combination |
| 2 | backend not found (unknown name, CLI not on PATH, nothing to auto-detect); usage error |
| 3 | backend invocation failed (non-zero exit, timeout) |
| 4 | contract violation: the backend's response failed shape or semantic validation |
| 5 | source file or proposal directory missing |
| 6 | output write failure |
| 7 | source or proposal path outside the root (`--allow-out-of-repo` overrides) |
| 8 | verb not implemented |
| 9 | promote: staged tree failed validation; the wiki is unchanged |
| 10 | promote: filesystem failure while writing the wiki; prior writes rolled back |
| 11 | audit-flush: not a git work tree, append-only invariant violated, malformed log, or git failed |

## Backends

| Name | Binary on PATH | Notes |
|---|---|---|
| `claude` | `claude` | Claude Code |
| `codex` | `codex` | Codex CLI |
| `cursor` | `cursor-agent` | Cursor |
| `pi` | `pi-code` | selectable with `--backend pi`; auto-detected only with `WIKI_STUDIO_ENABLE_PI=1` |
| `test` | (in-process) | deterministic responses; what the test suite and CI use |

Resolution order: `--backend`, then `WIKI_STUDIO_BACKEND`, then auto-detect,
which probes PATH for `claude`, `codex`, `pi` (only when enabled), `cursor`
in that order. `WIKI_INGEST_BACKEND` is still accepted and prints a
deprecation warning on stderr.

Backend stderr may echo source content, so error messages carry a
redacted fingerprint of it unless `--debug-unsafe-output` is given.

## Environment variables

| Variable | Meaning |
|---|---|
| `WIKI_STUDIO_ROOT` | project root (see Layout) |
| `WIKI_STUDIO_WIKI_DIR` | wiki directory |
| `WIKI_STUDIO_PROPOSALS_DIR` | proposals directory |
| `WIKI_STUDIO_BACKEND` | default backend name |
| `WIKI_STUDIO_ENABLE_PI` | `1` adds `pi` to the auto-detect order |
| `WIKI_INGEST_BACKEND` | deprecated alias of `WIKI_STUDIO_BACKEND` |

## Schema

The page schema (`page-types.md`, `ingest-rules.md`, `citation-rules.md`,
`lint-rules.md`, `audit-rules.md`, `WIKI_MAINTAINER.md`) ships inside the
package and is what the prompts and the linter follow. A project may carry
its own copy under `<wiki-dir>/schema/`; when that directory exists it is
used instead of the packaged one. The schema is a published contract
shared with memkernel's `WikiExporter` and `WikiImporter`; changing
frontmatter keys, page types or directory names needs a decision record
in `docs/adr/`.

The same facts are available as code in `wiki_studio.schema`: `PAGE_TYPES`
maps each page type to a `PageTypeSpec` (`directory`, `required_sections`,
`promotable`, `sources_required`), and `VALID_PAGE_TYPES`, `PAGE_TYPE_DIRS`
and `REQUIRED_KEYS` are derived from it. The linter and the validators read
this module; a consumer that keeps its own copy can test it against
`PAGE_TYPES`, and a test here keeps the module in step with `page-types.md`.

## Library

```python
from pathlib import Path

from wiki_studio import api
from wiki_studio.paths import WikiPaths

paths = WikiPaths.for_root(Path("."))                 # or WikiPaths.resolve(wiki_dir="kb")

result = api.ingest(Path("notes/2026-10-12-outage.md"), paths, backend="claude")
print(result.disposition, result.written, result.edits)

api.promote(result.written, paths)                     # PromoteResult
answer = api.query("what caused the outage?", paths, backend="claude").answer
print(answer.answer, [c.page for c in answer.citations])

report = api.lint(paths, health=True, strict=True)     # LintResult
print(report.passed, report.violations, report.health.findings)

api.audit_flush(paths, dry_run=True)                   # AuditFlushResult
```

A caller that composes pages itself (memkernel's exporter, a migration
script) hands them to `propose` and gets a proposal directory `promote`
accepts, so they pass the same gate as a backend's draft:

```python
from wiki_studio.api import PageEdit

edits = [
    PageEdit("concepts/retry-budget.md", "create", page_markdown, "New concept."),
    PageEdit("index.md", "append-index", "- [Retry budget](concepts/retry-budget.md) — draft.", "Index it."),
    PageEdit("log.md", "append-log", "- 2026-10-15 — created retry-budget (concept): draft.", "Log it."),
]
proposal = api.propose(edits, paths, name="2026-10-15-retry-budget")   # Path; ContractViolationError on bad edits
api.promote(proposal, paths)
```

The functions raise the exceptions in `wiki_studio.errors`; each carries the
exit code the CLI would use. `backend` may be a name, `None` (resolution
order as above) or any object with `call(prompt) -> dict`.

The `api` functions and their keywords, the result dataclasses, `PageEdit`,
`PageAction`, `WikiPatchSet` and the proposal directory format
([`docs/patch-set-format.md`](docs/patch-set-format.md)) are public and
follow semantic versioning: removals and renames only in a major version,
additions with defaults in a minor one.

Consumer recipes for code-copilot-team, memkernel and document-assistant
are in [`docs/consumers.md`](docs/consumers.md).

## Development

```bash
poetry install
poetry run ruff check src/ tests/ && poetry run ruff format --check src/ tests/
poetry run mypy src/
poetry run pytest -q --cov=wiki_studio --cov-fail-under=80
poetry build
```

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
