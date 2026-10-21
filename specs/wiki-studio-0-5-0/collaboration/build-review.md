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

The change adds an optional `avoid:` key to glossary pages and an `Avoid:` line to glossary index entries, plus a shared whole-word matcher used by the missing-cross-links check. The implementation is careful and well-tested, but there are a few correctness concerns around the matcher's handling of hyphenated slugs, the `_anchor` function's Unicode behavior, and the `_read_page_avoid` frontmatter scan that could miss or misreport edge cases.

## Findings

- [warning] f-fc984cfb: The `_INNER_SPACE` pattern allows a single line break between words of a term, but the docstring and CHANGELOG claim a slug written with spaces "matches only within one paragraph." A term like `origin check` will match across a soft-wrapped line inside a paragraph (intended), but the pattern also matches across a line break that is followed by a list marker or heading marker on the next line only if the marker itself is not a word char — e.g. `origin\n- check` would not match (good), but `origin\ncheck` at the start of a new paragraph without a blank line (e.g. after a hard-wrapped paragraph) does match. This is consistent with the tests but the "one paragraph" claim is slightly stronger than the implementation. Suggest tightening the docstring/CHANGELOG wording to "at most one line break, no blank line" to match behavior. (src/wiki_studio/prose_lint.py)
- [warning] f-186112a4: `_anchor` uses `re.sub(r"[^\w\s-]", "", lowered)` where `\w` is Unicode-aware by default in Python 3. This means non-ASCII letters (e.g. accented characters, CJK) are kept in the anchor, which may not match the anchor scheme used elsewhere in the codebase (e.g. GitHub-style anchors that strip non-ASCII or use a different transliteration). If the anchor is used to build links or compare against existing anchors, this could produce mismatches. Verify against the anchor scheme used by `_intra_wiki_links_from` / existing glossary index anchors. (src/wiki_studio/prose_lint.py)
- [warning] f-2c621f93: The frontmatter scan iterates `for i in range(1, end)` and matches `_FM_AVOID_RE` against each line. If a page has a multi-line YAML value (e.g. a folded scalar or a `sources:` block) that happens to contain a line starting with `avoid:` at column 0, it would be misread as the avoid key. More importantly, the scan does not skip indented lines, so an indented `  avoid: ...` inside another key's block would not match (good), but a top-level `avoid:` appearing after a `sources:` block is correctly found. The risk is low but worth a comment noting the scan is line-based and assumes `avoid:` is a top-level key. (src/wiki_studio/prose_lint.py)
- [warning] f-401833d4: When a term is listed under two canonicals, the code drops it from both entries (`terms = tuple(t for t in entry.terms if t.lower() not in shared)`). If an entry's only term is shared, the entry is dropped entirely from `avoid_map` (the `if terms:` guard). This means the canonical page loses its avoid-list association entirely, and the `avoid-format` finding is reported against only the *last* owner (`owners[term][-1]`), not all owners. A user fixing the reported page may not realize the other page also lists the term. Consider reporting one finding per owner, or including all owner pages in the message. (src/wiki_studio/prose_lint.py)
- [note] f-2a46fbc6: The "first non-blank line after each heading" logic uses `next((j for j in range(i + 1, len(lines)) if lines[j].strip()), None)`. If a heading is the last line of the file, `first` is `None` and the entry is skipped silently — no problem is reported even if the heading has no body. This is probably fine (an empty entry is not an avoid-format problem), but it means a heading followed only by blank lines and then EOF is silently accepted. Consider whether an empty entry should be flagged elsewhere (out of scope for this change). (src/wiki_studio/prose_lint.py)
- [note] f-44da0ada: `aliases = {e.canonical: list(e.terms) for e in avoid_map.values() if e.anchor is None}` filters to per-file glossary pages only, which matches the ADR ("Index-entry terms feed only the term lock"). However, the `avoid_map` is keyed by canonical term, and for per-file pages the canonical is the file stem. If a per-file glossary page's stem does not match any slug in `slug_to_page` (e.g. the page is not linked from anywhere and has no inbound edges), the alias is silently unused. This is correct behavior but worth a comment. (src/wiki_studio/health_lint.py)
- [note] f-cd0b84cf: The test asserts that the index `Avoid:` line is not counted as a mention, but it does not assert the positive case where a per-file glossary page's avoid term *is* counted as a mention in the same scenario. The `test_synonym_only_page_triggers_missing_cross_link` covers the positive case separately, but a combined test would catch regressions where `strip_index_avoid_lines` accidentally strips per-file page content. (tests/test_avoid_terms.py)
- [note] f-d336ab15: The ADR says "Not determined: whether memkernel's Memory model could store frontmatter extras elsewhere." This is an open question that could affect the round-trip guarantee. It is correctly flagged as a follow-up, but the ADR should note that if memkernel later stores extras, the accepted-syntax restriction may be relaxed. (docs/adr/0001-glossary-avoid-key.md)
- [note] f-6cced6d0: The check `if len(value) >= 2 and value[0] == '"' and value[-1] == '"'` strips one pair of outer double quotes, then checks for `"` inside. A value like `"a" "b"` (two quoted terms separated by space, no comma) would strip the outer quotes to `a" "b`, then fail the `"` check — good. But a value like `""` (empty double-quoted) strips to empty string, then `terms = [""]` and `any(not term ...)` catches it as "empty term after splitting" — good. A value like `"a,b"` strips to `a,b` and splits into `a`, `b` — this is arguably correct (the quotes are just wrapping the whole value, not individual terms). The behavior is consistent with the ADR's "one pair of double quotes" wording. (src/wiki_studio/prose_lint.py)
- [note] f-014ea56b: The check `if page.stem == INDEX_STEM` reports an `avoid:` key in the glossary index frontmatter as a problem. This is correct per the ADR, but the message says "put an 'Avoid:' line under each '### <term>' entry" — it does not mention that the index frontmatter `avoid:` is ignored entirely (not just moved). A user might think the frontmatter key is still read somewhere. The message is clear enough, but consider adding "the frontmatter key is not read on the index." (src/wiki_studio/prose_lint.py)
