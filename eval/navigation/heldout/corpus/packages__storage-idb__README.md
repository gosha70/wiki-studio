<!-- SPDX-License-Identifier: Apache-2.0 -->

# `@mapatlas/storage-idb`

The default persistence for [MAP-ATLAS](https://github.com/gosha70/mapatlas): the `StorageAdapter` and `MapAssetStore` seams
of `@mapatlas/core`, implemented on IndexedDB — [`api.md` §5](https://github.com/gosha70/mapatlas/blob/main/specs/api.md#5-persistence-seam-mapatlascore-default-impl-in-mapatlasstorage-idb).
Tracks, events, media and downloaded map archives live in the browser's own storage, under a
database name you choose, and nothing leaves the device unless your application sends it.

## Install

**The packages are not published to a registry.** They are built from a checkout and installed as
tarballs, and the one install path that is checked and run end to end is the quick start in
[`api.md` §0](https://github.com/gosha70/mapatlas/blob/main/specs/api.md#0-quick-start). Follow it; this page does not repeat an install command it
cannot run.

What this package needs beside itself, read from its own manifest:

<!-- generated:peers -->

_This package declares no peer dependencies._

<!-- /generated:peers -->

## Keep a track

Every code block on this page is a file that this repository compiles against the packed packages
on every change — the block names the file. It is **compiled, not executed**: the path that is also
run in a browser is the quick start's.

```ts examples/readme/storage-idb/adapter.ts
// SPDX-License-Identifier: Apache-2.0
import type { Track } from "@mapatlas/core";
import { createIdbStorageAdapter } from "@mapatlas/storage-idb";

// The default persistence: IndexedDB, opened lazily on first use, under a name you choose.
export const store = createIdbStorageAdapter({ databaseName: "my-field-app" });

export async function keep(track: Track): Promise<Track | undefined> {
  await store.saveTrack(track);
  return store.getTrack(track.id);
}
```

The database is opened lazily on the first call, so the adapter can be constructed at module
load. Whether the browser will *keep* what is stored is a separate question — origins can be
evicted under storage pressure — and the demo's persistence UX shows how to ask for a persistent
origin; the engine does not ask on your behalf.

## License

Apache-2.0. See [`SECURITY.md`](https://github.com/gosha70/mapatlas/blob/main/SECURITY.md) for what the engine does and does not
send anywhere, and the licensing rule in [`specs/architecture.md`](https://github.com/gosha70/mapatlas/blob/main/specs/architecture.md).
