# Proposal: 2026-10-28-packages__offline-pmtiles__README

**Rationale:** Gate passed. (1) Reusable: the README explains how offline regions work, the offlineLicensed refusal policy, and the extra install step. Future contributors and consumers need all three. (2) Citable: repo file eval/navigation/heldout/corpus/packages__offline-pmtiles__README.md. (3) Non-duplicative: no page covers @mapatlas/offline-pmtiles. The engine page only names the package path. (4) New-contributor-relevant: a newcomer must know that the quick start does not install this package, that download() refuses unlicensed sources, and that storing a region does not make the renderer read it. The patch creates one package page, mirroring the core and maplibre pages. It updates map-data-licensing with the offlineLicensed bulk-prefetch rule. It updates harness-neutral-specs-contract with the generated add-to-install block and the six-package packaging gate. It updates map-atlas-engine to name and link the package.

## concepts/mapatlas-offline-pmtiles-package.md
**Action:** create  
**Rationale:** No page covers the offline-regions package. The page follows the per-package concept pages for core and maplibre.

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
- The package declares no peer dependencies.
- The package is not published to a registry. A contributor builds it from a checkout and installs it as a tarball.
- The quick start in `specs/api.md` §0 does not install this package. The quick start packs only the five packages its example imports.
- To install this package, add `./packages/offline-pmtiles` to the `npm pack` line in §0.
- Then add `"$TARBALLS"/mapatlas-offline-pmtiles-0.0.0.tgz` to the `npm install` line in §0.
- The tarball filename follows the package version, because the install sentence is generated from the manifest.

## Where this shows up

- `packages/offline-pmtiles/README.md`, including the generated blocks between the `generated:add-to-install` and `generated:peers` markers.
- `examples/readme/offline-pmtiles/regions.ts` is the README's region example. The repository compiles it against the packed packages on every change, but does not execute it.
- `specs/api.md` §7 (offline tiles) and §0 (quick start).
- License: Apache-2.0. `SECURITY.md` describes what the engine does and does not send anywhere. The licensing rule lives in `specs/architecture.md`.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [@mapatlas/maplibre — the MapLibre GL renderer and its wiring](mapatlas-maplibre-package.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
```

## concepts/map-data-licensing.md
**Action:** update  
**Rationale:** The source adds a concrete licensing rule: bulk offline download requires an explicit offlineLicensed declaration, and absence means refusal.

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

## Where this shows up

- `README.md` section "Attribution & data licensing (downstream obligation)".
- `packages/maplibre/README.md` section "License".
- `packages/offline-pmtiles/README.md` section "Download a region".
- `specs/architecture.md` section "Map data & licensing".
- ADR-0024 in `specs/decisions.md`.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/maplibre — the MapLibre GL renderer and its wiring](mapatlas-maplibre-package.md)
- [@mapatlas/offline-pmtiles — offline map regions over PMTiles archives](mapatlas-offline-pmtiles-package.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
```

## concepts/harness-neutral-specs-contract.md
**Action:** update  
**Rationale:** The source refines the checked-docs contract. It adds the generated add-to-install block for packages outside the quick start, and it shows that the packaging gate packs all six packages.

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
- `packages/offline-pmtiles/README.md`, its `generated:add-to-install` block and its compiled example `examples/readme/offline-pmtiles/regions.ts`.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [@mapatlas/maplibre — the MapLibre GL renderer and its wiring](mapatlas-maplibre-package.md)
- [@mapatlas/offline-pmtiles — offline map regions over PMTiles archives](mapatlas-offline-pmtiles-package.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
```

## concepts/map-atlas-engine.md
**Action:** update  
**Rationale:** The overview page named only the package path. It now names the package, says what the package does, and links the new page.

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
```

## index.md
**Action:** append-index  
**Rationale:** Makes the new page reachable from the index.

```markdown
- [@mapatlas/offline-pmtiles — offline map regions over PMTiles archives](concepts/mapatlas-offline-pmtiles-package.md) — region download into a MapAssetStore, the offlineLicensed refusal rule, and the extra install step
```

## log.md
**Action:** append-log  
**Rationale:** Dated log entry for this ingest.

```markdown
- 2026-10-28 — create mapatlas-offline-pmtiles-package (concept): ingest of packages/offline-pmtiles/README.md, also updating map-data-licensing, harness-neutral-specs-contract and map-atlas-engine
```
