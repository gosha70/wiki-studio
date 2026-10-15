# Origin alignment check — wiki-studio-0-2-0

Gate: plan approved (Gate 1), 2026-10-15 22:30 local.

Origin: https://github.com/gosha70/wiki-studio/issues/7 (opened by the owner on 2026-10-15 from memkernel's `specs/memkernel-0-5/spec.md` FR-010, branch `feature/memkernel-0-5`), read in full through the GitHub API; memkernel's FR-007 to FR-010 and `src/memkernel/wiki/sync.py` read from the local checkout at `origin/feature/memkernel-0-5`.

Origin claim:
> memkernel is adopting wiki-studio behind an optional `memkernel[wiki]` extra. Two more pieces need a public contract and one doc line is wrong. (1) `api.propose(edits: list[PageEdit], paths: WikiPaths, *, name: str) -> Path` writing a patch-set directory under the proposals dir that `api.promote` applies; `PageEdit` and `WikiPatchSet` declared public and stable; the on-disk patch-set format documented. (2) A `wiki_studio.schema` module with one structure, `PAGE_TYPES: dict[str, PageTypeSpec(directory, required_sections)]`, re-exporting `VALID_PAGE_TYPES`, `PAGE_TYPE_DIRS`, `REQUIRED_KEYS`; memkernel keeps its own constants and tests them against this module. (3) `docs/consumers.md` runs `memkernel wiki_export`, which does not exist; call the MCP tool from the agent session or use the library. Items 1 and 2 are the 0.2.0 scope; item 3 can land any time. Changing frontmatter keys, page types or directory names is out of scope.

Working claim:
> The spec delivers `api.propose(edits, paths, *, name, source="", rationale="", backend="api") -> Path` as a validating wrapper over the existing `write_patch_set_dir` (same validators `ingest` and `promote` run; no ingest-log line; existing directories never overwritten), re-exports `PageEdit`, `PageAction`, `WikiPatchSet` from `api` with a semantic-versioning stability statement, and documents the unchanged plan.json/preview format in `docs/patch-set-format.md`. `wiki_studio.schema` becomes a package (`__init__.py` beside the markdown documents) defining `PageTypeSpec(directory, required_sections, promotable, sources_required)`, `PAGE_TYPES` for all ten types, the derived `VALID_PAGE_TYPES`, `PAGE_TYPE_DIRS`, `PROMOTABLE_PAGE_TYPES`, `SOURCELESS_PAGE_TYPES`, and `REQUIRED_KEYS`; `lint.py`, `prompt.py` and `proposal.py` read from it instead of their four copies; a test parses `page-types.md` against it. `docs/consumers.md` gets the library call and the propose → promote example. Version 0.2.0, CHANGELOG, README. No CLI verb, no schema change, no new validation rule.

Mismatches:
  - `propose` takes three optional provenance keywords (`source`, `rationale`, `backend`) beyond the issue's signature. The issue's call `propose(edits, paths, name=…)` remains valid as written; the extras fill `plan.json` fields that `promote` renders into the audit archive. Additive, not a divergence.
  - `PageTypeSpec` carries two booleans (`promotable`, `sources_required`) beyond the issue's `(directory, required_sections)`. They encode facts already stated in `page-types.md` and let the package delete its duplicated promotable and sourceless sets, which is the issue's "one structure" goal. memkernel's drift test reads only `directory` and `required_sections`. Additive.
  - `schema` is implemented as a package rather than a module file, because `wiki_studio/schema/` already exists as the package-data directory. `from wiki_studio.schema import PAGE_TYPES` works as the issue shows.

Verdict: aligned
Confidence: high
