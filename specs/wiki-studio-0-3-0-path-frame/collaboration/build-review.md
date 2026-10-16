---
feature_id: wiki-studio-0-3-0-path-frame
date: 2026-10-16
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: fix/11-path-frame
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-3-0-path-frame — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The change addresses issue #11 cleanly: the prompt now states the wiki-relative path frame, `WikiPaths.strip_wiki_label` removes exactly one configured label prefix before the unchanged validators, and a read-only `info` verb exposes the resolved layout. The implementation is small, well-tested, and the strip is correctly scoped to the exact configured label. I found one correctness concern around the `info` verb's `layout` classification and a couple of minor notes.

## Findings

- [warning] f-73b64ff4: `layout` is computed as `custom` only when wiki or proposals source is non-default, but `root` can also be set via `--root`/`WIKI_STUDIO_ROOT`; a user who only overrides root will see `layout: default` even though the resolved layout is not the packaged default. The spec (FR-003) says "custom when the wiki or proposals directory came from a flag or variable", so this matches the spec literally, but the printed `root (flag)` line next to `layout: default` is confusing and arguably contradicts the intent of "resolved layout". (src/wiki_studio/cli.py)
- [warning] f-e4fcb1fe: `_location_source` treats an empty-string flag value as "not set" and falls through to env/default. If a user passes `--wiki-dir ""` (or a flag whose value is falsy), the reported source will be wrong. `WikiPaths.resolve` may or may not treat empty strings the same way — worth confirming the two agree. (src/wiki_studio/cli.py)
- [note] f-6dfd796a: The method strips `wiki_label + "/"` unconditionally. When `wiki_label == "."` (wiki at root), the prefix is `"./"`, which is correct for `./concepts/x.md` but will not strip a bare `concepts/x.md` (fine) nor a Windows-style `.\concepts\x.md` (out of scope, POSIX-only project). No bug, but the docstring could note the POSIX assumption. (src/wiki_studio/paths.py)
- [note] f-47630620: The strip is applied to every edit path including `append-log`/`append-index` actions. That is consistent with the spec, but if a future action ever legitimately needs a path starting with the label (e.g., a nested wiki), this would silently rewrite it. The current contract forbids that, so it is fine today. (src/wiki_studio/ingestor_multi.py)
- [note] f-bf016c89: The test asserts `"(default"` appears in stdout, which is a substring of `"(default)"` but also of any future `"(defaults)"`; low risk but slightly loose. Also, the test does not assert the `root` line's source, so a regression in `root_source` reporting would not be caught. (tests/test_path_frame.py)
- [note] f-2976aa2d: The README says "a copied heading prefix is removed, exactly once, before validation" but does not mention that this applies only to the exact configured label (not arbitrary prefixes). The spec is explicit; the README could be too, to avoid users expecting broader normalization. (README.md)
- [note] f-a6c42ef7: The JSON output emits `"schema": "project copy"` while the text output emits `schema: project copy at <dir>`. Machine consumers may prefer a stable enum like `"project"`/`"packaged"`. Minor API-design nit. (src/wiki_studio/cli.py)
