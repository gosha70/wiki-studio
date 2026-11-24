---
feature_id: wiki-studio-duplicates-121
date: 2026-11-23
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-duplicates-121-evidence
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-duplicates-121 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The change adds a comprehensive test suite (`tests/test_duplicates_corpus.py`) that pins the extracted corpus to `corpus.json` via sha256, recomputes per-page input counts, verifies the README's corpus section against `corpus.json`, checks the six fixed items byte-for-byte against the builder, and runs structural lint on a temporary wiki. The README gains a detailed "The extracted corpus" section documenting counts, differences from the pitch, left-out items, empty-paragraph pages, input-count statistics, and lint results. Overall the tests are thorough and well-targeted at the FR-011/FR-012 requirements; a few correctness and robustness concerns remain.

## Findings

- [warning] f-cdae3e62: The test scans every file under `eval/duplicates/` (including `README.md`, `corpus.json`, `extract.py`, `sample.py`, `labels.json`, etc.) for `CLOSING_KEYWORD_RE`. This is broader than the stated intent ("no page or file holds closing-keyword text") and will fail if any future doc, comment, or test fixture legitimately mentions a closing keyword (e.g., a README example, or the regex definition itself in `extract.py`). It also couples the test to unrelated files in the directory. (tests/test_duplicates_corpus.py)
- [warning] f-466a97e3: For non-H3 forms, the test asserts `body.startswith(DECISION_HEADING)` and then checks that if a bold span opens the rest, its `title_from_label` differs from the entry title. This only catches a label that survives *at the very start* of the Decision section. A label left mid-body (e.g., after a blank line or a sub-bullet) would not be detected. The test name promises "no body keeps its label line" but the check is narrower. (tests/test_duplicates_corpus.py)
- [warning] f-eaea9441: The test asserts the README's "Pages" column equals `corpus.json` counts, but does not verify the "The pitch's count" column against any source. The pitch counts are hardcoded in the README and could drift silently (e.g., a typo in "84" vs "88"). Since the README explicitly claims these are the pitch's numbers and the rule was not tuned, a regression here would go undetected. (tests/test_duplicates_corpus.py)
- [warning] f-fbd195e3: The test builds `expected` as a `Counter` over `(repository, form)` for empty-paragraph entries, then compares to `{key: expected[key] for key in self.by("repository", "form")}`. This works only because `Counter` returns 0 for missing keys — but the README table is asserted to have exactly `len(self.by("repository","form"))` rows, so any (repo, form) with zero empty pages must still appear in the README with `0`. The README does show zeros, so this passes today, but the test would silently accept a README that omits a zero row if the row count check were relaxed. More importantly, the assertion `bullets(lines) == [entry["page"] for entry in empty]` depends on `corpus.json` iteration order matching the README bullet order; if `corpus.json` is ever re-sorted, this breaks without a semantic change. (tests/test_duplicates_corpus.py)
- [note] f-f8e54874: The test asserts `self.assertIn(f"\n  - path: {entry['spec_path']}\n    sha: {pins[repository]}\n", page)`. This hardcodes the exact YAML indentation (`  - path:` and `    sha:`) and key order. If the frontmatter emitter changes indentation or key order (e.g., `sha` before `path`), the test fails even though the page is semantically correct. It also assumes exactly one source entry per page. (tests/test_duplicates_corpus.py)
- [note] f-68ef535e: The test calls `is_excluded(row["repository"], row["spec_path"].split("/")[1])` — indexing `[1]` assumes every `spec_path` has the form `specs/<name>/...`. If a future entry uses a different layout (e.g., `docs/...`), this raises `IndexError` rather than a clear assertion failure. Similarly, `family["directories"]` is assumed to be a list of names. (tests/test_duplicates_corpus.py)
- [note] f-7283c2ac: The test copies pages into `decisions/` and writes an `index.md` linking them, but does not copy any other wiki structure (e.g., `decisions/index.md`, category pages) that `lint_wiki` might expect. If `lint_wiki`'s structural checks evolve to require additional files, this test will start failing for reasons unrelated to the corpus. The README's "The list is empty" claim is also only validated against the current lint implementation. (tests/test_duplicates_corpus.py)
- [note] f-b29fd24a: The README states "The test copies every page to `decisions/<slug>.md` in a temporary wiki, with an `index.md` that links every page and a `log.md`" — accurate. However, the "Structural-lint violations" subsection says "The list is empty: no page holds a Markdown link, so no link target is checked, and every page passes the other checks." This is a strong claim that will silently become stale if a future page gains a link; the test would catch it, but the README prose would then be wrong until updated. Consider phrasing as "As of this run, the list is empty" to signal it is a snapshot. (eval/duplicates/README.md)
- [note] f-bba8041a: These hardcode `last_reviewed: 2026-11-23` and `status: stable`. If `lint_wiki` adds a staleness check relative to "today," these fixtures will eventually fail. They are also duplicated knowledge of the frontmatter schema. (tests/test_duplicates_corpus.py)
