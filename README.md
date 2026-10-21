<p align="center">
  <img src="https://raw.githubusercontent.com/gosha70/wiki-studio/v0.5.0/docs/assets/wiki-studio-banner.png" alt="Wiki-Studio — Turn information into living knowledge." width="760">
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
wiki-studio --version           # 0.5.0
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
| `--prose` | add the prose checks: sentence length, semicolons, filler phrases, Summary and Key-ideas length, and the glossary term lock (an `avoid:` term used instead of its glossary term); advisory, exit 0 unless `--strict` |
| `--strict` | audit-format, health and prose findings become fatal (structural violations always are) |
| `--paths P [P ...]` | with `--health` or `--prose`, scope the findings to these wiki-relative pages (the term lock still reads the whole glossary) |
| `--backend NAME` | with `--health`, the backend for the contradiction check (skipped when omitted) |

### `wiki-studio audit-flush`

Commits pending lines of the ingest audit log. The only verb that runs
`git commit`; never invoked automatically.

| Flag | Effect |
|---|---|
| `--dry-run` | report the pending line count and blob SHA without committing |

### `wiki-studio info`

Prints the resolved layout before anything runs: `layout: default` or
`custom`, the root, wiki and proposals directories with where each came
from (`flag`, `env WIKI_STUDIO_…` or `default`) and whether they exist, the
query and audit logs, and which schema copy applies (`packaged`, or
`project` for a copy at `<wiki-dir>/schema/`). Overriding the root also
counts as custom. Read-only, exit 0. `--version` stays a single line.

| Flag | Effect |
|---|---|
| `--json` | the same facts as one JSON object |

Backends see wiki files under a heading named after the wiki directory
(`knowledge/wiki/index.md`, or `wiki/index.md` for a custom location);
every edit path they return is relative to that directory. If a backend
copies that exact heading prefix into a path, it is removed once before
validation; no other prefix is normalised, and a path that already has a
valid shape (`<page-dir>/<name>.md` or a root `<name>.md`) is left alone, so
a wiki directory named like a page directory (`concepts`) still works.

### `wiki-studio init`

Creates the wiki directory with a minimal `index.md` and `log.md` when they
are absent (`promote` needs both). Never overwrites; a second run is a no-op.
`--title` names a new index and log.

### `wiki-studio propose --from <dir>`

Lands pages you wrote yourself through the same gate as `ingest` output, with
no model. `<dir>` is laid out like the wiki: `decisions/<slug>.md`,
`concepts/<slug>.md` and so on are pages (a `create`, or an `update` when the
wiki already has that path, `glossary/index.md` included); `<dir>/index.md`
and `<dir>/log.md` hold the lines to append, one per line, never a page.

| Flag | Effect |
|---|---|
| `--promote` | apply the patch-set right after writing it |
| `--allow-out-of-repo` | with `--promote`: accept a proposals directory outside the root (otherwise the promote step exits 7, as `promote` does, and the written proposal stays there to promote later) |
| `--name NAME` | proposal directory name (default `<date>-<dir-name>`) |
| `--rationale TEXT` | recorded in `plan.json` and the audit archive |

Invalid pages exit 4 with every problem listed and nothing written.

### `wiki-studio find "<question>"`

Prints what `query` would put in front of a model, without calling one:
`index.md` first, then up to five index-linked pages ranked by the words they
share with the question, each with its title. Writes no query log. `--json`
for a JSON object, `--max-pages N` for a different limit.

`init`, `propose --from` and `find` are what an agent needs to use the wiki
from a shell with no model backend; `docs/agent-arm/` holds a ready arm for
memkernel's lifecycle suite built on them (issue #10).

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
| 10 | promote: a write into the wiki failed; every file it touched, including the failed one, rolled back |
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

## Evidence

