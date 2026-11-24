---
page_type: decision
slug: cct-routing-tier1-failover-plan-02
title: 'B''s bounded unit is the supervised ATTEMPT'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier1-failover/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Task-level packets
arrive with increment C's task metadata; until then the supervisor
already operates in attempt granularity, and the driver's own
ledger provides resumability. The checkpoint (decision 5) makes
that unit durable and backend-neutral. The route class for B is
effectively `tier1_only`; Tier-2 profiles are filtered
unconditionally.
