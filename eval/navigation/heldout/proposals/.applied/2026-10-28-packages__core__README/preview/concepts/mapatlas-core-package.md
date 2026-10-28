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
