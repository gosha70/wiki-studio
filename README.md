<p align="center">
  <img src="https://raw.githubusercontent.com/gosha70/wiki-studio/54bd46592032d86326366568ca2ca34b34228d55/docs/assets/wiki-studio-banner.png" alt="Wiki-Studio — Turn information into living knowledge." width="760">
</p>
<p align="center">
  <a href="https://memkernel.dev/wiki-studio/">memkernel.dev/wiki-studio</a> ·
  <a href="https://pypi.org/project/wiki-studio/">PyPI</a> ·
  <a href="https://github.com/gosha70/wiki-studio/blob/main/CHANGELOG.md">Changelog</a>
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
pip install 'wiki-studio[mcp]'   # optional: the MCP server, wiki-studio-mcp (see MCP)
wiki-studio --help
wiki-studio --version           # 0.7.0
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
| allowed source roots (directories outside the root that local links in pages may reference) | none | `--source-root` (repeatable) | `WIKI_STUDIO_SOURCE_ROOTS` (`os.pathsep`-separated) |
| query log | `<root>/doc_internal/wiki-query-log.jsonl` | | |
| ingest audit log | `<wiki-dir>/.audit/ingest-log.md` | | |
| schema override | `<wiki-dir>/schema/` (used when present) | | |
| wiki lock | `<wiki-parent>/.<wiki-dir-name>.wiki-studio.lock` | | |
| search cache (the `fts5` ranker's index; must lie outside the wiki) | `<wiki-parent>/.<wiki-dir-name>.wiki-studio.search.sqlite` | `--search-cache` | `WIKI_STUDIO_SEARCH_CACHE` |

Flags beat variables, variables beat defaults. The three flags are accepted
before or after the verb. Relative flag and variable values are taken from
the current directory. A `--search-cache` or `WIKI_STUDIO_SEARCH_CACHE` path
inside the wiki directory is refused (exit 1).

The lock and the search cache sit beside the wiki directory, never inside it.
Where the wiki lives in a git checkout, one `.gitignore` pattern covers both:

```gitignore
.<wiki-dir-name>.wiki-studio.*
```

(`.wiki.wiki-studio.*` for the default `knowledge/wiki`.) The search cache is
derived data: `find` and `query` with `--ranker fts5` refresh it from the
pages on every call (each eligible page is read and hashed, no timestamp
shortcut), rebuild it when it was built for another wiki, format or ranker
configuration, and remove and rebuild it when it is corrupt. When it cannot
be used safely (a symlink at the path or its directory, a directory that is
not writable, a read-only file system, another process holding it past five
seconds) that call ranks with an in-memory index, prints one warning and
still exits 0. The cache only ranks; the text a prompt carries is always read
from the wiki in that call. It is created readable by its owner only, because
it holds a copy of every eligible page's text. **To reset it, delete the
file**; the next `fts5` call rebuilds it. `info` reports its path and state
(`present`, `missing` or `unusable`, with a reason).

## Verbs

### `wiki-studio ingest <source>`

Runs the four-question gate over a source file and writes a patch-set
(`plan.json` plus `preview/<page>.md` for every page it would create or
update) under `<proposals-dir>/<date>-<source-stem>/`, then appends one
line to the ingest audit log.

An `update` to a page the wiki already has is compared with the live page.
Citations (`sources[].path`, `path:` in the body, `path:line`), backticked
identifiers and numbers with a unit that the new content drops are recorded as
`edits[].fact_warnings` in `plan.json` and printed to stderr as
`fact-check: <path>: N item(s) removed`. The check is a heuristic over
citations, identifiers and quantities: it compares those three kinds of
token as sets and does not detect a change of meaning, a reworded claim
or a dropped sentence that carries none of them. The warnings are
advisory: the exit code does not change and `promote` ignores them. A live page that
cannot be read or decoded is reported as `not compared` and recorded as
`edits[].fact_check_error`; the patch-set is still written. See
`docs/patch-set-format.md`. The proposal directory, its files, the
`.ingest-snapshot/` copy and the ingest-log record are all written under
the wiki lock, and a publication that fails part-way is removed before the
lock is released.

| Flag | Effect |
|---|---|
| `--legacy-single-source` | v1 single-page proposal: one `<date>-<slug>.md` file instead of a patch-set; a previous file of that name is moved aside and restored if publication fails (a leftover `<name>.bak-<pid>-<n>` beside it is that earlier proposal, to review by hand) |
| `--backend NAME` | `claude`, `codex`, `cursor`, `pi` or `test` (see Backends) |
| `--dry-run` | gate only, no draft body (legacy) / audit record marked as a dry run (multi-page) |
| `--check` | run the gate with zero filesystem side effects; exit 0 accept, 1 reject. Mutually exclusive with `--dry-run` |
| `--output-dir DIR` | write the proposal somewhere other than the proposals directory |
| `--allow-out-of-repo` | accept a source outside the root (otherwise exit 7) |
| `--debug-unsafe-output` | show raw backend stderr instead of a redacted fingerprint |

### `wiki-studio promote <proposal-dir>`

Applies a patch-set to the wiki. A promotion is validated, serialised
against other wiki-studio writers on the same machine, and rolled back on
failure; it is not crash-safe across files, and uncoordinated readers may
observe intermediate state. The staged tree is validated page by page and
by the structural linter before anything is written; the commit writes only
the paths the patch-set names plus the proposal's own archive under
`<wiki-dir>/.audit/proposals/`; on an exception during the commit every
touched file is restored to its exact previous bytes. A process killed in
the middle of the commit can leave some files written and others not: the
receipt described below recovers from a failure between the protocol's
steps, not from a crash inside the commit. On success the proposal
directory is archived under `<proposals-dir>/.applied/`. This is the only
code path that writes into the wiki.

| Flag | Effect |
|---|---|
| `--dry-run` | take the lock, stage, check the revision preconditions against the live wiki, release the lock, then validate the staged snapshot; writes nothing. Point-in-time evidence: a real promote checks again |
| `--allow-out-of-repo` | accept a proposal directory outside the root (otherwise exit 7) |
| `--allow-unguarded-updates` | apply `update` edits that carry no `base_sha256` (proposals from before 0.6.0, drafts without `.base.json`). Compatibility mode with incomplete conflict protection: a stale draft can overwrite a newer page; the paths are recorded as `unguarded_paths` in the receipt and printed as warnings. Without it such an update exits 9 |
| `--by NAME` | who promotes, recorded as the receipt's `actor` with source `flag`; see Attribution below |
| `--lock-timeout SECONDS` | how long to wait for the wiki lock that serialises wiki-studio writers on this machine (default 30, or `WIKI_STUDIO_LOCK_TIMEOUT`; `inf` waits indefinitely); on expiry exit 10 with reason `lock_timeout`. Also accepted by every other verb |

Before the commit, still under the lock, promote checks the revision
preconditions against the live wiki: a `create` needs its target absent; an
`update` is applied only while the live page's sha256 equals the edit's
`base_sha256` (the hash of the page as its author read it, see `read`); an
`update` without a base hash is refused unless `--allow-unguarded-updates`
is passed. A mismatch exits 9 naming the page and writes nothing. Appends
land on the current content, which was staged under the same lock.

Promote writes a `receipt.json` beside the proposal (moved with it into
`.applied/`) that records the outcome; promoting the same directory again
finishes an interrupted archive step and never re-applies an edit.

The wiki lock is an OS advisory lock on
`<wiki-parent>/.<wiki-dir-name>.wiki-studio.lock`, outside the wiki (ignore
it with the `.gitignore` pattern in Layout), keyed to the resolved wiki directory and taken by
`promote`, `propose --promote`, proposal-directory creation, the ingest-log
append and `audit-flush`. Its scope is one machine and one filesystem: it
is not distributed, it does not protect against direct edits of wiki files
by an editor or a script that does not take it, and network filesystems
are out of scope. Recovery of an interrupted promotion needs a filesystem
with stable inode identity. Details: `docs/patch-set-format.md`.

### `wiki-studio read <path>`

Prints one wiki page, read exactly once. `<path>` is wiki-relative
(`index.md`, `concepts/<slug>.md`); a path outside the wiki, or one that
passes through a symlink, exits 7, a missing page exits 5 and a page that is
not UTF-8 exits 4 with no content printed.

| Flag | Effect |
|---|---|
| `--json` | print `{"path", "sha256", "content"}`: the decoded text and the sha256 of the bytes it was decoded from |

This is how a replacement records the page it was drafted from. The
procedure is read, draft, record: read the page with `read --json`, write
the new version from that content, and record the printed `sha256` as the
edit's base revision, in `.base.json` beside a `propose --from` draft or as
`PageEdit.base_sha256` for `api.propose`. `promote` then applies the
replacement only while the live page still has that hash. `find` reports
the sha256 and byte count of each page it read (0.8.0); `info` stays
configuration.

### `wiki-studio query "<question>"`

Reads `index.md` first, loads the most relevant linked pages (selected as
`find` selects them, see below), asks the backend, and prints the answer;
citations and the pages loaded go to stderr and the pages-loaded set, the
ranker and the bytes loaded are appended to the query log.

Every citation in the reply is checked against the text that was in the
prompt: the cited page must be `index.md` or one of the pages loaded, and
the fragment must occur in that page's captured text (whitespace runs are
collapsed before comparing). A non-empty answer needs at least one
citation; an empty answer with one citation quoting `index.md` is the
abstention form. A reply that fails the check exits 4 naming the page.
The check verifies that the quotation is real, against the snapshot the
model saw rather than a file reread afterwards; it does not verify that
the fragment logically supports the answer.

