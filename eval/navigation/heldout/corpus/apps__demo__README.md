<!-- SPDX-License-Identifier: Apache-2.0 -->

# MAP-ATLAS demo

A generic field logger built **only from the published package entry points** — no deep imports,
no internals. Record a track, drop an event where it happened, attach a photo, review the trip,
export it as GeoJSON, over a self-hosted map.

## Run it

```bash
npm install
npm run demo
```

That is the whole thing. It prints one URL — open it.

The first run cuts the map archives, which needs the network once and takes about a minute. Later
runs reuse them and start immediately. `Ctrl-C` stops it.

## What you should see

A map of one alpine massif: landmass, landuse, water and roads from an OpenStreetMap extract,
shaded relief and brown contour lines from a Copernicus elevation model above it, and **two
attribution lines** in the corner — one for each source, because they are two derived works under
two unrelated licences.

Then the loop: **Start recording** (the browser will ask for your location), tap the map to drop
an event, attach a photo, **Stop and review**, and **Export GeoJSON**.

## Offline

Two different things, which fail independently:

- **The map's data.** **Download region** copies the three archives into IndexedDB, and the map
  then draws from them with the archive server unreachable; **Delete region** puts it back. This
  is the development runner's behaviour too, so the panel works under `npm run demo` (both servers
  it starts live in one process, so there is no way to stop only the archive one by hand — the
  browser lane is what actually cuts the host).
- **The application itself.** A service worker precaches the built shell, so a reload with the
  app's own server down still boots the real application rather than a browser error page. This
  exists **in a production build only** — see *What it is not* below.

Both are checked rather than claimed: `e2e/app-offline.e2e.ts` renders from a downloaded region
with the archive host cut, and `e2e/app-shell-offline.e2e.ts` boots the built application with its
own origin cut, on the production bundle rather than the development one. ADR-0035 and ADR-0039.

## What it is not

- **Not a production server.** `npm run demo` is the *development* runner, and it deliberately
  registers no service worker — running ordinary local development under an active worker helps
  nobody. So the offline shell described above is not what this command demonstrates; the
  production browser lane is where that claim is made and checked.
- **Not a global basemap.** The archives cover one small region; pan far and the map runs out.
  That is the point — they are cut locally rather than served from anyone's tile host.
- **No map tiles are in this repository.** `npm run demo` cuts them into `build/fixture/`, which
  git ignores. See `specs/decisions.md` ADR-0024 and ADR-0038 for the sources and their licences.

## If something goes wrong

- **"port 5175/5176 is already in use"** — something else is listening, often a previous run.
  Stop it and try again.
- **An error mentioning "HTTP Byte Serving"** — the archives are being served by something that
  ignores `Range`. PMTiles is read by range request, and the reader refuses a response carrying
  more bytes than it asked for. `npm run demo` uses a server that supports it; a plain static
  server such as `python3 -m http.server` does not.
