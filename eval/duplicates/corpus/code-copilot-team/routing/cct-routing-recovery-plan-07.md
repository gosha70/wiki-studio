---
page_type: decision
slug: cct-routing-recovery-plan-07
title: 'Reconcile-on-recovery'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-recovery/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

At a failback boundary (decision 5
firing), before the next build attempt the supervisor iterates
pending `verified_provisional` ledger records and runs C's
reconcile flow for each (same code path as `--reconcile`, bounded
to ONE reconcile attempt per record per boundary). A reconcile
refusal/park follows C's semantics and is journaled; it parks the
current boundary with the failback marker left retryable. With no
pending records the boundary is a plain failback.
