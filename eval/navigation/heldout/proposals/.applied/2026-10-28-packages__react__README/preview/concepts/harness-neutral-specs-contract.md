---
page_type: concept
slug: harness-neutral-specs-contract
title: Harness-neutral governing contract (specs/)
status: draft
last_reviewed: 2026-10-28
sources:
  - path: eval/navigation/heldout/corpus/README.md
    sha: 79de8a1
  - path: eval/navigation/heldout/corpus/packages__core__README.md
    sha: 79de8a1
  - path: eval/navigation/heldout/corpus/packages__maplibre__README.md
    sha: 79de8a1
  - path: eval/navigation/heldout/corpus/packages__offline-pmtiles__README.md
    sha: 79de8a1
  - path: eval/navigation/heldout/corpus/packages__react__README.md
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
- The quick start packs only the five packages its example imports.
- `check:packaging` compiles the quick-start example against the packed packages.
- The packaging gate packs all six packages together and installs them side by side. It does this on every change.
- `e2e/quick-start.e2e.ts` runs the quick-start example in a real browser.
- The packages are not published to a registry. A package README does not repeat an install command it cannot run. It points at the quick start instead.
- A package that the quick start does not install carries a generated install sentence between the `generated:add-to-install` markers.
- That sentence names the extra `npm pack` path and tarball to add to §0. It is generated from the package's manifest, so the tarball filename follows the version.
- Every code block in a package README names a file. The repository compiles that file against the packed packages on every change.
- A package README code block is compiled, not executed. Only the quick start is also run in a browser.
- A package README does not present a block that no gate checks as something to paste. It describes such a feature in prose instead.
- A package README's peer-dependency list is generated from the package's own manifest, between the `generated:peers` markers.
- The README status table is generated from `specs/tasks.md`. It counts tasks with a **Done** record per phase.
- A zero in the status table means *no Done record*. It does not mean *no completed work*.

## Where this shows up

- `specs/` at the repository root.
- `README.md` sections "Quick start", "Status" (between the `generated:status` markers) and "The governing contract".
- `examples/quick-start`, `e2e/quick-start.e2e.ts` and the `check:packaging` script.
- `packages/core/README.md` and its compiled example `examples/readme/core/track.ts`.
- `packages/maplibre/README.md` and its compiled examples `examples/readme/maplibre/worker.ts` and `examples/readme/maplibre/controller.ts`.
- `packages/maplibre/README.md` describes `--mapatlas-focus-ring-color` in prose only, because nothing in the repository exercises it yet.
- `packages/react/README.md`, its generated peers block and its compiled example `examples/readme/react/canvas.tsx`.
- `packages/offline-pmtiles/README.md`, its `generated:add-to-install` block and its compiled example `examples/readme/offline-pmtiles/regions.ts`.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [@mapatlas/maplibre — the MapLibre GL renderer and its wiring](mapatlas-maplibre-package.md)
- [@mapatlas/react — the React bindings over the engine's seams](mapatlas-react-package.md)
- [@mapatlas/offline-pmtiles — offline map regions over PMTiles archives](mapatlas-offline-pmtiles-package.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
