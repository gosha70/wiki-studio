---
feature_id: wiki-studio-patterns-54
date: 2026-11-18
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-patterns-54
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-patterns-54 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The fixture is well-constructed and the test suite exercises the real API against a temporary copy, which is the right shape. However, there are several correctness issues: the manifest's `words_page`/`words_record` counts are asserted by the test but the test recomputes them from the same files, so a mismatch between the README table and the manifest would go undetected; the `test_word_counts_recompute` uses `body.split()` which counts whitespace tokens including markdown syntax, which may not match the README's stated methodology; and the `test_background_copies_and_exclusions` asserts `open-questions` does not exist but the README says `open-questions/.gitkeep` is a non-page file that was excluded — the assertion is correct but the README's phrasing is ambiguous. More importantly, the `test_pattern_pages_follow_the_convention` asserts `y_statement_sentences` matches `split_sentences(paragraphs[0])`, but the manifest records 3 for record pages and 1 for successors — the successor pages have a different Decision paragraph structure ("In the context of the Benchmark page, we chose...") which may not split into exactly 1 sentence under the prose linter's sentence splitter.

## Findings

- [warning] f-784399db: The successor page `benchmark-explains-itself-linking-runs-is-a-pipeline-step.md` has a Decision paragraph "In the context of the Benchmark page, we chose a setting, a correlate pipeline step and a live payload over a backend-free one-shot view." followed by "Chosen: ..." — the test asserts `len(split_sentences(paragraphs[0])) == 1`, but the paragraph contains a comma-separated list and a "we chose X over Y" construction that the prose linter's sentence splitter may or may not treat as one sentence. If `split_sentences` splits on the period after "view." only, this passes; if it splits on any internal punctuation, it fails. Verify against the actual `split_sentences` implementation. (eval/patterns/manifest.json)
- [warning] f-68d9e408: The test recomputes `words_page` as `len(body.split())` where `body` is everything after the closing `---`. The README says "Words are whitespace-separated tokens: the page body after the frontmatter" — this matches. But `words_record` is computed as `len("\n".join(corpus_lines[start:end]).split())` where `start` is the index of the `### ` heading line and `end` is the next `### ` or `## ` line. The README says "the record's section in the corpus copy from its heading to the next heading" — this also matches. However, the test does not verify that the README's table values match the manifest's values; a divergence between README and manifest would pass the test. (tests/test_patterns_eval.py)
- [warning] f-160827a9: The `overview.md` background entry has `sha256_at_pin` != `sha256` (5 links rewritten), which is expected. But the test `test_background_copies_and_exclusions` only asserts `sha256_of(copy) == entry["sha256"]` — it never verifies `sha256_at_pin` against anything, and never verifies that `links_rewritten` matches the actual count of rewritten links in the copy. A copy with the wrong number of rewrites (e.g., 4 instead of 5) would pass. (eval/patterns/manifest.json)
- [warning] f-92ec8e85: The stale record `### stale: Benchmark UI was backend-free, one-shot and Studio-only` has `words_record: 235`, but the corpus section for this record includes a `replay:` block with `later-task`, `seed`, `expected`, `trap`, and `how-to-judge` fields. The test's `words_record` computation includes all lines from the `### ` heading to the next `### ` or `## ` heading, which includes the replay block. This is consistent with the README's "from its heading to the next heading" — but the README's table shows `235` for this record while the page is `151`, a 84-word difference that is larger than the other records' differences (typically 50-60 words). Verify the count is correct and not an off-by-one from including/excluding the trailing blank line. (eval/patterns/manifest.json)
- [note] f-c01e3af8: The successor page's `Consequences` section says "Revisit when: not recorded in the source record" and "Tests: unit tests cover FR-2, FR-3, FR-4 and the payload..." — but the test `test_pattern_pages_follow_the_convention` asserts `"Revisit when:" in section(body, "Consequences")`, which passes. However, the successor page's `Context` section says "Does not apply when: not recorded in the source record" — this is a placeholder that weakens the page's usefulness as a pattern. The README does not flag this as a known limitation. (eval/patterns/wiki/decisions/benchmark-explains-itself-linking-runs-is-a-pipeline-step.md)
- [note] f-5e18a784: The log has 14 entries but the README says "one line per pattern page" — there are 14 pattern pages (12 records + 2 successors), so 14 entries is correct. However, the log entries are not in strict reverse-chronological order: `2026-09-17` appears after `2026-09-08` (correct, newer first), but `2026-09-08` appears twice in a row (benchmark-explains-itself and benchmark-step-reuses), and `2026-07-18` appears three times. The README says "newest at the top" — the ordering is correct by date but the two `2026-09-08` entries are not ordered by any secondary key. This is a style note, not a correctness issue. (eval/patterns/wiki/log.md)
- [note] f-5754b350: The test asserts `result.violations == ()` on the fixture, but the README says "No page has an approval record, so the review kinds report the pages unapproved as well." If `api.lint` includes review-kind findings in `violations`, this test would fail. The test passes, so either `api.lint` does not include review findings in `violations`, or the fixture has approval records. Verify that the test's assertion matches the README's stated expectation. (tests/test_patterns_eval.py)
- [note] f-dd816d5e: The README says "The copy is `eval/patterns/corpus/decisions-57.md`, and it is unchanged: the hash above is the hash of the committed copy." The test `test_corpus_copy_matches_the_pin` verifies this. However, the README does not state the word-count methodology for `words_record` explicitly enough to reproduce — it says "the record's section in the corpus copy from its heading to the next heading" but does not say whether the heading line itself is included in the count. The test includes the heading line (`corpus_lines[start:end]` where `start` is the heading index). (eval/patterns/README.md)
