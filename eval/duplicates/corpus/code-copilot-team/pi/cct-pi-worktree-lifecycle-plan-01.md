---
page_type: decision
slug: cct-pi-worktree-lifecycle-plan-01
title: 'Lifecycle model'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-worktree-lifecycle/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

→ controller/`pi-code worktree create` provisions
pre-spawn; the extension validates/attaches (not create-and-switch).
