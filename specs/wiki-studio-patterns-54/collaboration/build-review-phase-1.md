---
feature_id: wiki-studio-patterns-54
date: 2026-11-18
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-patterns-54
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-patterns-54 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

This is a documentation-only change adding a research-spike README and a package marker under `eval/patterns/`, plus one line in `CLAUDE.md`. The content is descriptive prose about existing wiki-studio behaviour, with many file/line citations. The main correctness risk is that the README makes numerous precise claims about code at a specific commit; if any citation is wrong, the study's credibility (and its fit map) is undermined. I cannot verify the cited line numbers from the diff alone, so I flag the verification gap and a few internal-consistency concerns.

## Findings

- [warning] f-e81527fe: The README pins all citations to commit `43aab76000ccb7acf8d5cda1ae5cdd929e452f72`, but the feature branch head is `57ca775`. If any cited file/line drifted between the base commit and the branch head (or will drift as later phases land), the citations become stale and the study's claims unverifiable. There is no automated check that the cited line numbers still match. (eval/patterns/README.md)
- [warning] f-17c191bc: The fit map asserts specific line ranges in `src/wiki_studio/schema/page-types.md` (e.g., 104-121, 11-25, 16, 18-23, 27, 36-39, 40-42, 46-49, 196-212) and in many source files. These are unverifiable from the diff and are the load-bearing evidence for the "no schema change needed" conclusion. A single off-by-N range silently invalidates a row of the fit map. (eval/patterns/README.md)
- [note] f-74432f0d: The README states `FINDING_KINDS` lists exactly twelve kinds and enumerates them. If the list changes in a later phase of this feature (or in a concurrent branch), this count and enumeration go stale. The claim is also load-bearing for the "no deduplication service" recommendation. (eval/patterns/README.md)
- [note] f-90c6bc67: The behaviour inventory describes `propose --from`, `promote`, `approve --revision`, `review_state`, `stale-claim`, `findings`, discovery, supersession and the conflict callout — each with file/line citations — but the README does not state how these descriptions were validated (read-only inspection vs. executed). For a "correctness" study, the method matters: a reader cannot tell whether "what the real verbs do" was observed by running them or inferred from source. (eval/patterns/README.md)
- [note] f-fb8ea043: The scope statement correctly defers agent-behaviour measurement to issue 75, but the README does not state what the *deliverable* of this phase is (the recommendation is described as the spike's deliverable, but phase 1 appears to be inventory + fit map only). A reader landing here mid-build cannot tell what is done vs. pending. (eval/patterns/README.md)
- [note] f-267d0794: The claim "each opens at the line cited" is a strong correctness assertion about every citation in the document. It is exactly the kind of claim that should be machine-checked (see first finding) rather than asserted in prose; as written it invites a reviewer to spot-check and find one wrong. (eval/patterns/README.md)
- [note] f-d38230ba: `eval/patterns/__init__.py` makes `eval/patterns` an importable package, but the README describes the directory as holding "fixture, labels, scripts, results, report" — i.e., data and scripts, not an importable library. If nothing imports `eval.patterns`, the `__init__.py` is unnecessary and may mislead readers into thinking there is a Python API here. (eval/patterns/__init__.py)
