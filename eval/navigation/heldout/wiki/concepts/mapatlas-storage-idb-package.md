---
page_type: concept
slug: mapatlas-storage-idb-package
title: "@mapatlas/storage-idb — the default IndexedDB persistence"
status: draft
last_reviewed: 2026-10-28
sources:
  - path: eval/navigation/heldout/corpus/packages__storage-idb__README.md
    sha: 79de8a1
page_id: pg-d9af62c64e254ad092b12e8bca1c10a9
---

# @mapatlas/storage-idb — the default IndexedDB persistence

## Summary

`@mapatlas/storage-idb` is MAP-ATLAS's default persistence. It implements the `StorageAdapter` and `MapAssetStore` seams of `@mapatlas/core` on IndexedDB. Its contract is `specs/api.md` §5. Tracks, events, media and downloaded map archives live in the browser's own storage, under a database name the consumer chooses.

## Key ideas

- Nothing leaves the device unless the consumer's application sends it.
- `createIdbStorageAdapter` takes a `databaseName` and returns a `StorageAdapter`.
- The README example stores a track with `saveTrack` and reads it back with `getTrack`.
- The adapter opens the database lazily on the first call.
- A consumer can therefore construct the adapter at module load.
- Storing data does not guarantee that the browser keeps it. Browsers can evict an origin under storage pressure.
- The engine does not ask for a persistent origin on the consumer's behalf.
- The demo's persistence UX shows how to ask for a persistent origin.
- `createIdbMapAssetStore` is the `MapAssetStore` that `@mapatlas/offline-pmtiles` uses in its README example.
- `@mapatlas/recorder-web` can take this package's adapter as its `store` for autosave.
- The package declares no peer dependencies.
- The package is not published to a registry. A contributor builds it from a checkout and installs it as a tarball.
- The only install path that is checked and run end to end is the quick start in `specs/api.md` §0. The README does not repeat an install command.

## Where this shows up

- `packages/storage-idb/README.md`, including the generated peers block between the `generated:peers` markers.
- `examples/readme/storage-idb/adapter.ts` is the README's track example. The repository compiles it against the packed packages on every change, but does not execute it.
- `specs/api.md` §5 (persistence seam) and §0 (quick start).
- License: Apache-2.0. `SECURITY.md` describes what the engine does and does not send anywhere. The licensing rule lives in `specs/architecture.md`.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [@mapatlas/recorder-web — the browser's foreground TrackRecorder](mapatlas-recorder-web-package.md)
- [@mapatlas/offline-pmtiles — offline map regions over PMTiles archives](mapatlas-offline-pmtiles-package.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
