---
page_type: decision
slug: cct-routing-eval-plan-01
title: 'The comparison unit is a routing policy, and it is a new preset kind — not a new candidate shape'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-eval/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Today a preset lists
`candidates[]`, each fixing a backend and model. E1 adds
`arms[]` under a `scenario: "hybrid-routing"` preset. Overloading
`candidates[]` would make every existing preset ambiguous; a
distinct key keeps the old contract byte-compatible and lets the
validator reject a preset that mixes the two.
