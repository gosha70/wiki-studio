---
page_type: decision
slug: cct-routing-tier2-delegation-plan-08
title: 'Selection legality — the tier requirement is never weakened'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier2-delegation/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`rt_select` gains an OPTIONAL route-class argument (absent →
B's behavior byte-identical: tier2 filtered unconditionally).
With a route class: `primary_only` admits only the
highest-priority tier1 candidate's profile; `tier1_only` = B's
filter; `tier2_preferred` orders eligible tier2 candidates first,
tier1 as fallback. `tier2_fallback`'s unlock predicate is pinned
to B's AUTHORITATIVE selector output shapes — C never inspects
`considered[]` (frozen as evidence-only) or reasons independently
about whether Tier-1 is "really unavailable":

`selected != null` → run Tier-1;
`selected == null`, `earliest_retry != null`, `terminal_reason
== null` (temporary exhaustion) → wait to `earliest_retry`,
select again — Tier-2 does NOT unlock;
`selected == null`, `earliest_retry == null`, `terminal_reason
== routing_no_eligible_profile` (permanent exhaustion) → the
Tier-1 candidate set is permanently empty; Tier-2 may unlock.

Terminal outcomes from an ACTUAL Tier-1 attempt are never
transformed into a fallback opportunity: `denied`, `unknown`,
model-identity mismatch, reviewer-independence refusal, crash
ambiguity (`routing_attempt_indeterminate`) — all remain terminal
per B; none becomes "Tier-1 unavailable, therefore Tier-2". All
three B output shapes and the total order are unchanged within a
tier. A `tier1_only`/`primary_only` task can never resolve a
tier2 profile even as sole candidate; exhausted Tier-1 with no
eligible Tier-2-safe packet parks per B.
