---
spec_mode: full
feature_id: wiki-studio-0-2-0
risk_category: feature
justification: "Two new public contracts (a proposal API and a schema module) that a second repository builds against; a full spec pins the signatures and the on-disk format before memkernel 0.5 depends on them."
status: approved
date: 2026-10-15
collaboration_mode: single
origin:
  issue: 7
  urls:
    - https://github.com/gosha70/wiki-studio/issues/7
    - https://github.com/gosha70/memkernel/blob/feature/memkernel-0-5/specs/memkernel-0-5/spec.md
  origin_claim: |
    Issue #7 (opened by the owner from memkernel's 0.5 spec, FR-010): memkernel
    is adopting wiki-studio behind an optional `memkernel[wiki]` extra. Lint and
    health already work against 0.1.0. Two more pieces need a public contract
    and one doc line is wrong: (1) a public proposal API —
    `api.propose(edits: list[PageEdit], paths: WikiPaths, *, name: str) -> Path`
    writing a patch-set directory that `api.promote` applies, with `PageEdit`
    and `WikiPatchSet` declared public and stable and the on-disk patch-set
    format documented; (2) schema as code — a `wiki_studio.schema` module with
    one structure (`PAGE_TYPES: dict[str, PageTypeSpec(directory,
    required_sections)]`, re-exporting `VALID_PAGE_TYPES`, `PAGE_TYPE_DIRS`,
    `REQUIRED_KEYS`) so memkernel can test its duplicated constants for drift;
    (3) `docs/consumers.md` runs `memkernel wiki_export`, which does not exist
    (it is an MCP tool; the recipe should call the tool from the agent session
    or use the library). Items 1 and 2 are the 0.2.0 scope memkernel depends
    on; item 3 can land any time. Changing frontmatter keys, page types or
    directory names is out of scope and would need an ADR on both sides.
---

# Plan: wiki-studio 0.2.0 — public proposal API, schema as code, recipe fix

## Summary

0.1.0 shipped the extraction with a library API whose only way to produce a
patch-set is `ingest` (a backend drafts it). memkernel 0.5 wants to route the
pages its `WikiExporter` already composes through the same lint-gated
`promote`, which needs a way to hand a list of `PageEdit`s to the package and
get a proposal directory back. The code exists (`write_patch_set_dir` in
`ingestor_multi.py`, the two validators in `proposal.py`); this release exposes
it as `api.propose`, declares the edit types and the on-disk format public, and
documents the format. Separately, the page schema's required H2 sections exist
only in `schema/page-types.md` while the directory and type tables are copied
in four places in code; a `wiki_studio.schema` module becomes the one structure
the package reads and a consumer can test against. The memkernel recipe in
`docs/consumers.md` names a command that does not exist and is corrected.

## Technical Context

**Language/Version**: Python 3.11–3.13, Poetry, standard library only at runtime
**Primary Dependencies**: none at runtime; dev: pytest, pytest-cov, ruff, mypy, pip-audit
**Consumer**: memkernel `feature/memkernel-0-5` (`src/memkernel/wiki/sync.py`): `EXPORT_MAP`, `IMPORT_MAP`, `PAGE_SECTIONS`, `WikiExporter` writing a `create` page plus one index line and one log line per memory
**Testing**: `poetry run pytest -q -p no:cacheprovider` (unittest-style; temporary layouts via `tests/conftest.make_repo_layout`)
**Constraints**: no runtime dependency; CLI contract frozen; page schema frozen; `promoter.py` the only wiki writer; coverage ≥ 80 percent; ruff line length 120; mypy clean

## Constitution Check

| Rule file | Concern | Status |
|-----------|---------|--------|
| `coding-standards.md` | No duplicated tables, no magic strings, typed | OK — the schema module becomes the single source for page-type tables; the four copies are removed |
| `safety.md` | Writes stay inside the proposals dir; wiki untouched until promote | OK — `propose` writes only `<proposals_dir>/<name>/`; existing directories are never overwritten |
| `copilot-conventions.md` | Minimal change, one logical change per commit | OK — one phase per commit; no CLI change; no schema change |

## Architecture Decisions

### ADR-1: `propose` is a thin, validating wrapper over the existing writer

