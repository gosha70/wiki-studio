<!-- SPDX-License-Identifier: Apache-2.0 -->

# `@mapatlas/recorder-web`

The browser's `TrackRecorder` for [MAP-ATLAS](https://github.com/gosha70/mapatlas): foreground GPS through the Geolocation
API, with the sampling and sensor-merge policies [`api.md` §2](https://github.com/gosha70/mapatlas/blob/main/specs/api.md#2-track-recording-mapatlascore-interface--mapatlasrecorder-web-implementation)
and §3 specify. The interface it implements lives in `@mapatlas/core`; this package is one
implementation of it, and a native background recorder would be another.

## Install

**The packages are not published to a registry.** They are built from a checkout and installed as
tarballs, and the one install path that is checked and run end to end is the quick start in
[`api.md` §0](https://github.com/gosha70/mapatlas/blob/main/specs/api.md#0-quick-start). Follow it; this page does not repeat an install command it
cannot run.

What this package needs beside itself, read from its own manifest:

<!-- generated:peers -->

_This package declares no peer dependencies._

<!-- /generated:peers -->

## Record a track

Every code block on this page is a file that this repository compiles against the packed packages
on every change — the block names the file. It is **compiled, not executed**: the path that is also
run in a browser is the quick start's.

```ts examples/readme/recorder-web/record.ts
// SPDX-License-Identifier: Apache-2.0
import type { Track } from "@mapatlas/core";
import { createWebTrackRecorder } from "@mapatlas/recorder-web";

// Geolocation from the browser, in the foreground. Nothing is persisted unless a `store` is
// given; see @mapatlas/storage-idb for the default one.
const recorder = createWebTrackRecorder();

recorder.onPoint((point) => {
  console.log(point.lat, point.lng, point.t);
});

export async function recordForAMinute(): Promise<Track> {
  await recorder.start();
  await new Promise((resolve) => setTimeout(resolve, 60_000));
  return recorder.stop();
}
```

`start()` asks the browser for position permission and begins sampling; `stop()` resolves with the
finished `Track`. Give the recorder a `store` — an `@mapatlas/storage-idb` adapter, or your own
`StorageAdapter` — and it autosaves every `autosaveMs` milliseconds, so a reload mid-trip loses at
most one autosave interval's worth of points, provided the autosaves themselves succeeded. **Foreground only:** a web page cannot record with the screen locked, and this package
does not pretend otherwise. That gap is a consumer's to close with a native adapter.

## License

Apache-2.0. See [`SECURITY.md`](https://github.com/gosha70/mapatlas/blob/main/SECURITY.md) for what the engine does and does not
send anywhere, and the licensing rule in [`specs/architecture.md`](https://github.com/gosha70/mapatlas/blob/main/specs/architecture.md).
