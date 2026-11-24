---
page_type: decision
slug: cct-pi-worktree-lifecycle-plan-03
title: 'Path'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-worktree-lifecycle/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

→ namespaced `<repo-parent>/.cct-worktrees/<repo-name>/<worker-id>`;
explicit `CCT_WORKER_PATH` still validated.
