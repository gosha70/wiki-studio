<!-- SPDX-License-Identifier: Apache-2.0 -->

# MAP-ATLAS

**An open-source, domain-agnostic engine for interactive field mapping: record a track,
drop an event where it happened, attach a comment and photos, and — optionally — let a
pluggable AI analyze those photos.**

MAP-ATLAS knows nothing about fish, plants, or mushrooms. It knows about **places**,
**tracks**, **events**, **media**, and an optional **media analyzer**. The domain is
supplied by whoever consumes it:

| Consumer | Plugs in | Gets |
|---|---|---|
| A fishing journal | a fish-species analyzer | "log my catch on the water" |
| A foraging app | a mushroom/plant analyzer | "map where I found it, ID the species" |
| A field survey tool | no analyzer | "record a route and tag observations" |

MAP-ATLAS is the reusable core; the value-added domain, private data, and any
privacy/sharing rules live in the consuming application.

## Quick start

The getting-started path is a section of the API contract itself:
**[`specs/api.md` § 0 — Quick start](specs/api.md#0-quick-start)**. It takes an empty project to a
working record → pin → photo → review loop, and every fenced block in it is checked: each one is
**either** the same bytes as a file under [`examples/quick-start`](examples/quick-start) **or**
generated from this repository — the install command is the generated one. That example is
compiled against the packed packages by `check:packaging` and run in a real browser by
`e2e/quick-start.e2e.ts`. Nothing is repeated here, because a second copy is a copy that drifts.

## Status

<!-- generated:status -->

[`specs/tasks.md`](specs/tasks.md) carries a **Done** record for 15 of its 52 tasks; the first in document order is T4.6.
A zero below means *no Done record*, not *no completed work*: this table reports what that
file records, and is generated from it.

| Phase | Tasks | With a Done record |
| --- | --- | --- |
| 0 — Toolchain & skeleton | 8 | 0 |
| 1 — `@mapatlas/core` | 13 | 0 |
| 2 — `@mapatlas/storage-idb` | 3 | 0 |
| 3 — `@mapatlas/recorder-web` | 4 | 0 |
| 4 — `@mapatlas/maplibre` | 9 | 2 |
| 5 — `@mapatlas/react` | 6 | 5 |
| 6 — Offline regions | 2 | 2 |
| 7 — Demo + docs | 4 | 4 |
| 8 — Follow-ups (post-v1, recorded and unscheduled) | 3 | 2 |

<!-- /generated:status -->

[`specs/roadmap.md`](specs/roadmap.md) has the phase order and each phase's exit criteria.

## The governing contract

Everything in [`specs/`](specs/) is **harness-neutral** — the canonical source of truth,
written so that different build harnesses can consume the *same* brief. Build against it, and
change it in the same commit as any public interface it describes:

- [`specs/PRD.md`](specs/PRD.md) — product requirements: users, problems, scope, non-goals.
- [`specs/architecture.md`](specs/architecture.md) — package layout, module boundaries, data model, offline + AI seams.
- [`specs/api.md`](specs/api.md) — the public TypeScript API contract (the interfaces to build against).
- [`specs/roadmap.md`](specs/roadmap.md) — phased delivery.
- [`specs/tasks.md`](specs/tasks.md) — the buildable backlog: epics → tasks with acceptance criteria.
- [`specs/decisions.md`](specs/decisions.md) — architecture decision log (ADRs).

[`CLAUDE.md`](CLAUDE.md) is the entry point for the **Claude Code** harness; it points at
the same `specs/`. Any other harness should read `specs/` directly.

## Design at a glance

- **TypeScript**, framework-agnostic **core** + a **MapLibre GL** renderer + thin **React** bindings.
- **Offline-first**: PMTiles offline map regions; a pluggable storage adapter (default IndexedDB).
- **Track recording** behind a `TrackRecorder` abstraction (web `watchPosition` + Wake Lock;
  a native adapter for background tracking in a Capacitor/Cordova shell).
- **AI is optional and pluggable**: a `MediaAnalyzer` interface (photo → labels/summary).
  No model is bundled; consumers provide on-device or remote analyzers.
- **A consumer wires two things themselves**: the renderer's stylesheet and MapLibre's worker
  URL. Neither can be done for you — injecting global CSS is a decision about your document, and
  the worker's URL depends on your bundler. The quick start above shows both, in code that is
  checked; [`packages/maplibre/README.md`](packages/maplibre/README.md) explains what breaks
  without them.

## License

[Apache-2.0](LICENSE). Contributions are accepted under the **Developer Certificate of
Origin** — see [CONTRIBUTING.md](CONTRIBUTING.md). Every source file carries an
`SPDX-License-Identifier: Apache-2.0` header.

## Attribution & data licensing (downstream obligation)

MAP-ATLAS renders third-party map data. Consumers must honor the source licenses —
OpenStreetMap (ODbL) and OpenSeaMap seamarks (ODbL, share-alike) among them.

Bathymetry and elevation sources are **licensed per product, not per publisher**: terms differ
between datasets from the same agency, and some carry third-party contributions whose terms
travel with them. Check the specific product and its contributor metadata rather than relying
on a publisher's general reputation — the engine bundles no tiles and takes no position on
which sources you use. See [`specs/architecture.md`](specs/architecture.md#map-data--licensing)
and ADR-0024 in [`specs/decisions.md`](specs/decisions.md).
