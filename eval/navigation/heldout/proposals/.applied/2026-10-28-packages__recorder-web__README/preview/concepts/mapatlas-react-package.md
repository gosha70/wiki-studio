---
page_type: concept
slug: mapatlas-react-package
title: "@mapatlas/react — the React bindings over the engine's seams"
status: draft
last_reviewed: 2026-10-28
sources:
  - path: eval/navigation/heldout/corpus/packages__react__README.md
    sha: 79de8a1
page_id: pg-93b90f3411cf452abff662ab6b3c2c63
---

# @mapatlas/react — the React bindings over the engine's seams

## Summary

`@mapatlas/react` provides MAP-ATLAS's React bindings over the engine's seams. It exports the components `MapCanvas`, `EventComposer` and `TripReview`. It also exports the hooks `useTrackRecorder`, `useTrackDraft`, `useEventLog` and `useOfflineRegions`. Its contract is `specs/api.md` §9.

## Key ideas

- The package depends on `@mapatlas/maplibre` for drawing.
- The package depends on `@mapatlas/recorder-web` for recording.
- The full record → pin → review loop is the quick start in `specs/api.md` §0.
- `MapCanvas` takes the same `sources` that a `MapController` takes.
- `MapCanvas` owns the map's lifetime.
- `MapCanvas` also accepts an `initialCamera` with a `center` and a `zoom`.
- `useTrackRecorder` wraps the recorder from `@mapatlas/recorder-web` in React state.
- `useTrackRecorder` exposes `status`, `livePoint`, `start` and `stop`.
- The engine bundles no map data. The consumer's application serves its own archive, for example a `TileSource` with `kind: "vector"` and `transport: "pmtiles"`.
- The consumer must load the stylesheet and the worker URL that MapLibre needs. `@mapatlas/maplibre`'s README describes both steps.
- This package does not inject global CSS.
- The package declares one peer dependency: `react` at `>=18`.
- The package is not published to a registry. A contributor builds it from a checkout and installs it as a tarball.
- The only install path that is checked and run end to end is the quick start in `specs/api.md` §0. The README does not repeat an install command.

## Where this shows up

- `packages/react/README.md`, including the generated peers block between the `generated:peers` markers.
- `examples/readme/react/canvas.tsx` is the README's map and recording example. The repository compiles it against the packed packages on every change, but does not execute it.
- `specs/api.md` §9 (React bindings) and §0 (quick start).
- License: Apache-2.0. `SECURITY.md` describes what the engine does and does not send anywhere. The licensing rule lives in `specs/architecture.md`.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [@mapatlas/maplibre — the MapLibre GL renderer and its wiring](mapatlas-maplibre-package.md)
- [@mapatlas/offline-pmtiles — offline map regions over PMTiles archives](mapatlas-offline-pmtiles-package.md)
- [@mapatlas/recorder-web — the browser's foreground TrackRecorder](mapatlas-recorder-web-package.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
