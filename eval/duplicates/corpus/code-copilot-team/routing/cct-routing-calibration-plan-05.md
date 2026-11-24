---
page_type: decision
slug: cct-routing-calibration-plan-05
title: 'The classifier is FULLY specified — two conforming implementations cannot disagree'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-calibration/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`knn-recommendation.schema.json` (v1) carries `outcome` (the E2
closed trichotomy), `suggested` (arm+profile or null), `neighbors`
(each: evidence_set_id, task, distance, label, and the neighbor's
OWN evidence_refs in the closed E2 shape — one resolver serves both
surfaces), `k`,
`distance_metric`, and the policy identity. The normative rules:
*Encoding*: categorical features (task class, route class)
one-hot over their closed vocabularies; numeric features min-max
normalized to [0,1] with bounds fitted on the training fold
(query values clamped into [0,1]).
*Missing values*: a (set, task) lacking any required feature or a
defined label is EXCLUDED from the neighbor pool and, as a query,
is `insufficient_data` with the missing field named — no
imputation, ever.
*Distance*: L2 over the encoded vector (`distance_metric:
"l2_v1"`; changing it is a policy change via decision 3).
*Candidate filtering BEFORE ranking*: neighbors whose labeled
suggestion names a profile that is absent from the CURRENT
policy's declarations, below the tier floor, or ineligible under
the current security/role policy are removed before any distance
ranking (decision 8 defines the policy source).
*Neighborhood*: the `min(k, available)` nearest survivors; if
fewer than `k_min` survive, the recommendation is
`insufficient_data`.
*Vote*: distance-weighted, weight `1/(distance + epsilon)`
(epsilon from config), summed per outcome label.
*Ties and resolution*: equal weight sums resolve CONSERVATIVELY
to `no_change_recommended` (a tie never produces a switch). If
`switch_profile` wins, the suggested (arm, profile) is the
highest-weight switch-voting neighbor's suggestion (ties by
smaller distance, then set id, then task id); if that profile
fails the current-policy filter (registry drift between sets),
the result is `insufficient_data`, never a substitution.
*Determinism*: identical corpus bytes + identical policy ⇒
byte-identical output.
The kNN output renders BESIDE the E2 recommendation, clearly
labeled, and never replaces or reweights it.
