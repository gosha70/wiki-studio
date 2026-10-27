<!-- SPDX-License-Identifier: Apache-2.0 -->

# `@mapatlas/core`

The framework-agnostic heart of [MAP-ATLAS](https://github.com/gosha70/mapatlas): the data model — tracks, points, events,
media references — and every seam the rest of the engine is built behind: `TrackRecorder`,
`StorageAdapter`, `SensorSource`, `TileSource`, `MediaAnalyzer`, `EventPresentation`. It knows
nothing about a browser, a map library or a database, and nothing about any domain: no fish,
plants, products or users. Its contract is [`api.md` §1](https://github.com/gosha70/mapatlas/blob/main/specs/api.md#1-core-data-types-mapatlascore)
through §7 and §10.

## Install

**The packages are not published to a registry.** They are built from a checkout and installed as
tarballs, and the one install path that is checked and run end to end is the quick start in
[`api.md` §0](https://github.com/gosha70/mapatlas/blob/main/specs/api.md#0-quick-start). Follow it; this page does not repeat an install command it
cannot run.

What this package needs beside itself, read from its own manifest:

<!-- generated:peers -->

_This package declares no peer dependencies._

<!-- /generated:peers -->

## A track is data

Every code block on this page is a file that this repository compiles against the packed packages
on every change — the block names the file. It is **compiled, not executed**: the path that is also
run in a browser is the quick start's.

```ts examples/readme/core/track.ts
// SPDX-License-Identifier: Apache-2.0
import { haversineDistanceMeters, newId, trackToGeoJSON, type Track } from "@mapatlas/core";

// The engine's data model is plain data: a track is points on a timeline, no class required.
const startedAt = Date.now();
const track: Track = {
  id: newId(),
  startedAt,
  endedAt: startedAt + 60_000,
  status: "finalized",
  origin: "authored",
  points: [
    { lat: 45.9, lng: 7, t: startedAt },
    { lat: 45.91, lng: 7.01, t: startedAt + 60_000 },
  ],
  segments: [{ id: newId(), startIndex: 0, endIndex: 1, startedAt, endedAt: startedAt + 60_000 }],
};

export const metres = haversineDistanceMeters(track.points[0]!, track.points[1]!);
// Portable, with its events: the GeoJSON a consumer can hand to anything else.
export const exported = trackToGeoJSON(track, []);
```

Nothing here needs a browser: `newId` is a random id, `haversineDistanceMeters` is arithmetic,
and `trackToGeoJSON` produces the portable form that [`api.md` §10](https://github.com/gosha70/mapatlas/blob/main/specs/api.md#10-portability-mapatlascore)
specifies — the one `geoJSONToTrack` reads back. Recording a track from real GPS is
`@mapatlas/recorder-web`'s job; storing one is `@mapatlas/storage-idb`'s; drawing one is
`@mapatlas/maplibre`'s. Each of those depends on this package, and this package depends on none of
them.

Also exported, under `@mapatlas/core/testing`: first-party fakes for every seam, so a consumer can
test against the engine without hardware — [`api.md` §5c](https://github.com/gosha70/mapatlas/blob/main/specs/api.md#5c-first-party-test-utilities-mapatlascoretesting).

## License

Apache-2.0. See [`SECURITY.md`](https://github.com/gosha70/mapatlas/blob/main/SECURITY.md) for what the engine does and does not
send anywhere, and the licensing rule in [`specs/architecture.md`](https://github.com/gosha70/mapatlas/blob/main/specs/architecture.md).
