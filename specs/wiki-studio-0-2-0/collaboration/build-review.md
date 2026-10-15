---
feature_id: wiki-studio-0-2-0
date: 2026-10-15
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-2-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-2-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The 0.2.0 release adds a public `api.propose` wrapper, a `wiki_studio.schema` module as the single source of page-type facts, and a docs fix. The implementation is generally clean and well-tested, but there are a few correctness concerns around the `propose` validation path, the `_write_ingest_snapshot` error handling, and the schema drift test's robustness.

## Findings

- [warning] f-5cd6e2eb: `_write_ingest_snapshot(written)` is called inside the `try` that catches `OSError`, but if it raises a non-OSError (e.g. a `ContractViolationError` or `ValueError` from snapshot logic), the partially-written proposal directory is left on disk with no cleanup, contradicting the docstring's "nothing is written when they fail" promise for the snapshot step. (src/wiki_studio/api.py)
- [warning] f-12830346: `Path(name).name != name` rejects `"a/b"` and `"sub/"` but also silently accepts names containing backslashes on POSIX (e.g. `"a\\b"`), and does not reject names with NUL or other path-hostile characters; more importantly, `name` is not checked against `paths.proposals_dir` traversal via symlinks or `..`-like sequences that `Path.name` normalizes away (e.g. `"foo/../bar"` → `Path("foo/../bar").name == "bar"` != `"foo/../bar"`, so it is rejected — good — but `"foo\\..\\bar"` on POSIX passes). (src/wiki_studio/api.py)
- [warning] f-f54d3550: `validate_page_edit_semantics` is called for every edit including `append-index`/`append-log` edits, but the function's docstring/behavior for append actions is not shown here; if it assumes `new_content` is a full page (frontmatter parsing), append edits whose content is a single line may produce spurious errors or be silently skipped. The test `test_round_trip_equals_a_direct_write` passes, so this is likely fine, but the validation contract for append edits should be explicit. (src/wiki_studio/api.py)
- [warning] f-ed30e1a8: `overview` is given `_CONCEPT_SECTIONS` (the same tuple object as `concept`). Since `PageTypeSpec` is frozen but `required_sections` is a mutable tuple (immutable, fine) this is safe, but sharing the tuple means a future edit to `_CONCEPT_SECTIONS` silently changes `overview` too. The spec says overview's sections "match `concept`", so this is intentional, but it is a latent coupling. (src/wiki_studio/schema/__init__.py)
- [warning] f-29e685f2: The markdown parser is brittle: `_required_sections` stops at the first blank line after bullets, and the inline branch joins lines until a blank line. If `page-types.md` ever adds a blank line between the "Required H2 sections" marker and its bullets, or uses a different bullet style, the parser silently returns `()` and the drift test would then fail with a confusing message rather than a clear parse error. The test `test_parser_reads_the_shapes_the_document_uses` mitigates this for current content but does not assert the parser found sections for every type. (tests/test_schema.py)
- [note] f-115fcb06: `_LEGACY_PAGE_TYPE_DIR` is now derived from `PROMOTABLE_PAGE_TYPES` via `PAGE_TYPE_DIRS[name]`. This is correct today, but it silently changes behavior if a future page type is added as promotable with a directory that is not a valid legacy mapping (e.g. a root-level promotable type). The original hardcoded dict was explicit about which legacy types map where. (src/wiki_studio/audit.py)
- [note] f-fb6790f3: The example uses `WikiPaths.resolve(wiki_dir="knowledge/wiki")` while `docs/consumers.md` uses `WikiPaths.for_root(Path.cwd(), wiki_dir=Path("knowledge/wiki"))`. Both may be valid, but the inconsistency is confusing for a consumer copying the snippet. (docs/patch-set-format.md)
- [note] f-60b89c13: `__all__` lists `PROPOSE_BACKEND` and the hint constants, but `PROPOSE_BACKEND` is a new public name not mentioned in the stability statement or README. If it is intended as public, document it; if not, drop it from `__all__`. (src/wiki_studio/api.py)
- [note] f-bf80a4b9: The `except OSError` wraps both `write_patch_set_dir` and `_write_ingest_snapshot`, but `write_patch_set_dir` may raise `OutputWriteError` (a subclass of the package's error, not `OSError`) for its own reasons; those propagate unchanged, which is fine, but the message from the wrapper (`"could not write patch-set dir at ..."`) may mask the more specific inner error if it is an `OSError` subclass raised by the writer. (src/wiki_studio/api.py)
