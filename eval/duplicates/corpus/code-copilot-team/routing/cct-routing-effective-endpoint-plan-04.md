---
page_type: decision
slug: cct-routing-effective-endpoint-plan-04
title: 'is not "configured is good enough."'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-effective-endpoint/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

That framing would recreate
the exact semantic mistake the audits caught, in new wording. The
amendment replaces an unimplementable observation requirement with a
stronger TRUTHFULNESS contract: record the configured origin *with its
provenance*, and carry an explicit effective-upstream verification
state that is never satisfied by a configured value.
