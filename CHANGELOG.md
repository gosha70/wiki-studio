# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
