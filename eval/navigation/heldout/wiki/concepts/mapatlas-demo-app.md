---
page_type: concept
slug: mapatlas-demo-app
title: MAP-ATLAS demo — a field logger built only from the published packages
status: draft
last_reviewed: 2026-10-28
sources:
  - path: eval/navigation/heldout/corpus/apps__demo__README.md
    sha: 79de8a1
page_id: pg-874baca67e924d679bf597ec2ce84a32
---

# MAP-ATLAS demo — a field logger built only from the published packages

## Summary

The MAP-ATLAS demo is a generic field logger built only from the published package entry points. It uses no deep imports and no internals. A user records a track, drops an event where it happened, attaches a photo, reviews the trip and exports it as GeoJSON. All of this runs over a self-hosted map.

## Key ideas

- A contributor runs `npm install` and then `npm run demo`. The command prints one URL to open.
- The first run cuts the map archives. This needs the network once and takes about a minute.
- Later runs reuse the archives and start immediately. `Ctrl-C` stops the demo.
- The map shows one alpine massif.
- An OpenStreetMap extract supplies the landmass, landuse, water and roads.
- A Copernicus elevation model supplies shaded relief and brown contour lines above them.
- The corner shows two attribution lines, one for each source. The two sources are two derived works under two unrelated licences.
- The demo loop is **Start recording**, tap the map to drop an event, attach a photo, **Stop and review** and **Export GeoJSON**.
- The browser asks for the user's location when recording starts.
- "Offline" covers two different things. They fail independently.
- The first thing is the map's data. **Download region** copies the three archives into IndexedDB.
- The map then draws from IndexedDB with the archive server unreachable. **Delete region** puts it back.
- The development runner has this map-data behaviour too. The panel therefore works under `npm run demo`.
- `npm run demo` starts both servers in one process. A user cannot stop only the archive server by hand.
- The browser lane is what actually cuts the archive host in the tests.
- The second thing is the application itself. A service worker precaches the built shell.
- With the service worker, a reload with the app's own server down still boots the real application. It does not show a browser error page.
- The service worker exists in a production build only.
- The tests check both offline claims instead of asserting them.
- `e2e/app-offline.e2e.ts` renders from a downloaded region with the archive host cut.
- `e2e/app-shell-offline.e2e.ts` boots the built application with its own origin cut. It runs on the production bundle, not the development one.
- `npm run demo` is the development runner, not a production server.
- The development runner deliberately registers no service worker. Ordinary local development under an active worker helps nobody.
- `npm run demo` therefore does not demonstrate the offline shell. The production browser lane makes and checks that claim.
- The demo is not a global basemap. The archives cover one small region, so the map runs out if the user pans far.
- The archives are cut locally on purpose. They are not served from anyone's tile host.
- The repository holds no map tiles. `npm run demo` cuts them into `build/fixture/`, which git ignores.
- The error "port 5175/5176 is already in use" means something else is listening, often a previous run. Stop it and try again.
- An error that mentions "HTTP Byte Serving" means the archive server ignores `Range`.
- PMTiles is read by range request. The reader refuses a response that carries more bytes than it asked for.
- `npm run demo` uses a server that supports range requests. A plain static server such as `python3 -m http.server` does not.

## Where this shows up

- `apps/demo/README.md`.
- `e2e/app-offline.e2e.ts` checks rendering from a downloaded region with the archive host cut.
- `e2e/app-shell-offline.e2e.ts` checks the offline application shell on the production bundle.
- `build/fixture/` holds the cut archives and is gitignored.
- `specs/decisions.md` ADR-0035 and ADR-0039 cover the two offline layers.
- `specs/decisions.md` ADR-0024 and ADR-0038 cover the map sources and their licences.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [@mapatlas/offline-pmtiles — offline map regions over PMTiles archives](mapatlas-offline-pmtiles-package.md)
- [@mapatlas/storage-idb — the default IndexedDB persistence](mapatlas-storage-idb-package.md)
- [@mapatlas/recorder-web — the browser's foreground TrackRecorder](mapatlas-recorder-web-package.md)
- [@mapatlas/core — the framework-agnostic data model and seams](mapatlas-core-package.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
