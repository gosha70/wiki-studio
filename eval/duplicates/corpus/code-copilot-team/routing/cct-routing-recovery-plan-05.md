---
page_type: decision
slug: cct-routing-recovery-plan-05
title: 'Failback lives in the supervisor loop, boundary-only'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-recovery/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

After every completed attempt (the task boundary — never inside
one), a routed run evaluates: preferred profile (the registry's
`preferred_profile`, promoted to enforced behavior) is `healthy`
AND `consecutive_probe_successes >= healthy_probes_required` AND
`now - healthy_since >= minimum_profile_dwell_sec` (dwell ALSO
gates the CURRENT ACTIVE profile — a switch is refused until the
active profile has been active at least the same dwell, so
flapping is contained on both sides) AND the repo
`recovery.auto_failback_enabled` is not false AND the promoted
`[policy] failback` is `auto` → the attempted-set entry for the
preferred profile is cleared and selection naturally prefers it
the boundary target is set to preferred and fed through B's same
selector (no second eligibility implementation);
the switch is journaled `routing_failback`. With `failback =
"operator"` or the repo restriction, the run stays on the
fallback and journals why. Hysteresis is therefore enforced at
the CONSUMPTION point, not inside the store.
