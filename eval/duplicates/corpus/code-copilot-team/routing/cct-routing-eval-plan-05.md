---
page_type: decision
slug: cct-routing-eval-plan-05
title: '`quality_fn: v1` orders arms; it does not redefine the metrics'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-eval/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

An earlier draft forbade combining the primary metrics while also
demanding one quality axis and a "per-row best" oracle — which is not satisfiable, because ordering a vector
requires a projection. The resolution is to make the projection
explicit, versioned, and clearly subordinate:

`quality_fn` is a named, versioned function over the primary
metric vector, used **only** for ranking arms and for the
oracle's per-cell choice. §quality_fn v1 defines it numerically;
nothing about the scoring policy is left to the implementer.
Every report states which `quality_fn` version produced its
ordering and carries the full metric vector beside it. The
scalar never appears without the vector.
**It admits only metrics applicable to every arm being
compared.** Sequence-dependent measures are `not_applicable` for
derived arms, so including one would make the arms incomparable —
which is why reconciliation rework is *not* a `quality_fn`
component or tie-break, despite an earlier draft using it as one.
**The oracle bounds quality, not cost.** The earlier assertion
that oracle cost is `<=` always-best's is dropped: a
quality-maximising choice may legitimately cost more. The only
invariant asserted is that oracle quality under the declared
`quality_fn` is `>=` every other arm on the same matrix. A
separate, explicitly-labelled `oracle_budget` arm — best quality
subject to a stated cost ceiling — may be reported alongside, and
is the only arm for which a cost inequality is meaningful.
