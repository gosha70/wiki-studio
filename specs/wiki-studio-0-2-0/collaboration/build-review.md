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

- [warning] f-b187fe81: `_write_ingest_snapshot` is called inside the `try` that catches only `OSError`; if it raises a non-`OSError` (e.g. `ContractViolationError` or `ValueError` from snapshot logic), the partially-written proposal directory is left on disk with no cleanup, contradicting the docstring's "nothing is written when they fail" promise for the snapshot step. (src/wiki_studio/api.py)
- [warning] f-50f3649b: The regex `^[A-Za-z0-9][A-Za-z0-9._-]*$` rejects `/`, `.`, `..`, and leading dots, but on POSIX it accepts backslashes (e.g. `a\b`) and other path-hostile characters; the test asserts `a\b` is rejected, but the regex does not actually reject it, so the test would fail or the check is inconsistent with the test. (src/wiki_studio/api.py)
- [warning] f-b382c999: `validate_page_edit_semantics` is invoked for every edit including `append-index`/`append-log`; if it assumes `new_content` is a full page (frontmatter parsing), append edits whose content is a single line may produce spurious errors or be silently skipped. The round-trip test passes, so behavior is likely fine, but the validation contract for append edits is not explicit. (src/wiki_studio/api.py)
- [warning] f-ae5761a8: `overview` reuses the same `_CONCEPT_SECTIONS` tuple object as `concept`; since `PageTypeSpec` is frozen and the tuple is immutable this is safe today, but a future edit to `_CONCEPT_SECTIONS` silently changes `overview` too. The spec says overview's sections "match `concept`", so this is intentional, but it is a latent coupling. (src/wiki_studio/schema/__init__.py)
- [warning] f-7117caa1: The markdown parser is brittle: `_required_sections` stops at the first blank line after bullets, and the inline branch joins lines until a blank line. If `page-types.md` ever adds a blank line between the "Required H2 sections" marker and its bullets, or uses a different bullet style, the parser silently returns `()` and the drift test fails with a confusing message rather than a clear parse error. The `test_parser_reads_the_shapes_the_document_uses` test mitigates this for current content but does not assert the parser found sections for every type. (tests/test_schema.py)
- [note] f-115fcb06: `_LEGACY_PAGE_TYPE_DIR` is now derived from `PROMOTABLE_PAGE_TYPES` via `PAGE_TYPE_DIRS[name]`. This is correct today, but it silently changes behavior if a future page type is added as promotable with a directory that is not a valid legacy mapping (e.g. a root-level promotable type). The original hardcoded dict was explicit about which legacy types map where. (src/wiki_studio/audit.py)
- [note] f-fb6790f3: The example uses `WikiPaths.resolve(wiki_dir="knowledge/wiki")` while `docs/consumers.md` uses `WikiPaths.for_root(Path.cwd(), wiki_dir=Path("knowledge/wiki"))`. Both may be valid, but the inconsistency is confusing for a consumer copying the snippet. (docs/patch-set-format.md)
- [note] f-bbcfb4dc: `__all__` lists `PROPOSE_BACKEND` and the hint constants, but `PROPOSE_BACKEND` is a new public name not mentioned in the stability statement or README. If it is intended as public, document it; if not, drop it from `__all__`. (src/wiki_studio/api.py)
- [note] f-83c1ce85: The `except OSError` wraps both `write_patch_set_dir` and `_write_ingest_snapshot`, but `write_patch_set_dir` may raise `OutputWriteError` (a subclass of the package's error, not `OSError`) for its own reasons; those propagate unchanged, which is fine, but the wrapper message (`"could not write patch-set dir at ..."`) may mask the more specific inner error if it is an `OSError` subclass raised by the writer. (src/wiki_studio/api.py)
