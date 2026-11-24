---
page_type: decision
slug: cct-routing-recovery-plan-09
title: 'Scope honesty'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-recovery/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

D adds no new terminal reasons (parked runs
still park per B/C); wake never bypasses caps — a woken supervisor
re-enters with its own attempt/wall budgets. The probe engine
never writes ledgers of supervised runs; ticks and supervisors
share only the circuit store, under its lock.
