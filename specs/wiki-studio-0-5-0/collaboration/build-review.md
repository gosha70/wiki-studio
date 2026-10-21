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

The change adds a `## Writing rules` section to `ingest-rules.md` and cross-references it from `page-types.md`, `WIKI_MAINTAINER.md`, and `lint-rules.md`, plus tests asserting the section reaches all three composed prompts. The core change is documentation-only and the tests correctly verify the wiring through `load_schema_files` and the three prompt composers. I found one documentation inconsistency (the lint-rules text references a `--prose` flag that does not exist in this change) and a minor test-coverage gap.

## Findings

- [warning] f-9aace01b: The new text advertises a `wiki-studio lint --prose` flag and says its findings are advisory, but no such flag is added in this diff and the CHANGELOG does not mention it. If the flag does not exist yet, the schema now documents a non-existent CLI surface, which will mislead both users and the model reading the schema. (src/wiki_studio/schema/lint-rules.md)
- [note] f-d8dba697: The tests assert the literal string `## Writing rules` appears in `schema_excerpts["ingest_rules"]`, but do not assert that the excerpt is actually rendered into the final prompt text the model sees. If `compose_*` ever stops embedding `schema_excerpts` into the rendered prompt, these tests would still pass while the rules silently drop out of the model input. (tests/test_prompt.py)
- [note] f-69ba3356: The preserve list mixes categories: identifiers, paths, numbers, and `path:` citations are syntactic tokens, while "if", "unless", and "not verified" are semantic qualifiers. Grouping them under one "preserve exactly" list is fine, but the rationale for the qualifier words is not stated, so a model may not understand why they must survive a rewrite (they change the truth value of a claim). (src/wiki_studio/schema/ingest-rules.md)
- [note] f-d866d481: The upgrade note tells users to merge the `## Writing rules` section into a local `schema/ingest-rules.md`, but does not say where in the file it should go or that the section is self-contained (no dependencies on surrounding text). A user could paste it in a spot that breaks the surrounding structure. (CHANGELOG.md)
