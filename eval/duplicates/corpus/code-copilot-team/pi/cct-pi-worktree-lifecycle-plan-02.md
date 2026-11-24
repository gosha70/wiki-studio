---
page_type: decision
slug: cct-pi-worktree-lifecycle-plan-02
title: 'Isolation failure'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-worktree-lifecycle/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

→ not warn-only: set state `invalid` and **block**
edit/write/bash at the existing `tool_call` gate (review #1).
