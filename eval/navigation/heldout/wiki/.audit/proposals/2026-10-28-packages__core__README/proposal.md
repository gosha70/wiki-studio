# Proposal: 2026-10-28-packages__core__README

**Rationale:** The source passes the four-question gate. (1) Reusable: it defines what @mapatlas/core contains, which seams it owns, and the dependency direction between packages. Any future contributor needs that. (2) Citable: the repo file eval/navigation/heldout/corpus/packages__core__README.md at sha 79de8a1. (3) Non-duplicative: the existing pages mention @mapatlas/core only by name. No page covers the core package's data model, seams, portability functions or testing fakes. I create one new concept page for it and update the related pages instead of repeating their content. (4) New-contributor-relevant: a newcomer has to learn the core package boundary before touching any other package. Edits: I create concepts/mapatlas-core-package.md. I update map-atlas-engine to link the new page and to state the dependency direction. I update harness-neutral-specs-contract with the rule that package README code blocks are compiled but not executed, and that packages are not published to a registry. I also append one index entry and one log entry.

## concepts/mapatlas-core-package.md
**Action:** create  
**Rationale:** No existing page covers the core package's data model, seams, portability functions, testing fakes or dependency direction. This new concept page is the one canonical entry for it.

```markdown
---
page_type: concept
slug: mapatlas-core-package
title: "@mapatlas/core — the framework-agnostic data model and seams"
status: draft
last_reviewed: 2026-10-28
sources:
  - path: eval/navigation/heldout/corpus/packages__core__README.md
    sha: 79de8a1
page_id: pg-944f0a2326874aaab648e16aec803007
---

# @mapatlas/core — the framework-agnostic data model and seams

## Summary

`@mapatlas/core` holds MAP-ATLAS's data model and every seam the rest of the engine is built behind. It knows nothing about a browser, a map library or a database. It knows nothing about any domain, such as fish, plants, products or users. Every other engine package depends on it, and it depends on none of them.

## Key ideas

- The data model covers tracks, points, events and media references.
- The core defines six seams: `TrackRecorder`, `StorageAdapter`, `SensorSource`, `TileSource`, `MediaAnalyzer` and `EventPresentation`.
- The package contract is `specs/api.md` §1 through §7 and §10.
- A track is plain data. A track is points on a timeline, and no class is required.
- A `Track` carries `id`, `startedAt`, `endedAt`, `status`, `origin`, `points` and `segments`.
- Each point carries `lat`, `lng` and a timestamp `t`. Each segment carries `startIndex` and `endIndex` into `points`.
- `newId` returns a random id. `haversineDistanceMeters` computes the distance in metres between two points with plain arithmetic.
- `trackToGeoJSON` turns a track and its events into portable GeoJSON. `geoJSONToTrack` reads that form back. `specs/api.md` §10 specifies the form.
- None of these functions needs a browser.
- Other packages do the platform work. `@mapatlas/recorder-web` records a track from real GPS. `@mapatlas/storage-idb` stores it. `@mapatlas/maplibre` draws it.
- The subpath `@mapatlas/core/testing` exports first-party fakes for every seam. A consumer can test against the engine without hardware. `specs/api.md` §5c specifies them.
- The package declares no peer dependencies.
- The package is not published to a registry. A contributor builds it from a checkout and installs it as a tarball.
- The only install path that is checked and run end to end is the quick start in `specs/api.md` §0.

## Where this shows up

- `packages/core/README.md`, including the generated peers block between the `generated:peers` markers.
- `examples/readme/core/track.ts` is the README's track example. The repository compiles it against the packed packages on every change.
- `specs/api.md` §1–§7, §5c and §10.
- `SECURITY.md` describes what the engine does and does not send anywhere.
- License: Apache-2.0. The licensing rule lives in `specs/architecture.md`.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
```

## concepts/map-atlas-engine.md
**Action:** update  
**Rationale:** The source refines the engine overview with the core package's role and the dependency direction between packages. The update adds one key idea, one pointer and a link to the new core page. The existing content is unchanged.

