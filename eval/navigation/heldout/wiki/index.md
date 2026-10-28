---
page_type: index
slug: index
title: Wiki
status: stable
last_reviewed: 2026-10-28
---

# Wiki
- [MAP-ATLAS — a domain-agnostic field-mapping engine](concepts/map-atlas-engine.md) — places, tracks, events, media and a pluggable analyzer; consumers supply the domain
- [Harness-neutral governing contract](concepts/harness-neutral-specs-contract.md) — specs/ is the source of truth; the quick start is checked; status is generated
- [Map-data licensing is a downstream obligation](concepts/map-data-licensing.md) — consumers honor ODbL and per-product bathymetry and elevation terms
- [@mapatlas/core — the framework-agnostic data model and seams](concepts/mapatlas-core-package.md) — tracks as plain data, the six seams, GeoJSON portability and testing fakes
- [@mapatlas/maplibre — the MapLibre GL renderer and its wiring](concepts/mapatlas-maplibre-package.md) — exact-version maplibre-gl peer, worker URL and stylesheet wiring, silent failure modes
- [@mapatlas/offline-pmtiles — offline map regions over PMTiles archives](concepts/mapatlas-offline-pmtiles-package.md) — region download into a MapAssetStore, the offlineLicensed refusal rule, and the extra install step
- [@mapatlas/react — the React bindings over the engine's seams](concepts/mapatlas-react-package.md) — MapCanvas, EventComposer, TripReview and the hooks; react >=18 peer; no injected CSS
- [@mapatlas/recorder-web — the browser's foreground TrackRecorder](concepts/mapatlas-recorder-web-package.md) — Geolocation-based recording, store autosave every autosaveMs, foreground only
- [@mapatlas/storage-idb — the default IndexedDB persistence](concepts/mapatlas-storage-idb-package.md) — StorageAdapter and MapAssetStore on IndexedDB, lazy open, on-device data, browser eviction
- [MAP-ATLAS demo — a field logger built only from the published packages](concepts/mapatlas-demo-app.md) — npm run demo, two independent offline layers, dev runner has no service worker, range-request troubleshooting
