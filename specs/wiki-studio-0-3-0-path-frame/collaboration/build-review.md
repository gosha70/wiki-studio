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

The change addresses issue #11 with a small, well-scoped fix: the multi-page prompt now states the wiki-relative path frame, `WikiPaths.strip_wiki_label` removes exactly one configured label prefix before the unchanged validators, and a read-only `info` verb exposes the resolved layout. The implementation is careful about the collision case (wiki directory named like a page directory) and is well-tested. I found one correctness concern in the `info` verb's source detection and a few minor notes.

## Findings

- [warning] f-869811a9: An empty-string flag value (e.g. `--wiki-dir ""`) is treated as "not set" and falls through to env/default, reporting the wrong source. The origin-alignment record claims `WikiPaths.resolve` uses the same falsy test, but `resolve` uses `root or environ.get(...)` on the *raw* value, whereas `_location_source` inspects `args.wiki_dir` — if argparse ever yields a non-empty-but-falsy value or the two paths diverge, the reported source will disagree with the actual resolved path. (src/wiki_studio/cli.py)
- [note] f-399f842a: The `must_exist` heuristic only fires when the path *as given* does not exist but the stripped one does. If both exist (e.g. a real nested `decisions/index.md` alongside a root `index.md`), the shape rule wins and the copied prefix is kept — which is the intended behavior, but the docstring's "the prefix was copied and is removed" phrasing could be read as unconditional. Worth a one-line clarification that the existence check is a tiebreaker, not a rule. (src/wiki_studio/paths.py)
- [note] f-94cb6523: `parts[1].endswith(".md")` accepts `concepts/.md` and `concepts/x.md.md`; the shape check is intentionally loose (validators do the rest), but a path like `concepts/.md` would be treated as wiki-relative and skip the strip. Low impact given downstream validation, but worth a note in the docstring that the check is deliberately permissive. (src/wiki_studio/paths.py)
- [note] f-d5f6aff5: `layout: custom` is set when *any* of root/wiki/proposals is non-default, including a root-only override. This matches the updated spec text, but the printed `wiki-dir: … (default)` next to `layout: custom` may read as contradictory. The origin-alignment record acknowledges this; consider a short parenthetical in the text output (e.g. `layout: custom (root overridden)`) to make the reason visible. (src/wiki_studio/cli.py)
- [note] f-2f58df4c: The substring `"(default"` also matches a future `"(defaults)"`; and the test does not assert the `root` line's source, so a regression in `root_source` reporting would not be caught. The `test_overridden_root_is_custom` case does cover the flag path, but not the default path for root. (tests/test_path_frame.py)
- [note] f-0a604aa6: The README says a copied heading prefix is removed once before validation but does not state that this applies only to the *exact configured label* (not arbitrary prefixes). The spec is explicit; the README could mirror that to avoid a reader assuming broader normalization. (README.md)
- [note] f-14276c90: The strip is applied to `append-log`/`append-index` actions too. Consistent with the spec today, but if a future action legitimately needs a path starting with the label (e.g. a nested wiki), this would silently rewrite it. The `must_exist` tiebreaker mitigates the common case. (src/wiki_studio/ingestor_multi.py)
