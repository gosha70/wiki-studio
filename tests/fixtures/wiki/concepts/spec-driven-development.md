---
page_type: concept
slug: spec-driven-development
title: Spec-Driven Development
status: stable
last_reviewed: 2026-10-12
sources:
  - path: README.md
    sha: 77d3811c1afe59832e9faa935deff81cb4b10b92
---

# Spec-Driven Development

## Summary

Work starts from a written specification with user scenarios and requirements, a plan is derived from it, and the build is reviewed against both. The spec, not the conversation, is the source of truth.

## Key ideas

- Requirements are numbered so reviews can cite them.
- Each build phase maps to one user scenario.
- Drift from the originating request is caught by an alignment gate.

## Where this shows up

- `specs/<feature-id>/spec.md`, `plan.md` and `tasks.md` in a project.
- The promote step in [Promote a Lesson to the Wiki](../workflows/promote-lesson-to-wiki.md).

## Related

- [Use Hybrid Search Before Graph Traversal](../decisions/use-hybrid-search.md)
- [Prefer Small Commits](prefer-small-commits.md)
