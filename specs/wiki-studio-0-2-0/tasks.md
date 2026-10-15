# Tasks: wiki-studio 0.2.0 — public proposal API, schema as code, recipe fix

<!-- One `## US<n>:` group = one auto-build phase. [US#] tags trace to spec.md. -->
<!-- Run per phase: poetry run ruff check src/ tests/ && poetry run ruff format --check src/ tests/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=80 -->

## US1: Public proposal API

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 1 | | Add `api.propose(edits, paths, *, name, source="", rationale="", backend="api") -> Path`: validate `name` (single path component, else `ValueError`), build the `WikiPatchSet`, run `validate_patch_set` and `validate_page_edit_semantics` (raise `ContractViolationError`), refuse an existing `<proposals_dir>/<name>` (`OutputWriteError`), call `write_patch_set_dir`, write the `.ingest-snapshot/`, return the absolute dir (FR-001, FR-002) | `src/wiki_studio/api.py` | build | [ ] |
| 2 | [P] | Re-export `PageEdit`, `PageAction`, `WikiPatchSet` from `api`; add the stability statement to the `api` and `proposal` module docstrings (FR-004) | `src/wiki_studio/api.py`, `src/wiki_studio/proposal.py` | build | [ ] |
| 3 | [P] | Document the patch-set directory format: `plan.json` keys, `preview/<path>`, `.ingest-snapshot/`, what `promote` does with it, the propose-against-live-wiki note (FR-003) | `docs/patch-set-format.md` | build | [ ] |
| 4 | | Tests: memkernel-shaped round trip (concept create + append-index + append-log → propose → promote → wiki content equals direct write; `.audit/proposals/<name>/` archived); wrong directory → `ContractViolationError`, nothing written; empty edits → `ContractViolationError`; bad `name` → `ValueError`; existing dir → `OutputWriteError`; `plan.json` matches the documented keys; `promote(dry_run=True)` leaves the wiki untouched; single-writer test still passes (FR-001, FR-002, FR-010) | `tests/test_propose.py` | build | [ ] |

**Checkpoint US1** — verify before continuing:
- [ ] `python -c "from wiki_studio.api import propose, PageEdit, WikiPatchSet"` works
- [ ] Round-trip test green; `tests/test_package_boundaries.py` single-writer scan green
- [ ] Full gate green

---

## US2: Schema as code

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 5 | | Create `wiki_studio.schema` as a package (`schema/__init__.py` beside the markdown documents): `PageTypeSpec(directory, required_sections, promotable, sources_required)`, `PAGE_TYPES` for the ten types in the 0.1.0 order, derived `VALID_PAGE_TYPES`, `PAGE_TYPE_DIRS`, `PROMOTABLE_PAGE_TYPES`, `SOURCELESS_PAGE_TYPES`, and `REQUIRED_KEYS`; no imports from the package (FR-005) | `src/wiki_studio/schema/__init__.py` | build | [ ] |
| 6 | | Migrate consumers: `lint.py` imports and re-exports `VALID_PAGE_TYPES`, `PAGE_TYPE_DIRS`, `REQUIRED_KEYS` and uses `SOURCELESS_PAGE_TYPES`; `prompt.py` drops `_PROMOTABLE_PAGE_TYPES`/`_PAGE_TYPE_TO_DIR`/`_VALID_PAGE_TYPES` for the schema constants; `proposal.py` drops `_PROMOTABLE_PAGE_TYPES` and the inline `page_type_to_dir`; messages unchanged (FR-006) | `src/wiki_studio/lint.py`, `src/wiki_studio/prompt.py`, `src/wiki_studio/proposal.py` | build | [ ] |
| 7 | | Tests: parse `page-types.md` (type headings, directory, required-section bullets, overview inline form) and assert equality with `PAGE_TYPES`; derived constants equal the 0.1.0 values and order; `resources.files("wiki_studio").joinpath("schema")` still lists the six documents; existing `test_lint.py` / `test_prompt.py` / `test_proposal.py` unchanged and green (FR-007) | `tests/test_schema.py` | build | [ ] |

**Checkpoint US2** — verify before continuing:
- [ ] `grep -rn '"concepts"' src/wiki_studio/*.py` matches nothing (the string lives only in `schema/__init__.py`)
- [ ] `poetry build` still packages the six `schema/*.md` (wheel listing)
- [ ] Full gate green

---

## US3: Docs, changelog, version

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 8 | | `docs/consumers.md`: replace `memkernel wiki_export` with the library call, note the MCP tool, add the propose → promote example (FR-008) | `docs/consumers.md` | build | [ ] |
| 9 | [P] | README Library section: `api.propose` example, stability statement, links to `docs/patch-set-format.md` and `wiki_studio.schema`; Schema section mentions the module (FR-009) | `README.md` | build | [ ] |
| 10 | [P] | CHANGELOG `[0.2.0]`; version `0.2.0` in `pyproject.toml`, `src/wiki_studio/__init__.py`, `tests/test_cli_contract.py` (FR-009) | `CHANGELOG.md`, `pyproject.toml`, `src/wiki_studio/__init__.py`, `tests/test_cli_contract.py` | build | [ ] |

**Checkpoint US3** — verify before continuing:
- [ ] `grep -n "memkernel wiki_export" docs/consumers.md` matches nothing
- [ ] `poetry run wiki-studio --version` prints 0.2.0; `poetry build` succeeds
- [ ] Full gate green

---

## Final Verification

- [ ] Type checker: 0 errors
- [ ] Linter: 0 errors
- [ ] Full suite green with coverage ≥ 80 percent
- [ ] No runtime dependency in `pyproject.toml`
- [ ] CLI `--help` output unchanged (contract tests)
