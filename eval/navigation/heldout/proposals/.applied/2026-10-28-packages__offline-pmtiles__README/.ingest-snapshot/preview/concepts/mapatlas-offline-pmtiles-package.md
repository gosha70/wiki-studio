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
