---
feature_id: wiki-studio-0-8-0
date: 2026-10-27
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-8-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-8-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The change adds ranked discovery (FTS5 + index-first) with a byte budget, a UTF-8 structural lint rule, and new `find`/`query` flags. The design is coherent and well-tested, but there are a few correctness issues around the FTS5 fallback path, the `min_match_tokens` counting logic, and the `_read_index` silent-empty behavior that can mask a missing index as an empty one.

## Findings

- [warning] f-db5485ac: When `ranker == RANKER_FTS5` and FTS5 is unavailable, `select` sets `ranker = RANKER_INDEX_FIRST` and `fallback_reason`, but `config_hash` is computed *after* the fallback check using the (now index-first) ranker, so it is `None` — correct. However `_rank_index_first` is called with `candidate_count=len(links)`, which includes ineligible links; `_select_query_candidates` will re-read every linked page (including non-UTF-8, superseded, missing) via its own reads, defeating the "read once per call" contract and potentially re-reading pages that `_read_eligible` already classified. This is a performance and consistency concern: the sha256/bytes reported come from `_read_eligible`, but ranking uses a second read that could observe different bytes if the file changed between reads. (src/wiki_studio/discovery.py)
- [warning] f-9efc983d: The `min_match_tokens` filter counts a page as matching a token if `_matching(_quote(token), weights)` returns it, but `_matching` uses `bm25` with the full weight vector and the token alone — a page that contains the token in *any* column matches. That is fine, but the loop iterates `question_tokens(question)` which is `sorted(set(...))` from `_tokenise`, so duplicate tokens are already deduped — good. However, the initial `scores` from the OR query may include pages that match only via a token that the per-token loop also matches, so the count is consistent. The real issue: `matched` is initialized from `ranked` (pages matching the OR), but a page could match the OR via token A and the per-token loop for token B might not return it — that's correct. No bug, but the double-query is O(tokens) round-trips; acceptable for in-memory. Note only. (src/wiki_studio/search_index.py)
- [warning] f-f9123e97: If `index.md` exists but is not valid UTF-8, `_read_index` returns `("", 0)`, and `select` returns an empty `Selection` with `index_md=""`. `api.find` then raises `SourceMissingError` ("index.md not found"), which is misleading — the file exists but is malformed. The lint rule will catch it, but `find`/`query` give a wrong error message. Also `bytes_loaded` is reported as 0 even though the file has bytes. (src/wiki_studio/discovery.py)
- [warning] f-3c057944: `_read_eligible` does `lstat()` then `read_bytes()`. Between the two, the file could be replaced by a symlink or a directory (TOCTOU). `read_bytes()` on a symlink would follow it, potentially reading outside the wiki. The eligibility contract says "no symlink on the way" — but the check is only `lstat` on the final component, and `_extract_index_links` is relied on to reject `../` and symlinked intermediate dirs. If `_extract_index_links` already resolves and rejects symlinked paths, this is defense-in-depth; if not, it's a real gap. Worth confirming `_extract_index_links` rejects symlinked intermediate directories, not just `../`. (src/wiki_studio/discovery.py)
- [note] f-d1adf6c5: The lazy import inside `query()` avoids a circular import, but it means `resolve_ranker` is called twice per query (once in `api.query` via `resolve_ranker(ranker)` for validation, once inside `DefaultQuerier.query`). Minor duplication; also `api.query` calls `resolve_ranker(ranker)` and discards the result, then passes the raw `ranker` (possibly `None`) to `DefaultQuerier`, which re-resolves. If `WIKI_STUDIO_RANKER` changes between the two calls (unlikely but possible in tests), behavior diverges. (src/wiki_studio/querier.py)
- [note] f-c38b1c31: When `ranker == RANKER_FTS5` but FTS5 is unavailable, `config_hash` is `None` (correct, since index-first ran). But `describe_discovery` always reports `ranker_config_hash()` for the FTS5 config regardless of availability — that's the "live configuration hash" and is fine. Just confirm the contract doc's statement "`ranker_config_hash` is ... `null` for `index-first`" matches: in `select`, when the *requested* ranker was fts5 but fell back, the result's `ranker` is `index-first` and hash is `None` — consistent. No action needed; noting for reviewer awareness. (src/wiki_studio/discovery.py)
- [note] f-13cf7c80: `self.skipTest(...)` inside a `for` loop with `subTest` will skip the *entire test method* on the first FTS5-unavailable iteration, not just that subtest. On a no-FTS5 Python, the index-first iterations after the first fts5 iteration never run. The test still passes (as skipped), but coverage of index-first operator questions is silently lost on such hosts. (tests/test_discovery.py)
- [note] f-96df1841: The doc says "Each eligible page is read once per call" but the index-first ranker path calls `_select_query_candidates`, which re-reads pages. This contradicts the stated contract and the `sha256`/`bytes` semantics ("describe that read"). (docs/knowledge-contract.md)
- [note] f-7728a806: Passing `len(links)` as `max_pages` to `_select_query_candidates` means the 0.7.0 selector returns up to `len(links)` pages, but `_select_query_candidates` may internally cap or behave differently with a large `max_pages`. More importantly, if `links` contains duplicates (same page linked twice in index.md), `len(links)` overcounts and `eligible` dedupes by dict key — the ranked list from the selector may contain duplicates that are then filtered by `rel in eligible`, but ordering could be affected. Minor. (src/wiki_studio/discovery.py)
- [note] f-335482f6: `api.find` accepts `ranker_config` but `api.query` does not. The docstring for `find` says "`ranker_config` (None: the live default) configures `fts5`", but there's no way to pass a custom config through `query`. This is an API asymmetry — acceptable if intentional (query uses defaults), but worth documenting in the contract that `query` always uses `DEFAULT_RANKER_CONFIG`. (src/wiki_studio/api.py)