What is measured so far is one component, not an agent: the querier's
page selection, which runs without a model (token overlap of the question
with each index-linked page's slug, path and first 400 characters, top 5).
The fixture under `eval/navigation/` is memkernel's documentation at tag
`v0.4.0` (ten files, attributed in NOTICE), a question set written from
those files and committed before any ingest, and a wiki that `wiki-studio
ingest` and `promote` produced from them once, through the normal gate, with
one attempt per document and nothing edited by hand. Gold pages were
assigned afterwards by reading the frozen wiki. Two runs exist, with the
same questions, corpus and stop list: run 1 on 0.2.0, run 2 on the 0.3.0
code after the issue #11 fix under a revised protocol (`eval/navigation/run2/`).
`python -m eval.navigation.run` reproduces run 1 and
`python -m eval.navigation.run eval/navigation/run2 --shared eval/navigation`
run 2; CI asserts both against their committed `results.json`. Every count
is in whitespace-separated words, not model tokens.

| Number | Run 1 (2026-10-16, on 0.2.0) | Run 2 (2026-10-16, on 0.3.0 at 61b3d9b) |
|---|---|---|
| Documents promoted, of the 10 in the corpus | 1 | 7 |
| Ingest coverage: answerable questions (29 of 35; 6 have no answer in the corpus) whose answer landed in some page | 3 of 29 (10.3%) | 21 of 29 (72.4%) |
| Navigation hit at 1 / at 5, over questions with a gold page | 3 of 3 / 3 of 3 | 3 of 21 (14.3%) / 10 of 21 (47.6%) |
| Competing questions where a distractor outranks the gold page (denominator: those of the 6 competing questions that have a gold page in that run: 1 in run 1, 4 in run 2) | 0 of 1 | 2 of 4 |
| Words loaded by `query` (index plus selected pages) vs the grep rule, over the questions with gold (none had empty grep output) | 2,286 vs 16,706; median ratio 0.16 | 40,647 vs 110,895; median ratio 0.33 |
| Questions the corpus cannot answer: empty selection / mean pages loaded | 4 of 6 / 0.33 | 1 of 6 / 4.0 |
| Ingest cost per document (tokens not exposed by the `claude` backend) | wall time not isolated (see below) | 52 s mean wall time, isolated (probe passed) |

The grep rule, the negative control: lower-case the question, split it
with the querier's own token pattern `[a-z0-9][a-z0-9-]*`, drop the
querier's own stop list (`eval/navigation/stopwords.txt`) and words shorter
than three characters, then over every corpus file take each line that
matches any remaining word whole-word and case-insensitively, with two lines
of context before and after, windows merged per file, and count the words.

Read these numbers with their caveats. Run 1 promoted one document in ten:
eight ingests failed validation because the model returned paths prefixed
with the wiki directory's name, a contract gap in the prompt
([issue #11](https://github.com/gosha70/wiki-studio/issues/11), fixed in
this release; run 1 was measured on 0.2.0), and one timed out. The three navigation numbers therefore rest on three
questions and one page, and the coverage number is the finding. The corpus
shares its vocabulary with the wiki schema, and the question writer knows
the scorer. During the run, a Claude Code Stop hook executed this
repository's test suite inside each backend call with the fixture's paths
inherited; that added test records to the fixture's audit and query logs
(preserved, not cleaned) and inflated per-document wall time, so the run is
marked `requires_review` in `eval/navigation/manifest.json` and documented in
`eval/navigation/ingest-notes.md`.

Run 2 is the clean measurement: the Stop hook was kept out of the backend
calls and that was verified by a recorded probe before the first attempt
(`run2/manifest.json`, `isolation_probe`), the commit, versions, model and
settings were pinned before the first attempt, one attempt per document, no
retries, nothing edited (`eval/navigation/run2_protocol.py` did the
bookkeeping). The model was pinned by full name, `claude-opus-5-5`, where run
1 used the alias `opus`; both are recorded. Seven documents promoted; the
three that did not (ADR-009, licensing, sibling-projects) failed on a
different contract gap than run 1: the model returned `index.md` as a full
page edit instead of an `append-index` line, which the validators correctly
rejected. That is a known, still unfixed prompt gap, recorded under "Known
issues" in the CHANGELOG for a later release. What two runs can show is
narrower than a cause: none of run 2's failures was the path-prefix defect
that #11 fixed, and run 2 also differed from run 1 in the pinned model name,
the hook isolation and the absence of a timeout, so the rise from one
promoted document to seven is not attributed to the fix alone. One scoring
note: for q25 the gold reason records that the distractor page also states
the answer; the selector ranked that page first, which the frozen rule
counts as a miss at 1 and as a distractor outranking gold. The rule is kept
as preregistered; had any page carrying the answer counted, hit at 1 would
be 4 of 21 and distractor-outranks 1 of 4 (q24 has the same kind of
distractor but selected nothing, so it is unaffected). The
navigation numbers now rest on 21 questions over nine content pages, and
they are the finding: with more pages, the token-overlap selector puts the
gold page first in one case out of seven and within the top five in about
half, and a question the corpus cannot answer now loads four pages on
average. Two facts make "about half" readable. The selector loads few pages:
2.24 on average for the 21 answerable questions, and for five of them (q06,
q13, q16, q21, q24) nothing beyond the index, because no index-linked page
shared a word with the question; those five are misses by construction and
a finding in their own right. And a derived baseline, computed in
`results.json` and not a measurement: drawing the same number of pages per
question at random from the nine index-linked pages would hit at 1 about
8.5% of the time and within the loaded set about 25%, against the observed
14.3% and 47.6%. The corpus and the question writer caveats from run 1 apply
unchanged. Agent-level evidence, an arm in `agent-memory-bench` next to
memkernel's, is tracked in
[issue #10](https://github.com/gosha70/wiki-studio/issues/10).

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
