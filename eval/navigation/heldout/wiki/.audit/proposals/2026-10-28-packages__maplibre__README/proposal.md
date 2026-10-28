# Proposal: 2026-10-28-packages__maplibre__README

**Rationale:** The source passes the four-question gate. It is reusable: it explains the two consumer wiring steps, the exact-version peer pin and the silent failures each one prevents. It is citable at eval/navigation/heldout/corpus/packages__maplibre__README.md (79de8a1). It does not duplicate an existing page: map-atlas-engine only mentions the stylesheet and worker steps in passing, and no page covers @mapatlas/maplibre. A new contributor wiring the renderer, or debugging a map that never paints, needs it. This patch creates a concept page for the package, the counterpart of mapatlas-core-package. It also updates map-data-licensing with the renderer's licence obligation, harness-neutral-specs-contract with the rule that unchecked features are described only in prose, and map-atlas-engine with a source and a link. It adds an index entry and a log entry.

## concepts/mapatlas-maplibre-package.md
**Action:** create  
**Rationale:** No existing page covers the renderer package. This page records the exact-version peer pin, the single-MapLibre-instance reason, the worker and stylesheet failure modes, the focus-ring property and the mount API.

```markdown
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
```

## concepts/map-data-licensing.md
**Action:** update  
**Rationale:** The renderer README restates the licensing obligation from the renderer's side. This edit adds that framing, the new source, the README section pointer and a link to the new page.

```markdown
---
page_type: concept
slug: map-data-licensing
title: Map-data licensing is a downstream obligation
status: draft
last_reviewed: 2026-10-28
sources:
  - path: eval/navigation/heldout/corpus/README.md
    sha: 79de8a1
  - path: eval/navigation/heldout/corpus/packages__maplibre__README.md
    sha: 79de8a1
page_id: pg-84b04a06f55b4355a9fb8040849767f4
---

# Map-data licensing is a downstream obligation

## Summary

Consumers of MAP-ATLAS must honor the licenses of the third-party map data the engine renders. The engine bundles no tiles. It takes no position on which data sources a consumer uses.

## Key ideas

- A consumer inherits the downstream tile and data licences when it points the renderer at those sources.
- OpenStreetMap data is licensed under ODbL.
- OpenSeaMap seamarks are licensed under ODbL, which is share-alike.
- Bathymetry and elevation sources are licensed per product, not per publisher.
- Terms can differ between datasets from the same agency.
- Some datasets carry third-party contributions whose terms travel with them.
- A consumer must check the specific product and its contributor metadata. A publisher's general reputation is not enough.

## Where this shows up

- `README.md` section "Attribution & data licensing (downstream obligation)".
- `packages/maplibre/README.md` section "License".
- `specs/architecture.md` section "Map data & licensing".
- ADR-0024 in `specs/decisions.md`.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/maplibre — the MapLibre GL renderer and its wiring](mapatlas-maplibre-package.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
```

## concepts/harness-neutral-specs-contract.md
**Action:** update  
**Rationale:** The renderer README adds a documentation rule to the contract: a block no gate checks is described in prose and is not presented as something to paste. This edit also records the renderer's compiled example files.

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

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [@mapatlas/maplibre — the MapLibre GL renderer and its wiring](mapatlas-maplibre-package.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
```

## concepts/map-atlas-engine.md
**Action:** update  
**Rationale:** The engine page already summarizes the two wiring steps. This edit cites the renderer README as a source and links to the new renderer page, which holds the details.

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
- [@mapatlas/maplibre — the MapLibre GL renderer and its wiring](mapatlas-maplibre-package.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
```

## index.md
**Action:** append-index  
**Rationale:** Makes the new page reachable from index.md.

```markdown
- [@mapatlas/maplibre — the MapLibre GL renderer and its wiring](concepts/mapatlas-maplibre-package.md) — exact-version maplibre-gl peer, worker URL and stylesheet wiring, silent failure modes
```

## log.md
**Action:** append-log  
**Rationale:** Records the ingest in the append-only log.

```markdown
- 2026-10-28 — create mapatlas-maplibre-package (concept): ingest of packages/maplibre/README.md, also updating map-data-licensing, harness-neutral-specs-contract and map-atlas-engine
```
