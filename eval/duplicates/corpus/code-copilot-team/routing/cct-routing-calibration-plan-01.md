---
page_type: decision
slug: cct-routing-calibration-plan-01
title: 'Placement: session analytics, read-only over E1 sets via the E2 loader — plus TWO labeled E1 evidence additions'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-calibration/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

New module
`session_analytics/routing_calibration.py` beside
`routing_evidence.py`, consuming `load_evidence_sets` output only.
E3 never opens an evidence file through any other path and never
writes into an evidence root. The frozen artifacts do NOT carry two
inputs the metrics provably require, so — per the "E1 change, not a
workaround" rule — E1 gains two additions (decision 11): per-task
PRE-ROUTING descriptors, and the per-profile policy declarations
(capability tier, roles) of the executed registry. No other E1
change is anticipated.
