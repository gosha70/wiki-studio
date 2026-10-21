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

The fact-preservation feature is well-scoped and the advisory-only contract is respected throughout (no exit-code changes, `promote` ignores the key). The core `removed_facts` logic is sound for the tested cases, but I found a few correctness gaps around regex edge cases, frontmatter parsing, and a subtle interaction with the `_PATH_LINE_RE` "kept" logic that could produce false negatives (missed warnings) or false positives.

## Findings

- [warning] f-10ec7c36: The lookbehind excludes `/` and `.` before the match, so a path like `./src/retry.py:42` or `../src/retry.py:42` will not match at the leading `.`/`..` — but more importantly, a path embedded after a `/` (e.g. `see /abs/src/retry.py:42`) is silently skipped. Also `foo.bar.py:42` matches only `bar.py:42` because the lookbehind rejects the `.` before `bar`, producing a truncated fact that won't match the same citation written differently. (src/wiki_studio/fact_diff.py)
- [warning] f-4dc06d35: `kept  (src/wiki_studio/fact_diff.py)
- [warning] f-d5f93691: When frontmatter parsing fails, the function returns `([], body)` — the body is still extracted, but the `sources[].path` values are silently dropped. That means a page with malformed frontmatter will never warn about dropped `sources[].path` citations, which is exactly the case where a curator most needs the warning. The test `test_page_without_or_with_broken_frontmatter` only checks backticked identifiers, not sources. (src/wiki_studio/fact_diff.py)
- [warning] f-a83b1586: The regex allows a single newline between the number and its unit (`[ \t]*\n?[ \t]*`), which is intended for reflowed prose. But it also matches across a paragraph break if the next line happens to start with a unit word — e.g. `"5\ns"` at the end of one paragraph and `"s"` starting the next. More concretely, `"3\nmin"` where `min` is the start of a new sentence ("min is the minimum") would be captured as `3 min`. The `(?![A-Za-z0-9])` guard does not prevent this because `min` is followed by a space. (src/wiki_studio/fact_diff.py)
- [warning] f-b198644c: `_BACKTICK_RE` is applied to `prose` (fences blanked), which is correct. But `_BODY_PATH_RE` and `_PATH_LINE_RE` are applied to the *raw* `body`, not `prose`. So a `path: foo.md` or `src/x.py:1` inside a fenced code block will be counted as a fact. If the old page has such a reference only inside a fence and the new page removes the fence, it will be reported as a removed fact — a false positive. The test `test_fenced_code_is_not_an_identifier_source` only covers backticks. (src/wiki_studio/fact_diff.py)
- [warning] f-42a24cdb: `live.read_text(encoding="utf-8")` can raise `UnicodeDecodeError` or `OSError` (e.g. permission denied, file deleted between `is_file()` and `read_text`). The docstring says "Raises OSError if the filesystem operations fail; the caller maps to OutputWriteError exit code 6" — but a `UnicodeDecodeError` is not an `OSError` and will propagate as an unhandled exception, breaking `ingest`/`propose`/`query --file-back` for a page with non-UTF-8 bytes. The fact check is advisory and must never block the write. (src/wiki_studio/ingestor_multi.py)
- [warning] f-4300da3a: `json.loads(plan_path.read_text(...))` is unguarded. If `plan.json` is malformed (e.g. truncated by a prior crash, or hand-edited), the CLI raises an unhandled `JSONDecodeError` and the verb exits with a traceback instead of the documented exit code. Since this is called after a successful write, a corrupt plan.json is unlikely but possible; more importantly, `_do_propose` calls it *before* `--promote`, so a parse error would block promotion of an otherwise-valid patch-set. (src/wiki_studio/cli.py)
- [note] f-705ac8b3: `ident[:-2] if ident.endswith("()")` strips `()` from `foo()` → `foo`, but also from `foo(bar)()` → `foo(bar)`, and from a literal `()` → empty string (filtered out by `if f`). The intent is to treat `retry_budget()` and `retry_budget` as the same fact, which is reasonable, but stripping `()` from a call with arguments is inconsistent. Minor; document the intent or only strip when the identifier is a bare name. (src/wiki_studio/fact_diff.py)
- [note] f-836ee13e: `([^\s`)\],]+)` stops at `)`, `]`, `,`, backtick, whitespace — but not at `.`, `;`, `:`, `?`, `!`. So `path: docs/retry.md.` captures `docs/retry.md.` (with trailing period), which will not match the frontmatter `docs/retry.md` and produces a spurious removed fact. The test `test_moved_citation_is_kept` uses `(path: docs/retry.md).` — the `)` saves it, but `path: docs/retry.md.` at end of sentence would fail. (src/wiki_studio/fact_diff.py)
- [note] f-17562978: The test asserts `removed_facts(old, new) == []` for `1,000 tokens` vs `1000 TOKENS`, `50 %` vs `50%`, `2 KB` vs `2 kb`, `30ms` vs `30 ms`. This is good coverage, but it does not cover the case where the *unit* changes case in a way that should still match (it does, via `.lower()`), nor the `%` no-space rule vs other units. Consider adding `2KB` vs `2 KB` (no space) and `50%` vs `50 %` (space) explicitly to lock the normalization contract. (tests/test_fact_diff.py)
- [note] f-a7151818: The doc says "Compared as normalized sets over the whole page, so a moved citation or a reflowed paragraph is no warning." This is accurate for the tested cases, but does not mention the path-only-vs-path:line asymmetry (see finding above) or that fenced code is excluded only for backticks, not for `path:`/`path:line` (see finding above). Curators reading the doc will be surprised by both. (docs/patch-set-format.md)
- [note] f-86c39b08: Adding `wiki_dir: Path  (src/wiki_studio/ingestor_multi.py)
