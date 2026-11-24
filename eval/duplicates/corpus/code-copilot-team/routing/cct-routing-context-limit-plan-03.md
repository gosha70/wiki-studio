---
page_type: decision
slug: cct-routing-context-limit-plan-03
title: 'fail-closed only where a requirement exists'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-context-limit/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

A task with no
`min_context_tokens` filters nothing, so every existing registry and
feature keeps behaving byte-identically. The fail-closed rule engages
only once someone states a requirement. This is what makes rule 2 safe
to adopt: it cannot retroactively strand an existing configuration.