| Flag | Effect |
|---|---|
| `--backend NAME` | as for ingest |
| `--max-pages N` | cap on pages loaded into the prompt (default 5) |
| `--ranker {fts5,index-first}` | how pages are ranked, as for `find` |
| `--max-bytes N` | byte budget for `index.md` plus the pages, as for `find` |
| `--file-back` | also ingest the question + answer as a source and write a patch-set the curator can promote; an `update` gets the fact warnings described under `ingest` |
| `--output-dir DIR` | with `--file-back`, where to write that patch-set |
| `--debug-unsafe-output` | as for ingest |

### `wiki-studio lint`

Structural lint of every page: frontmatter present and well formed with
the required keys; `page_type` known; `slug` equals the file name and is
unique; the page lives in its type's directory; intra-wiki links resolve;
every page except `index.md` and `log.md` is reachable from `index.md`;
every page (`index.md` and `log.md` included) is valid UTF-8. A page that is
not is one violation, `<path>: not valid UTF-8 (<reason> at byte <n>)`, and
its other checks are skipped; like every structural violation it fails
`lint` and refuses every `promote` until the page is fixed (0.8.0). The audit tree under `.audit/` is always checked against
`schema/audit-rules.md` as well.

| Flag | Effect |
|---|---|
| `--health` | add the knowledge-health checks: stale `path:` sources (a heuristic that verifies the cited path still exists, not that the recorded revision is current), weak orphans, missing cross-links and, with a backend, contradictions |
| `--prose` | add the prose checks: sentence length, semicolons, filler phrases, Summary and Key-ideas length, and the glossary term lock (an `avoid:` term used instead of its glossary term); advisory, exit 0 unless `--strict` |
| `--strict` | audit-format, health and prose findings become fatal (structural violations always are) |
| `--paths P [P ...]` | with `--health` or `--prose`, scope the findings to these wiki-relative pages (the term lock still reads the whole glossary) |
| `--backend NAME` | with `--health`, the backend for the contradiction check (skipped when omitted) |