`api.propose` builds a `WikiPatchSet`, runs `validate_patch_set` and
`validate_page_edit_semantics` (the same two checks `ingest` runs before writing
and `promote` runs before staging) and calls `write_patch_set_dir`. Validating
at propose time fails fast with the same `ContractViolationError` a backend's
bad output would raise, and the directory it leaves behind is identical to what
`ingest` writes, so `promote` needs no change. It does not append to the ingest
log: no source was ingested, and the audit tree's `.audit/proposals/<name>/`
archive (written by `promote`) is the record of the promotion.

### ADR-2: Optional provenance keywords, nothing else

Issue #7 asks for `propose(edits, paths, *, name)`. `plan.json` also carries
`source_path`, `backend` and `rationale`, which `promote` renders into the
archived `proposal.md`. Three optional keywords (`source`, `rationale`,
`backend="api"`) let a consumer fill them; the defaults keep the issue's
signature valid as written.

### ADR-3: `schema/` becomes a package

`wiki_studio/schema/` already holds the six markdown documents as package data.
Adding `__init__.py` there makes `wiki_studio.schema` a regular package whose
data files sit beside its code; `importlib.resources.files("wiki_studio").joinpath("schema", …)`
keeps resolving. The alternative, a `schema.py` beside a `schema/` directory,
imports correctly (a module shadows a namespace portion) but is a trap for the
next reader. On 0.1.0 `import wiki_studio.schema` succeeds as an empty namespace
package; consumers must probe for `PAGE_TYPES`, not for the import.

### ADR-4: The schema module is the source; `lint`, `prompt`, `proposal` consume it

`VALID_PAGE_TYPES`, `PAGE_TYPE_DIRS` and `REQUIRED_KEYS` move to the schema
module and `lint.py` re-exports them (public names in 0.1.0's README). The
promotable set duplicated in `prompt.py` and `proposal.py`, and the inline
directory table in `validate_page_edit_semantics`, are replaced by the schema
constants. Order is preserved so lint messages are byte-identical. The module
imports nothing from the package, so `lint`, `prompt` and `proposal` can import
it without cycles.

### ADR-5: Two drift tests, one on each side

Here, a test parses `page-types.md` and compares it with `PAGE_TYPES`; in
memkernel, FR-009 compares its constants with `wiki_studio.schema`. The markdown
document remains what humans and prompts read; the module is what code reads.

## Project Structure

```
src/wiki_studio/api.py                 propose(); re-exports PageEdit, PageAction, WikiPatchSet
src/wiki_studio/proposal.py            stability statement; promotable set and dir table from schema
src/wiki_studio/schema/__init__.py     PageTypeSpec, PAGE_TYPES, derived constants, REQUIRED_KEYS
src/wiki_studio/schema/*.md            unchanged package data
src/wiki_studio/lint.py                imports + re-exports from schema
src/wiki_studio/prompt.py              imports from schema
docs/patch-set-format.md               on-disk format
docs/consumers.md                      memkernel recipe fix + propose/promote example
tests/test_api.py                      propose tests
tests/test_schema.py                   page-types.md drift test, derived-constant test
README.md, CHANGELOG.md, pyproject.toml, src/wiki_studio/__init__.py
```

## Scope

### Task 1: Public proposal API (US1)

`api.propose`, `name` validation, no-clobber, snapshot, re-exports, stability
statements, `docs/patch-set-format.md`, tests (round trip through promote;
each failure mode; single-writer test still green).

### Task 2: Schema as code (US2)

`schema/__init__.py`, migrate `lint.py`, `prompt.py`, `proposal.py` to it,
`tests/test_schema.py` with the page-types.md parser, existing lint tests
unchanged and green.

### Task 3: Docs, changelog, version (US3)

`docs/consumers.md` fix and example, README Library section, CHANGELOG
`[0.2.0]`, version bump to 0.2.0 in `pyproject.toml`, `__init__.py` and the
version test.

## Risks

- **Parsing page-types.md in a test is brittle.** Mitigated by parsing only the
  `###` type headings and the bullets directly under "Required H2 sections",
  and by the overview special case being explicit in the test.
- **A consumer may pass edits whose `update` targets a page another pending
  proposal creates.** `propose` rejects it (as `promote` would). Documented in
  the format doc: propose against the live wiki, promote in order.
- **Namespace-package import on 0.1.0.** `import wiki_studio.schema` does not
  fail on the old version; documented in the CHANGELOG and the issue reply so
  memkernel's skip condition checks for `PAGE_TYPES`.
