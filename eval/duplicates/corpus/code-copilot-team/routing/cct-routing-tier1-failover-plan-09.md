---
page_type: decision
slug: cct-routing-tier1-failover-plan-09
title: 'Exhaustion + caps'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier1-failover/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

No eligible profile: if the earliest
re-eligibility time fits inside the remaining wall-clock cap the
supervisor sleeps to it (journaled); otherwise FR-B8's
park/terminate names every profile's reason. All existing
attempt/wall/cooldown caps remain authoritative and are checked
before every launch, unchanged.
