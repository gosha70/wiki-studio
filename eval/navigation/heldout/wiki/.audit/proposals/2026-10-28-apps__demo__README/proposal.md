# Proposal: 2026-10-28-apps__demo__README

**Rationale:** Gate passed. (1) Reusable: the source explains how to run the demo and how its two offline layers work. It also says what the demo does not show and how to fix two common failures. A future contributor needs all of this. (2) Citable: the source is the repo file eval/navigation/heldout/corpus/apps__demo__README.md. (3) Non-duplicative: no wiki page covers the demo app, so I create one concept page, mapatlas-demo-app. (4) New-contributor-relevant: `npm run demo` is the first thing a new contributor runs. The source also refines three existing pages, which I update. map-data-licensing gains the demo's two attribution lines and the gitignored build/fixture/ tiles. mapatlas-offline-pmtiles gains the range-request (HTTP Byte Serving) requirement and the e2e check of rendering from a downloaded region. map-atlas-engine gains a pointer to the demo. The index gets one link and the log gets one entry.

## concepts/mapatlas-demo-app.md
**Action:** create  
**Rationale:** No existing page covers the demo app. This page records how to run it, its two independent offline layers, what it does not demonstrate, and how to fix its two common failures.

```markdown
---
page_type: concept
slug: mapatlas-demo-app
title: MAP-ATLAS demo — a field logger built only from the published packages
status: draft
last_reviewed: 2026-10-28
sources:
  - path: eval/navigation/heldout/corpus/apps__demo__README.md
    sha: 79de8a1
page_id: pg-874baca67e924d679bf597ec2ce84a32
---

# MAP-ATLAS demo — a field logger built only from the published packages

## Summary

The MAP-ATLAS demo is a generic field logger built only from the published package entry points. It uses no deep imports and no internals. A user records a track, drops an event where it happened, attaches a photo, reviews the trip and exports it as GeoJSON. All of this runs over a self-hosted map.

## Key ideas

- A contributor runs `npm install` and then `npm run demo`. The command prints one URL to open.
- The first run cuts the map archives. This needs the network once and takes about a minute.
- Later runs reuse the archives and start immediately. `Ctrl-C` stops the demo.
- The map shows one alpine massif.
- An OpenStreetMap extract supplies the landmass, landuse, water and roads.
- A Copernicus elevation model supplies shaded relief and brown contour lines above them.
- The corner shows two attribution lines, one for each source. The two sources are two derived works under two unrelated licences.
- The demo loop is **Start recording**, tap the map to drop an event, attach a photo, **Stop and review** and **Export GeoJSON**.
- The browser asks for the user's location when recording starts.
- "Offline" covers two different things. They fail independently.
- The first thing is the map's data. **Download region** copies the three archives into IndexedDB.
- The map then draws from IndexedDB with the archive server unreachable. **Delete region** puts it back.
- The development runner has this map-data behaviour too. The panel therefore works under `npm run demo`.
- `npm run demo` starts both servers in one process. A user cannot stop only the archive server by hand.
- The browser lane is what actually cuts the archive host in the tests.
- The second thing is the application itself. A service worker precaches the built shell.
- With the service worker, a reload with the app's own server down still boots the real application. It does not show a browser error page.
- The service worker exists in a production build only.
- The tests check both offline claims instead of asserting them.
- `e2e/app-offline.e2e.ts` renders from a downloaded region with the archive host cut.
- `e2e/app-shell-offline.e2e.ts` boots the built application with its own origin cut. It runs on the production bundle, not the development one.
- `npm run demo` is the development runner, not a production server.
- The development runner deliberately registers no service worker. Ordinary local development under an active worker helps nobody.
- `npm run demo` therefore does not demonstrate the offline shell. The production browser lane makes and checks that claim.
- The demo is not a global basemap. The archives cover one small region, so the map runs out if the user pans far.
- The archives are cut locally on purpose. They are not served from anyone's tile host.
- The repository holds no map tiles. `npm run demo` cuts them into `build/fixture/`, which git ignores.
- The error "port 5175/5176 is already in use" means something else is listening, often a previous run. Stop it and try again.
- An error that mentions "HTTP Byte Serving" means the archive server ignores `Range`.
- PMTiles is read by range request. The reader refuses a response that carries more bytes than it asked for.
- `npm run demo` uses a server that supports range requests. A plain static server such as `python3 -m http.server` does not.

## Where this shows up

- `apps/demo/README.md`.
- `e2e/app-offline.e2e.ts` checks rendering from a downloaded region with the archive host cut.
- `e2e/app-shell-offline.e2e.ts` checks the offline application shell on the production bundle.
- `build/fixture/` holds the cut archives and is gitignored.
- `specs/decisions.md` ADR-0035 and ADR-0039 cover the two offline layers.
- `specs/decisions.md` ADR-0024 and ADR-0038 cover the map sources and their licences.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/offline-pmtiles — offline map regions over PMTiles archives](mapatlas-offline-pmtiles-package.md)
- [@mapatlas/storage-idb — the default IndexedDB persistence](mapatlas-storage-idb-package.md)
- [@mapatlas/recorder-web — the browser's foreground TrackRecorder](mapatlas-recorder-web-package.md)
- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
```

