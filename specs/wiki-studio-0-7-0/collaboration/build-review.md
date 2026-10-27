---
feature_id: wiki-studio-0-7-0
date: 2026-10-26
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-7-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-7-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The `findings` feature is well-structured: it correctly avoids backend resolution, uses `MappingProxyType` for immutable counts, and the tests exercise the no-model-call guarantee via patching. However, there are correctness concerns around `pages_checked` semantics, scoping behavior for graph-based health checks, and a potential inconsistency between `counts` and `findings` when scoping is applied.

## Findings

- [warning] f-42cbe603: When `pages` is provided, `pages_checked` is `len(canonical)` (the scoped pages), but the health checks still read the whole wiki and can produce findings whose `pages` tuple includes out-of-scope pages (e.g., `missing-cross-link` findings reference the mentioned entity page). The `in_scope.intersection(f.pages)` filter keeps such findings, so `pages_checked` under-reports the pages actually inspected while findings may reference pages outside the scope. This is a semantic inconsistency in the contract. (src/wiki_studio/findings.py)
- [warning] f-8c8883b7: The `in_scope.intersection(f.pages)` filter uses `any`-style semantics: a health finding is kept if *any* of its pages is in scope. For `missing-cross-link`, the finding's `pages` may include the entity page plus the pages mentioning it; if only one is in scope, the finding is reported but its `pages` tuple contains out-of-scope entries. The test `test_scoped_pages_limit_every_kind_and_paths_are_canonical` only asserts `target in finding.pages`, not that all pages are in scope, so this behavior is untested and undocumented. (src/wiki_studio/findings.py)
- [warning] f-6af4e596: `counts` is built from `found` (the filtered list), but `FINDING_KINDS` includes kinds that may never appear in `found` when scoped. The contract says "counts names every kind this build reports, zero included" — this is satisfied. However, `pages_checked` for the scoped case is `len(canonical)` while `health.pages_checked` (whole wiki) is used for the unscoped case. A host comparing `pages_checked` across scoped and unscoped runs cannot distinguish "scoped to N pages" from "wiki has N pages". (src/wiki_studio/findings.py)
- [note] f-dbe48967: `_intra_wiki_links_from(paths.wiki_dir / INDEX_NAME, paths.wiki_dir)` is called unconditionally even when `pages` is scoped and `index.md` is not in scope. This is a minor inefficiency but also means a scoped run still reads `index.md`; if `index.md` is missing, behavior depends on `_intra_wiki_links_from`'s handling. The test `test_a_clean_scope_exits_zero` scopes to a single page and still passes, so the missing-index case is not exercised. (src/wiki_studio/findings.py)
- [note] f-ec7b3766: `_REVIEW_KINDS[state.state]` is indexed after the `if state.state in _REVIEW_KINDS` guard, which is correct. However, `ReviewState.state` values not in `_REVIEW_KINDS` (e.g., `approved`) are silently dropped — this is intended, but the contract table in `docs/knowledge-contract.md` does not list `approved` as a non-finding state, so a reader may wonder why an approved page produces no finding. Minor documentation gap. (src/wiki_studio/findings.py)
- [note] f-bbe5ce87: The test asserts `set(by_kind) == set(FINDING_KINDS)`, which is strong, but it does not assert that `counts` values match `len(by_kind[kind])` for kinds with zero findings (it does via the final `assertEqual`, which is good). However, the test does not verify that `pages_checked` equals the number of pages in the wiki for the unscoped case — it only checks `isinstance(int)` in the JSON test. A regression where `pages_checked` is always 0 would pass. (tests/test_findings.py)
- [note] f-df398d15: The doc says "`pages=None` covers the whole wiki; an explicit list scopes every kind to those pages." This is imprecise: graph-based health kinds still read the whole wiki to count edges, and findings may reference out-of-scope pages (see above). The doc should clarify that scoping filters *which findings are reported* (by intersection), not *which pages are read*. (docs/knowledge-contract.md)
- [note] f-5fe2b02d: The function accepts `pages: list[str]  (src/wiki_studio/findings.py)
- [note] f-4595ae4d: `_page_findings` returns `[*still_indexed, *missing_id]`, so `superseded-still-indexed` findings precede `no-page-id` findings within the page loop. The overall `found` list order is: health findings, review findings, then page findings. The contract says "Key order carries no meaning" for JSON keys but does not specify finding order. This is fine, but a host that assumes findings are grouped by kind (as `counts` suggests) may be surprised. Minor. (src/wiki_studio/findings.py)
- [note] f-b6f23c93: The test patches `wiki_studio.backends.resolve_backend`, `wiki_studio.api.resolve_backend`, `wiki_studio.api.prepare_backend`, and `wiki_studio.health_lint._check_contradictions`. It does not patch `wiki_studio.health_lint.lint_health`'s internal backend resolution if any exists — but since `lint_health(paths, backend=None)` is called with `backend=None`, this is likely sufficient. However, the test does not assert that `_check_contradictions` was actually called with `backend=None` (the `_no_model_check` stand-in raises if backend is not None, which is good). Solid. (tests/test_findings.py)
