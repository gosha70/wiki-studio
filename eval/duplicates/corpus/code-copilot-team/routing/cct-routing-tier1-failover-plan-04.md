---
page_type: decision
slug: cct-routing-tier1-failover-plan-04
title: 'Circuit state store'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier1-failover/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`scripts/lib/routing-state.sh` owns
`~/.code-copilot-team/routing-state.json` (schema_version 1;
`profiles.<id>.{state,reason,failed_at,until,last_success_at}`;
`pools.<pool>.{state,reason,until}`): read-modify-write under an
exclusive lock directory (`routing-state.lock`, mkdir-based, stale
after a journaled timeout) with temp+rename atomic writes.
Pool cooldown OUTRANKS profile state at selection. Time-based
re-eligibility only: when `until` passes, the entry decays to
`unknown` (not `healthy` — B has no probes; the journal names the
decay so D's probe layer has a clean hook). `auth`-disabled and
`denied` never decay automatically.
