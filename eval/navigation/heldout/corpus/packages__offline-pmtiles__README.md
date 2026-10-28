<!-- SPDX-License-Identifier: Apache-2.0 -->

# `@mapatlas/offline-pmtiles`

Offline map regions for [MAP-ATLAS](https://github.com/gosha70/mapatlas): an `OfflineRegionStore` over PMTiles archives,
downloaded into a `MapAssetStore` and served from it when the network is not there —
[`api.md` §7](https://github.com/gosha70/mapatlas/blob/main/specs/api.md#7-basemap-terrain--offline-tiles). It works on archives you supply; the engine
bundles no map data, and the data licence travels with the archive.

## Install

**The packages are not published to a registry.** They are built from a checkout and installed as
tarballs. The install path that is checked and run end to end is the quick start in
[`api.md` §0](https://github.com/gosha70/mapatlas/blob/main/specs/api.md#0-quick-start) — and
**it does not install this package**: it packs the five packages the quick-start example imports,
and the example never imports this one. Follow §0 for the pattern, then:

<!-- generated:add-to-install -->

Add `./packages/offline-pmtiles` to §0's `npm pack` line, and the tarball it produces — `"$TARBALLS"/mapatlas-offline-pmtiles-0.0.0.tgz` — to its `npm install` line.

<!-- /generated:add-to-install -->

That sentence is generated from this package's manifest, so the filename follows the version. It
is exactly what this repository's packaging gate does on every change to compile the block below:
it packs all six packages together and installs them side by side. This page does not repeat an
install command it cannot run.

What this package needs beside itself, read from its own manifest:

<!-- generated:peers -->

_This package declares no peer dependencies._

<!-- /generated:peers -->

## Download a region

Every code block on this page is a file that this repository compiles against the packed packages
on every change — the block names the file. It is **compiled, not executed**: the path that is also
run in a browser is the quick start's.

```ts examples/readme/offline-pmtiles/regions.ts
// SPDX-License-Identifier: Apache-2.0
import type { OfflineRegion, TileSource } from "@mapatlas/core";
import { createPMTilesRegionStore } from "@mapatlas/offline-pmtiles";
import { createIdbMapAssetStore } from "@mapatlas/storage-idb";

// Your archive, served by your application: the engine bundles no map data.
const basemap: TileSource = {
  id: "basemap",
  kind: "vector",
  transport: "pmtiles",
  url: new URL("/basemap.pmtiles", window.location.href).toString(),
  attribution: "© your basemap provider",
  // A policy declaration, and yours to make: bulk download runs only against a source you host
  // yourself or are explicitly licensed to prefetch. Absent, `download()` refuses.
  offlineLicensed: true,
};

// Downloaded regions are kept in IndexedDB. Keeping them is this store's job; making the renderer
// read them is a separate step — `installOfflineArchives`, in this package — and nothing below does it.
export const regions = createPMTilesRegionStore({
  sources: [basemap],
  assets: createIdbMapAssetStore(),
});

export function downloadValley(): Promise<OfflineRegion> {
  return regions.download(
    { name: "the valley", bbox: [6.9, 45.85, 7.1, 45.95], minZoom: 8, maxZoom: 14 },
    (fraction) => console.log(`${String(Math.round(fraction * 100))}%`),
  );
}
```

`download(region)` fetches the archive's bytes into the asset store and reports progress, and
resolves with the stored region; `list()` and `delete(id)` manage what is kept. **It refuses any
source not marked `offlineLicensed: true`**, throwing `OfflineLicenseError` — absence is refusal,
not permission, because bulk prefetching a host you do not own is a policy violation and not a bug
that can be fixed afterwards. The flag is a declaration about *your* archive, and yours to make. Serving a stored archive to the renderer is
`installOfflineArchives` and `createStoredArchiveSource`, also exported here. Eviction-aware
re-download, a quota UI and download resume are **not** implemented; a consumer that needs them
builds them on these seams.

## License

Apache-2.0. See [`SECURITY.md`](https://github.com/gosha70/mapatlas/blob/main/SECURITY.md) for what the engine does and does not
send anywhere, and the licensing rule in [`specs/architecture.md`](https://github.com/gosha70/mapatlas/blob/main/specs/architecture.md).
