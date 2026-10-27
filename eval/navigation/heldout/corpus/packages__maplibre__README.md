<!-- SPDX-License-Identifier: Apache-2.0 -->

# `@mapatlas/maplibre`

The MapLibre GL renderer for [MAP-ATLAS](https://github.com/gosha70/mapatlas): the tile-source
stack, terrain, and the track, event and draft geometry the engine draws. Its contract is
[`api.md` §8](https://github.com/gosha70/mapatlas/blob/main/specs/api.md#8-renderer-mapatlasmaplibre);
this page shows how to get it on screen and what breaks if a step is skipped.

## Install

**The packages are not published to a registry.** They are built from a checkout and installed as
tarballs, and the one install path that is checked and run end to end is the quick start in
[`api.md` §0](https://github.com/gosha70/mapatlas/blob/main/specs/api.md#0-quick-start). Follow it;
this page does not repeat an install command it cannot run.

What this package needs beside itself, read from its own manifest:

<!-- generated:peers -->

- `maplibre-gl` — `6.6.0` (an exact version, not a range)

<!-- /generated:peers -->

`maplibre-gl` is a **peer dependency**, and the range is a single exact version rather than
`^6.6.0`. Every browser test in this repository runs against exactly 6.6.0; a caret would let a
fresh install resolve a 6.x release nothing here has exercised, which is the drift the pin
exists to prevent. Renderer dependencies in MAP-ATLAS carry no ranges — the packaging gate
enforces it.

Two MapLibre copies in one application would be worse than wasteful: `addProtocol` registers a
handler on a MapLibre *module instance*, so a second copy would register PMTiles on a runtime that
is not the one drawing your map, and the archive would silently fail to load. Declaring it as a
peer means your application resolves exactly one.

## Load the stylesheet, and point MapLibre at its worker

Every code block on this page is a file that this repository compiles against the packed
packages on every change — the block names the file. They are **compiled, not executed**: the path
that is also run in a browser is the quick start's.

```ts examples/readme/maplibre/worker.ts
// SPDX-License-Identifier: Apache-2.0
import "maplibre-gl/dist/maplibre-gl.css";

import { setWorkerUrl } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url"; // Vite

setWorkerUrl(workerUrl);
```

MapLibre loads its worker as a separate module, resolved relative to the **importing chunk**.
Under a bundler that rewrites imports — Vite's optimised dependency chunks, for instance — that
resolution lands beside the rewritten chunk rather than beside the package, and the request
404s. Nothing errors: the map is constructed, the style parses, sources emit `sourcedata`, and
then **nothing is ever painted**, because no tile is ever built.

The engine cannot do this for you: the correct URL depends on your bundler. The syntax above is
Vite's; other bundlers have their own. If your map shows controls and markers but no map, this
is the first thing to check.

This package does **not** import the stylesheet for you. Injecting global CSS is a decision about
your document rather than ours, and it breaks any application that bundles CSS itself. Without it
MapLibre's own controls are unstyled and — the part that looks like an engine bug rather than a
missing import — map marks lose their absolute positioning and render outside the map.

The peer dependency above is what makes that import resolvable from your application under
strict resolvers (pnpm, Yarn PnP) as well as under npm's hoisting.

### The one style you may need to set

Draft vertices in draw mode draw their own focus ring, because a keyboard user needs one whether
or not you ship a stylesheet. Its colour is the CSS custom property
`--mapatlas-focus-ring-color`, read on the map's ancestors, since the ring sits over whatever your
basemap shows and a fixed blue has no guaranteed contrast against satellite imagery. Set it
anywhere above the map. Unset, the ring is `3px solid #0969da`.

It is described here in prose rather than shown as a stylesheet to copy, because nothing in this
repository exercises the property yet: a block a gate cannot check is not presented as something
to paste.

## Mount a map

```ts examples/readme/maplibre/controller.ts
// SPDX-License-Identifier: Apache-2.0
import type { TileSource } from "@mapatlas/core";
import { createMapController, type MapController } from "@mapatlas/maplibre";

// Your archive, served by your application: the engine bundles no map data.
const basemap: TileSource = {
  id: "basemap",
  kind: "vector",
  transport: "pmtiles",
  url: new URL("/basemap.pmtiles", window.location.href).toString(),
  attribution: "© your basemap provider",
};

const container = document.getElementById("map");
if (container === null) throw new Error("no #map element");

export const controller: MapController = createMapController({
  container,
  sources: [basemap],
});
```

The complete `MapController` contract — camera, marks, draft geometry, replay — is
[`api.md` §8](https://github.com/gosha70/mapatlas/blob/main/specs/api.md#8-renderer-mapatlasmaplibre).
Its event marks and draft vertices are keyboard-operable, camera motion follows
`prefers-reduced-motion`, and draw-mode vertices keep pointer hit-testing on the canvas while a
parallel DOM layer supplies the accessible controls.

## License

Apache-2.0. Downstream tile and data licences are obligations you inherit when you point the
renderer at those sources. OpenStreetMap and OpenSeaMap seamarks are ODbL (share-alike);
**bathymetry and elevation are licensed per product, not per publisher** — terms differ between
datasets from the same agency, and some carry third-party contributions whose terms travel with
them, so check the specific product and its contributor metadata. See
[`SECURITY.md`](https://github.com/gosha70/mapatlas/blob/main/SECURITY.md) and the licensing
rule in
[`specs/architecture.md`](https://github.com/gosha70/mapatlas/blob/main/specs/architecture.md).