## concepts/map-data-licensing.md
**Action:** update  
**Rationale:** The demo README shows the licensing rule in practice. It uses two attribution lines for two derived works under unrelated licences, keeps tiles out of git, and cites ADR-0038 for the sources and licences.

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
  - path: eval/navigation/heldout/corpus/packages__offline-pmtiles__README.md
    sha: 79de8a1
  - path: eval/navigation/heldout/corpus/apps__demo__README.md
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
- For offline regions, the data licence travels with the PMTiles archive the consumer supplies.
- Bulk download runs only against a source the consumer hosts or is explicitly licensed to prefetch.
- The consumer declares that licence with `offlineLicensed: true` on the `TileSource`.
- `download()` in `@mapatlas/offline-pmtiles` refuses a source without that flag. It throws `OfflineLicenseError`.
- An absent flag means refusal, not permission. Bulk prefetching from a host the consumer does not own is a policy violation.
- The demo app shows one attribution line for each map source.
- The demo's OpenStreetMap extract and Copernicus elevation model are two derived works under two unrelated licences. That is why the demo shows two lines.
- The repository holds no map tiles. `npm run demo` cuts the demo's archives into `build/fixture/`, which git ignores.

## Where this shows up

- `README.md` section "Attribution & data licensing (downstream obligation)".
- `packages/maplibre/README.md` section "License".
- `packages/offline-pmtiles/README.md` section "Download a region".
- `apps/demo/README.md` sections "What you should see" and "What it is not".
- `specs/architecture.md` section "Map data & licensing".
- ADR-0024 and ADR-0038 in `specs/decisions.md`.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/maplibre — the MapLibre GL renderer and its wiring](mapatlas-maplibre-package.md)
- [@mapatlas/offline-pmtiles — offline map regions over PMTiles archives](mapatlas-offline-pmtiles-package.md)
- [MAP-ATLAS demo — a field logger built only from the published packages](mapatlas-demo-app.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
```

## concepts/mapatlas-offline-pmtiles-package.md
**Action:** update  
**Rationale:** The demo README adds the range-request requirement for serving PMTiles and the 'HTTP Byte Serving' failure mode. It also adds the e2e check that the map renders from a downloaded region with the archive host cut.

```markdown
---
page_type: concept
slug: mapatlas-offline-pmtiles-package
title: "@mapatlas/offline-pmtiles — offline map regions over PMTiles archives"
status: draft
last_reviewed: 2026-10-28
sources:
  - path: eval/navigation/heldout/corpus/packages__offline-pmtiles__README.md
    sha: 79de8a1
  - path: eval/navigation/heldout/corpus/apps__demo__README.md
    sha: 79de8a1
page_id: pg-97e0c898c77a4a52aa6550939fa1a6e6
---

# @mapatlas/offline-pmtiles — offline map regions over PMTiles archives

## Summary

`@mapatlas/offline-pmtiles` gives MAP-ATLAS offline map regions through an `OfflineRegionStore` over PMTiles archives. The store downloads an archive into a `MapAssetStore`. The engine serves the archive from that store when the network is not there. The package works on archives the consumer supplies, and the engine bundles no map data.

## Key ideas

- The package contract is `specs/api.md` §7 (basemap, terrain and offline tiles).
- The data licence travels with the archive. The consumer supplies both.
- `createPMTilesRegionStore` takes a list of `sources` and an `assets` store, and returns the region store.
- The README example uses `createIdbMapAssetStore` from `@mapatlas/storage-idb`. Downloaded regions are then kept in IndexedDB.
- `download(region)` fetches the archive's bytes into the asset store. It reports progress as a fraction through an optional callback.
- `download(region)` resolves with the stored `OfflineRegion`.
- A region carries a `name`, a `bbox`, a `minZoom` and a `maxZoom`.
- `list()` returns the stored regions. `delete(id)` removes one.
- `download()` refuses any source that is not marked `offlineLicensed: true`. It throws `OfflineLicenseError`.
- An absent `offlineLicensed` flag means refusal, not permission.
- Bulk prefetching from a host the consumer does not own is a policy violation. It is not a bug that can be fixed afterwards.
- The `offlineLicensed` flag is a declaration about the consumer's own archive. Only the consumer can make it.
- Storing a region does not make the renderer read it. That is a separate step.
- `installOfflineArchives` and `createStoredArchiveSource` serve a stored archive to the renderer. This package exports both.
- Eviction-aware re-download is not implemented.
- A quota UI is not implemented.
- Download resume is not implemented.
- A consumer that needs these features builds them on the package's seams.
- A PMTiles archive is read by range request. The server that hosts the archive must honor `Range`.
- The reader refuses a response that carries more bytes than it asked for. The error then mentions "HTTP Byte Serving".
- A plain static server such as `python3 -m http.server` does not support range requests. `npm run demo` uses a server that does.
- The demo app's **Download region** copies its three archives into IndexedDB. The map then draws from them with the archive server unreachable.
- `e2e/app-offline.e2e.ts` checks that the demo renders from a downloaded region with the archive host cut.
- The package declares no peer dependencies.
- The package is not published to a registry. A contributor builds it from a checkout and installs it as a tarball.
- The quick start in `specs/api.md` §0 does not install this package. The quick start packs only the five packages its example imports.
- To install this package, add `./packages/offline-pmtiles` to the `npm pack` line in §0.
- Then add `"$TARBALLS"/mapatlas-offline-pmtiles-0.0.0.tgz` to the `npm install` line in §0.
- The tarball filename follows the package version, because the install sentence is generated from the manifest.

## Where this shows up

- `packages/offline-pmtiles/README.md`, including the generated blocks between the `generated:add-to-install` and `generated:peers` markers.
- `examples/readme/offline-pmtiles/regions.ts` is the README's region example. The repository compiles it against the packed packages on every change, but does not execute it.
- `apps/demo/README.md` sections "Offline" and "If something goes wrong".
- `e2e/app-offline.e2e.ts` and ADR-0035 in `specs/decisions.md`.
- `specs/api.md` §7 (offline tiles) and §0 (quick start).
- License: Apache-2.0. `SECURITY.md` describes what the engine does and does not send anywhere. The licensing rule lives in `specs/architecture.md`.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [@mapatlas/maplibre — the MapLibre GL renderer and its wiring](mapatlas-maplibre-package.md)
- [MAP-ATLAS demo — a field logger built only from the published packages](mapatlas-demo-app.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
```

## concepts/map-atlas-engine.md
**Action:** update  
**Rationale:** The engine overview page lists every package README. It now also points at the demo app, which is built only from the published entry points.

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
  - path: eval/navigation/heldout/corpus/apps__demo__README.md
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
- The demo app is a generic field logger built only from the published package entry points. It uses no deep imports and no internals.
- `npm run demo` runs the demo over a self-hosted map of one small region.

## Where this shows up

- Packages: `@mapatlas/core`, `@mapatlas/storage-idb`, `@mapatlas/recorder-web`, `@mapatlas/maplibre`, `@mapatlas/react` and `@mapatlas/offline-pmtiles`.
- `packages/core/README.md` describes the data model, the seams and the testing fakes.
- `packages/storage-idb/README.md` describes the IndexedDB adapter, its lazy open and browser eviction.
- `packages/maplibre/README.md` explains what breaks without the stylesheet and the worker URL.
- `packages/react/README.md` describes the React components and hooks.
- `packages/offline-pmtiles/README.md` describes region download, the `offlineLicensed` rule and the extra install step.
- `packages/recorder-web/README.md` describes the browser recorder, its autosave and its foreground-only limit.
- `apps/demo/README.md` describes the demo field logger, its two offline layers and its common failures.
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
- [MAP-ATLAS demo — a field logger built only from the published packages](mapatlas-demo-app.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
```

## index.md
**Action:** append-index  
**Rationale:** This links the new page from the index so it is reachable.

```markdown
- [MAP-ATLAS demo — a field logger built only from the published packages](concepts/mapatlas-demo-app.md) — npm run demo, two independent offline layers, dev runner has no service worker, range-request troubleshooting
```

## log.md
**Action:** append-log  
**Rationale:** This is the dated log entry for this ingest.

```markdown
- 2026-10-28 — create mapatlas-demo-app (concept): ingest of apps/demo/README.md, also updating map-data-licensing, mapatlas-offline-pmtiles-package and map-atlas-engine
```
