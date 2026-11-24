---
page_type: decision
slug: cct-pi-team-controller-plan-04
title: 'Authz'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-team-controller/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

→ re-validated **inside the lock per mutation**: team-binding + active
actor; lead-only for assign/approve/activate/recover/close; `join`/`task` = any
active member; `create` = bootstrap; never cached; sole active lead can't leave
an open team.
