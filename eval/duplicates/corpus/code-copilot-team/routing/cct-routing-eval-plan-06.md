---
page_type: decision
slug: cct-routing-eval-plan-06
title: 'A router score without a complete control set is a hard error'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-eval/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The reporter refuses to emit a `cct_router` figure unless
`always_best`, `always_cheapest`, and `oracle` are all present for
the same task set, trial seeds, and event stream. This is FR-E1-8
enforced in code, not documented as guidance — an uncontrolled routing number
is the specific failure mode this increment exists to prevent.
