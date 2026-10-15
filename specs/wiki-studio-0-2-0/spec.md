---
spec_mode: full
feature_id: wiki-studio-0-2-0
risk_category: feature
status: approved
date: 2026-10-15
---

# Spec: wiki-studio 0.2.0 — public proposal API, schema as code, memkernel recipe fix

<!-- Project constitution: shared/skills/ — copilot-conventions, coding-standards, safety -->

Design references (read before building): `CLAUDE.md`; issue
[gosha70/wiki-studio#7](https://github.com/gosha70/wiki-studio/issues/7);
memkernel's `specs/memkernel-0-5/spec.md` FR-007 to FR-010 on branch
`feature/memkernel-0-5` (the consumer this release unblocks) and its
`src/memkernel/wiki/sync.py` (`EXPORT_MAP`, `IMPORT_MAP`, `PAGE_SECTIONS`,
`WikiExporter`); in this repository `src/wiki_studio/api.py`, `proposal.py`,
`ingestor_multi.py` (`write_patch_set_dir`), `promoter.py` (`_load_patch_from_dir`),
`lint.py` (`VALID_PAGE_TYPES`, `PAGE_TYPE_DIRS`, `REQUIRED_KEYS`), `prompt.py`
and `schema/page-types.md`.

## User Scenarios

### US1: A library consumer can propose a patch-set and promote it (Priority: HIGH)

**Given** memkernel's `WikiExporter` holding a list of draft pages, index lines and log lines it wants in the wiki
**When** it calls `api.propose(edits, paths, name="…")` and then `api.promote(<returned dir>, paths)`
**Then** a patch-set directory in the documented on-disk format is written under the proposals directory, `promote` applies it atomically through the existing lint gate, a validation failure leaves the wiki untouched, and `PageEdit` / `WikiPatchSet` are importable from `wiki_studio.api` with a written stability promise

### US2: The page schema is one Python structure a consumer can test against (Priority: HIGH)

**Given** memkernel keeping its own copy of page type → directory and required H2 sections (its bridge must work without the extra)
**When** its contract test imports `wiki_studio.schema`
**Then** `PAGE_TYPES`, `PageTypeSpec`, `VALID_PAGE_TYPES`, `PAGE_TYPE_DIRS` and `REQUIRED_KEYS` describe every page type in `schema/page-types.md`, the package's own linter, prompt and validators read from that structure (no second copy in code), and a test in this repository fails when the module and the markdown document disagree

### US3: The memkernel recipe is runnable (Priority: MEDIUM)

**Given** a memkernel user following `docs/consumers.md`
**When** they run the memkernel section
**Then** no step names a command that does not exist: the export is shown through memkernel's library (or the `wiki_export` MCP tool from an agent session), followed by `wiki-studio lint`, and the propose → promote flow of US1 is shown for the 0.5 bridge

## Requirements

- **FR-001**: `wiki_studio.api` MUST expose `propose(edits: list[PageEdit], paths: WikiPaths, *, name: str, source: str = "", rationale: str = "", backend: str = "api") -> Path` that validates the edits (set-level `validate_patch_set` and per-edit `validate_page_edit_semantics` against the live wiki, raising `ContractViolationError` as `ingest` does), writes `<paths.proposals_dir>/<name>/` in the patch-set format (FR-003), writes the `.ingest-snapshot/` copy that `promote` diffs for `curator-delta.md`, and returns the absolute directory path that `api.promote` accepts. It MUST NOT write the ingest log (no source was ingested) and MUST NOT write into the wiki directory.
- **FR-002**: `name` MUST be a single path component (non-empty, no `/`, not `.` or `..`); otherwise `ValueError`. A directory that already exists at `<proposals_dir>/<name>` MUST raise `OutputWriteError` rather than be overwritten. `edits` MUST be non-empty (`ContractViolationError` from the set-level check).
- **FR-003**: The on-disk patch-set format MUST be documented in `docs/patch-set-format.md` and linked from the README: `plan.json` (`version` 1, `source_path`, `backend`, `rationale`, `edits[]` with `path`, `action`, `rationale`, `preview`), `preview/<path>` holding each edit's full content, the optional `.ingest-snapshot/` copy, and what `promote` does with the directory (`.applied/`, `.audit/proposals/<name>/`). The format is the one `ingest` already writes and `promote` already reads; nothing about it changes.
- **FR-004**: `PageEdit`, `PageAction` and `WikiPatchSet` MUST be re-exported from `wiki_studio.api`, and `proposal.py`, `api.py` and the README MUST state that these two dataclasses, `PageAction`, the plan.json format and the `api` function signatures are public and follow semantic versioning (field removal or renaming only in a major version; additions in a minor version).
- **FR-005**: A new module `wiki_studio.schema` (the `schema/` package-data directory becomes a package with `__init__.py`; the markdown documents stay where they are and `importlib.resources` lookups keep working) MUST define `PageTypeSpec` (frozen dataclass: `directory: str`, `required_sections: tuple[str, ...]`, `promotable: bool`, `sources_required: bool`) and `PAGE_TYPES: dict[str, PageTypeSpec]` for the ten page types in `schema/page-types.md`, in the order `concept, workflow, incident, decision, playbook, glossary, open-question, index, log, overview` (the order `VALID_PAGE_TYPES` has today, which lint messages print). It MUST derive and export `VALID_PAGE_TYPES: tuple[str, ...]`, `PAGE_TYPE_DIRS: dict[str, str]`, `PROMOTABLE_PAGE_TYPES: frozenset[str]`, `SOURCELESS_PAGE_TYPES: frozenset[str]` and define `REQUIRED_KEYS: tuple[str, ...]` (`page_type, slug, title, status, last_reviewed`). The module MUST import nothing from the rest of the package.
- **FR-006**: `lint.py` MUST import `VALID_PAGE_TYPES`, `PAGE_TYPE_DIRS`, `REQUIRED_KEYS` and the sourceless set from `wiki_studio.schema` and keep re-exporting the first three under the same names (existing imports `from wiki_studio.lint import VALID_PAGE_TYPES, PAGE_TYPE_DIRS` keep working); `prompt.py` and `proposal.py` MUST replace their private promotable-type sets and `proposal.py` its inline `page_type_to_dir` table with the schema module's constants. Lint and validation messages MUST NOT change.
- **FR-007**: A test MUST parse `src/wiki_studio/schema/page-types.md` (the `### \`<type>\` — \`<dir>/…\`` headings and the `Required H2 sections` bullets, including `overview`'s inline "match `concept`" form) and assert it equals `PAGE_TYPES` type for type (directory and required sections), so the markdown contract and the Python structure cannot drift. Another test MUST assert the derived constants equal the values 0.1.0 exported.
- **FR-008**: `docs/consumers.md` MUST replace `memkernel wiki_export` with the library call (`WikiExporter(build_service(), Path("knowledge/wiki")).export()`), note that `wiki_export` is memkernel's MCP tool for agent sessions, and add the propose → promote example a memkernel ≥ 0.5 bridge uses.
- **FR-009**: `README.md` MUST document `api.propose` in the Library section with the stability statement and link `docs/patch-set-format.md` and `wiki_studio.schema`; `CHANGELOG.md` MUST get a `[0.2.0]` section (Added: propose, schema module, format doc; Changed: schema becomes a package; Fixed: the memkernel recipe); `pyproject.toml`, `wiki_studio.__version__` and the version test MUST say `0.2.0`.
- **FR-010**: No runtime dependency is added; every new source file carries the licence header; the single-writer test (`promoter.py` is the only module writing into the wiki) still passes; the CLI contract (verbs, flags, exit codes, `--help`) is unchanged: `propose` is a library function only.

## Constraints / What NOT to Build

- No change to the page schema itself: frontmatter keys, page types, directory names and required sections stay exactly as `schema/page-types.md` says (an ADR on both sides would be needed). The schema module encodes the document; it does not amend it.
- No `propose` CLI verb and no MCP server: memkernel calls the library. The CLI surface is frozen at the five verbs.
- No new validation rules: `propose` reuses the two validators `ingest` and `promote` already run. Required H2 sections are published through the schema module but the structural linter does not start enforcing them in this release.
- No change to what `promote` does or to the plan.json format; the documentation describes the existing format.
- No edits to memkernel in this feature; its FR-007/FR-009 land in its own repository against the released 0.2.0.

## Key Entities

- **PageEdit / WikiPatchSet / PageAction**: the public edit model (`create`, `update`, `append-log`, `append-index`) a consumer builds and `propose` writes.
- **Patch-set directory**: `<proposals_dir>/<name>/` with `plan.json` and `preview/`; the unit `promote` applies atomically.
- **PageTypeSpec / PAGE_TYPES**: the schema as code — one entry per page type with its directory, required H2 sections, whether it can be the target of a create/update edit, and whether `sources:` is required.

## Success Criteria

1. US1 is demonstrable: in a test, three memkernel-shaped edits (a `concept` create, an `append-index` line, an `append-log` line) go through `api.propose` then `api.promote`, and the wiki afterwards equals what writing the files directly would produce; a fourth edit with a wrong directory fails `propose` with `ContractViolationError` and nothing is written; an invalid `name` fails with `ValueError`; an existing directory fails with `OutputWriteError`.
2. US2 is demonstrable: `from wiki_studio.schema import PAGE_TYPES, PageTypeSpec, VALID_PAGE_TYPES, PAGE_TYPE_DIRS, REQUIRED_KEYS` works; `PAGE_TYPES["decision"].required_sections == ("Decision", "Context", "Alternatives considered", "Consequences")`; the page-types.md drift test passes; `grep -rn "concepts\"" src/wiki_studio/*.py` finds the directory names only in `schema/__init__.py`.
3. US3 is demonstrable: `docs/consumers.md` contains no `memkernel wiki_export` shell line; the memkernel section's Python snippets import only names that exist in memkernel 0.5 and wiki-studio 0.2.
4. `poetry run ruff check src/ tests/`, `ruff format --check`, `mypy src/` and `pytest --cov=wiki_studio --cov-fail-under=80` are clean; CI is green on 3.11–3.13; `wiki-studio --version` prints `0.2.0`.
