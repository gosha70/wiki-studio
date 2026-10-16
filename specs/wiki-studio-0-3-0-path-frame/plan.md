---
spec_mode: full
feature_id: wiki-studio-0-3-0-path-frame
risk_category: bugfix
justification: "A defect that loses most ingests at any custom wiki location; the owner holds the 0.3.0 release until it is fixed, so the fix is specified and reviewed like a feature."
status: approved
date: 2026-10-16
collaboration_mode: single
origin:
  issue: 11
  urls:
    - https://github.com/gosha70/wiki-studio/issues/11
  origin_claim: |
    Issue #11 (filed from run 1 of the navigation evaluation): the ingest
    prompt labels every wiki file it shows as "<wiki-label>/<path>" so no
    absolute path leaks, but the response contract requires wiki-relative
    paths and the instructions never say so; with a one-word label the model
    copied the prefix in eight of ten documents. Fix, in one small release
    separate from the evidence PR: (1) the response instructions state the
    frame; (2) the parser strips only the exact configured label prefix and
    then runs all existing path-safety validation unchanged; (3) tests with a
    one-word and a nested label. Expose the resolved layout (default or
    custom; root, wiki dir, proposals dir, and which flag or variable set
    each) through `lint` output or a dedicated `info` command; `--version`
    stays machine-readable. Page types and directories stay fixed. The owner:
    no release until #10 and #11 are addressed.
---

# Plan: one path frame for the ingest prompt, and `info`

## Summary

Three small changes in the places the defect touches: a sentence in the
multi-page response instructions and a `description` on the schema's `path`
property (what the model is told); `WikiPaths.strip_wiki_label` applied in
the multi-ingestor before the validators (what the parser forgives, exactly
one configured prefix); and a read-only `info` verb that prints the resolved
layout with the source of each location (what a user sees before running
anything). Everything else, including every validator and the five verbs,
stays as it is.

## Technical Context

**Language/Version**: Python 3.11–3.13, stdlib only
**Touched**: `paths.py`, `ingestor_multi.py`, `backends/copilot_cli.py`, `prompt.py`, `cli.py`, README, CHANGELOG, tests
**Testing**: stub backends in-process; no model call

## Constitution Check

| Rule file | Concern | Status |
|-----------|---------|--------|
| `coding-standards.md` | Fix the root cause, not the symptom | OK — the prompt gets the rule it lacked; the strip is a guard for the exact prefix only |
| `safety.md` | Path handling | OK — stripping happens before the unchanged `..`/escape/placement checks |
| `copilot-conventions.md` | Minimal, one logical change | OK — separate branch and PR from the evidence work |

## Architecture Decisions

### ADR-1: Tell the model, then forgive exactly one thing
The instruction removes the cause; the strip removes the one copy the
headings invite. Nothing else is normalised, so a genuinely wrong path still
fails with the same message.

### ADR-2: `info` rather than a line in `lint`
`lint` needs a wiki to exist and exits non-zero on violations; a user asking
"where will this write?" wants an answer before that. `info` is read-only,
additive and exits 0; `--version` stays one line.

### ADR-3: The strip lives on `WikiPaths`
The label is a property of the resolved layout, so the inverse belongs beside
it; the ingestor already holds a `WikiPaths`.

## Scope

### Task 1: Prompt and strip (US1)
### Task 2: `info` (US2)
### Task 3: Tests, docs, CHANGELOG

## Risks

- A wiki at the root itself gives label `.`; stripping `./` is harmless and
  covered by a test.
- Models may still invent other prefixes; those fail validation as before and
  are visible in stderr, which is the desired behaviour.
