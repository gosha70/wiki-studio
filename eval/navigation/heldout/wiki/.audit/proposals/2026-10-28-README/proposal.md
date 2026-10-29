# Proposal: 2026-10-28-README

**Rationale:** Four-question gate passed. The source is the MAP-ATLAS root README (eval/navigation/heldout/corpus/README.md at 79de8a1). It describes durable project knowledge a new contributor needs: the domain-agnostic engine model, the harness-neutral specs/ contract, and the downstream map-data licensing obligation. The wiki is empty, so no existing page covers these topics. I created three concept pages, one per concept, and added index and log entries for each. The README's status table is generated and changes over time, so I left its counts out of the wiki. The pages point to specs/tasks.md instead.

## concepts/map-atlas-engine.md
**Action:** create  
**Rationale:** This is the core mental model of the project: what the engine knows, what consumers supply, the design at a glance and the two wiring steps that only a consumer can do.

```markdown
---
page_type: concept
slug: map-atlas-engine
title: MAP-ATLAS — a domain-agnostic field-mapping engine
status: draft
last_reviewed: 2026-10-28
sources:
  - path: eval/navigation/heldout/corpus/README.md
    sha: 79de8a1
page_id: pg-85080ebfb8cc4b41b76d5559bc3d1c3f
---

# MAP-ATLAS — a domain-agnostic field-mapping engine

## Summary

MAP-ATLAS is an open-source, domain-agnostic engine for interactive field mapping. A user records a track and drops an event where something happened. The user can attach a comment and photos to the event. A pluggable AI can analyze those photos, and this step is optional.

## Key ideas

- The engine knows about five things: **places**, **tracks**, **events**, **media** and an optional **media analyzer**.
- The engine knows nothing about fish, plants or mushrooms. The consuming application supplies the domain.
- A fishing journal plugs in a fish-species analyzer to log a catch on the water.
- A foraging app plugs in a mushroom or plant analyzer to map a find and identify the species.
- A field survey tool plugs in no analyzer. It records a route and tags observations.
- MAP-ATLAS is the reusable core. The consuming application owns the domain value, the private data and any privacy or sharing rules.
- The engine is written in **TypeScript**. It has a framework-agnostic **core**, a **MapLibre GL** renderer and thin **React** bindings.
- The engine is **offline-first**. It uses PMTiles for offline map regions. Storage goes through a pluggable adapter, and the default adapter is IndexedDB.
- Track recording sits behind a `TrackRecorder` abstraction. The web adapter uses `watchPosition` and Wake Lock.
- A native `TrackRecorder` adapter gives background tracking inside a Capacitor or Cordova shell.
- AI sits behind a `MediaAnalyzer` interface that turns a photo into labels or a summary. No model is bundled. Consumers provide on-device or remote analyzers.
- A consumer must wire two things alone: the renderer's stylesheet and MapLibre's worker URL.
- The engine cannot inject the stylesheet, because global CSS is a decision about the consumer's document.
- The engine cannot set the worker URL, because that URL depends on the consumer's bundler.

## Where this shows up

- Packages: `@mapatlas/core`, `@mapatlas/storage-idb`, `@mapatlas/recorder-web`, `@mapatlas/maplibre`, `@mapatlas/react`, plus offline regions in `packages/offline-pmtiles`.
- `packages/maplibre/README.md` explains what breaks without the stylesheet and the worker URL.
- `specs/api.md` § 0 (Quick start) shows both wiring steps in checked code.
- `specs/architecture.md` describes the package layout, module boundaries, data model, and the offline and AI seams.
- License: Apache-2.0. Contributions are accepted under the Developer Certificate of Origin (see `CONTRIBUTING.md`). Every source file carries an `SPDX-License-Identifier: Apache-2.0` header.

## Related

- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
```

## concepts/harness-neutral-specs-contract.md
**Action:** create  
**Rationale:** New contributors need to know which document is authoritative, how the quick start is kept from drifting, and how to read the generated status table.

