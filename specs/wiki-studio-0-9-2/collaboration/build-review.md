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

This diff adds a "Memory tools" section to the wiki maintainer instructions, documenting the boundary between memkernel's memory tools and wiki-studio's governed path. The content is documentation-only and appears consistent with the spec's intent to clarify that `wiki_export`/`wiki_import` are memkernel tools while `wiki-studio promote`/`approve` are the governed path. I found no correctness defects in the added text itself, but a few documentation-accuracy and cross-reference concerns are worth flagging.

## Findings

- [note] f-4f0aab76: The link pins memkernel to tag v0.8.0 while the surrounding text explicitly disclaims a compatibility claim; a reader may still infer v0.8.0 is the tested pair. The compatibility page is referenced but the pinned tag in the URL is a second, implicit version signal. (src/wiki_studio/schema/WIKI_MAINTAINER.md)
- [note] f-4a6c628f: The sentence asserts a specific behavior of `wiki_export` (that it goes through propose and promote) that lives in memkernel, not wiki-studio. If memkernel's implementation changes, this file becomes stale and misleading without any test catching it. (src/wiki_studio/schema/WIKI_MAINTAINER.md)
- [note] f-7c9abb46: This paragraph describes an end-to-end autonomous flow but does not state what happens when the host *does* reserve approval — i.e., whether `wiki-studio approve` fails, queues, or requires a human token. The "Unless" clause leaves the failure mode unspecified for the curator agent. (src/wiki_studio/schema/WIKI_MAINTAINER.md)
- [note] f-d1a8477a: Good disambiguation, but the two `promote` tools are only distinguished by name collision; a curator skimming may still confuse them. Consider also noting the inverse: `wiki-studio promote` does not touch memory tiers. (src/wiki_studio/schema/WIKI_MAINTAINER.md)
