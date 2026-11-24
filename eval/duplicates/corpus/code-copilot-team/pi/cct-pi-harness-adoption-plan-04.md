---
page_type: decision
slug: cct-pi-harness-adoption-plan-04
title: 'Launcher symmetry with `claude-code`'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-harness-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`pi-code` mirrors `claude-code` for `init`/`sync`/peer-review
flags and the `CCT_PEER_*` env contract, reusing the existing scaffolder
and sync implementations rather than forking them.