### `wiki-studio approve <page>...`

Records that each page's live revision is approved under the wiki's policy:
one immutable record per decision under `<wiki>/.audit/approvals/`, written
under the wiki lock. Frontmatter never makes a page approved; `status: stable`
alone is `unapproved`. The batch is checked first and refused (exit 9,
nothing written) for a draft, a page carrying `superseded_by`, a
structural-lint violation for the page, or a missing approver when the
policy requires one. A legacy wiki (no manifest) is refused (exit 4); run
`init` first. `api.review_state` reports each page `approved`, `stale`,
`policy-changed`, `unapproved` or `superseded`. Details in
`docs/knowledge-contract.md`.

| Flag | Effect |
|---|---|
| `--revision SHA` | the sha256 you reviewed (`read --json`); refused when the live page differs; one page only |
| `--by NAME` | the approver, recorded with source `flag` (else `WIKI_STUDIO_ACTOR`); attribution, not authentication |

### `wiki-studio findings`

Reports what needs a curator's attention without calling a model: counts by
kind, then each finding. The kinds are the health checks that need no backend
(`stale-claim`, `weak-orphan`, `missing-cross-link`, `avoid-format`), the
review kinds `unapproved`, `approval-stale` and `approval-policy-changed`,
`superseded-still-indexed` (`index.md` links a superseded page) and
`no-page-id`. It takes no backend, reads only, takes no lock, and exits 0 on a
completed run whatever it finds; `lint --health --strict` stays the CI gate.
The JSON format is in `docs/knowledge-contract.md`.

