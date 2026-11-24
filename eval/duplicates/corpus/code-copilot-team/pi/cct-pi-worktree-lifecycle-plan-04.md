---
page_type: decision
slug: cct-pi-worktree-lifecycle-plan-04
title: 'Reconcile'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-worktree-lifecycle/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

→ run on every start inside the lock, **fail-closed** on an
untrustworthy/malformed listing (strict result-bearing parse) and
**primary-excluded**.
