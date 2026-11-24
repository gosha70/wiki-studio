---
page_type: decision
slug: cct-routing-tier1-failover-plan-07
title: 'Codex is NOT in this increment — B makes NO codex-support claim'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier1-failover/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The umbrella's B bullet names a Claude→DeepSeek→Codex
scenario. The architectural property (cross-BACKEND handoff from
durable state, no session reuse) is proven here with the pi
backend, which is already a first-class build backend;
DeepSeek-style profiles prove the cross-PROVIDER half on the
claude-code backend. A codex EXECUTION adapter for the driver is
real new surface (the benchmark's verified `codex exec` knowledge
transfers, but launch, result, review, and cost wiring are driver
work) and is its own child increment after B — REQUIRED to reuse
this increment's normalized attempt/result/checkpoint contracts
rather than growing a codex-special path. Flagged as a deviation
in the origin-alignment record.