| Flag | Effect |
|---|---|
| `--json` | print `findings_version`, `counts`, `pages_checked` and `findings` as one JSON object |
| `--paths P [P ...]` | scope every kind to these wiki-relative pages |

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
counts as custom. Then the knowledge contract: package version, schema
contract and fingerprints (with drift), format versions, capabilities and the
root manifest (`governed`, `managed` or `legacy`), and discovery (whether
this Python's SQLite has FTS5, the default ranker and where it came from, the
ranker configuration hash); the keys are in
`docs/knowledge-contract.md`. Read-only, exit 0 (4 for a malformed or newer
manifest). `--version` stays a single line.

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
are absent (`promote` needs both), and the root manifest
`<wiki>/.wiki-studio.json`: the wiki's id, the schema contract and
fingerprint, and the review policy (`approve` needs it). Never overwrites; a
wiki made before 0.7.0 gains the manifest and nothing else changes; a second
run is a no-op. Details in `docs/knowledge-contract.md`.

| Flag | Effect |
|---|---|
| `--title TEXT` | names a new index and log |
| `--update-schema` | acknowledge changed project schema overrides: rewrites only the manifest's `schema_fingerprint`, under the wiki lock |

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
| `--allow-unguarded-updates` | with `--promote`: as for `promote` (compatibility mode with incomplete conflict protection) |
| `--name NAME` | proposal directory name (default `<date>-<dir-name>`) |
| `--rationale TEXT` | recorded in `plan.json` and the audit archive |
| `--by NAME` | who proposes, recorded as `plan.json`'s `proposer` (and, with `--promote`, the receipt's `actor`) with source `flag`; see Attribution below |

Every page the patch-set creates gets a fresh `page_id: pg-<32 hex>` as its
last frontmatter line, in the preview and so in the committed page; a
`page_id` you wrote yourself is kept.

Invalid pages exit 4 with every problem listed and nothing written. An
`update` prints the fact warnings described under `ingest` after the
patch-set is written and before the optional `--promote` step.

An `update` carries the base revision recorded in `<dir>/.base.json`, a
JSON object mapping each replaced wiki path to the `sha256` that
`wiki-studio read <path> --json` printed for the page the draft was made
from:

```json
{"decisions/retry-backoff.md": "3f6c…e1"}
```

`propose` never fills a missing hash from the live page: a page without a
manifest entry is an unguarded update, which `promote` refuses unless
`--allow-unguarded-updates` is passed.

#### Attribution

`--by NAME` on `propose` and `promote` (`by=` on `api.propose` and
`api.promote`) names who acts. Without it the name comes from
`WIKI_STUDIO_ACTOR`; without either, none is recorded. `plan.json` records
the proposer and the receipt the promoter as `{name, source}` with `source`
`flag`, `env` or `none`; the OS user name is never captured. `--by` is
attribution, not authentication: nothing verifies the name, and the host
that runs wiki-studio supplies authority. The local audit files give
traceability, not tamper-proof evidence.

