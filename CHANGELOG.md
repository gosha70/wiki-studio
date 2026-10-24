# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- The wiki lock (`wiki_studio.wikilock.WikiLock`): an OS advisory lock
  (`fcntl.flock` on POSIX) on `<wiki-parent>/.<wiki-dir-name>.wiki-studio.lock`,
  keyed to the resolved wiki directory and held by `promote`,
  `propose --promote`, proposal-directory creation (`ingest`, `query
  --file-back`, `api.propose`), the ingest-log append and `audit-flush`. Two
  promotes that start together on the same machine no longer revert each
  other's pages (the lock is not distributed and does not cover direct edits).
  `--lock-timeout` and `WIKI_STUDIO_LOCK_TIMEOUT` (default 30 s; `inf` waits
  indefinitely); on expiry every holder, `ingest` included, exits 10 with
  reason `lock_timeout`. `info` prints the lock file and timeout.
- Receipts: `promote` writes `receipt.json` into the proposal directory before
  the commit (`committing`), rewrites it after (`committed`) and archives it
  with the proposal: the submission digest and manifest, the wiki's device and
  inode, every tracked write with its pre- and post-commit sha256, timing and
  the promoter's identity. Promoting the same directory again resolves the
  receipt instead of re-applying anything; refusals exit 10 with reasons
  `uncertain_outcome`, `wiki_mismatch`, `wiki_identity_unavailable` or
  `payload_changed`. Documented in `docs/patch-set-format.md`.
- `PromoteApplyError.reason` (`wiki_studio.errors.REASON_*`); the CLI prints
  it as `[reason=...]`.
- Base revisions for replacements: `PageEdit.base_sha256` (last field,
  default `None`) and the optional `plan.json` key `edits[].base_sha256`, the
  sha256 of the page bytes the author read. `ingest` records the hash of the
  exact bytes it placed in the prompt for each candidate page it shows (the
  model cannot set or change it); `propose --from` reads `<draft>/.base.json`
  (wiki path to sha256) and never the live page; `api.propose` passes the
  caller's value through.
- `wiki-studio read <path>` and `api.read_page(path, paths)`: one page, read
  once, returning bytes, UTF-8 text and the sha256 of those bytes (`--json`
  prints `{"path", "sha256", "content"}`); a path outside the wiki or through
  a symlink exits 7, a missing page 5, a page that is not UTF-8 exits 4. The
  documented procedure for a replacement is read, draft, record.
- Revision preconditions, checked under the lock immediately before the
  commit: a `create` requires its target absent, an `update` with
  `base_sha256` requires the live page to still have that hash, appends land
  on the current content. A mismatch is `PromoteValidationError` (exit 9)
  naming the page, with nothing written.
- `--allow-unguarded-updates` / `api.promote(allow_unguarded_updates=True)`:
  compatibility mode with incomplete conflict protection that applies
  `update` edits without a base hash and records them as `unguarded_paths` in
  the receipt. `PromoteResult.unguarded_paths` and `PromoteResult.warnings`
  (both last, with defaults); the CLI prints the warnings to stderr.

### Changed

- An `update` without `base_sha256` is refused (exit 9) with the two
  remedies named: regenerate the proposal from a fresh `read`, or pass the
  compatibility option. Creates and appends from older proposals promote
  unchanged.
- `promote --dry-run` takes the lock, stages, checks the revision
  preconditions against the live wiki, releases the lock and then validates
  the staged snapshot; it still writes nothing. The result is point-in-time
  evidence; a real promote checks again.

- The commit writes only the paths the patch-set names plus the proposal's own
  `.audit/proposals/` archive; a staged file outside that set is never written
  back.
- The archive under `<proposals-dir>/.applied/<name>/` is written from the
  captured bytes into a hidden temporary sibling and published by atomic
  rename; names are unchanged (`<name>`, `-2`, `-3`). The original directory
  is removed only while it still matches the archive.
