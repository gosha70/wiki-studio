---
page_type: workflow
slug: promote-lesson-to-wiki
title: Promote a Lesson to the Wiki
status: stable
last_reviewed: 2026-10-12
sources:
  - path: README.md
    sha: 77d3811c1afe59832e9faa935deff81cb4b10b92
---

# Promote a Lesson to the Wiki

## When to use this

A session produced a lesson worth keeping: a root cause, a decision, a procedure that will recur.

## Steps

1. Run `ai-wiki ingest <source>` to produce a patch-set under the proposals directory.
2. Review the preview files; edit them if needed.
3. Run `ai-wiki promote <proposal-dir>`; the structural linter gates the apply.
4. Run `ai-wiki audit-flush` to commit the ingest log.

## Verification

`ai-wiki lint` reports zero violations and the new page is linked from `index.md`.

## Related

- [Spec-Driven Development](../concepts/spec-driven-development.md)
- [Recover From a Torn Audit Log](../playbooks/recover-from-torn-audit-log.md)
