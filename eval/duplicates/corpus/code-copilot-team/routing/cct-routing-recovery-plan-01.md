---
page_type: decision
slug: cct-routing-recovery-plan-01
title: 'State-store extension, same schema, closed vocabulary'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-recovery/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`routing-state.sh` keeps `schema_version: 1`; profile/pool entries
gain `next_probe_at`, `consecutive_probe_successes`,
`last_probe_at`, and `healthy_since` (all nullable; absent in
pre-D stores — reads treat absence as null, writes are additive).
The state set is CLOSED at `unknown | cooldown | disabled |
healthy | degraded | probe_due | probing`. Frozen read rules:
eligibility (rs_effective_info): `healthy` and `unknown` are
selectable exactly as B selects today (`unknown` keeps its
never-treated-as-healthy journal); `degraded | probe_due |
probing` are NOT selectable; `cooldown | disabled` unchanged.
B's pool-outranks-profile, decay-to-`unknown`, and fail-closed
read rules are untouched — the B suite passes unmodified.
`healthy` is VERIFIED-GOOD only within its dwell provenance
(healthy_since + the promoted dwell key); a stale `healthy`
decays to `unknown` like any cooldown expiry, journaled.
`probing` is a crash-visible in-flight marker, and an ABANDONED
marker is ABSENCE of evidence, never provider evidence (review
round 1): a tick that dies mid-probe leaves `probing` +
`next_probe_at`; the next tick journals
`routing_probe_abandoned`, sets the state to `unknown`,
schedules a fresh probe via the recovery backoff, and touches NO
failure streak or consecutive-success counter — a supervisor
crash is never attributed to the provider, and abandonment can
never produce `healthy` either.
The D recovery transition matrix is CLOSED and executable: its
ONLY edge into probe-qualified `healthy` is a verified canary
success reaching the threshold. B's inherited `rs_mark_success`
still records a genuinely successful full attempt as `healthy`
for byte-compatible history, but it carries no probe streak or
`healthy_since` and can trigger neither D wake nor failback.
