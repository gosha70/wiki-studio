---
feature_id: wiki-studio-0-11-0
date: 2026-11-22
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-11-0-evidence
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-11-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The change adds a well-structured, model-free evaluation fixture for the revision-check study: labels, protocol, seven supplementary cases, a pre-successor copy, and a structural test. The design is careful and the test coverage of the committed files is thorough. I found a small number of correctness and consistency issues, mostly around the test's fence check and a couple of protocol/README mismatches, none of which block the study from proceeding.

## Findings

- [warning] f-29565011: The fence test scans every file under `eval/revisions/` except `keyword-quoting/`, but the README's fence rule says the exclusion is exactly `eval/revisions/cases/keyword-quoting/`. The test's `FENCED_DIR in path.parents` check is correct for that, but the test also scans `README.md`, `labels.json`, `protocol.json`, and `case.json` files whose `reason` fields for the fenced cases are supposed to be in the labeller's own words. If any future edit to a fenced case's `reason` (in its own `case.json`, which is inside the fence) is fine, but a copy of that reason into `protocol.json` or `README.md` would be caught — good. However, the test does not scan `CLAUDE.md` or the commit message, which the README's fence rule also covers. This is a gap between the stated rule and the enforced check. (tests/test_revisions_fixture.py)
- [warning] f-56fb6783: The README says "any closing-keyword file check excludes exactly `eval/revisions/cases/keyword-quoting/` and nothing else. `tests/test_revisions_fixture.py` runs such a check over the rest of this directory." But the test's `CLOSING_KEYWORD_RE` is `(close[sd]? (eval/revisions/README.md)
- [warning] f-bc8565b7: The protocol says the `Revisit when:` line is "the first body line outside fenced code whose text, after leading whitespace and an optional list marker, starts with the prefix". The README says the same. But the `pre-successor` copy's `Revisit when:` line is `Revisit when: a driver-side CI gate is reintroduced or the merge profile changes.` — this is fine. However, the two built cases (`provider-config-guarantee`, `benchmark-provider-id`) have `Revisit when: not recorded in the spec.` The protocol's `not_recorded` rule says "a page with no such line, or whose line contains \"not recorded\" (case-insensitive), has no Revisit-when tokens". This means C3 and C4 fall back to C1 for both built cases. That is consistent, but it means the two built cases cannot exercise C3/C4 at all — they only test C0/C1/C2. This is a design limitation worth noting, not a bug. (eval/revisions/protocol.json)
- [warning] f-c6f5d986: The case is labelled `should_flag: false` because the cited file does not exist at the cited commit. The test `test_a_flagged_case_changed_between_its_sha_and_its_read_commit` correctly skips the `at_sha`/`at_read` comparison for non-flagged cases. But the test `test_the_page_cites_the_case_source` requires the page's frontmatter to contain `  - path: benchmarks/backends/vllm.md` followed by `    sha: c8b1f97`. The page does contain that. However, the page also cites `scripts/run-compare-anthropic-vs-vllm.sh` at `sha: c8b1f97` — and the case's `path` is `benchmarks/backends/vllm.md`. The test only checks the first occurrence of the case's `path`, which is correct. No bug, but the case's `reason` says "the correction repointed the page's two sha values" — the page has two `sha: c8b1f97` lines, and the correcting commit changed both. The test does not verify that the page's other cited source (`scripts/run-compare-anthropic-vs-vllm.sh`) is also absent at `c8b1f97`, which would strengthen the "citation error" label. Minor. (eval/revisions/cases/vllm-backend-doc/case.json)
- [note] f-89a789ef: The README says "The page is always the page as it stood at the correcting commit's parent." But for the two spec cases (`provider-config-guarantee`, `benchmark-provider-id`), the page is a **built** page, not a page from the repository. The README's "The fixtures" section clarifies this ("for the two spec cases, a **built** `decision` page"), but the "read rule" section's blanket statement is slightly misleading. A reader could think the built pages are also from the parent commit. (eval/revisions/README.md)
- [note] f-c7e56f84: The `sha_derivation` for `pre-pr-doc-audit` says the derived sha is "the commit of the page's previous revision, the last to touch the page before the correcting commit." The `page_from.commit` is `69926b16...`, which is the read commit (the correcting commit's parent). The derived sha is `a9628e5...`, which is the commit of the page's previous revision. But the `source_change_commits` are `d0e48c3`, `34a752d`, `801309f` — three commits that changed the script. The derived sha `a9628e5` is not among them. This is correct per the derivation rule (the derived sha is the page's previous revision, not a source change commit), but a reader might expect the derived sha to be one of the source change commits. The README's "The fixtures" section explains this, but the `case.json`'s `sha_derivation` string could be clearer. (eval/revisions/cases/keyword-quoting/pre-pr-doc-audit/case.json)
- [note] f-18fc46b4: The test asserts that each changed source's judgment appears in the README as `@ \`{sha}\`  (tests/test_revisions_fixture.py)
- [note] f-77fc37a4: The bar's recall condition says "With at least 4 cases labelled `should_flag: true` (matched negatives excluded), the candidate keeps at least three quarters of them, rounded up: 3 of 4, 4 of 5, 5 of 6, 6 of 7." The study has exactly 5 positives (three keyword-quoting + two built). So the bar is "4 of 5". This is a reasonable bar, but it means a candidate that flags all 5 positives and 5 false pages passes, while a candidate that flags 4 positives and 4 false pages also passes. The bar does not distinguish between these. This is a design choice, not a bug, but it means the bar is relatively lenient on recall. (eval/revisions/protocol.json)
- [note] f-2082d718: The README says "Five cases are labelled `should_flag: true`: the three keyword-quoting cases (one page at three moments) and the two built pages. Without the two built pages the count is three." This is clear, but the README does not explain why the two built pages are counted as separate cases rather than as one case (they are both built pages from spec decision text). The reader might wonder whether the two built pages are independent evidence or two views of the same phenomenon. (eval/revisions/README.md)
- [note] f-9d1a7663: The case is labelled `should_flag: false` because "the cited rules file gained a section on writing style and kept the four-question gate the page cites it for; the page's edit answered the removal of two scripts and an environment variable it names, not the cited change." This is a matched-negative-style label, but the README says "None was added" for matched negatives. The case is not a matched negative (it is a case in its own right, labelled false), but the README's "Matched negatives" section could be clearer that this case is a false positive of the plain check, not a matched negative. (eval/revisions/cases/run-wiki-ingest-rules/case.json)