### `wiki-studio find "<question>"`

Prints what `query` would put in front of a model, without calling one:
`index.md` first, then up to five eligible index-linked pages within a byte
budget, each with its title and size. Writes nothing (no query log, no file in
the wiki). A page is eligible when `index.md` links it inside the wiki (no
symlink, no `../`), it is a regular file, it is valid UTF-8 and it carries no
`superseded_by`; `index.md` and `log.md` are never candidates.

Two rankers order the eligible pages. `index-first` (the default) counts the
question's words in each page's slug, path and first 400 characters, as
0.7.0 did. `fts5` ranks by bm25 over SQLite FTS5 (path words, title, headings
and body, weighted 4, 4, 2, 1); ties go to the page listed first in
`index.md`. If this Python's SQLite has no FTS5, `fts5` falls back to
`index-first`, prints one notice to stderr
(`find: FTS5 is not available in this Python's SQLite (<reason>); using
index-first`) and still exits 0; `info` reports whether FTS5 is available.

The budget counts the UTF-8 bytes of `index.md` plus the selected pages. A
page that does not fit is skipped, listed as omitted, and the next page is
tried; pages are never truncated. If `index.md` alone is over budget, no
page is loaded and a warning goes to stderr.

| Flag | Effect |
|---|---|
| `--ranker {fts5,index-first}` | the ranker; overrides `WIKI_STUDIO_RANKER`, which overrides the default `index-first`; an unknown name exits 1 |
| `--max-bytes N` | the byte budget (default 65536); not a positive integer: exit 1 |
| `--max-pages N` | at most this many pages (default 5) |
| `--json` | one JSON object: `question`, `index`, `pages` (`path`, `file`, `title`, `sha256`, `bytes`), `ranker`, `fallback_reason`, `bytes_loaded`, `max_bytes`, `ranker_config_hash`, `omitted` (`path`, `bytes`), `ineligible` (`path`, `reason`: `missing`, `not-regular-file`, `not-utf8` or `superseded`), `warnings` |

`init`, `propose --from`, `find` and `read` are what an agent needs to use
the wiki from a shell with no model backend; `docs/agent-arm/` holds a ready
arm for memkernel's lifecycle suite built on them (issue #10).

## Exit codes

| Code | Meaning |
|---|---|
| 0 | success (for `lint`: no fatal findings; for `ingest --check`: gate accepted) |
| 1 | `ingest --check` rejected; fatal lint findings; a rejected flag combination |
| 2 | backend not found (unknown name, CLI not on PATH, nothing to auto-detect); usage error |
| 3 | backend invocation failed (non-zero exit, timeout) |
| 4 | contract violation: the backend's response failed shape or semantic validation; a page `read` that is not UTF-8; a malformed, newer or unknown-schema manifest; schema drift on a governed wiki; `approve` on a wiki without a manifest |
| 5 | source file, page or proposal directory missing |
| 6 | output write failure; `approve` published some records and then failed (the error names the pages published and not) |
| 7 | source or proposal path outside the root (`--allow-out-of-repo` overrides); a `read` path outside the wiki |
| 8 | verb not implemented |
| 9 | promote: staged tree failed validation, or a revision precondition failed (stale or unguarded `update`, `create` of a page that now exists); the wiki is unchanged. approve: the batch was refused; nothing was written |
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
| `WIKI_STUDIO_SOURCE_ROOTS` | `os.pathsep`-separated directories outside the root that local links in pages may reference (see Layout) |
| `WIKI_STUDIO_RANKER` | the ranker `find` and `query` use when `--ranker` is not given: `fts5` or `index-first` (default `index-first`) |
| `WIKI_STUDIO_SEARCH_CACHE` | where the `fts5` ranker keeps its search cache when `--search-cache` is not given (default beside the lock file; never inside the wiki; see Layout) |
| `WIKI_STUDIO_ACTOR` | who proposes or promotes when `--by` is not given, recorded with source `env` (attribution, not authentication) |
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
in `docs/adr/`. Since 0.5.0 a glossary page may carry one optional key,
`avoid:`, one line of comma-separated terms the wiki should not use for
that term (`avoid: alignment check, origin check`); a `glossary/index.md`
entry names its terms on an `Avoid: …` line instead. `lint --prose` reports
their use on other pages, outside code and quotes. Decision record:
`docs/adr/0001-glossary-avoid-key.md`.

