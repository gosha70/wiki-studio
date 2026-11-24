---
page_type: decision
slug: cct-pi-team-controller-plan-05
title: 'Create safety + bootstrap'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-team-controller/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

→ refuse over existing/corrupt (never overwrite);
lead = declared member; no restart. `create [--no-plan-approval]` (default on).
