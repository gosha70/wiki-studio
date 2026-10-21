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

The prose-lint tier (checks 1–5) is wired through `api.lint` and the CLI with sensible advisory/strict semantics, and the term-lock check correctly reuses the masked segments so code, fences and quotes are skipped. The main correctness concerns are around the `--paths` scoping of the avoid-format findings (which can silently drop glossary problems when the glossary page isn't in scope) and the interaction between `--prose` and `--health` for avoid-format reporting. A few smaller issues around line-number computation and the `_is_glossary_page` fallback are worth noting.

## Findings

- [warning] f-93759d86: When `--paths` is given and the glossary page is not in scope, avoid-format problems are silently dropped because `problem.path in scoped` filters them out — but the glossary is always read in full, so a malformed `Avoid:` line is invisible under `--paths` even though the term lock itself still uses the (possibly empty) avoid map. This is inconsistent with the documented "term lock still reads the whole glossary" behavior and can hide a real data problem. (src/wiki_studio/prose_lint.py)
- [warning] f-aaec6e35: `line = segment.line + segment.text.count("\n", 0, match.start())` assumes `segment.line` is the line of the segment's first character and that `segment.text` starts exactly at that line. If `scan_page` ever trims leading whitespace/newlines from a segment (e.g., list-item continuation), the computed line will drift. Worth a targeted test with a multi-line list item or a paragraph preceded by blank lines to confirm the invariant. (src/wiki_studio/prose_lint.py)
- [warning] f-c56e8b6e: The function returns `True` for any page under `GLOSSARY_DIR/` even if its frontmatter is malformed or missing `page_type: glossary`. That means a broken glossary page silently suppresses the term lock on itself, which is probably fine, but the `except ContractViolationError: return False` path means a malformed glossary page *outside* `GLOSSARY_DIR/` would be treated as non-glossary and get term-lock findings against its own `Avoid:` lines. Confirm this is intended; if a page declares `page_type: glossary` but has a contract violation, the safer default is to skip the term lock (treat as glossary) rather than flag it. (src/wiki_studio/prose_lint.py)
- [note] f-efe68262: The docstring says "Avoid-format problems are reported by the health tier when it runs and by the prose tier otherwise, so each appears once." This is true only when `health=True`; but if `health=True` and `prose=False`, avoid-format is reported by health (correct), and if `prose=True` and `health=True`, prose suppresses it (correct). However, if `health=True` but the health tier itself is scoped by `only` and the glossary page isn't in scope, the health tier may also drop the avoid-format finding — leaving it unreported in both tiers. Verify the health tier's scoping behavior for avoid-format. (src/wiki_studio/api.py)
- [note] f-4cff884a: Findings are appended in `avoid_map.values()` → `entry.terms` → `find_term` order, then the whole list is sorted by `finding.line` only. Two findings on the same line (e.g., two avoid terms in one sentence) will have non-deterministic relative order across Python versions if `avoid_map` is a plain dict built from parsing order — usually stable, but worth pinning with a secondary sort key (`(line, check, message)`) for reproducible CLI output and stable test assertions. (src/wiki_studio/prose_lint.py)
- [note] f-863acc2f: The test name promises two assertions (heading checked, glossary page not checked) but only asserts the heading case. The "glossary page is not" half is untested — a regression that starts flagging the glossary's own `Avoid:` lines would pass this test. (tests/test_prose_cli.py)
- [note] f-a09547f0: The test asserts `both.stderr.count("flow list is not supported") == 1`, but doesn't assert *which* tier reported it (health vs. prose). A regression where prose reports it and health doesn't (or vice versa) would still pass. The API test `test_avoid_format_goes_to_health_when_both_run` covers the API side, but the CLI test could assert the `[avoid-format]` tag is absent from prose output when `--health` is also passed. (tests/test_prose_cli.py)
- [note] f-b5103c64: Adding `prose: ProseLintResult  (src/wiki_studio/api.py)
- [note] f-5a2ae35d: The changelog says "the term lock still reads the whole glossary" but doesn't mention that avoid-format problems are also read from the whole glossary yet filtered by `--paths` (see first finding). Once the scoping behavior is settled, update the changelog to match. (CHANGELOG.md)
