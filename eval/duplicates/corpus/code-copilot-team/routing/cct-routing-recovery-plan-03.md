---
page_type: decision
slug: cct-routing-recovery-plan-03
title: 'Timing precedence + named backoff defaults'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-recovery/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`rb_next_probe_at` derives from, in order: the durable reset
evidence B already persists (provider reset_at, Retry-After);
subscription `rate_limits.*.resets_at` when the transcript carries
it; else bounded exponential backoff with jitter:
`RD_BACKOFF_BASE_SEC` (default 60) doubling to
`RD_BACKOFF_MAX_SEC` (default 3600), jitter ±`RD_JITTER_PCT`
(default 20) derived DETERMINISTICALLY from a hash of
profile-id + failure count (reproducible in tests; no wall-clock
randomness). All RD_* are named implementation defaults journaled
when applied — not configuration.