```markdown
---
page_type: concept
slug: harness-neutral-specs-contract
title: Harness-neutral governing contract (specs/)
status: draft
last_reviewed: 2026-10-28
sources:
  - path: eval/navigation/heldout/corpus/README.md
    sha: 79de8a1
page_id: pg-aacf9da786834129a092f122d775ad68
---

# Harness-neutral governing contract (specs/)

## Summary

Everything in MAP-ATLAS's `specs/` directory is the canonical source of truth. It is written to be harness-neutral, so different build harnesses can consume the same brief. Contributors build against it. A contributor changes it in the same commit as any public interface it describes.

## Key ideas

- `specs/PRD.md` holds the product requirements: users, problems, scope and non-goals.
- `specs/architecture.md` holds the package layout, module boundaries, data model, and the offline and AI seams.
- `specs/api.md` holds the public TypeScript API contract. These are the interfaces to build against.
- `specs/roadmap.md` holds the phased delivery. It lists the phase order and each phase's exit criteria.
- `specs/tasks.md` holds the buildable backlog of epics and tasks with acceptance criteria.
- `specs/decisions.md` holds the architecture decision log (ADRs).
- `CLAUDE.md` is the entry point for the Claude Code harness. It points at the same `specs/`.
- Any other harness should read `specs/` directly.
- The quick start lives only in `specs/api.md` § 0. The README does not repeat it, because a second copy drifts.
- Every fenced block in the quick start is checked. Each block either matches the bytes of a file under `examples/quick-start` or is generated from the repository.
- The install command in the quick start is the generated one.
- `check:packaging` compiles the quick-start example against the packed packages.
- `e2e/quick-start.e2e.ts` runs the quick-start example in a real browser.
- The README status table is generated from `specs/tasks.md`. It counts tasks with a **Done** record per phase.
- A zero in the status table means *no Done record*. It does not mean *no completed work*.

## Where this shows up

- `specs/` at the repository root.
- `README.md` sections "Quick start", "Status" (between the `generated:status` markers) and "The governing contract".
- `examples/quick-start`, `e2e/quick-start.e2e.ts` and the `check:packaging` script.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [Map-data licensing is a downstream obligation](map-data-licensing.md)
```

## concepts/map-data-licensing.md
**Action:** create  
**Rationale:** The per-product licensing rule is easy to miss, and it applies to every consumer, so it gets its own page.

```markdown
---
page_type: concept
slug: map-data-licensing
title: Map-data licensing is a downstream obligation
status: draft
last_reviewed: 2026-10-28
sources:
  - path: eval/navigation/heldout/corpus/README.md
    sha: 79de8a1
page_id: pg-84b04a06f55b4355a9fb8040849767f4
---

# Map-data licensing is a downstream obligation

## Summary

Consumers of MAP-ATLAS must honor the licenses of the third-party map data the engine renders. The engine bundles no tiles. It takes no position on which data sources a consumer uses.

## Key ideas

- OpenStreetMap data is licensed under ODbL.
- OpenSeaMap seamarks are licensed under ODbL, which is share-alike.
- Bathymetry and elevation sources are licensed per product, not per publisher.
- Terms can differ between datasets from the same agency.
- Some datasets carry third-party contributions whose terms travel with them.
- A consumer must check the specific product and its contributor metadata. A publisher's general reputation is not enough.

## Where this shows up

- `README.md` section "Attribution & data licensing (downstream obligation)".
- `specs/architecture.md` section "Map data & licensing".
- ADR-0024 in `specs/decisions.md`.

## Related

- [MAP-ATLAS — a domain-agnostic field-mapping engine](map-atlas-engine.md)
- [Harness-neutral governing contract](harness-neutral-specs-contract.md)
```

## index.md
**Action:** append-index  
**Rationale:** Link the new engine concept page from the index.

```markdown
- [MAP-ATLAS — a domain-agnostic field-mapping engine](concepts/map-atlas-engine.md) — places, tracks, events, media and a pluggable analyzer; consumers supply the domain
```

## index.md
**Action:** append-index  
**Rationale:** Link the new specs-contract concept page from the index.

```markdown
- [Harness-neutral governing contract](concepts/harness-neutral-specs-contract.md) — specs/ is the source of truth; the quick start is checked; status is generated
```

## index.md
**Action:** append-index  
**Rationale:** Link the new licensing concept page from the index.

```markdown
- [Map-data licensing is a downstream obligation](concepts/map-data-licensing.md) — consumers honor ODbL and per-product bathymetry and elevation terms
```

## log.md
**Action:** append-log  
**Rationale:** Log the page creation.

```markdown
- 2026-10-28 — create map-atlas-engine (concept): ingest of the MAP-ATLAS root README
```

## log.md
**Action:** append-log  
**Rationale:** Log the page creation.

```markdown
- 2026-10-28 — create harness-neutral-specs-contract (concept): ingest of the MAP-ATLAS root README
```

## log.md
**Action:** append-log  
**Rationale:** Log the page creation.

```markdown
- 2026-10-28 — create map-data-licensing (concept): ingest of the MAP-ATLAS root README
```
