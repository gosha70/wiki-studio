---
feature_id: wiki-studio-0-6-0
date: 2026-10-24
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-6-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-6-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The change implements FR-014 citation evidence checking against the prompt snapshot rather than a file reread, which is the correct architectural choice. The implementation is clean, well-tested, and the test backend was correctly updated to quote real page text. I found one correctness concern around the abstention form and one minor edge case, but nothing blocking.

## Findings

- [warning] f-c8ab95b1: The abstention form is documented as "empty answer, one citation quoting index.md", but the code only enforces "non-empty answer needs ≥1 citation" and "each citation must quote its page". An empty answer with zero citations passes (test_empty_answer_without_citations_is_not_an_evidence_failure confirms this), and an empty answer with multiple citations also passes. The spec/README wording ("an empty answer with one citation quoting index.md is the abstention form") implies a stricter contract than what is enforced. This is a spec-vs-implementation mismatch that could let a backend return an empty answer with no evidence at all and still be accepted. (src/wiki_studio/querier.py)
- [note] f-5febc54c: The containment check uses substring matching on whitespace-normalised text. A fragment that happens to be a substring of a larger word (e.g. fragment "Foo" matching "Foobar") will pass. This is acceptable for the stated goal ("verifies quotation, not logical support") but worth noting: a very short fragment like "a" or "the" trivially passes against almost any page. Consider a minimum fragment length or word-boundary check if stronger evidence is desired. (src/wiki_studio/querier.py)
- [note] f-5d67307f: The test backend now quotes the first non-blank line, which for a page with YAML frontmatter is the `---` delimiter (as the new test asserts: `abstained.citations[0].fragment == "---"`). This is technically valid evidence (the `---` does occur in index.md) but is a degenerate quotation that doesn't exercise the interesting path. It also means the abstention citation quotes frontmatter rather than content. (src/wiki_studio/backends/test.py)
- [note] f-ea950a11: The `padded` variant replaces only the first space with "\n " and prepends "  ", which does exercise leading/trailing whitespace and one newline, but does not exercise a multi-space run collapse (the page has "with   extra spaces" — three spaces). The test name promises whitespace-run collapsing but the variant doesn't actually contain a multi-space run in the fragment. (tests/test_query_evidence.py)
- [note] f-94d9bf25: The refactor to cache `contents[rel]` only for scored pages is correct and avoids the double-read, but note that `pages_content` is now built from the cached dict rather than re-reading. This is the intended fix (snapshot consistency) and is good. No action needed beyond confirming `contents` is populated for every rel in `pages_loaded` — it is, since `pages_loaded` derives from `selected` which derives from `scored`, and every scored rel was added to `contents`. Correct as written. (src/wiki_studio/querier.py)
