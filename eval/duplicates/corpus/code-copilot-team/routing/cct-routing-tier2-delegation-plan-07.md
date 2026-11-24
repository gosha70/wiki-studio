---
page_type: decision
slug: cct-routing-tier2-delegation-plan-07
title: '`verified_provisional` is a ledger state that satisfies nothing'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier2-delegation/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

A packet passing scope + verifiers records
`verified_provisional` in the driver ledger with full evidence:
diff sha, per-verifier outputs, repair count, profile identity
(B's `routing_identity` shape). The driver MAY commit the packet
diff as a clearly-marked WIP commit (driver-owned git; pushing
stays under the repository's existing push policy — C adds no
auto-push). Every completion/phase/landing gate treats
`verified_provisional` as INCOMPLETE: a run whose remaining work
is all provisional ends parked/incomplete per #190 semantics, and
the unrouted ledger stays byte-identical (the provisional state
appears only for delegated tasks).
