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

The changes add three test files covering FR-019, FR-020, and FR-021: approval through the gate, memkernel round-trip preservation of conflict callouts, and clean-install import of an approved callout pair. The tests are well-structured and the verbatim-copy approach for the memkernel parser is a reasonable way to pin evidence. I found a few correctness concerns around test isolation, fixture fidelity, and one assertion that may not actually exercise what it claims.

## Findings

- [warning] f-ec0d0254: The test compares `page.sources` against `wiki_studio.yaml_lite.parse_frontmatter(text)["sources"]`, but the copied memkernel parser and the wiki_studio parser are independent implementations. If they diverge on edge cases (e.g., quoting, nested keys, comments), the test could pass or fail for reasons unrelated to the actual memkernel behavior being pinned. The test claims to verify memkernel's parse, but the assertion is really "memkernel's copy agrees with wiki_studio's parser" — which is a different property. (tests/test_conflict_memkernel_roundtrip.py)
- [warning] f-cf4a30f6: `_frontmatter_lines` and `_body_after_frontmatter` both call `lines.index("---", 1)`, which finds the *first* `---` after line 0. If a page body legitimately contains a `---` (horizontal rule, YAML in a code fence, etc.), these helpers will mis-slice. The current fixtures don't trigger this, but the helper is fragile and the failure mode would be a confusing assertion error rather than a clear one. (tests/test_conflict_memkernel_roundtrip.py)
- [warning] f-8798c75a: `callout = "\n".join(line for line in text.splitlines() if line.startswith(">"))` collects *all* blockquote lines in the document, not just the conflict callout. If a page had two blockquotes, the assertion `self.assertIn(callout, page.body)` would require them to be contiguous in the body, which they may not be. For the current fixtures this is fine, but the helper's contract is unclear. (tests/test_conflict_memkernel_roundtrip.py)
- [warning] f-3f1e0baf: The helper hardcodes `decisions/use-postgres-for-the-user-db.md` and `concepts/all-services-log-json-to-stdout-never-write-log-files.md` and assumes both exist in the exported wiki. If the export fixture changes (page renamed, removed, or the export set is trimmed), this test fails with a confusing `read_page` error rather than a clear "fixture missing" message. It also couples the test to specific fixture content that isn't asserted anywhere. (tests/integration/test_memkernel_clean_install.py)
- [warning] f-2ddb5bd4: The filter `if "wiki" in m.tags` assumes the tag is exactly the string `"wiki"`. If memkernel tags are namespaced (e.g., `"source:wiki"`) or the tag set changes, the test silently selects zero memories and the subsequent `assertEqual(sorted(memories), sorted([left, right]))` fails with a misleading message. The test also doesn't assert that the filter matched anything before the equality check. (tests/integration/test_memkernel_clean_install.py)
- [note] f-ff48609d: The test name says "promotes and is dangling" but the body only asserts the file exists and that a dangling finding is produced. It doesn't assert the page's approval state or that promotion actually went through the gate (vs. being written directly). Given the class docstring emphasizes "not a lint or approval rule," asserting the page's state (e.g., `self.state(rel).state == "draft"` or `"approved"`) would strengthen the claim. (tests/test_conflict_callouts.py)
- [note] f-0d062324: `_KNOWN_SCALARS` is defined at module level and `parse_page` defines its own local `known` set with identical contents. This duplication is a maintenance hazard: if the copied parser is ever updated, the two sets can drift and the `set(page.extra)` assertion will silently check the wrong thing. (tests/test_conflict_memkernel_roundtrip.py)
- [note] f-ac0b32a1: The docstring says the parser functions are "copied verbatim" but `parse_page` uses a local `known` set rather than the module-level `_KNOWN_SCALARS`, and `WikiPage` is a dataclass substitute. The `WikiPage` departure is documented; the `known` duplication is not. Minor, but the "verbatim" claim is slightly overstated. (tests/test_conflict_memkernel_roundtrip.py)
