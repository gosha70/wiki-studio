---
page_type: decision
slug: cct-routing-usage-evidence-plan-03
title: 'the cost cap is not a usage source'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-usage-evidence/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The driver's
`.totals.cost_usd` / `.totals.cost_estimated_usd` and the unmetered
estimate path are budget accounting, not observation. Nothing here
reads them. This is the specific "satisfying the criterion by
implication" the audit refused, so it is a named prohibition rather
than an oversight to avoid.
