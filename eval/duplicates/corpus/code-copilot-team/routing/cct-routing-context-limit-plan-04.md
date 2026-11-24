---
page_type: decision
slug: cct-routing-context-limit-plan-04
title: 'one numeric-extraction pattern, named and separate'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-context-limit/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The
observed value comes from its own named pattern applied ONLY to
evidence already classified `invalid_request`, never from a free scan
of arbitrary output. A number appearing in an auth or transport failure
is not a context limit. Vague overflow wording ("prompt is too long"
with no number) records null and changes nothing — rule 5.
