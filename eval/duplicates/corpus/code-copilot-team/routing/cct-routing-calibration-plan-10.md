---
page_type: decision
slug: cct-routing-calibration-plan-10
title: 'API + Studio surface'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-calibration/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Endpoints:
`GET /api/routing/calibration` (the current gate report, or
insufficient_data when none, with the stale state explicit),
`GET /api/routing/calibration/evaluation` (the current evaluation
report, stale-flagged), and the kNN recommendations served beside
the E2 recommendations for a set/task. Studio: a Calibration panel
on the Routing tab (per-gate status with measured/threshold/
evidence, overall verdict, stale banner) and a labeled kNN section
in the recommendation cards with openable neighbors.
Browser-verified against live fixtures at desktop and mobile
widths for: no-data, insufficient, gates-mixed, gates-all-pass,
and stale (corpus-changed AND policy-changed) states. No new npm
dependencies.
