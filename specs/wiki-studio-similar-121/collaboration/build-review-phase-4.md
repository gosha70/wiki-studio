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
target_ref: feature/wiki-studio-similar-121
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

The implementation is well-structured and thoroughly tested: the similar-pages hint is correctly isolated from the write path, runs before the lock, degrades gracefully without FTS5, and never blocks a proposal. I found no blocking correctness issues; the findings below are minor robustness and consistency notes.

## Findings

- [note] f-dac651a3: If the new page has no `page_type` frontmatter, `page_type` is `None`/empty and the filter `review.frontmatter_value(page.text, PAGE_TYPE_KEY) != page_type` will match every existing page that also lacks `page_type` — but more importantly, a create with no `page_type` will silently list pages of any type that also lack it, which may be surprising. Consider short-circuiting to an empty list (or an explicit error) when the new page has no `page_type`, since the hint's contract is "pages of its page type". (src/wiki_studio/discovery.py)
- [note] f-144c1e7a: The catch is narrow by design, but `select`/`rank_cached` may raise other exceptions (e.g. `OSError` from cache I/O, `UnicodeDecodeError` from a malformed page). Those would propagate out of `propose` and abort the proposal, contradicting the "advisory: it never blocks the proposal" contract in the docstring. Consider broadening to `Exception` (logging the class name) or at least adding `OSError`. (src/wiki_studio/discovery.py)
- [note] f-31f983ed: `exclude` includes every edit's path, including `update`/`append-index` targets. That is intentional (a proposal's own pages are never listed), but it means an `update` to an existing page will hide that page from a sibling `create`'s similar list even though the page exists in the live wiki. This is defensible but worth a one-line comment so a future reader doesn't "fix" it. (src/wiki_studio/api.py)
- [note] f-9a086762: Passing `sys.maxsize` as `max_bytes` relies on `select` summing byte sizes without overflow; on a very large wiki this is fine in CPython but is a slightly fragile idiom. A named sentinel or `None` (if `select` supports it) would be clearer. Low priority. (src/wiki_studio/discovery.py)
- [note] f-bd9831d6: The test patches `discovery.rank_cached`, but `similar_pages` calls `select`, which presumably calls `rank_cached` internally. This works today, but it couples the test to an internal call path; if `select` is refactored to call a different ranker entry point, the test silently stops exercising the error path (the mock would be unused and the real ranking would run). Consider asserting the mock was called, or patching at the `select` boundary. (tests/test_similar_pages.py)
- [note] f-f53ce06e: The docstring says "unset or empty is on, else `on` or `off` in any case after stripping; any other value raises `ValueError`." The code checks `if similar_value and choice not in (...)` — so a whitespace-only value like `"   "` is truthy, strips to `""`, and raises. That matches the test (`"   "` raises), but the docstring's "unset or empty is on" could be read as "whitespace-only is on". Tighten the wording to "unset or empty string is on; a value that strips to empty raises". (src/wiki_studio/paths.py)
- [note] f-383a4c76:  None` (src/wiki_studio/ingestor_multi.py)
