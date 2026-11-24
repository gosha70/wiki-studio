---
page_type: decision
slug: cct-routing-tier2-delegation-plan-09
title: 'Tier-1 reconciliation is a fresh gated session, not a rubber stamp — and independence must be POSITIVELY established'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier2-delegation/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`--reconcile <task-id>` (supervisor, same refusal rules) binds to
the SAME immutable packet and provisional result it promotes
(decision-4 validation steps 1–2 and the provenance check apply;
drift → `packet_provenance_drift`), selects a Tier-1 profile
holding the `reconcile` role (registry vocabulary from A; role
absent → named refusal), and evaluates B's reviewer-independence
gate against the packet's BUILDER identity — reusing B's evaluator
unchanged but applying a STRONGER C-specific disposition, because
reconciliation is the promotion boundary:

`independent` → reconciliation may proceed;
`not_independent` → fail closed, named
`reconcile_not_independent` — cannot promote;
`unevaluable` → fail closed, named
`reconcile_independence_unevaluable` — its OWN disposition,
never conflated with a collision; a Tier-2 change must never
become `accepted` precisely when the system cannot establish
that its reconciler is independent. (B's non-blocking
unevaluable disposition is unchanged for B's own flows.)

On `independent`, it launches a fresh session (a fresh B-style
supervised attempt per decision 6) with the patch, the packet, and
the verifier evidence. The reconciler may simplify or repair
WITHIN the packet's scope (decision 5 applies to its cumulative
diff: scope/safety → verifiers → verdict); the driver then re-runs
the packet verifiers and records `accepted | accepted_with_changes
| rejected` (closed) in the ledger — `rejected` reverts the
packet's diff (and its WIP commit via driver-owned revert commit).
Only `accepted`/`accepted_with_changes` flip the task from
`verified_provisional` to done-eligible. Reconciliation attempts
ride the same accounting/journal machinery as any attempt.
