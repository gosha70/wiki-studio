---
page_type: decision
slug: cct-routing-shadow-plan-10
title: 'Studio slice follows the benchmark-ui conventions — verified in a browser, not only by the compiler'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-shadow/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Typed fetcher in
`studio/lib/api.ts` mirroring payloads exactly; a Routing tab in
the `TABS` nav; `Card`/`Stat`/`useApi`,
`Loading`/`ErrorNote`; explanatory empty state pointing at the E1
scenario; the three recommendation outcomes visually distinct
(insufficient-data never renders like no-change); no new npm
dependencies; `npm run build` green.
