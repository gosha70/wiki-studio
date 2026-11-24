---
page_type: decision
slug: cct-routing-usage-evidence-plan-01
title: 'one price table, read not copied'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-usage-evidence/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Pricing comes from the
existing configured table (`session_analytics/config_data/defaults.json`
`.pricing.models`, overridable per the established config layering).
The routing shell reads it; it does not embed rates, extend the rate
schema, or add a second source of truth. This satisfies the repo rule
against hard-coded structured data and keeps a single pricing contract
for the whole system.
