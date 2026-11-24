---
page_type: decision
slug: cct-routing-context-limit-plan-06
title: 'the requirement is read from `routing-tasks.yaml`, not the packet envelope'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-context-limit/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Architecturally the packet is the immutable,
provenance-bound record of a task's constraints, and `route_class`
already lives there, so a context requirement belongs there too. It is
NOT put there because `RP_ENVELOPE_KEYS` is frozen and the envelope is
digest-bound: adding a key would change every packet digest and
invalidate existing packets. Instead the supervisor reads the value
from `routing-tasks.yaml` immediately AFTER `rp_provenance_check` has
verified `routing_tasks_sha256` against that exact file — so the bytes
are proven identical to the ones the packet was built from, and the
read is equivalent to reading the envelope without breaking it. If the
envelope is ever versioned for another reason, this value should move
into it.
