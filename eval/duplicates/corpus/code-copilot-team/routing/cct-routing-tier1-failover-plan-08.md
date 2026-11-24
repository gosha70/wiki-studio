---
page_type: decision
slug: cct-routing-tier1-failover-plan-08
title: 'Identity + independence'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier1-failover/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The supervisor exports the active
profile identity to the driver
(`CCT_ROUTING_PROFILE/BACKEND/PROVIDER/MODEL...`); the driver
records it in the run ledger and review-request context, and the
summary/analytics fields gain additive identity columns. After
every switch the supervisor re-evaluates reviewer independence:
it resolves the gating reviewer's provider+model (providers.toml,
read-only) and on collision with the active builder follows #190
disposition (park attended / terminate unattended; advisory
journals and continues). providers.toml semantics are untouched.
