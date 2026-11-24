---
page_type: decision
slug: cct-routing-context-limit-plan-05
title: 'observations are additive state'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-context-limit/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

A new top-level
`observations` key in `routing-state.json`, deliberately NOT added to
`rs_read`'s shape validation: an existing state file without it must
keep loading, absent meaning "no observations". Adding it to the shape
check would refuse every live state file on upgrade.
