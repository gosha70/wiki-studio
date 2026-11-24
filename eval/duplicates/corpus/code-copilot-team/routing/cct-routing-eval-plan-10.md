---
page_type: decision
slug: cct-routing-eval-plan-10
title: 'adds no runtime authority'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-eval/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

No new key the router reads at
execution time, no new policy surface, no code path that changes a
routing decision. Everything E1 adds is downstream of execution.
This is what makes E1 independently verifiable and what lets E2
depend on it as a stable evidence contract.
