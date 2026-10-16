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

The change correctly addresses issue #11: the prompt now states the wiki-relative path frame, `strip_wiki_label` removes exactly one configured label prefix before the unchanged validators, and a read-only `info` verb exposes the resolved layout. The implementation is small and well-tested. I found one correctness concern in the `info` verb's source detection (empty-string flag values) and a couple of minor notes.

## Findings

- [warning] f-d826e63a: `_location_source` uses `if flag_value:` which treats an empty-string flag value (e.g. `--wiki-dir ""`) as "not set" and falls through to env/default, reporting the wrong source. It is unclear whether `WikiPaths.resolve` treats empty strings the same way; if it does not, the reported source will disagree with the actual resolved path. (src/wiki_studio/cli.py)
- [note] f-cefb5489: `layout` is `custom` only when root/wiki/proposals source is non-default, which matches FR-003 literally, but a user who overrides only `--root` sees `layout: custom` while the wiki/proposals lines still say `(default)` — the printed `root (flag)` next to `layout: custom` is fine, but the reverse case (root default, wiki custom) is the only one that flips the label, which may surprise readers. (src/wiki_studio/cli.py)
- [note] f-49ae0c8a: The method strips `wiki_label + "/"` unconditionally. When `wiki_label == "."` the prefix is `"./"`, which correctly handles `./concepts/x.md` but not a bare `concepts/x.md` (fine) nor Windows-style `.\concepts\x.md` (out of scope, POSIX-only). No bug, but the docstring could note the POSIX assumption. (src/wiki_studio/paths.py)
- [note] f-6df49abd: The strip is applied to every edit path including `append-log`/`append-index` actions. Consistent with the spec today, but if a future action legitimately needs a path starting with the label (e.g. a nested wiki), this would silently rewrite it. (src/wiki_studio/ingestor_multi.py)
- [note] f-ee98f9d4: The test asserts `"(default"` appears in stdout, which is a substring of `"(default)"` but also of any future `"(defaults)"`; slightly loose. Also, the test does not assert the `root` line's source, so a regression in `root_source` reporting would not be caught. (tests/test_path_frame.py)
- [note] f-6ce2b12c: The README says a copied heading prefix is removed exactly once before validation but does not state that this applies only to the exact configured label (not arbitrary prefixes). The spec is explicit; the README could be too. (README.md)
- [note] f-4aac8bf4: The JSON output emits `"schema": "project"` / `"packaged"` (enum), while the text output emits `schema: project copy at <dir>`. The commit message says the JSON schema field is an enum, which is good; just confirm the text form is intentional and documented. (src/wiki_studio/cli.py)
