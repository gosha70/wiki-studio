# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-10-12

The extraction release. The maintainer that lived in
`code-copilot-team/scripts/wiki_ingest` becomes the `aiwiki` package with
the `ai-wiki` console script. Behaviour, verbs, flags and exit codes are
unchanged; the paths are decoupled.

### Moved

- Every module of `code-copilot-team/scripts/wiki_ingest/` at commit
  `df2c29212e3bed8b547f47bf7976105a6a4678c0` is now `src/aiwiki/`:
  `__main__.py` became `cli.py` (a two-line `__main__.py` remains for
  `python -m aiwiki`); the other modules keep their names, including the
  `backends/` package with `copilot_cli.py`, `json_extract.py` and `test.py`.
- The six schema documents from `code-copilot-team/knowledge/wiki/schema/`
  ship as package data under `aiwiki/schema/`.
- The 240 tests moved to `tests/` and pass in-process (see "Tests" below).

### Added

- `aiwiki.paths.WikiPaths`: every location (`root`, `wiki_dir`,
  `proposals_dir`, `query_log`, `audit_log`, `schema_dir`) resolved once
  from the global options `--root`, `--wiki-dir`, `--proposals-dir`, then
  `AIWIKI_ROOT`, `AIWIKI_WIKI_DIR`, `AIWIKI_PROPOSALS_DIR`, then the
  defaults (git toplevel of the current directory; `knowledge/wiki`;
  `doc_internal/proposals`). The defaults reproduce the original layout
  byte for byte. The options are accepted before or after the verb.
- `aiwiki.lint`: the six structural checks of `lint-wiki.sh` in Python,
  with the same messages; `lint` and `promote` run it in-process.
- `aiwiki.api`: `ingest`, `promote`, `query`, `lint`, `audit_flush` taking
  a `WikiPaths` and returning typed results; `cli.py` is a thin parser over
  them and maps exceptions to exit codes in one place.
- `aiwiki.errors.PathOutsideRootError` (exit 7) so the library can report
  the confinement refusal the CLI always had.
- `AIWIKI_BACKEND` names the default backend; `AIWIKI_ENABLE_PI=1` adds
  `pi` to the auto-detect order.
- `ai-wiki --version`.
- A fixture wiki (`tests/fixtures/wiki/`) with one page of every page type
  and three draft pages in the shape memkernel 0.3's `WikiExporter`
  writes; the suite asserts it lints clean, which pins the schema
  contract between the two packages.
- `docs/consumers.md` with the recipes for code-copilot-team, memkernel and
  document-assistant; CI on Python 3.11, 3.12 and 3.13; a PyPI release
  workflow using trusted publishing.

### Changed

- `load_schema_files` prefers `<wiki-dir>/schema/` when that directory
  exists and otherwise reads the packaged documents.
- The root is no longer derived from the package's own location (which is
  meaningless once installed) but from the working directory's git
  toplevel.
- The `pi` backend no longer reads `shared/capabilities/pi.yaml`;
  `--backend pi` works as before, auto-detection needs `AIWIKI_ENABLE_PI=1`.
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
  stderr; use `AIWIKI_BACKEND`.

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
  is now `TestE2EModuleEntryPoint::test_python_m_aiwiki_help_lists_verbs`,
  the one subprocess test (`python -m aiwiki --help`); every other CLI test
  calls `aiwiki.cli.main(argv)` in-process inside a temporary layout.
- `tests/test_e2e.py::TestE2ESingleWriterInvariant::test_only_promoter_writes_to_knowledge_wiki`
  is now `test_only_promoter_writes_to_wiki_dir` and keys on `wiki_dir`.
- `tests/test_audit.py::TestLintWikiShellAuditExclusion` (two tests of the
  bash linter) is now `tests/test_lint.py::TestAuditExclusion`.
- `tests/test_pi_wiki_backend.py::test_capability_reader_reflects_the_real_pi_yaml`
  is now `test_pi_auto_detect_is_gated_by_environment_flag`; the patched
  symbol `_pi_capability_enabled` is `_pi_enabled`.
- `tests/test_copilot_cli.py` reads `AIWIKI_BACKEND`; the deprecated alias
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
- The legacy argv shim (`python -m aiwiki <source>` without a verb) treats
  the value of a flag other than the three global options as a positional
  when deciding whether a verb is present; the documented shapes work.
- In the staged-tree lint, a sibling directory whose symlink cannot be
  created is skipped silently (files are copied instead).

[Unreleased]: https://github.com/gosha70/ai-wiki/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/gosha70/ai-wiki/releases/tag/v0.1.0
