---
page_type: concept
slug: harness-neutral-specs-contract
title: Harness-neutral governing contract (specs/)
status: draft
last_reviewed: 2026-10-28
sources:
  - path: eval/navigation/heldout/corpus/README.md
    sha: 79de8a1
page_id: pg-aacf9da786834129a092f122d775ad68
---

# Harness-neutral governing contract (specs/)

## Summary

Everything in MAP-ATLAS's `specs/` directory is the canonical source of truth. It is written to be harness-neutral, so different build harnesses can consume the same brief. Contributors build against it. A contributor changes it in the same commit as any public interface it describes.

## Key ideas

- `specs/PRD.md` holds the product requirements: users, problems, scope and non-goals.
- `specs/architecture.md` holds the package layout, module boundaries, data model, and the offline and AI seams.
- `specs/api.md` holds the public TypeScript API contract. These are the interfaces to build against.
- `specs/roadmap.md` holds the phased delivery. It lists the phase order and each phase's exit criteria.
- `specs/tasks.md` holds the buildable backlog of epics and tasks with acceptance criteria.
- `specs/decisions.md` holds the architecture decision log (ADRs).
- `CLAUDE.md` is the entry point for the Claude Code harness. It points at the same `specs/`.
- Any other harness should read `specs/` directly.
- The quick start lives only in `specs/api.md` § 0. The README does not repeat it, because a second copy drifts.
- Every fenced block in the quick start is checked. Each block either matches the bytes of a file under `examples/quick-start` or is generated from the repository.
- The install command in the quick start is the generated one.
- `check:packaging` compiles the quick-start example against the packed packages.
- `e2e/quick-start.e2e.ts` runs the quick-start example in a real browser.
- The README status table is generated from `specs/tasks.md`. It counts tasks with a **Done** record per phase.
- A zero in the status table means *no Done record*. It does not mean *no completed work*.

## Where this shows up

- `specs/` at the repository root.
- `README.md` sections "Quick start", "Status" (between the `generated:status` markers) and "The governing contract".
- `examples/quick-start`, `e2e/quick-start.e2e.ts` and the `check:packaging` script.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
