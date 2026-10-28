# Proposal: 2026-10-28-packages__storage-idb__README

**Rationale:** Gate passed. (1) Reusable: the README sets out how the default persistence package works: lazy open, a consumer-chosen database name, local-only storage and browser eviction. (2) Citable: eval/navigation/heldout/corpus/packages__storage-idb__README.md. (3) Non-duplicative: no page covers @mapatlas/storage-idb. Existing pages only mention it from the recorder, core and offline-pmtiles side. (4) New-contributor-relevant: it is one of the six engine packages, and the wiki already has a page for each of the other five. This patch creates concepts/mapatlas-storage-idb-package.md. It updates map-atlas-engine (package summary, where-this-shows-up entry and source), harness-neutral-specs-contract (compiled README example and generated peers block) and mapatlas-core-package (the README places the MapAssetStore seam in core beside StorageAdapter). It also appends one index line and one log line.

## concepts/mapatlas-storage-idb-package.md
**Action:** create  
**Rationale:** No page covers the storage-idb package. This page follows the per-package pattern the wiki already uses.

```markdown
---
page_type: concept
slug: mapatlas-storage-idb-package
title: "@mapatlas/storage-idb — the default IndexedDB persistence"
status: draft
last_reviewed: 2026-10-28
sources:
  - path: eval/navigation/heldout/corpus/packages__storage-idb__README.md
    sha: 79de8a1
page_id: pg-d9af62c64e254ad092b12e8bca1c10a9
---

# @mapatlas/storage-idb — the default IndexedDB persistence

## Summary

`@mapatlas/storage-idb` is MAP-ATLAS's default persistence. It implements the `StorageAdapter` and `MapAssetStore` seams of `@mapatlas/core` on IndexedDB. Its contract is `specs/api.md` §5. Tracks, events, media and downloaded map archives live in the browser's own storage, under a database name the consumer chooses.

## Key ideas

- Nothing leaves the device unless the consumer's application sends it.
- `createIdbStorageAdapter` takes a `databaseName` and returns a `StorageAdapter`.
- The README example stores a track with `saveTrack` and reads it back with `getTrack`.
- The adapter opens the database lazily on the first call.
- A consumer can therefore construct the adapter at module load.
- Storing data does not guarantee that the browser keeps it. Browsers can evict an origin under storage pressure.
- The engine does not ask for a persistent origin on the consumer's behalf.
- The demo's persistence UX shows how to ask for a persistent origin.
- `createIdbMapAssetStore` is the `MapAssetStore` that `@mapatlas/offline-pmtiles` uses in its README example.
- `@mapatlas/recorder-web` can take this package's adapter as its `store` for autosave.
- The package declares no peer dependencies.
- The package is not published to a registry. A contributor builds it from a checkout and installs it as a tarball.
- The only install path that is checked and run end to end is the quick start in `specs/api.md` §0. The README does not repeat an install command.

## Where this shows up

- `packages/storage-idb/README.md`, including the generated peers block between the `generated:peers` markers.
- `examples/readme/storage-idb/adapter.ts` is the README's track example. The repository compiles it against the packed packages on every change, but does not execute it.
- `specs/api.md` §5 (persistence seam) and §0 (quick start).
- License: Apache-2.0. `SECURITY.md` describes what the engine does and does not send anywhere. The licensing rule lives in `specs/architecture.md`.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [@mapatlas/recorder-web — the browser's foreground TrackRecorder](mapatlas-recorder-web-package.md)
- [@mapatlas/offline-pmtiles — offline map regions over PMTiles archives](mapatlas-offline-pmtiles-package.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
```

## concepts/map-atlas-engine.md
**Action:** update  
**Rationale:** The engine overview lists one entry per package. This edit adds the storage-idb summary, its README pointer, its source and a Related link.

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
  - path: eval/navigation/heldout/corpus/packages__maplibre__README.md
    sha: 79de8a1
  - path: eval/navigation/heldout/corpus/packages__offline-pmtiles__README.md
    sha: 79de8a1
  - path: eval/navigation/heldout/corpus/packages__react__README.md
    sha: 79de8a1
  - path: eval/navigation/heldout/corpus/packages__recorder-web__README.md
    sha: 79de8a1
  - path: eval/navigation/heldout/corpus/packages__storage-idb__README.md
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
- `@mapatlas/react` exports `MapCanvas`, `EventComposer`, `TripReview` and four hooks over the seams. It draws through `@mapatlas/maplibre` and records through `@mapatlas/recorder-web`.
- The engine is **offline-first**. It uses PMTiles for offline map regions. Storage goes through a pluggable adapter, and the default adapter is IndexedDB.
- `@mapatlas/storage-idb` is that default adapter. It implements the `StorageAdapter` and `MapAssetStore` seams on IndexedDB.
- Stored data stays on the device unless the consumer's application sends it. The browser can still evict it under storage pressure.
- `@mapatlas/offline-pmtiles` downloads PMTiles regions into a `MapAssetStore` and serves them when the network is not there. The engine bundles no map data.
- Track recording sits behind a `TrackRecorder` abstraction. The web adapter uses `watchPosition` and Wake Lock.
- `@mapatlas/recorder-web` is the web adapter. It records in the foreground only, because a web page cannot record with the screen locked.
- A native `TrackRecorder` adapter gives background tracking inside a Capacitor or Cordova shell.
- AI sits behind a `MediaAnalyzer` interface that turns a photo into labels or a summary. No model is bundled. Consumers provide on-device or remote analyzers.
- A consumer must wire two things alone: the renderer's stylesheet and MapLibre's worker URL.
- The engine cannot inject the stylesheet, because global CSS is a decision about the consumer's document.
- The engine cannot set the worker URL, because that URL depends on the consumer's bundler.
- The React bindings do not change this rule. `@mapatlas/react` does not inject global CSS either.

