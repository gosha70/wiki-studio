---
page_type: decision
slug: cct-routing-calibration-plan-03
title: 'Reports bind to corpus AND policy'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-calibration/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`corpus_id = sha256(canonical JSON of the sorted consumed set ids)`.
`policy_id = sha256(canonical JSON of the full evaluation policy)`:
the feature-vocabulary version, k, k_min, distance metric,
weighting epsilon, normalization scheme, tier floor, the canonical
digest of the current security/role policy source, and
`max_false_downgrade_rate`. Evaluation and gate reports carry BOTH;
serving recomputes both from the live corpus and configuration and
marks any mismatch `stale: true` — a stale report renders with an
explicit stale state and satisfies no gate. An evaluation produced
under an old metric, floor, or policy can never pass G3–G5.
