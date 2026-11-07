---
feature_id: wiki-studio-0-9-0
date: 2026-11-07
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-9-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-9-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The conflict-scan module is well-structured and the pairing/dangling logic is largely sound, but there are correctness concerns around the `_body_lines` frontmatter detection (a page whose body legitimately starts with `---` after a missing frontmatter could be misparsed), the `_resolve_target` symlink/`..` handling relative to `wiki_dir` resolution, and the dedup key in `conflict_findings` which can silently drop a distinct dangling callout when two callouts share the same raw target but resolve differently. The `findings.py` scope-filtering also has a subtle issue: a paired `open-conflict` finding whose two pages straddle the scope boundary will be reported with only one page, which changes the finding's meaning.

## Findings

- [warning] f-c182f83e: `_body_lines` treats any file whose first line is `---` as having frontmatter and skips to the next `---`; a page with no frontmatter but a body starting with a horizontal rule (`---`) will silently drop all lines up to the next `---`, hiding callouts. Also, if the opening `---` has no closing `---`, `start` stays 0 and the whole file (including the `---`) is scanned — inconsistent with the "frontmatter present" branch. (src/wiki_studio/conflicts.py)
- [warning] f-c7eef817: `(wiki_dir / candidate).resolve()` follows symlinks and collapses `..`; if a symlink inside the wiki points outside, `relative_to(wiki_dir.resolve())` correctly rejects it — good. But `wiki_dir.resolve()` is recomputed per call and the comparison is against the resolved wiki root while `candidate` is built from the *unresolved* `page` relative path; if `wiki_dir` itself is a symlink, `page` (a relative path from `default_review_pages`) is still fine, but the asymmetry is fragile and the per-call `.resolve()` is wasteful. More importantly, `posixpath.join` on a `page` that already contains `..` (shouldn't happen, but not asserted) could escape before `.resolve()` normalizes — the `.resolve()` + `relative_to` guard does catch it, so this is a note not a bug. (src/wiki_studio/conflicts.py)
- [warning] f-754abeba: The dedup key is `("resolved", callout.resolved)` when resolved, else `("raw", callout.raw_target)`. Two callouts on the same page with the same raw target but different resolutions cannot occur (resolution is deterministic from page+target), so that's fine. However, two callouts with *different* raw targets that resolve to the *same* page (e.g. `../decisions/target.md` and `../decisions/./target.md`) are deduped by resolved path — correct — but the *first* one's `raw_target` is what appears in the dangling message if it later turns out dangling. Since dedup happens before `_dangling_reason`, a page with two spellings of a dangling target reports only one, which matches the docstring ("repeated callout to the same other page counts once") — acceptable. The real gap: a callout with `raw_target=None` (no `.md` link) and another with a raw target that resolves to `None` (escape) are keyed differently (`("raw", None)` vs `("resolved", None)` is impossible since resolved-None falls to raw branch) — actually both fall to `("raw", ...)`, so `("raw", None)` vs `("raw", "../x.md")` are distinct, which is correct. No bug, but the key construction is hard to verify by inspection. (src/wiki_studio/conflicts.py)
- [warning] f-1366ea89: For `open-conflict`, `conflict.pages` is the sorted pair `(a, b)`. The scope filter `tuple(page for page in conflict.pages if page in in_scope)` can yield a 1-tuple when only one side is in scope. The resulting finding then claims an "open conflict" but names only one page, which is misleading and changes the finding's semantics (a reader can't tell what the other page is). The docstring says "the same scope rule as the health findings keeps it and lists only its in-scope pages" — but for a paired finding, dropping one side loses essential information. (src/wiki_studio/findings.py)
- [note] f-4a40dc0c: `superseded_cache` is populated lazily and only for targets that pass the earlier checks (file exists, is a content page, not self). That's fine, but `read_live_page(target, paths)` is called with `target` as a *relative* path — consistent with how `scan_callouts` calls it (`read_live_page(page, paths)` where `page` is from `default_review_pages`). Confirm `read_live_page` accepts a wiki-relative path (it does per the call site in `scan_callouts`), so this is consistent. No action needed beyond a sanity check that `read_live_page`'s contract is "wiki-relative path". (src/wiki_studio/conflicts.py)
- [note] f-075bd2a1: `_LINK_TITLE_RE.sub("", match.group(1).split("#", 1)[0])` strips the fragment *before* the title. If a link is `[x](foo.md#frag "title")`, `split("#",1)[0]` yields `foo.md` and the title regex has nothing to strip — fine. But if a link is `[x](foo.md "title#with-hash")`, `split("#",1)[0]` yields `foo.md "title` — the title regex then fails to match (unbalanced quote) and the target becomes `foo.md "title`, which does not end with `.md`, so the link is skipped. This is an edge case but the ordering is fragile. (src/wiki_studio/conflicts.py)
- [note] f-5a44f0d3: The diff shows extensive fixture coverage for the scan itself, but the `findings.py` scope-filter interaction (a scoped run where only one side of an `open-conflict` pair is in scope) is the riskiest new behavior and should have an explicit test asserting the chosen semantics. (tests/test_conflict_callouts.py)
- [note] f-7cf33b44: The deferred import avoids a circular import (`findings` imports `conflicts`), which is correct, but it means the module-level `TYPE_CHECKING` import of `Finding` and the runtime import inside the function must stay in sync. A comment explaining the circular-import reason would help future maintainers not "clean it up". (src/wiki_studio/conflicts.py)
