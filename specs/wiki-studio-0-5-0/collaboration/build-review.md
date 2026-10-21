---
feature_id: wiki-studio-0-5-0
date: 2026-10-20
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-5-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-5-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The prose scanner and checks 1–4 are well-structured, well-tested, and the documented "known limits" are honest. I found one correctness bug in the sentence splitter's abbreviation handling (a period after "etc." at end-of-sentence is never treated as a boundary, so a following sentence gets merged), plus a few smaller correctness/robustness concerns around the URL regex, the `_ends_with_abbreviation` prefix check, and the `paths` scoping semantics. None are blocking for an advisory feature, but the abbreviation bug will produce wrong word counts and missed findings in real prose.

## Findings

- [warning] f-df813b79: `_ends_with_abbreviation` returns True whenever the text before the match ends with an abbreviation, regardless of whether the match is actually the abbreviation's own period. For "Tools, etc. Next sentence." the regex matches the period after "etc", `text[start:match.end()]` ends with "etc.", so the boundary is skipped and "Next sentence." is merged into the previous sentence. This inflates word counts (false `sentence-length` findings) and can hide a real boundary. The docstring says "A period that ends 'e.g.', 'i.e.', 'etc.' or 'vs.' is not a boundary" — but the period *after* "etc." at end of sentence *is* a boundary. (src/wiki_studio/prose_lint.py)
- [warning] f-992320d0: The guard `if not before or not before[-1].isalnum()` is intended to avoid matching "etc." inside a longer word, but it only checks the character immediately before the abbreviation. For "abcetc." the char before "etc." is "c" (alnum) so it's correctly rejected; however for "e.g." the check is on the char before "e", which is fine. The real gap: abbreviations are matched by `endswith` on the *lowercased* slice, so "ETC." matches, but a word like "etcetera." does not end with "etc." so it's fine. The subtle bug is that `before[-1].isalnum()` rejects legitimate cases like "…, etc." only if the char before is alnum — but punctuation like "(" before "e.g." is allowed, which is correct. Low risk, but the logic is fragile and undocumented. (src/wiki_studio/prose_lint.py)
- [warning] f-72a2e888: The URL regex `\b(?:(?:https? (src/wiki_studio/prose_lint.py)
- [note] f-bb1feb06: `for index in range(end + 1 if end else 0, len(lines))` — when `end` is 0 (no frontmatter, or frontmatter ends at line 0), the expression `end + 1 if end else 0` yields 0, which is correct. But if `_frontmatter_end` returns 0 for a file that *starts* with `---` on line 1 and closes on line 1 (degenerate), the `if end` falsy check treats it as "no frontmatter" and starts at line 0, re-scanning the `---` lines. Edge case, but the `if end else 0` idiom is a footgun. (src/wiki_studio/prose_lint.py)
- [note] f-629158b3: `scoped = {Path(p).as_posix() for p in paths}` normalizes to posix, but `rel` is computed via `page.relative_to(wiki_dir).as_posix()`. If a caller passes an absolute path or a path with `./` prefix, `Path(p).as_posix()` won't match `rel`. The test only passes clean relative paths. Also, `paths=[]` (empty list) yields `scoped = set()` and scans zero pages — arguably correct, but `paths=None` vs `paths=[]` semantics should be documented. (src/wiki_studio/prose_lint.py)
- [note] f-8e7b8b4e: When Summary spans multiple segments, the finding is reported at `summary[0].line` — the first Summary paragraph's line, not the line of the sentence that pushed it over the limit. That's a reasonable choice but the message says "Summary has N sentences" without pointing at the offending sentence. Minor UX. (src/wiki_studio/prose_lint.py)
- [note] f-37fdf506: `_INLINE_CODE_RE` runs before `_LINK_RE` and `_URL_RE`. A URL inside inline code is masked as `CODE_TOKEN` first (good), but a link whose text contains a backtick (e.g. ``[`code`](url)``) will have the backtick span masked first, then the link unwrapped to `` `…` `` — the link text becomes the code token, which is fine. However, a link *target* containing a backtick or a URL containing `](` could confuse `_LINK_RE`. Low risk given the advisory nature. (src/wiki_studio/prose_lint.py)
- [note] f-8f3a7d5a: The page-count assertion `pages = [p for p in (FIXTURES_DIR / "wiki").rglob("*.md") if p.name != "log.md" or p.parent.name != "wiki"]` is convoluted and duplicates `_list_wiki_pages` logic. If `_list_wiki_pages` changes its exclusion rules, this test will silently diverge. (tests/test_prose_lint.py)
- [note] f-89c43ed3: The doc says "A sentence that starts with a digit or a lowercase word is joined to the sentence before it" — this is accurate given `_SENTENCE_END_RE` requires `[A-Z`]` after whitespace. But it doesn't mention the abbreviation-at-end-of-sentence bug (see first finding), which will be a common surprise ("etc. Next" merges). (src/wiki_studio/schema/lint-rules.md)
- [note] f-079e7390: `from .health_lint import _list_wiki_pages` is a private-symbol import done lazily to avoid a cycle. This is a known pattern but couples prose_lint to health_lint's internals. If `_list_wiki_pages` is renamed or its exclusion rules change, prose lint silently changes scope. (src/wiki_studio/prose_lint.py)
