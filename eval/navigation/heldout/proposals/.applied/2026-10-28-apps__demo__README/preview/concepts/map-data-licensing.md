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
