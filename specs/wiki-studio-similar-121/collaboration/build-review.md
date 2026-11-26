---
feature_id: wiki-studio-similar-121
date: 2026-11-25
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-similar-121
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-similar-121 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

This round's diff is documentation-only (CHANGELOG, README, MCP adapter doc, patch-set format doc) for the similar-pages feature. The docs are internally consistent with each other and with the described behavior (advisory, `create`-only, `WIKI_STUDIO_SIMILAR_PAGES` switch, `similar_pages`/`similar_pages_error` keys, stderr `similar:` lines, MCP `similar_pages` field). No code correctness, security, or API-design issues are introduced by these changes; a few documentation-accuracy notes are worth addressing.

## Findings

- [note] f-30807717: The CHANGELOG entry embeds a long inline URL to `eval/similar/report.md` on `main`, which will drift from the release tag and is inconsistent with the README's relative-path reference; also the phrasing "in 1 of the 3 `supersedes` tries" is ambiguous (1 of 3 supersedes cases, or 1 of 3 total tries?). (CHANGELOG.md)
- [note] f-c02704b8: README says the hint "lists unrelated pages beside any real match on every create," which overstates the behavior — the list may be empty (per `docs/patch-set-format.md`: "possibly empty") and may be absent entirely when the switch is off or when `similar_pages_error` is written. (README.md)
- [note] f-97969a29: The MCP doc says `similar_pages` is `[]` "when the server was launched with `WIKI_STUDIO_SIMILAR_PAGES=off`," but the patch-set format doc says with the switch off "`off` writes neither key" — so the adapter must synthesize `[]` from absence. The doc should state this explicitly so implementers don't assume the key is present in `plan.json`. (docs/mcp-adapter.md)
- [note] f-e47b14f0: The error row lists `FTS5 not available: <reason>` and `not computed: <exception class name>` but does not say whether `similar_pages` and `similar_pages_error` are mutually exclusive per edit (the row says "instead of," which is good) nor whether `similar_pages_error` can appear alongside an empty `similar_pages`. Minor, but worth one clarifying clause for consumers parsing `plan.json`. (docs/patch-set-format.md)
- [note] f-5e21d708: The env var row says "any other value exits 1," but does not say at what point (startup vs. first `propose`). For a CLI user this matters — e.g., does `find` also fail? The MCP doc implies the switch is read at server launch. Clarify scope (which commands validate it). (README.md)
