---
page_type: decision
slug: cct-routing-usage-evidence-plan-05
title: '`unavailable` means nothing was reported, not "subscription"'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-usage-evidence/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Reconciled after review, because the first wording and the code
disagreed. The rule is about FABRICATION, not about billing model:

a USD figure the backend itself states on its authoritative result
event is recorded as `basis=reported`. `reported` asserts only that
the backend stated it — it makes no claim that the figure is a billed
marginal cost. Suppressing a number the backend actually reported
would discard real evidence;
where nothing is reported and nothing can be computed, the record is
`unavailable`. Subscription execution with no attributable
per-request cost is the common case, and it lands there naturally.

A `0.00` is never written for either case: zero would be a false claim
of a free request.
