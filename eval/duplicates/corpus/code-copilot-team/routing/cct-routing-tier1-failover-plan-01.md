---
page_type: decision
slug: cct-routing-tier1-failover-plan-01
title: 'The seam is the supervisor, opt-in by flag'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier1-failover/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`cooldown-supervisor.sh --routing` activates the failover loop;
the flag additionally requires a validating registry and an
effective-enabled merge (with the repo `automation.json` when
present), else the supervisor REFUSES with guidance (never guesses,
never silently falls back to legacy). Without `--routing`, the
script's behavior is byte-identical to today, proven by the
existing suite passing unmodified. The driver stays
one-profile-per-attempt and is not taught about routing.