Schema version 2 (0.7.0) adds optional page keys: `page_id`
(`pg-<32 hex>`, the page's stable identity, assigned to pages that
`propose --from` and `ingest` create; lint refuses a malformed or duplicated
one), `superseded_by` and memkernel's `corrects`, and reserves `approved`,
`approved_by`, `approval` and `review_state` for the approval record.
Decision record: `docs/adr/0002-page-identity-and-review-keys.md`.

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

debt = api.findings(paths)                             # FindingsResult; no backend, no model call
print(debt.counts)

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

A replacement names the revision it was drafted from. `read_page` reads the
page once and returns its bytes, text and the sha256 of those bytes; pass
that hash as the edit's `base_sha256` and `promote` applies the update only
while the live page still has it (`PromoteValidationError`, exit 9,
otherwise). `promote(..., allow_unguarded_updates=True)` applies updates
without a hash and lists them in `PromoteResult.unguarded_paths` and
`.warnings` (compatibility mode with incomplete conflict protection).

```python
page = api.read_page("concepts/retry-budget.md", paths)          # ReadResult: path, data, text, sha256
edit = PageEdit("concepts/retry-budget.md", "update", page.text + "\nMore.\n", "Extend.", base_sha256=page.sha256)
api.promote(api.propose([edit], paths, name="2026-10-16-retry-budget-more"), paths)
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

## MCP

An MCP host (Claude Code, Kiro) can use the wiki without a shell through
the optional adapter, the one optional dependency (the official `mcp` SDK):

```bash
pip install 'wiki-studio[mcp]'
claude mcp add wiki-studio -- wiki-studio-mcp --root /path/to/project --by agent
```

`wiki-studio-mcp` serves eight tools over stdio: `find`, `read_page`,
`propose`, `promote`, `lint`, `info`, `findings` and `review_state`. The
wiki, the actor (`--by`) and the default ranker are fixed at launch; no tool
takes a root, directory, backend or actor, and `approve`, `ingest`, `query`,
`audit-flush` and `init` are not exposed. `--disable-tool promote` is
propose-only mode: proposals wait for a person to promote and approve them.
Errors are `{error, exit_code, message}` with the exit codes above. Without
the extra, `wiki-studio-mcp` prints the install instruction and exits 2; the
base install still imports nothing outside the standard library. Flags,
results, host configuration and the trace file:
[`docs/mcp-adapter.md`](docs/mcp-adapter.md); the dependency review and the
tool contract: `docs/adr/0003-optional-mcp-dependency-and-tool-contract.md`.

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

Run 3 and a held-out set (0.8.0) measure the second ranker, `fts5`, beside
`index-first` without touching runs 1 and 2: their files are pinned by
sha256 (`tests/test_frozen_runs.py`) and the numbers above stay the
published baseline. `python -m eval.navigation.discovery run` calls `find`
with both rankers and reports, beside every hit rate, the eligible page
count and the random baseline, plus absent-question behaviour, bytes and
words loaded, and latency through the cache and without it. Run 3 is the
development set, run 2's frozen wiki and its 21 questions with a gold page:
`eval/navigation/run3/results-untuned.json` is the untuned configuration's
result, committed before any tuning, and it is development-set evidence
only. The default is decided on a fresh held-out corpus, the eight
user-facing READMEs of mapatlas at a pinned commit, under the preregistered
protocol in `eval/navigation/heldout/protocol.md`: questions committed
before the ingest, one ingest with no retries, the wiki and the gold frozen
before tuning, one held-out run under a frozen configuration hash. `fts5`
becomes the default only if it is no worse than `index-first` at hit at 1
and at 5 there, with at least 15 gold questions and ten eligible pages;
until that run exists the default is `index-first`.

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
