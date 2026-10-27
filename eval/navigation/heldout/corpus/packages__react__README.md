<!-- SPDX-License-Identifier: Apache-2.0 -->

# `@mapatlas/react`

The React bindings for [MAP-ATLAS](https://github.com/gosha70/mapatlas): `MapCanvas`, `EventComposer`, `TripReview` and the
hooks — `useTrackRecorder`, `useTrackDraft`, `useEventLog`, `useOfflineRegions` — over the engine's
seams, [`api.md` §9](https://github.com/gosha70/mapatlas/blob/main/specs/api.md#9-react-bindings-mapatlasreact). It depends on `@mapatlas/maplibre`
for drawing and `@mapatlas/recorder-web` for recording; the full record → pin → review loop is the
quick start.

## Install

**The packages are not published to a registry.** They are built from a checkout and installed as
tarballs, and the one install path that is checked and run end to end is the quick start in
[`api.md` §0](https://github.com/gosha70/mapatlas/blob/main/specs/api.md#0-quick-start). Follow it; this page does not repeat an install command it
cannot run.

What this package needs beside itself, read from its own manifest:

<!-- generated:peers -->

- `react` — `>=18`

<!-- /generated:peers -->

## Draw a map, start a recording

Every code block on this page is a file that this repository compiles against the packed packages
on every change — the block names the file. It is **compiled, not executed**: the path that is also
run in a browser is the quick start's.

```tsx examples/readme/react/canvas.tsx
// SPDX-License-Identifier: Apache-2.0
import type { TileSource } from "@mapatlas/core";
import { MapCanvas, useTrackRecorder } from "@mapatlas/react";
import type { ReactElement } from "react";

// Your archive, served by your application: the engine bundles no map data.
const basemap: TileSource = {
  id: "basemap",
  kind: "vector",
  transport: "pmtiles",
  url: new URL("/basemap.pmtiles", window.location.href).toString(),
  attribution: "© your basemap provider",
};

export function FieldMap(): ReactElement {
  const recorder = useTrackRecorder();
  return (
    <>
      <button onClick={() => void recorder.start()}>Record</button>
      <MapCanvas sources={[basemap]} initialCamera={{ center: { lat: 45.9, lng: 7 }, zoom: 12 }} />
    </>
  );
}
```

`MapCanvas` takes the same `sources` a `MapController` does and owns the map's lifetime;
`useTrackRecorder` wraps `@mapatlas/recorder-web`'s recorder in React state — `status`,
`livePoint`, `start`, `stop`. The stylesheet and worker URL that MapLibre needs are the
consumer's to load, exactly as `@mapatlas/maplibre`'s README describes: this package does not
inject global CSS.

## License

Apache-2.0. See [`SECURITY.md`](https://github.com/gosha70/mapatlas/blob/main/SECURITY.md) for what the engine does and does not
send anywhere, and the licensing rule in [`specs/architecture.md`](https://github.com/gosha70/mapatlas/blob/main/specs/architecture.md).
