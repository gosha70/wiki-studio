---
page_type: decision
slug: cct-routing-context-limit-plan-08
title: 'That evidence was invalid'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-context-limit/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The 18 failures were an unbound-variable
crash — `PKT_MINCTX` is referenced under `set -euo pipefail` and was
never initialized on the reconcile path — not a semantic signal about
reconciliation at all. A shell crash was read as a design finding.
`PKT_MINCTX` is now initialized globally, and with that fixed,
reconcile filtering passes.

On the merits the owner's call is correct: FR-F3 and the owner rule
attach the minimum to the TASK, not to a role, so an undeclared or
undersized reviewer is ineligible for exactly the reason a builder
would be. Both paths resolve the requirement through the same
fail-closed helper.
