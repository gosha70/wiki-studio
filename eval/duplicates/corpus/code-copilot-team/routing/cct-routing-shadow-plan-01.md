---
page_type: decision
slug: cct-routing-shadow-plan-01
title: 'Placement: consumption and derivation live in session analytics'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-shadow/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

New module
`scripts/session_analytics/routing_evidence.py` owns evidence-set
discovery, validation, and shadow-recommendation derivation; API
routes join the existing FastAPI app; the Studio gains a Routing
view. The dependency direction is one-way — `session_analytics`
imports `benchmark_runner.routing_eval` READ-ONLY (record_check
validation, matrix/record parsing) — mirroring #261: "Consume E1
artifacts through session analytics / studio". Nothing under
`scripts/lib/`, `benchmark_runner`, or the supervisor imports
analytics.
