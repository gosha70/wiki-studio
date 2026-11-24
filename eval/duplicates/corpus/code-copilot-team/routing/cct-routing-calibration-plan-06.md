---
page_type: decision
slug: cct-routing-calibration-plan-06
title: 'Held-out evaluation: leave-one-task-out, leakage-free, durable'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-calibration/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

For every labeled corpus task: remove ALL of that task's records
and cells from the neighbor pool (across every set), fit
normalization bounds on the REMAINING pool (per fold), predict,
compare to the E2 truth. `evaluation-report.schema.json` (v1): the
split definition, per-task `{predicted, truth, downgrade_flag}`,
aggregate agreement, the false-downgrade numerator/denominator/
rate, the `unevaluable` count, `corpus_id`, `policy_id`, and the
full policy echo. Written atomically (tmp + rename +
pre-rename schema validation) into the analytics-owned
`routing_calibration_root` — never into an E1 evidence root.
