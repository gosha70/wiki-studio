---
page_type: decision
slug: cct-routing-tier1-failover-plan-05
title: 'Checkpoint + the FROZEN crash-ordering contract'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier1-failover/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The durable
handoff document lives at
`.cct/auto-build/<feature>/routing/checkpoint-<attempt>.json`:
base commit, current HEAD, dirty flag, `git diff` sha256 + the
patch bytes as a sibling artifact, the FULL normalized result of
the failed attempt, prior profile id + requested/effective model,
transcript path, attempt/cooldown counters, and the attempted-set.
The ordering is NORMATIVE:

persist attempt-started (attempt id + selected profile),
launch exactly one FRESH child session,
persist the normalized terminal result,
atomically apply the circuit/pool action — IDEMPOTENT, keyed by
attempt id (state entries record `last_applied_attempt`, so
replaying checkpoint processing can never apply the same
failure action twice),
checkpoint the next selection.

A restart that finds attempt-started WITHOUT a durable terminal
result must NEITHER replay the attempt NOR fail over as though it
definitely failed — the child may have mutated the workspace; the
outcome is indeterminate. It parks/terminates with the named
reason `routing_attempt_indeterminate` and full checkpoint
provenance for the operator. The supervisor's existing feature
lock prevents concurrent duplicate runs; the checkpoint never
carries a session or conversation identifier — a new profile
always cold-starts its backend from repository + ledger state
(Scenario 4). This ordering matters more than session hygiene:
without it, crash recovery can duplicate agent side effects.
