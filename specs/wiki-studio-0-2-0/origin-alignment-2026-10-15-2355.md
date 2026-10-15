# Origin alignment check — wiki-studio-0-2-0

Gate: phase complete (Gate 3), 2026-10-15 23:55 local. Three build phases (US1 proposal API, US2 schema as code, US3 docs/changelog/version) plus one fix commit from review notes; DeepSeek correctness review PASS on the whole diff twice (before and after the fix commit), zero blocking findings.

Origin: https://github.com/gosha70/wiki-studio/issues/7, read in full through the GitHub API; memkernel's `specs/memkernel-0-5/spec.md` FR-007 to FR-010 and `src/memkernel/wiki/sync.py` read from the local checkout at `origin/feature/memkernel-0-5`. The plan-time record (2026-10-15-2230) is kept as written.

Origin claim:
> (1) `api.propose(edits: list[PageEdit], paths: WikiPaths, *, name: str) -> Path` writing a patch-set directory under the proposals dir that `api.promote` applies; `PageEdit` and `WikiPatchSet` declared public and stable; the on-disk patch-set format documented. (2) A `wiki_studio.schema` module with one structure, `PAGE_TYPES: dict[str, PageTypeSpec(directory, required_sections)]`, re-exporting `VALID_PAGE_TYPES`, `PAGE_TYPE_DIRS`, `REQUIRED_KEYS`. (3) `docs/consumers.md` must not run `memkernel wiki_export` as a shell command. Items 1 and 2 are the 0.2.0 scope; schema changes are out of scope.

Working claim:
> Delivered on `feature/wiki-studio-0-2-0`: `api.propose(edits, paths, *, name, source="", rationale="", backend="api") -> Path` validating with the two checks `ingest` and `promote` already run, writing `plan.json` + `preview/` + `.ingest-snapshot/` under `<proposals_dir>/<name>`, never overwriting, never touching the wiki or the ingest log; `PageEdit`, `PageAction`, `WikiPatchSet` re-exported from `api` with a semantic-versioning statement in `api`, `proposal` and the README; `docs/patch-set-format.md`. `wiki_studio.schema` as a package beside the markdown documents: `PageTypeSpec(directory, required_sections, promotable, sources_required)`, `PAGE_TYPES` for all ten types in the 0.1.0 order, derived `VALID_PAGE_TYPES`, `PAGE_TYPE_DIRS`, `PROMOTABLE_PAGE_TYPES`, `SOURCELESS_PAGE_TYPES`, and `REQUIRED_KEYS`; `lint`, `prompt`, `proposal` and `audit` read it (five duplicated tables removed), lint re-exports the 0.1.0 names, messages unchanged; a test parses `page-types.md` against `PAGE_TYPES`. `docs/consumers.md` shows the memkernel library call, notes the MCP tool, and adds the propose → promote example. Version 0.2.0, CHANGELOG `[0.2.0]`, README, SECURITY table. 409 tests, coverage 91.6 percent; no CLI change; no runtime dependency; schema document unchanged.

Mismatches:
  - As at plan time: three optional provenance keywords on `propose` and two booleans on `PageTypeSpec`, both additive; the issue's calls work as written.
  - `name` is restricted to `[A-Za-z0-9][A-Za-z0-9._-]*` (review note): stricter than "a path component", documented in the format doc and the docstring; memkernel's date-prefixed names fit.
  - The version bump to 0.2.0 is in the branch; cutting the tag and the PyPI release is a separate owner action.

Verdict: aligned
Confidence: high
