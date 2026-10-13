---
feature_id: ai-wiki-0-1-0
date: 2026-10-13
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/ai-wiki-0-1-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: ai-wiki-0-1-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The change replaces the symlink-mirroring approach in `_lint_staged_tree` with a `live_wiki_dir` parameter on `lint_wiki`, resolving escape links against the live wiki while keeping intra-wiki links authoritative in the staged copy. This is a cleaner design and the new tests cover the key scenarios. However, the `_link_resolves` helper has a subtle correctness issue with path normalization and relative-path handling that could cause false negatives or false positives in edge cases.

## Findings

- [warning] f-5557fa84: `Path(os.path.normpath(candidate))` does not resolve symlinks or `..` across symlinked parents the way `Path.resolve()` does, and `candidate.exists()` is checked *before* normalization — so a link like `../guide.md` that happens to exist relative to the staged copy (e.g., a stray file) would be accepted even though it should be judged at the live wiki. Conversely, `normalized.is_relative_to(...)` compares lexically-normalized paths, which can misclassify when `wiki_dir` itself contains symlinks or `..` segments. (src/aiwiki/lint.py)
- [warning] f-9bad0dca: `(live_wiki_dir / page.parent.relative_to(wiki_dir) / target)` assumes `page.parent` is always under `wiki_dir`. If `page` was produced by `list_pages(wiki_dir)` this holds, but the function is public-ish and the assumption is implicit; a `ValueError` from `relative_to` would propagate as an unhandled exception rather than a lint violation. (src/aiwiki/lint.py)
- [note] f-8e242c68: The escape branch does not verify that the resolved target stays within `live_wiki_dir`'s project root; a link like `../../../../etc/passwd` would be checked against the live filesystem. This matches prior behavior (the old symlink mirror also exposed siblings), so it is not a regression, but it is worth documenting that escape links are trusted to point at real project files. (src/aiwiki/lint.py)
- [note] f-ac9e7e87: The new implementation is much simpler and removes the `tempfile`/`shutil` symlink dance — good. But the docstring still says "escape links are resolved at `paths.wiki_dir`", which is accurate; consider also noting that intra-wiki links are judged against `stage_dir` (the post-apply tree), since that is the key correctness property being relied on. (src/aiwiki/promoter.py)
- [note] f-a4e84071: Good coverage of the intra-wiki case. Missing: a test where an escape link target exists in the staged copy's neighborhood but *not* at the live wiki (should be reported broken), and a test where the escape target exists at the live wiki but the staged copy has a same-named file (should still resolve via live wiki). These pin down the branch ordering in `_link_resolves`. (tests/test_lint.py)
- [note] f-c349ca03: The test name says "set-level validation rejects duplicate create" but the comment acknowledges the apply-time clobber guard fires first, so the test does not actually exercise set-level validation. The assertion is just `assertRaises(PromoteApplyError)` with no message check, so it would pass even if the wrong guard fired. (tests/test_promoter.py)
- [note] f-85a57c62: The `failing_read` predicate matches on `"knowledge/wiki" in str(self_)`, which is brittle (depends on the fixture layout string). If the layout changes, the test silently stops exercising the intended path and may pass vacuously. (tests/test_promoter.py)
