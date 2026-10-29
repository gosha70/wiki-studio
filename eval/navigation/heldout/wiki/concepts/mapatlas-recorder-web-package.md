---
page_type: concept
slug: mapatlas-recorder-web-package
title: "@mapatlas/recorder-web — the browser's foreground TrackRecorder"
status: draft
last_reviewed: 2026-10-28
sources:
  - path: eval/navigation/heldout/corpus/packages__recorder-web__README.md
    sha: 79de8a1
page_id: pg-95228640ba8a4805a8c3c75b92103872
---

# @mapatlas/recorder-web — the browser's foreground TrackRecorder

## Summary

`@mapatlas/recorder-web` is MAP-ATLAS's browser implementation of `TrackRecorder`, and it records in the foreground only. It reads GPS through the Geolocation API. It applies the sampling and sensor-merge policies that `specs/api.md` §2 and §3 specify. The `TrackRecorder` interface lives in `@mapatlas/core`.

## Key ideas

- This package is one implementation of the `TrackRecorder` interface. A native background recorder would be another implementation.
- `createWebTrackRecorder()` returns a recorder.
- `onPoint` registers a callback for each new point. Each point carries `lat`, `lng` and `t`.
- `start()` asks the browser for position permission. Then it begins sampling.
- `stop()` resolves with the finished `Track`.
- Nothing is persisted unless a `store` is given.
- A `store` is an `@mapatlas/storage-idb` adapter or the consumer's own `StorageAdapter`. `@mapatlas/storage-idb` provides the default one.
- With a `store`, the recorder autosaves every `autosaveMs` milliseconds.
- A reload mid-trip then loses at most one autosave interval's worth of points. This holds only if the autosaves themselves succeeded.
- The recorder is foreground only. A web page cannot record with the screen locked.
- The package does not pretend otherwise. The consumer closes that gap with a native adapter.
- The package declares no peer dependencies.
- The package is not published to a registry. A contributor builds it from a checkout and installs it as a tarball.
- The only install path that is checked and run end to end is the quick start in `specs/api.md` §0. The README does not repeat an install command.

## Where this shows up

- `packages/recorder-web/README.md`, including the generated peers block between the `generated:peers` markers.
- `examples/readme/recorder-web/record.ts` is the README's recording example. The repository compiles it against the packed packages on every change, but does not execute it.
- `specs/api.md` §2 (track recording), §3 (sampling and sensor merge) and §0 (quick start).
- License: Apache-2.0. `SECURITY.md` describes what the engine does and does not send anywhere. The licensing rule lives in `specs/architecture.md`.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [@mapatlas/react — the React bindings over the engine's seams](mapatlas-react-package.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
