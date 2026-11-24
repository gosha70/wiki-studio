---
page_type: decision
slug: cct-memkernel-integration-plan-01
title: 'Single on-demand rule replaces per-agent GCC sections'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/memkernel-integration/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

all memory instructions live in `shared/rules/on-demand/memkernel-memory.md`. Agents reference this rule with a 2-line section. No conditional logic per agent.