## Where this shows up

- Packages: `@mapatlas/core`, `@mapatlas/storage-idb`, `@mapatlas/recorder-web`, `@mapatlas/maplibre`, `@mapatlas/react` and `@mapatlas/offline-pmtiles`.
- `packages/core/README.md` describes the data model, the seams and the testing fakes.
- `packages/storage-idb/README.md` describes the IndexedDB adapter, its lazy open and browser eviction.
- `packages/maplibre/README.md` explains what breaks without the stylesheet and the worker URL.
- `packages/react/README.md` describes the React components and hooks.
- `packages/offline-pmtiles/README.md` describes region download, the `offlineLicensed` rule and the extra install step.
- `packages/recorder-web/README.md` describes the browser recorder, its autosave and its foreground-only limit.
- `specs/api.md` § 0 (Quick start) shows both wiring steps in checked code. It also runs the full record → pin → review loop.
- `specs/architecture.md` describes the package layout, module boundaries, data model, and the offline and AI seams.
- License: Apache-2.0. Contributions are accepted under the Developer Certificate of Origin (see `CONTRIBUTING.md`). Every source file carries an `SPDX-License-Identifier: Apache-2.0` header.

## Related

- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [@mapatlas/storage-idb — the default IndexedDB persistence](mapatlas-storage-idb-package.md)
- [@mapatlas/maplibre — the MapLibre GL renderer and its wiring](mapatlas-maplibre-package.md)
- [@mapatlas/react — the React bindings over the engine's seams](mapatlas-react-package.md)
- [@mapatlas/offline-pmtiles — offline map regions over PMTiles archives](mapatlas-offline-pmtiles-package.md)
- [@mapatlas/recorder-web — the browser's foreground TrackRecorder](mapatlas-recorder-web-package.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
```

## concepts/mapatlas-core-package.md
**Action:** update  
**Rationale:** The storage-idb README names MapAssetStore as a core seam beside StorageAdapter. The core page's seam list omitted it, so this edit records it without changing the existing six-seam statement.

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
  - path: eval/navigation/heldout/corpus/packages__storage-idb__README.md
    sha: 79de8a1
page_id: pg-944f0a2326874aaab648e16aec803007
---

# @mapatlas/core — the framework-agnostic data model and seams

## Summary

`@mapatlas/core` holds MAP-ATLAS's data model and every seam the rest of the engine is built behind. It knows nothing about a browser, a map library or a database. It knows nothing about any domain, such as fish, plants, products or users. Every other engine package depends on it, and it depends on none of them.

## Key ideas

- The data model covers tracks, points, events and media references.
- The core defines six seams: `TrackRecorder`, `StorageAdapter`, `SensorSource`, `TileSource`, `MediaAnalyzer` and `EventPresentation`.
- The persistence seam in `specs/api.md` §5 also includes `MapAssetStore`, which holds downloaded map archives.
- `@mapatlas/storage-idb` implements `StorageAdapter` and `MapAssetStore` on IndexedDB.
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
- [@mapatlas/storage-idb — the default IndexedDB persistence](mapatlas-storage-idb-package.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
```

## concepts/harness-neutral-specs-contract.md
**Action:** update  
**Rationale:** The storage-idb README follows the same compiled-example and generated-peers conventions. This edit adds it to the list of places where the contract applies.

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
  - path: eval/navigation/heldout/corpus/packages__maplibre__README.md
    sha: 79de8a1
  - path: eval/navigation/heldout/corpus/packages__offline-pmtiles__README.md
    sha: 79de8a1
  - path: eval/navigation/heldout/corpus/packages__react__README.md
    sha: 79de8a1
  - path: eval/navigation/heldout/corpus/packages__recorder-web__README.md
    sha: 79de8a1
  - path: eval/navigation/heldout/corpus/packages__storage-idb__README.md
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
- `packages/recorder-web/README.md`, its generated peers block and its compiled example `examples/readme/recorder-web/record.ts`.
- `packages/storage-idb/README.md`, its generated peers block and its compiled example `examples/readme/storage-idb/adapter.ts`.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [@mapatlas/maplibre — the MapLibre GL renderer and its wiring](mapatlas-maplibre-package.md)
- [@mapatlas/react — the React bindings over the engine's seams](mapatlas-react-package.md)
- [@mapatlas/offline-pmtiles — offline map regions over PMTiles archives](mapatlas-offline-pmtiles-package.md)
- [@mapatlas/recorder-web — the browser's foreground TrackRecorder](mapatlas-recorder-web-package.md)
- [@mapatlas/storage-idb — the default IndexedDB persistence](mapatlas-storage-idb-package.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
```

## index.md
**Action:** append-index  
**Rationale:** This link makes the new page reachable from index.md.

```markdown
- [@mapatlas/storage-idb — the default IndexedDB persistence](concepts/mapatlas-storage-idb-package.md) — StorageAdapter and MapAssetStore on IndexedDB, lazy open, on-device data, browser eviction
```

## log.md
**Action:** append-log  
**Rationale:** This is the log entry for the ingest.

```markdown
- 2026-10-28 — create mapatlas-storage-idb-package (concept): ingest of packages/storage-idb/README.md, also updating map-atlas-engine, mapatlas-core-package and harness-neutral-specs-contract
```
