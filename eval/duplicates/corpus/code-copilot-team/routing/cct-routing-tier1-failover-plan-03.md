---
page_type: decision
slug: cct-routing-tier1-failover-plan-03
title: 'Class→action mapping — TOTAL, exactly one place'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier1-failover/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

A new
`scripts/lib/routing-actions.sh` maps the frozen taxonomy to
supervisor behavior. The supervisor calls increment A's
`rr_result` over the SAME captured output the legacy regex read;
the legacy `USAGE_PATTERN` grep result is recorded into the
normalized result's evidence as fallback confidence only. The
table is NORMATIVE and total — every cause freezes scope, durable
state change, same-profile retry budget, whether another candidate
may be selected, re-eligibility, and the exhaustion/terminal
reason; the implementation may not invent a fallback the table
does not name. TIMING VALUES ARE NOT COMPATIBILITY SURFACE: B uses
named deterministic default cooldowns for temporary causes — cause
scope, action, retry CARDINALITY, and the rule that expiry returns
a profile/pool to `unknown` are normative; the literal seconds
(`RA_*_SEC` constants in the actions lib, current values below,
journaled whenever applied and covered by tests) are
implementation defaults that may be retuned from observed provider
behavior without a spec revision. They are not configuration in
increment B either — a config knob, if ever wanted, takes the
refused→implemented→tested promotion path.

The `routing_*` terminal reasons below form a CLOSED
machine-readable enum, defined once in the actions lib — cause (A's
observation), action (B's response), and terminal reason (why the
supervisor finally refused/parked) are three different things, and
no call site may assemble a reason dynamically (`routing_${class}`
is forbidden: a new A failure class must never silently create a
new B park reason). The journal may carry richer text BESIDE the
enum value. `routing_attempt_indeterminate` stays distinct from
exhaustion — crash ambiguity is not "no usable candidates".

| cause | scope | durable state | same-profile retries | select next? | re-eligibility | terminal reason |
|---|---|---|---|---|---|---|
| `quota_exhausted` | POOL | pool cooldown `until reset_at`; when `reset_at` is absent or malformed, `RA_QUOTA_FALLBACK_COOLDOWN_SEC` (default 3600) journaled as "reset evidence absent — bounded fallback cooldown" | 0 | yes (a different pool only) | time decay → `unknown` | `routing_pool_exhausted` naming pool + until |
| `rate_limited` | profile | none on the FIRST occurrence; after the budget, profile cooldown until `retry_after_sec` (else `RA_RATE_COOLDOWN_SEC`, default 120) | exactly ONE same-profile retry per supervised attempt, after `retry_after_sec` (else `RA_RATE_RETRY_DELAY_SEC`, default 60) | yes, after the budget | time decay → `unknown` | `routing_rate_limited` |
| `unavailable` | profile | after the budget, profile cooldown `RA_UNAVAILABLE_COOLDOWN_SEC` (default 300) | exactly ONE retry after `RA_UNAVAILABLE_RETRY_DELAY_SEC` (default 30) | yes, after the budget | time decay → `unknown` | `routing_provider_unavailable` |
| `transport` | profile | after the budget, profile cooldown `RA_UNAVAILABLE_COOLDOWN_SEC` (default 300) | exactly ONE retry after `RA_UNAVAILABLE_RETRY_DELAY_SEC` (default 30) | yes, after the budget | time decay → `unknown` | `routing_transport_failure` |
| `auth` | profile | profile DISABLED, never auto-decays | 0 | yes | operator action only (increment D adds operator-requested probes) | `routing_auth_failure` |
| `invalid_request` | ATTEMPT-LOCAL | NONE — the profile joins this unit's attempted-set as incompatible; no circuit write, no provider penalty (a request-local cause must never poison a profile for unrelated future work) | 0 | yes | next supervised unit starts clean | `routing_task_incompatible` |
| `denied` | run | none | 0 | NO — never rerouted around | n/a | park/terminate `routing_policy_denied` (#190 semantics) |
| `execution` | not an availability event | none | n/a (router takes no action) | NO — the existing breaker path owns disposition | n/a | existing #190 semantics, unchanged |
| `unknown` | run — FAIL CLOSED | none | 0 | NO | n/a | park/terminate `routing_unknown_failure` |