- Digest recipe 2 (`audit.payload_digest`: no dot-component exclusion) for
  receipts and for new ingest-log records, which carry the optional key
  `hash_recipe: 2`; recipe 1 (`audit.proposal_hash`) stays implemented to
  verify records written before 0.6.0. The audit lint accepts the optional key
  in `v: 1`. A consumer that recomputes `proposal_hash` against the documented
  recipe must pick the recipe by the key (`schema/audit-rules.md`).
- A `preview` pointer that does not name a regular file under `preview/` is a
  contract violation (exit 4).
- Proposal directories are created exclusively under the lock: `ingest` and
  `query --file-back` take `<name>-2`, `-3` on a clash instead of writing into
  an existing directory; `api.propose` still raises `OutputWriteError`.
- The `Operating System` classifier is narrowed to POSIX: the `msvcrt` lock
  backend and the path-based staging fallback exist but are untested and
  unsupported in this release.
- Package metadata and the README point to the project page at
  https://memkernel.dev/wiki-studio/ (PyPI shows the link from the next release).

## [0.5.0] — 2026-10-20

Plain technical English for wiki pages (closes #28): writing rules in the
prompts, a glossary term lock, advisory prose checks and fact-preservation
warnings on updates. Exit codes are unchanged; the patch-set format and the
page schema gain one optional key each; `promote` is never blocked by the new
findings.

### Added

- Writing rules for wiki prose (issue #28). `schema/ingest-rules.md` gains a
  `## Writing rules` section: one fact per sentence, at most 25 words per
  sentence (20 in numbered steps), one instruction per step, active voice, no
  semicolons, the glossary term for each concept, and a first `## Summary`
  sentence that states the main claim. A preserve list keeps identifiers,
  paths, numbers, `path:` citations and the words "if", "unless" and
  "not verified", and tells the model to split long sentences, not cut them.
  The ingest, multi-page ingest and query prompts already load
  `ingest-rules.md`, so all three now carry the rules. `page-types.md`,
  `WIKI_MAINTAINER.md` and `lint-rules.md` point to the section.
- Optional `avoid:` key on glossary pages (page schema addition, issue #28).
  A per-file glossary page may carry `avoid: alignment check, origin check`,
  and a `glossary/index.md` entry may carry an `Avoid: …` line as the first
  line after its `### <term>` heading. The value is one line of
  comma-separated terms, unquoted or double-quoted; a term cannot contain a
  comma, `"` or `\`. Any other form is reported by `lint --health` as the new
  `avoid-format` finding and contributes no terms. A per-file glossary page's
  avoid terms count as mentions of that page in the missing-cross-links
  check. Existing pages stay valid. Decision record:
  `docs/adr/0001-glossary-avoid-key.md`.
- `wiki-studio lint --prose` (issue #28): advisory prose checks for sentence
  length, semicolons, filler phrases, `## Summary` and `## Key ideas` length,
  and the glossary term lock, which reports each avoid term used on a
  non-glossary page with its canonical term. Code, tables, quotes and HTML
  comments are skipped. Findings go to stderr as `path:line [check] message`;
  the exit code is 0, or 1 under `--strict`. `--paths` limits the pages
  scanned; the term lock still reads the whole glossary. `api.lint` gains
  `prose: bool = False` and `LintResult.prose`.
- Fact-preservation warnings on updates (issue #28). When `ingest`,
  `query --file-back` or `propose` writes an `update` edit whose page exists,
  the citations (`sources[].path`, `path:line`), backticked identifiers and
  numbers with a unit that the new content drops are recorded as
  `edits[].fact_warnings` in `plan.json` (an optional key, documented in
  `docs/patch-set-format.md`) and printed to stderr as
  `fact-check: <path>: N item(s) removed`. `propose --promote` prints them
  before it applies the patch-set. The warnings are advisory: no exit code
  changes and `promote` ignores the key. A number keeps its minus sign and a
  fraction without a leading zero (`.5 s`) is read as `0.5 s`. When the live
  page cannot be read or decoded, `edits[].fact_check_error` records why,
  the CLI prints `fact-check: <path>: not compared (<reason>)` and the
  proposal is still written.

### Changed

- Whole-word slug matching in the missing-cross-links check. A slug used to
  count as mentioned when it appeared anywhere as a substring, so `lint`
  matched `linter` and `lint-rules`. Letters, digits, `_` and `-` now count
  as word characters on both sides, and a slug written with spaces matches
  only within one paragraph. This removes false `missing-cross-link`
  findings, which can change the result of `lint --health --strict`.

### Upgrade notes

- A wiki with its own `schema/ingest-rules.md` overrides the packaged copy, so
  its prompts do not get the writing rules. Merge the `## Writing rules`
  section from the packaged `src/wiki_studio/schema/ingest-rules.md` into the
  local copy.

## [0.4.1] — 2026-10-17

Fixes only. The one addition is `propose --allow-out-of-repo` (#24); exit codes,
the patch-set format and the page schema are unchanged.

### Fixed

- `promote` keeps its all-or-nothing guarantee when a write into the wiki fails
  (issue #21). The file being written when the error hit was never restored,
  because a target counted as written only after its write returned, so a new
  page stayed half-written and an existing `index.md` or `log.md` stayed
  truncated. Rollback ran only for `OSError`, so any other exception (an
  encoding error, `KeyboardInterrupt`) left every earlier write in place. And
  rollback rewrote a page from its decoded text, which turned CRLF line endings
  into LF. Each target is now recorded before it is written, rollback restores
  each file's exact original bytes and removes directories the commit created,
  and it runs on any exception: an
  `Exception` still exits 10, while `KeyboardInterrupt` and `SystemExit` are
  re-raised after the rollback. Present since 0.1.0.
- Two edits that spell the same file differently (`index.md` and
  `./index.md`) no longer share a preview file (issue #23). The #18 fix counted
  edits per raw path string, so the second append overwrote the first and
  promote rejected the first page as an orphan. Previews are now allocated by
  normalised path; `./index.md` is still accepted. Affected 0.4.0.
- `propose --from DIR --promote` works with a proposals directory outside the
  root (issue #24). It wrote the proposal and then exited 7, telling the user to
  pass `--allow-out-of-repo`, which `propose` did not accept. `propose` now
  takes `--allow-out-of-repo` and forwards it to the promote step; without it
  the refusal is unchanged. Affected 0.4.0.

### Changed

- README banner pinned to the `v0.4.1` tag; the memkernel arm (`docs/agent-arm/`)
  and the consumer install step pin `wiki-studio==0.4.1`.

## [0.4.0] — 2026-10-16

What an agent needs to use the wiki from a shell with no model backend, and a
ready arm for memkernel's lifecycle suite (issue #10, layer 2).

### Added

- `wiki-studio init` / `api.init`: create the wiki directory with a minimal
  `index.md` and `log.md` when absent (promote needs both); never overwrites.
  Lives in the promoter, which stays the only module that writes into the wiki.
- `wiki-studio propose --from DIR [--promote]` / `api.edits_from_dir`: pages an
  agent wrote, laid out like the wiki, become a validated patch-set (`create`,
  or `update` when the page exists); `DIR/index.md` and `DIR/log.md` hold the
  lines to append and are refused if they carry frontmatter. `--promote`
  applies it at once. No backend.
- `wiki-studio find "<question>"` / `api.find`, `FindResult`, `FoundPage`: the
  pages `query` would load, without a model and without writing the query log.
- `docs/agent-arm/`: a `wiki_studio` arm for memkernel's
  `eval/lifecycle-suite/` (config in its format, an instruction within 5
  percent of memkernel's block length, the list of memkernel changes needed).
  Adopting and running it happens in memkernel.

### Fixed

- Several `append-index` or `append-log` edits to the same file in one
  patch-set are all applied, in order (issue #18). The patch-set writer gave
  every edit the preview file `preview/<path>`, so a second edit to the same
  path overwrote the first and only the last line survived; promote then
  rejected the earlier pages as orphans. Each edit now has its own preview
  file (`preview/<path>`, then `preview/<path>.2`, `.3`, ...), which `plan.json`
  already points at. This affected `ingest`, `api.propose` and the new
  `propose --from` with a multi-line `index.md` or `log.md` since 0.1.0. The
  workaround of joining lines into one edit keeps working.
- `promote` no longer leaves a proposal behind when the archive already holds
  one with the same name: it is archived next to it as `<name>-2`, `-3`, ...
  (as `.audit/proposals/` already did), and the CLI no longer prints
  "archived to" for a move that did not happen. Old behaviour, reachable once
  `propose --from` made repeated same-day recordings routine.

### Changed

- README banner pinned to the `v0.4.0` tag.
- `propose --from` names a proposal `<date>-<HHMMSS>-<dir-name>`, with a
  numeric suffix if that name is taken, so repeated recordings never collide.
- `find` on a wiki without `index.md` exits 5 and points at `init`.

## [0.3.1] — 2026-10-16

### Fixed

- Multi-page ingest no longer leaves the model to guess how `index.md` and
  `log.md` change (issue #15). In run 2 of the navigation evaluation, three of
  ten documents were rejected because the model returned `index.md` as a full
  page edit (`page_type: index`, no sources) instead of an `append-index`
  line. The prompt now says that the root `index.md` changes only through a
  one-line `append-index` edit and `log.md` only through a one-line
  `append-log` edit, never as a full page and never with frontmatter; that a
  `<dir>/index.md` which is itself a content page (`glossary/index.md`) is
  edited with `create` or `update`; and that `create` and `update` are only
  for content pages; the response schema's `action` and
  `new_content` carry the same rule. The validator is unchanged: a full-page
  index edit is still a contract violation (exit 4). Run 2 is kept as
  measured on 0.3.0.

### Added

- `py.typed`: the package declares its type hints (PEP 561), so type
  checkers in consuming projects (memkernel) read them without a per-package
  override.

### Changed

- The README banner points at the image at this release's tag, so the PyPI
  page shows it (0.3.0's page cannot; PyPI descriptions are frozen per
  version) and stays intact if the file later moves.

## [0.3.0] — 2026-10-16

The evidence release: the first measured numbers about the tool, with the
caveats they need (issue #10, mirror of memkernel #17).

### Added

- `eval/navigation/`: a frozen corpus (memkernel's documentation at tag
  `v0.4.0`, attributed in NOTICE), a question set committed before any
  ingest ran, a wiki the tool produced from the corpus once through its own
  gate, gold pages assigned afterwards with a written reason each, and
  `run.py`, a stdlib script reporting ingest coverage, navigation hit rate at
  1 and at 5, and words loaded by `query` against a written-down grep rule.
  `tests/test_navigation_eval.py` asserts the script reproduces the committed
  `results.json` and that the fixture is the preregistered one.
- README "Evidence" section with run 1's numbers and caveats, and run 2's
  next to them: `eval/navigation/run2/` is a second measurement on the 0.3.0
  code under a revised protocol (`eval/navigation/run2_protocol.py`: Claude
  hooks isolated and verified by a recorded probe before any attempt, commit,
  versions, model and settings pinned, one attempt per document), with the
  same questions, corpus and stop list used in place. Run 1 is unchanged.
- `wiki-studio info`: prints the resolved layout (default or custom; root,
  wiki and proposals directories with their source, flag, variable or
  default, and whether they exist; logs; which schema copy applies), or the
  same as JSON with `--json`. Read-only, exit 0. `--version` is unchanged.

### Fixed

- Ingest at a custom wiki location (issue #11). The prompt shows wiki files
  under `<wiki-dir>/…` headings but never said that edit paths are relative
  to the wiki directory; with a one-word directory name the model copied the
  prefix and eight of ten ingests in the navigation evaluation's run 1 failed
  validation. The multi-page response instructions and the response schema
  now state the rule, and the exact configured prefix is removed once before
  the unchanged validators run, unless the path already has a valid
  wiki-relative shape (a wiki directory named `concepts` keeps
  `concepts/x.md`). Run 1's numbers were measured on 0.2.0 and are kept as
  measured.

### Changed

- `ingest --help` no longer says multi-page ingest "lands in Phase 1" or that
  `--legacy-single-source` is required; multi-page has been the default since
  0.1.0. Help text only.

### Not built

- The mutation suite for the promote gate (spec US4) is dropped for this
  release under its own condition: run 1 archived a single patch-set, too few
  to generate a corpus from, and a hand-written one would duplicate the unit
  tests.

### Known issues

- Run 1 of the navigation evaluation was measured on 0.2.0, before the
  issue #11 fix above, and promoted one document in ten; it is kept as
  measured. Run 2, on the fixed code, promoted seven.
- In run 2 the three documents that did not promote were rejected by the
  per-edit validator, correctly: the model answered with `index.md` as a full
  page edit (`frontmatter page_type 'index' is not promotable for
  create/update`; `'sources:' must be a non-empty list`) instead of an
  `append-index` line. The validator did its job; the gap is in the prompt,
  which tells the model to "add a link from the appropriate section of
  index.md" without naming the action. To be filed and fixed in a later
  release; run 2 is kept as measured.
- The `claude` text-mode backend exposes no token counts, so ingest cost is
  reported as wall time only. In run 1 a Claude Code Stop hook ran this
  repository's test suite inside each backend call with the fixture's paths
  inherited, which inflated wall time and added test records to the fixture's
  audit and query logs; everything is preserved and the manifest marks the
  run `requires_review` (`eval/navigation/ingest-notes.md`).

## [0.2.0] — 2026-10-15

The memkernel release: the two contracts memkernel 0.5's `memkernel[wiki]`
extra builds against, and a recipe fix (issue #7).

### Added

- `wiki_studio.api.propose(edits, paths, *, name, source="", rationale="", backend="api")`:
  a library caller hands a list of `PageEdit`s to the package and gets back a
  patch-set directory under the proposals dir that `api.promote` applies
  through the usual gate. The edits are validated first with the checks
  `ingest` and `promote` already run; an invalid list, an invalid `name` or an
  existing directory writes nothing. `propose` never touches the wiki or the
  ingest log.
- `PageEdit`, `PageAction` and `WikiPatchSet` are re-exported from
  `wiki_studio.api` and, together with the `api` functions, the result
  dataclasses and the patch-set directory format, declared public under
  semantic versioning (`api.__all__` lists the surface).
- `docs/patch-set-format.md`: the on-disk patch-set format (`plan.json`,
  `preview/`, `.ingest-snapshot/`) and what `promote` does with it.
- `wiki_studio.schema`: the page schema as code. `PAGE_TYPES: dict[str, PageTypeSpec]`
  (`directory`, `required_sections`, `promotable`, `sources_required`) for the
  ten page types of `page-types.md`, plus the derived `VALID_PAGE_TYPES`,
  `PAGE_TYPE_DIRS`, `PROMOTABLE_PAGE_TYPES`, `SOURCELESS_PAGE_TYPES` and
  `REQUIRED_KEYS`. A test parses `page-types.md` and fails when the two
  disagree.

### Changed

- `wiki_studio/schema/` is now a package (it gained `__init__.py`); the six
  markdown documents stay there and are loaded as before. `lint.VALID_PAGE_TYPES`,
  `lint.PAGE_TYPE_DIRS` and `lint.REQUIRED_KEYS` are re-exports of the schema
  module; the linter, the prompt composer, the edit validator and the audit
  record builder read the schema module instead of their own copies of the
  page-type tables. Lint and validation messages are unchanged.
- For consumers probing for the module: on 0.1.0 `import wiki_studio.schema`
  succeeds as an empty namespace package; test for `wiki_studio.schema.PAGE_TYPES`.

### Fixed

- `docs/consumers.md`: the memkernel recipe ran `memkernel wiki_export`, which
  is not a shell command (`wiki_export` is memkernel's MCP tool). The recipe
  now shows the library call and the propose → promote flow a memkernel ≥ 0.5
  bridge uses.

## [0.1.0] — 2026-10-12

The extraction release. The maintainer that lived in
`code-copilot-team/scripts/wiki_ingest` becomes the `wiki_studio` package with
the `wiki-studio` console script. Behaviour, verbs, flags and exit codes are
unchanged; the paths are decoupled.

### Moved

- Every module of `code-copilot-team/scripts/wiki_ingest/` at commit
  `df2c29212e3bed8b547f47bf7976105a6a4678c0` is now `src/wiki_studio/`:
  `__main__.py` became `cli.py` (a two-line `__main__.py` remains for
  `python -m wiki_studio`); the other modules keep their names, including the
  `backends/` package with `copilot_cli.py`, `json_extract.py` and `test.py`.
- The six schema documents from `code-copilot-team/knowledge/wiki/schema/`
  ship as package data under `wiki_studio/schema/`.
- The 240 tests moved to `tests/` and pass in-process (see "Tests" below).

### Added

- `wiki_studio.paths.WikiPaths`: every location (`root`, `wiki_dir`,
  `proposals_dir`, `query_log`, `audit_log`, `schema_dir`) resolved once
  from the global options `--root`, `--wiki-dir`, `--proposals-dir`, then
  `WIKI_STUDIO_ROOT`, `WIKI_STUDIO_WIKI_DIR`, `WIKI_STUDIO_PROPOSALS_DIR`, then the
  defaults (git toplevel of the current directory; `knowledge/wiki`;
  `doc_internal/proposals`). The defaults reproduce the original layout
  byte for byte. The options are accepted before or after the verb.
- `wiki_studio.lint`: the six structural checks of `lint-wiki.sh` in Python,
  with the same messages; `lint` and `promote` run it in-process.
- `wiki_studio.api`: `ingest`, `promote`, `query`, `lint`, `audit_flush` taking
  a `WikiPaths` and returning typed results; `cli.py` is a thin parser over
  them and maps exceptions to exit codes in one place.
- `wiki_studio.errors.PathOutsideRootError` (exit 7) so the library can report
  the confinement refusal the CLI always had.
- `WIKI_STUDIO_BACKEND` names the default backend; `WIKI_STUDIO_ENABLE_PI=1` adds
  `pi` to the auto-detect order.
- `wiki-studio --version`.
- A fixture wiki (`tests/fixtures/wiki/`) with one page of every page type
  and three draft pages in the shape memkernel 0.3's `WikiExporter`
  writes; the suite asserts it lints clean, which pins the schema
  contract between the two packages.
- `docs/consumers.md` with the recipes for code-copilot-team, memkernel and
  document-assistant; CI on Python 3.11, 3.12 and 3.13; a PyPI release
  workflow using trusted publishing.

### Changed

- The distribution, console script and repository are named `wiki-studio`
  (import `wiki_studio`, variables `WIKI_STUDIO_*`). The bundle's earlier
  working names were `aiwiki` (`ai-wiki` is taken on PyPI) and `wikiforge`
  (PyPI rejects it as too similar to the existing `wiki-forge`). The GitHub
  repository was renamed to `gosha70/wiki-studio` on 2026-10-13.
- `load_schema_files` prefers `<wiki-dir>/schema/` when that directory
  exists and otherwise reads the packaged documents.
- The root is no longer derived from the package's own location (which is
  meaningless once installed) but from the working directory's git
  toplevel.
- The `pi` backend no longer reads `shared/capabilities/pi.yaml`;
  `--backend pi` works as before, auto-detection needs `WIKI_STUDIO_ENABLE_PI=1`.
- Rendered prompts label wiki pages with the root-relative wiki directory
  (`knowledge/wiki/...` by default) or the directory name when the wiki is
  outside the root.
- `health_lint.lint_health(paths, only=...)`: the first parameter is a
  `WikiPaths`; the page filter formerly called `paths` is now `only`.
- `audit_flush.flush` is a printing wrapper around the new `flush_state`.
- The CLI help text mentions the new wrapper name and the configurable
  directories instead of the old script paths; wording of error prefixes
  on stderr is unchanged.

### Deprecated

- `WIKI_INGEST_BACKEND`: still honoured, prints a one-line warning on
  stderr; use `WIKI_STUDIO_BACKEND`.

### Removed

- The bash structural linter is not shipped; `lint` no longer exits 2 when
  it is missing (it cannot be).
- The `code-copilot-team` capability-file lookup and the `PYTHONPATH`
  wrapper scripts (replaced by the console script; see
  `docs/consumers.md` for the two `exec` lines).

### Tests

357 tests (240 moved, 117 added). Moved tests that were renamed or
re-homed:

- `tests/test_e2e.py::TestE2EBashEntrypoint::test_bash_entrypoint_runs_test_backend`
  is now `TestE2EModuleEntryPoint::test_python_m_wiki_studio_help_lists_verbs`,
  the one subprocess test (`python -m wiki-studio --help`); every other CLI test
  calls `wiki_studio.cli.main(argv)` in-process inside a temporary layout.
- `tests/test_e2e.py::TestE2ESingleWriterInvariant::test_only_promoter_writes_to_knowledge_wiki`
  is now `test_only_promoter_writes_to_wiki_dir` and keys on `wiki_dir`.
- `tests/test_audit.py::TestLintWikiShellAuditExclusion` (two tests of the
  bash linter) is now `tests/test_lint.py::TestAuditExclusion`.
- `tests/test_pi_wiki_backend.py::test_capability_reader_reflects_the_real_pi_yaml`
  is now `test_pi_auto_detect_is_gated_by_environment_flag`; the patched
  symbol `_pi_capability_enabled` is `_pi_enabled`.
- `tests/test_copilot_cli.py` reads `WIKI_STUDIO_BACKEND`; the deprecated alias
  has its own tests in `TestBackendEnvironmentVariables`.
- `tests/test_prompt.py` and `tests/test_ingestor_with_test_backend.py`
  build a temporary layout instead of locating the repository.

New modules: `test_cli_contract.py`, `test_paths.py`, `test_lint.py`,
`test_package_boundaries.py`, `test_api.py`, `test_fixture_wiki.py`.

### Known issues

Pre-existing behaviour of the moved code, flagged in review and recorded
for 0.2 rather than changed in the extraction release:

- `audit_flush` counts data lines after a fixed two-line preamble; a
  working log without the marker is rejected as malformed before the
  count is used, so the count cannot be acted on, but the helper does not
  verify the marker itself.
- `audit_flush` treats any `git show HEAD:<log>` failure other than
  "not a git repository" as "file absent at HEAD".
- Multi-page `ingest --dry-run` is not dry: the backend drafts every page
  and the patch-set directory is written; only the audit record is marked
  (`proposal_hash` null). A dry-run signal in the prompt contract that the
  backends honour is planned for 0.2.
- The legacy single-source ingest records the proposals directory, not the
  proposal file, as `proposal_dir`, hashes an empty payload, and leaves an
  empty `.ingest-snapshot/` next to the file. This is the v1 shim's
  original behaviour; consumers parsing the log would see the change, so
  it is kept for 0.1.0.
- The legacy single-source ingest passes the dry-run intent to the prompt
  through the `WIKI_INGEST_TASK` environment variable; the multi-page path
  does not use it.
- `build_log_record` records a source inside the root as repo-relative
  even with `--allow-out-of-repo` (the flag only matters for sources
  outside the root).
- `append_ingest_log` rewrites the file rather than renaming a temp file;
  a torn write is detected and refused by `audit-flush`.
- The contradiction check assumes a backend returns a dict; a backend that
  returns a non-string, non-dict value would raise inside the health pass.
- The cross-link heuristic strips frontmatter by searching for the first
  `\n---` after the opening marker.
- The legacy argv shim (`python -m wiki_studio <source>` without a verb) treats
  the value of a flag other than the three global options as a positional
  when deciding whether a verb is present; the documented shapes work.

[Unreleased]: https://github.com/gosha70/wiki-studio/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/gosha70/wiki-studio/releases/tag/v0.1.0
