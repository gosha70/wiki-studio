---
page_type: decision
slug: cct-routing-shadow-plan-09
title: 'The figure-provenance gate'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-shadow/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Every numeric figure the API serves
carries an exact source: a JSON-Pointer-style reference into one
artifact, or a declared delta naming its two source pointers. The
gate parses each artifact ONCE (canonical parse), resolves every
pointer, and requires SEMANTIC equality of the parsed values
(float64 equality after one canonical parse — no lexical byte
comparison) for direct figures, and exact float64 equality with
the recomputed subtraction for deltas. A served figure with no
source pointer, an unresolvable pointer, or a value differing from
its source fails the gate.
