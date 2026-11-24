---
page_type: decision
slug: cct-routing-recovery-plan-08
title: 'Promotions, both config layers, the established path'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-recovery/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Repo `routing.recovery`: CLOSED object
`{auto_failback_enabled?: bool, wake_enabled?: bool}` —
restriction-only (false restricts; true/absent restrict
nothing); unknown keys refused; validator + schema + rc_effective
(`auto_failback_allowed`, `wake_allowed` fields with the
explicit-null discipline — never `// true`).
Registry `[policy]`: `healthy_probes_required` (int ≥ 1,
default 2), `minimum_profile_dwell_sec` (int ≥ 0, default 300),
`failback` (`auto | operator`, default `auto`) move from
RC_POLICY_FUTURE_KEYS to validated keys with behavior; defaults
are named constants when the key is absent.
`max_switches_per_task` STAYS refused by name.
