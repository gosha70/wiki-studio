---
feature_id: wiki-studio-similar-121
date: 2026-11-25
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-similar-121-evidence
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-similar-121 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The ranking script is well-structured, deterministic, and thoroughly tested. The frozen-input check, protocol-driven configuration, and refusal semantics are correctly implemented. I found a few correctness edge cases worth addressing, primarily around the `slug_paths` collision algorithm and the `check_frozen` behavior when `protocol.json` itself is missing or malformed.

## Findings

- [warning] f-82e1a668: The collision-suffix loop only checks `taken` (slugs already assigned or reserved as bases), but does not account for the case where a later page's *base* slug equals a suffix that an earlier page would want. Consider: pages with titles "Foo", "Foo", "Foo 2". The first "Foo" keeps `foo`; the second "Foo" wants `foo-2`, but `foo-2` is `taken` (base of "Foo 2"), so it gets `foo-3`. That matches the test. However, if a page's base is `foo-2` and it is *not* the keeper of `foo-2` (i.e., a later duplicate of "Foo 2"), the algorithm assigns it `foo-2-2` rather than `foo-2-3` or similar — this is arguably fine but the docstring says "skipping any value another page holds: one a page keeps as its own slug or one already given to an earlier page", which is accurate. The real gap: `taken` is seeded from `keeper` keys, but a page whose base is `foo-2` and which is *not* the keeper will still have `foo-2` in `taken` (from keeper), so it correctly avoids it. This appears correct on inspection; downgrading to note. (eval/similar/rank.py)
- [warning] f-d2a60633: If `protocol.json` itself is missing or unreadable, `load_json(root / PROTOCOL_PATH)` raises `OSError`/`ValueError`, which is caught in `run` and reported as "nothing was written" — good. But `check_frozen` reads `protocol["inputs"]` and `protocol["corpus_pages"]["root"]` without validating their presence; a malformed protocol raises `KeyError`, which is caught. Acceptable, but the error message will be a bare `KeyError: 'inputs'` rather than a helpful diagnostic. Minor. (eval/similar/rank.py)
- [warning] f-0e47a06a: `check_frozen` iterates `protocol["inputs"]` and then separately iterates `corpus.json` pages. If `corpus.json` is listed in `protocol["inputs"]` (it is, per the test setup), its hash is checked twice — once as an input, once implicitly via the corpus loop reading it. Not a bug, but the corpus loop reads `corpus.json` *after* the inputs check has already validated its hash, so a tampered `corpus.json` would be caught by the inputs check first. Fine. However, if `corpus.json` were *not* in `inputs`, the corpus loop would still read it and check page hashes — but the corpus.json file itself would be unverified. This is a latent gap if the protocol ever drops corpus.json from inputs. (eval/similar/rank.py)
- [note] f-073f4109: `later.get(frozenset((first, second)))` returns `None` if the pair is absent, and the check `if query not in (first, second)` correctly raises. But if `later` contains a *different* pair that happens to map to `first` or `second` (impossible given frozenset keying), no issue. The logic is sound. Note only: the error message says "names no later page" but the actual failure could also be that the pair is present with a query that isn't one of the two — the message is slightly imprecise but acceptable. (eval/similar/rank.py)
- [note] f-437c154e: `by_path = {page.path: page for page in indexed}` — if two pages share the same `path` (shouldn't happen given slug_paths dedup, but if `template` were misconfigured or a collision slipped through), the dict silently drops one, and `by_path[path]` in the comprehension would KeyError or misattribute. The slug_paths algorithm guarantees uniqueness, so this is defensive-only. (eval/similar/rank.py)
- [note] f-f91ffe47: `_extract_index_links(index_md, wiki_dir)` — the second argument's semantics depend on `wiki_studio.querier._extract_index_links`; if it resolves links relative to `wiki_dir`, then `posixpath.normpath(link)` on an already-resolved absolute-ish path could behave unexpectedly. The test fixture uses relative links, so this passes, but the contract isn't obvious from the call site. (eval/similar/rank.py)
- [note] f-044d9be6: This test runs against the real repository's `eval/` inputs. If a developer has uncommitted changes to `eval/similar/protocol.json` or corpus pages, the test will fail with a refusal (exit 1) rather than a clean assertion — the failure mode is confusing. Also, it depends on the real `protocol.json` being present and valid. (tests/test_similar_rank.py)
- [note] f-434d4af2: `except (OSError, ValueError, KeyError, sqlite3.Error)` — `sqlite3.Error` is caught but `build_in_memory` failures could also surface as `RuntimeError` or other exceptions from the FTS5 layer. The test suite skips when FTS5 is unavailable, but a runtime FTS5 error mid-ranking would propagate uncaught and produce a traceback rather than the clean "nothing was written" message. Since `out_dir.mkdir` happens *after* `rank_study`, nothing is written on exception — good — but the error surface is inconsistent. (eval/similar/rank.py)
- [note] f-529531bf: The docstring says "reads only files under the repository and writes only `--out-dir`" — but `--out-dir` can be an absolute path outside the repo (as the tests do with `tempfile`). The claim is about *default* behavior; worth clarifying "writes only under `--out-dir` (default: `eval/similar/results/`)". (eval/similar/rank.py)
