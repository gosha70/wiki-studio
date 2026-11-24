---
page_type: decision
slug: cct-routing-recovery-plan-06
title: 'Operator re-enable'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-recovery/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`cct routing enable <profile-id>`:
auth-disabled → `probe_due` (never straight to eligible),
journaled as an operator action with the profile named; any other
state refuses by name (nothing else needs enabling). The next
tick probes it; only a passed probe reaches `healthy`.
