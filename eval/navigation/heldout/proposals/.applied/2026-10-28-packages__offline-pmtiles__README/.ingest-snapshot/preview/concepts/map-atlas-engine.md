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
- `@mapatlas/offline-pmtiles` downloads PMTiles regions into a `MapAssetStore` and serves them when the network is not there. The engine bundles no map data.
- Track recording sits behind a `TrackRecorder` abstraction. The web adapter uses `watchPosition` and Wake Lock.
- A native `TrackRecorder` adapter gives background tracking inside a Capacitor or Cordova shell.
- AI sits behind a `MediaAnalyzer` interface that turns a photo into labels or a summary. No model is bundled. Consumers provide on-device or remote analyzers.
- A consumer must wire two things alone: the renderer's stylesheet and MapLibre's worker URL.
- The engine cannot inject the stylesheet, because global CSS is a decision about the consumer's document.
- The engine cannot set the worker URL, because that URL depends on the consumer's bundler.

## Where this shows up

- Packages: `@mapatlas/core`, `@mapatlas/storage-idb`, `@mapatlas/recorder-web`, `@mapatlas/maplibre`, `@mapatlas/react` and `@mapatlas/offline-pmtiles`.
- `packages/core/README.md` describes the data model, the seams and the testing fakes.
- `packages/maplibre/README.md` explains what breaks without the stylesheet and the worker URL.
- `packages/offline-pmtiles/README.md` describes region download, the `offlineLicensed` rule and the extra install step.
- `specs/api.md` § 0 (Quick start) shows both wiring steps in checked code.
- `specs/architecture.md` describes the package layout, module boundaries, data model, and the offline and AI seams.
- License: Apache-2.0. Contributions are accepted under the Developer Certificate of Origin (see `CONTRIBUTING.md`). Every source file carries an `SPDX-License-Identifier: Apache-2.0` header.

## Related

- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [@mapatlas/maplibre — the MapLibre GL renderer and its wiring](mapatlas-maplibre-package.md)
- [@mapatlas/offline-pmtiles — offline map regions over PMTiles archives](mapatlas-offline-pmtiles-package.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
