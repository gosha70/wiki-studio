---
page_type: decision
slug: cct-pi-team-controller-plan-02
title: 'Canonical root'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-team-controller/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

→ `resolveTeamRoot` via `primaryRepoRoot(cwd)`,
**fail-closed** (no `?? cwd`); unresolved ⇒ refuse + `team.root-unresolved`.
