# Proposal: 2026-10-28-packages__recorder-web__README

**Rationale:** Gate passed. The source is reusable because it documents the engine's browser TrackRecorder. It is citable as a corpus file. It is non-duplicative because no page covers @mapatlas/recorder-web; existing pages only name it. It is new-contributor-relevant because it states the foreground-only limit, the autosave guarantee and the store behaviour. I created one concept page for the package. I updated map-atlas-engine and harness-neutral-specs-contract with the new facts and the new source. I added a Related link from mapatlas-react-package, which records through this package. I appended one log entry and one index entry.

## concepts/mapatlas-recorder-web-package.md
**Action:** create  
**Rationale:** No existing page covers @mapatlas/recorder-web. The page records the recorder API, the store and autosave guarantee, and the foreground-only limit.

```markdown
---
page_type: concept
slug: mapatlas-recorder-web-package
title: "@mapatlas/recorder-web — the browser's foreground TrackRecorder"
status: draft
last_reviewed: 2026-10-28
sources:
  - path: eval/navigation/heldout/corpus/packages__recorder-web__README.md
    sha: 79de8a1
page_id: pg-95228640ba8a4805a8c3c75b92103872
---

# @mapatlas/recorder-web — the browser's foreground TrackRecorder

## Summary

`@mapatlas/recorder-web` is MAP-ATLAS's browser implementation of `TrackRecorder`, and it records in the foreground only. It reads GPS through the Geolocation API. It applies the sampling and sensor-merge policies that `specs/api.md` §2 and §3 specify. The `TrackRecorder` interface lives in `@mapatlas/core`.

## Key ideas

- This package is one implementation of the `TrackRecorder` interface. A native background recorder would be another implementation.
- `createWebTrackRecorder()` returns a recorder.
- `onPoint` registers a callback for each new point. Each point carries `lat`, `lng` and `t`.
- `start()` asks the browser for position permission. Then it begins sampling.
- `stop()` resolves with the finished `Track`.
- Nothing is persisted unless a `store` is given.
- A `store` is an `@mapatlas/storage-idb` adapter or the consumer's own `StorageAdapter`. `@mapatlas/storage-idb` provides the default one.
- With a `store`, the recorder autosaves every `autosaveMs` milliseconds.
- A reload mid-trip then loses at most one autosave interval's worth of points. This holds only if the autosaves themselves succeeded.
- The recorder is foreground only. A web page cannot record with the screen locked.
- The package does not pretend otherwise. The consumer closes that gap with a native adapter.
- The package declares no peer dependencies.
- The package is not published to a registry. A contributor builds it from a checkout and installs it as a tarball.
- The only install path that is checked and run end to end is the quick start in `specs/api.md` §0. The README does not repeat an install command.

## Where this shows up

- `packages/recorder-web/README.md`, including the generated peers block between the `generated:peers` markers.
- `examples/readme/recorder-web/record.ts` is the README's recording example. The repository compiles it against the packed packages on every change, but does not execute it.
- `specs/api.md` §2 (track recording), §3 (sampling and sensor merge) and §0 (quick start).
- License: Apache-2.0. `SECURITY.md` describes what the engine does and does not send anywhere. The licensing rule lives in `specs/architecture.md`.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [@mapatlas/react — the React bindings over the engine's seams](mapatlas-react-package.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
```

## concepts/map-atlas-engine.md
**Action:** update  
**Rationale:** The engine overview names @mapatlas/recorder-web as the web TrackRecorder adapter. The source adds that it is foreground only. Added the source, a pointer to the package README and a Related link.

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
- `packages/maplibre/README.md` explains what breaks without the stylesheet and the worker URL.
- `packages/react/README.md` describes the React components and hooks.
- `packages/offline-pmtiles/README.md` describes region download, the `offlineLicensed` rule and the extra install step.
- `packages/recorder-web/README.md` describes the browser recorder, its autosave and its foreground-only limit.
- `specs/api.md` § 0 (Quick start) shows both wiring steps in checked code. It also runs the full record → pin → review loop.
- `specs/architecture.md` describes the package layout, module boundaries, data model, and the offline and AI seams.
- License: Apache-2.0. Contributions are accepted under the Developer Certificate of Origin (see `CONTRIBUTING.md`). Every source file carries an `SPDX-License-Identifier: Apache-2.0` header.

## Related

- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [@mapatlas/maplibre — the MapLibre GL renderer and its wiring](mapatlas-maplibre-package.md)
- [@mapatlas/react — the React bindings over the engine's seams](mapatlas-react-package.md)
- [@mapatlas/offline-pmtiles — offline map regions over PMTiles archives](mapatlas-offline-pmtiles-package.md)
- [@mapatlas/recorder-web — the browser's foreground TrackRecorder](mapatlas-recorder-web-package.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
```

## concepts/harness-neutral-specs-contract.md
**Action:** update  
**Rationale:** The recorder-web README follows the same contract as the other package READMEs: it has a generated peers block and a compiled, unexecuted example, and it points to §0 instead of giving an install command. Added it as another place the contract shows up.

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

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [@mapatlas/maplibre — the MapLibre GL renderer and its wiring](mapatlas-maplibre-package.md)
- [@mapatlas/react — the React bindings over the engine's seams](mapatlas-react-package.md)
- [@mapatlas/offline-pmtiles — offline map regions over PMTiles archives](mapatlas-offline-pmtiles-package.md)
- [@mapatlas/recorder-web — the browser's foreground TrackRecorder](mapatlas-recorder-web-package.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
```

## concepts/mapatlas-react-package.md
**Action:** update  
**Rationale:** useTrackRecorder wraps the recorder from @mapatlas/recorder-web. Added only a Related link to the new page. No new facts, so the sources are unchanged.

```markdown
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
```

## log.md
**Action:** append-log  
**Rationale:** One dated log entry for this ingest.

```markdown
- 2026-10-28 — create mapatlas-recorder-web-package (concept): ingest of packages/recorder-web/README.md, also updating map-atlas-engine, harness-neutral-specs-contract and mapatlas-react-package
```

## index.md
**Action:** append-index  
**Rationale:** Makes the new page reachable from index.md.

```markdown
- [@mapatlas/recorder-web — the browser's foreground TrackRecorder](concepts/mapatlas-recorder-web-package.md) — Geolocation-based recording, store autosave every autosaveMs, foreground only
```
