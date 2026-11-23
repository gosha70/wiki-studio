---
feature_id: wiki-studio-0-11-0
date: 2026-11-23
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-11-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-11-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The change adds a new `source-revision-changed` finding kind (C2 anchor-touch rule) with a `Revisit when:` line quote, plus supporting parsing, git diff collection, and a study replay test. The implementation is generally careful and well-tested, but I found a few correctness concerns around the `_Changes` cache keying, the `revision_changed` fallback semantics, and the `heading_above` fence handling that warrant attention.

## Findings

- [warning] f-e894fca5: The `_Changes` caches (`differs`, `hunks`) key on `(id(repo), commit, path)`. `id()` is only stable while the object is alive; `_Repo` instances are held by `repos` for the run so this is safe in practice, but it is fragile and inconsistent with the rest of the module which uses `repos.index(...)` for grouping. If a future refactor reuses `_Changes` across runs or drops the `repos` reference, stale hits could occur. (src/wiki_studio/revisions.py)
- [warning] f-a42e9290: `revision_changed` returns `bool(whitespace_differs)` for a page with no anchors. If `whitespace_differs` is `None` (git could not answer), this silently returns `False` rather than surfacing "not checked". The caller `_decide_changed` does guard against `None` before calling, so this is currently safe, but the pure function's contract is ambiguous: a `None` input yields a definitive `False` decision. (src/wiki_studio/revisions.py)
- [warning] f-efdaa02e: The fence-close check requires `set(stripped) == {fence[0]}` and `len(stripped) >= len(fence)`. This rejects a valid close like ```` ``` ```` when the opener was ```` ```` ```` (4 backticks) — correct — but also rejects a close with trailing whitespace stripped correctly, and more importantly it treats any line of only the fence char as a close even if it is indented up to 3 spaces (correct per CommonMark) but does not handle a close fence with a different char count that is still valid (e.g., opener ```` ``` ````, closer ```` ```` ```` is valid per CommonMark but rejected here). This can cause headings inside a fenced block to be treated as real headings, producing false anchor matches. (src/wiki_studio/revisions.py)
- [note] f-6172a459: Lines beginning with `\` (the "no newline" marker) are neither hunk headers nor `+`/`-` lines, so they are skipped — correct. But a `+`/`-` line whose content itself begins with `\` after the marker is preserved as `line[1:]` starting with `\`, which is fine. No bug, but worth a comment noting the marker is intentionally dropped. (src/wiki_studio/revisions.py)
- [note] f-de5846d8: For a backticked identifier containing `/`, the last dotted component is *not* added (per the rule). For one without `/`, `identifier.rsplit(".", 1)[-1]` is added even when the identifier has no dot — in which case the rsplit returns the whole identifier, duplicating it in the set (harmless). But for an identifier like `foo.bar.baz` the added component is `baz`, which may be a very short/common token; the length/letter filter catches short ones but not e.g. `data`. This matches the documented rule, so it is a known limit, not a bug. (src/wiki_studio/revisions.py)
- [note] f-2b0ebff8: `_LIST_MARKER_RE.sub("", line.lstrip(), count=1)` strips a leading list marker, but `line.lstrip()` also strips leading whitespace that the ADR says is allowed ("after leading whitespace and an optional list marker"). This is consistent with the ADR. However, a line like `  - Revisit when: x` becomes `Revisit when: x` — correct. A line like `1. Revisit when: x` becomes `Revisit when: x` — correct. A line like `-Revisit when: x` (no space) is not stripped (regex requires `[ \t]+`), so it would not match — consistent with "optional list marker" requiring a space. Fine. (src/wiki_studio/revisions.py)
- [note] f-d9e50fce: The test imports `from eval.revisions import candidates` and reads `results/candidates.json` at class setup. If `eval/` is not shipped in the installed package or the JSON is absent, the test errors rather than skips. This couples the unit test suite to a study artifact. (tests/test_revision_findings.py)
- [note] f-a2211a08: When a source is `OUTCOME_CHANGED` and flagged, the loop `continue`s, so a source can never produce both `source-revision-changed` and `source-not-at-revision`. This matches the spec ("Superseded pages, sources with `source-not-at-revision` ... get none"), but the `continue` also skips the `if source.outcome != OUTCOME_NOT_AT_REVISION: continue` guard — which is fine since `OUTCOME_CHANGED != OUTCOME_NOT_AT_REVISION`. No bug, but the control flow is slightly subtle; a comment would help. (src/wiki_studio/findings.py)
- [note] f-2558a966: `SourceCheck.revision_changed` defaults to `False`, but `_Source.revision_changed` uses `None` to mean "undecided". The `check_sources` conversion sets `flagged = source.outcome == OUTCOME_CHANGED and bool(source.revision_changed)`, so an undecided changed source becomes `False` in the `SourceCheck` — but it was already converted to `OUTCOME_NOT_CHECKED` by the preceding `if`, so `outcome == OUTCOME_CHANGED` is false. Consistent, but the dual `None`/`False` semantics across the two dataclasses is easy to misread. (src/wiki_studio/revisions.py)