```markdown
---
page_type: concept
slug: map-atlas-engine
title: MAP-ATLAS — a domain-agnostic field-mapping engine
status: draft
last_reviewed: 2026-10-28
sources:
  - path: eval/navigation/heldout/corpus/README.md
    sha: 79de8a1
  - path: eval/navigation/heldout/corpus/packages__core__README.md
    sha: 79de8a1
page_id: pg-85080ebfb8cc4b41b76d5559bc3d1c3f
---

# MAP-ATLAS — a domain-agnostic field-mapping engine

## Summary

MAP-ATLAS is an open-source, domain-agnostic engine for interactive field mapping. A user records a track and drops an event where something happened. The user can attach a comment and photos to the event. A pluggable AI can analyze those photos, and this step is optional.

## Key ideas

- The engine knows about five things: **places**, **tracks**, **events**, **media** and an optional **media analyzer**.
- The engine knows nothing about fish, plants or mushrooms. The consuming application supplies the domain.
- A fishing journal plugs in a fish-species analyzer to log a catch on the water.
- A foraging app plugs in a mushroom or plant analyzer to map a find and identify the species.
- A field survey tool plugs in no analyzer. It records a route and tags observations.
- MAP-ATLAS is the reusable core. The consuming application owns the domain value, the private data and any privacy or sharing rules.
- The engine is written in **TypeScript**. It has a framework-agnostic **core**, a **MapLibre GL** renderer and thin **React** bindings.
- `@mapatlas/core` defines the data model and every seam. Every other package depends on it, and it depends on none of them.
- The engine is **offline-first**. It uses PMTiles for offline map regions. Storage goes through a pluggable adapter, and the default adapter is IndexedDB.
- Track recording sits behind a `TrackRecorder` abstraction. The web adapter uses `watchPosition` and Wake Lock.
- A native `TrackRecorder` adapter gives background tracking inside a Capacitor or Cordova shell.
- AI sits behind a `MediaAnalyzer` interface that turns a photo into labels or a summary. No model is bundled. Consumers provide on-device or remote analyzers.
- A consumer must wire two things alone: the renderer's stylesheet and MapLibre's worker URL.
- The engine cannot inject the stylesheet, because global CSS is a decision about the consumer's document.
- The engine cannot set the worker URL, because that URL depends on the consumer's bundler.

## Where this shows up

- Packages: `@mapatlas/core`, `@mapatlas/storage-idb`, `@mapatlas/recorder-web`, `@mapatlas/maplibre`, `@mapatlas/react`, plus offline regions in `packages/offline-pmtiles`.
- `packages/core/README.md` describes the data model, the seams and the testing fakes.
- `packages/maplibre/README.md` explains what breaks without the stylesheet and the worker URL.
- `specs/api.md` § 0 (Quick start) shows both wiring steps in checked code.
- `specs/architecture.md` describes the package layout, module boundaries, data model, and the offline and AI seams.
- License: Apache-2.0. Contributions are accepted under the Developer Certificate of Origin (see `CONTRIBUTING.md`). Every source file carries an `SPDX-License-Identifier: Apache-2.0` header.

## Related

- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
```

## concepts/harness-neutral-specs-contract.md
**Action:** update  
**Rationale:** The source extends the checked-documentation contract to package READMEs. Their code blocks are compiled against packed packages but not executed. Their peers lists are generated. They defer install to the quick start because the packages are not published. The update adds these rules to the page that already owns the checked quick start.

```markdown
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
- The packages are not published to a registry. A package README does not repeat an install command it cannot run. It points at the quick start instead.
- Every code block in a package README names a file. The repository compiles that file against the packed packages on every change.
- A package README code block is compiled, not executed. Only the quick start is also run in a browser.
- A package README's peer-dependency list is generated from the package's own manifest, between the `generated:peers` markers.
- The README status table is generated from `specs/tasks.md`. It counts tasks with a **Done** record per phase.
- A zero in the status table means *no Done record*. It does not mean *no completed work*.

## Where this shows up

- `specs/` at the repository root.
- `README.md` sections "Quick start", "Status" (between the `generated:status` markers) and "The governing contract".
- `examples/quick-start`, `e2e/quick-start.e2e.ts` and the `check:packaging` script.
- `packages/core/README.md` and its compiled example `examples/readme/core/track.ts`.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
```

## index.md
**Action:** append-index  
**Rationale:** This links the new concept page from the index so it is reachable.

```markdown
- [@mapatlas/core — the framework-agnostic data model and seams](concepts/mapatlas-core-package.md) — tracks as plain data, the six seams, GeoJSON portability and testing fakes
```

## log.md
**Action:** append-log  
**Rationale:** This records the ingest in the append-only log.

```markdown
- 2026-10-28 — create mapatlas-core-package (concept): ingest of packages/core/README.md, also updating map-atlas-engine and harness-neutral-specs-contract
```
