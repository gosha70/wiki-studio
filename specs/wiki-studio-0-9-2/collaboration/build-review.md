---
feature_id: wiki-studio-0-9-2
date: 2026-11-15
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-9-2
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-9-2 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The test file is a well-structured, self-checking suite that validates the packaged persona against the CLI and MCP parsers, with explicit "the checker bites" tests to guard against false negatives. The design is sound and the assertions are mostly precise, but a few correctness gaps exist: the `_wiki_studio_failure` flag-allowlist check can be bypassed by abbreviated flags that argparse accepts as prefixes, the `--disable-tool` detection in `command_failure` is fragile against `--disable-tool=value` spellings, and `loop_step`/`section_text` will raise `ValueError` rather than a clear assertion when the persona drifts. These are worth addressing before merge.

## Findings

- [warning] f-e249a87f: The flag check `if flag.startswith("--") and flag not in allowed` only rejects flags that argparse did not accept; but argparse accepts unambiguous prefixes (e.g. `--revis` for `--revision`), so an abbreviated flag in the persona would parse successfully and then be rejected by the allowlist — good — but the allowlist is built from `_option_string_actions` of the *parsed* verb, which for a prefix-abbreviated flag will contain the canonical name, not the abbreviation. The check therefore does catch it, but the error message says "spelled in full" while the actual failure mode is that argparse silently expanded it. This is correct behavior but the diagnostic is misleading; consider asserting the token equals the canonical option string rather than relying on set membership. (tests/test_maintainer_persona.py)
- [warning] f-85a93958: The dispatch `tokens[0].startswith("--disable-tool")` will also match `--disable-tool-foo` or `--disable-toolbar`, routing unrelated spans into `_mcp_failure` where they will fail with a confusing message. It also misses the case where `--disable-tool` appears as a non-first token in a bare span (e.g. a fenced line that is just `--disable-tool promote` is fine, but `--disable-tool=promote` as first token is handled, while `--disable-tool promote` as a *second* token in a non-`wiki-studio` span is not). (tests/test_maintainer_persona.py)
- [warning] f-0e6c291c: Both helpers use `text.index(...)` / `PERSONA.index(...)` which raise `ValueError` with a bare message when the heading or step label is missing. A persona edit that renames a heading would surface as an opaque `ValueError: substring not found` rather than a clear test failure naming the missing anchor. `loop_step` already raises `AssertionError` for a missing step label but not for a missing `LOOP_HEADING`. (tests/test_maintainer_persona.py)
- [note] f-3a97aaaf: `_parse` catches `SystemExit` but not `argparse.ArgumentError` or other exceptions; if a future parser change raises instead of exiting, the test will error rather than report a clean failure. Low risk given current argparse behavior, but worth noting. (tests/test_maintainer_persona.py)
- [note] f-c9b2876a: `flag_value` returns `None` both when the flag is absent and when it is present with no value (e.g. `--by` at end of tokens). Callers use `assertIsNotNone` to mean "flag present with value", which conflates the two cases. If the persona ever writes `--by` with no value, the test would report "missing" rather than "present but valueless". (tests/test_maintainer_persona.py)
- [note] f-f9ace77b: The "checker bites" tests cover the listed `REJECTED_SPANS` but do not include a case for an abbreviated flag (e.g. `wiki-studio approve <page> --revis <sha256> --by x`) that argparse would accept as a prefix. Adding one would lock in the "spelled in full" guarantee the docstring claims. (tests/test_maintainer_persona.py)
- [note] f-8db7f60c: The comment cites "line 46" of a pinned memkernel tag; if the upstream file is reflowed, the line number drifts even though the content is unchanged. The test only checks the constant's content, not the line number, so the citation is decorative but could mislead a future re-pinner. (tests/test_maintainer_persona.py)
