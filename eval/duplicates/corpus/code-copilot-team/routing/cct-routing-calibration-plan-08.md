---
page_type: decision
slug: cct-routing-calibration-plan-08
title: 'Configuration, not constants — including the policy source'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-calibration/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

New keys through the existing layering (`config_data/defaults.json`
< user config < env): `routing_calibration_root`, gate thresholds
(`min_sufficiency`, `min_tasks`, `min_trials`, `min_sets`,
`min_coverage`, `max_false_downgrade_rate`), classifier parameters
(`k`, `k_min`, `distance_metric`, `vote_epsilon`), `tier_floor`,
and `policy_source`. `tier_floor` is a CLOSED vocabulary validated
where the policy is assembled (a mistyped floor refuses with
CalibrationError, never a KeyError from inside recommendation);
`policy_source` is the path of the operator's CURRENT routing
policy declarations (the registry file or an exported policy
document) from which per-profile tier/role/security eligibility is
read and whose canonical digest enters `policy_id`. No default
value lives in Python source; the policy source is read, never
written.
