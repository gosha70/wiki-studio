---
page_type: concept
slug: mapatlas-maplibre-package
title: "@mapatlas/maplibre — the MapLibre GL renderer and its wiring"
status: draft
last_reviewed: 2026-10-28
sources:
  - path: eval/navigation/heldout/corpus/packages__maplibre__README.md
    sha: 79de8a1
page_id: pg-9c57ce813aea454291036b083024494e
---

# @mapatlas/maplibre — the MapLibre GL renderer and its wiring

## Summary

`@mapatlas/maplibre` is MAP-ATLAS's MapLibre GL renderer, and a consumer must wire its stylesheet and worker URL alone. It draws the tile-source stack, terrain, and the track, event and draft geometry. Its contract is `specs/api.md` §8. If a consumer skips a wiring step, the map usually fails silently instead of raising an error.

## Key ideas

- The package declares `maplibre-gl` as a peer dependency at the exact version `6.6.0`, not a range such as `^6.6.0`.
- Every browser test in the repository runs against exactly 6.6.0. A caret range would let a fresh install resolve a 6.x release that no test has exercised.
- Renderer dependencies in MAP-ATLAS carry no version ranges. The packaging gate enforces this rule.
- The peer dependency makes the application resolve exactly one MapLibre copy.
- `addProtocol` registers a handler on one MapLibre module instance. With two copies, PMTiles could register on a runtime that does not draw the map. The archive would then silently fail to load.
- The peer dependency also makes the stylesheet import resolvable under strict resolvers, such as pnpm and Yarn PnP, and under npm's hoisting.
- A consumer must call `setWorkerUrl` with the URL of `maplibre-gl/dist/maplibre-gl-worker.mjs`. The README shows Vite's `?worker&url` syntax. Other bundlers have their own syntax.
- MapLibre resolves its worker relative to the importing chunk. A bundler that rewrites imports, such as Vite's optimised dependency chunks, makes that request 404.
- A missing worker raises no error. The map is constructed, the style parses and sources emit `sourcedata`. No tile is ever built, so nothing is painted.
- If a map shows controls and markers but no map, check the worker URL first.
- The engine cannot set the worker URL, because the correct URL depends on the consumer's bundler.
- The package does not import `maplibre-gl/dist/maplibre-gl.css`. Injecting global CSS is the consumer's decision, and it breaks applications that bundle CSS themselves.
- Without the stylesheet, MapLibre's controls are unstyled. Map marks also lose their absolute positioning and render outside the map. This looks like an engine bug, but it is a missing import.
- Draft vertices in draw mode draw their own focus ring, because a keyboard user needs one with or without a stylesheet.
- The CSS custom property `--mapatlas-focus-ring-color` sets the ring colour. The renderer reads it on the map's ancestors. Unset, the ring is `3px solid #0969da`.
- A fixed blue has no guaranteed contrast against satellite imagery. That is why the colour is configurable.
- `createMapController` takes a `container` element and a list of `sources` and returns a `MapController`.
- The engine bundles no map data. The consumer's application serves its own archive, for example a `TileSource` with `kind: "vector"` and `transport: "pmtiles"`.
- The `MapController` contract covers camera, marks, draft geometry and replay. `specs/api.md` §8 specifies it.
- Event marks and draft vertices are keyboard-operable. Camera motion follows `prefers-reduced-motion`.
- Draw-mode vertices keep pointer hit-testing on the canvas. A parallel DOM layer supplies the accessible controls.
- The package is not published to a registry. The only install path that is checked and run end to end is the quick start in `specs/api.md` §0.

## Where this shows up

- `packages/maplibre/README.md`, including the generated peers block between the `generated:peers` markers.
- `examples/readme/maplibre/worker.ts` is the README's stylesheet and worker example. The repository compiles it against the packed packages on every change.
- `examples/readme/maplibre/controller.ts` is the README's mount example. The repository compiles it, but does not execute it.
- `specs/api.md` §8 (renderer contract) and §0 (quick start).
- License: Apache-2.0. `SECURITY.md` and the licensing rule in `specs/architecture.md` cover downstream data licences.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
