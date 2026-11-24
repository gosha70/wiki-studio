---
page_type: decision
slug: cct-routing-calibration-plan-07
title: 'False downgrade, exactly — against the SAFETY BASELINE tier'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-calibration/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The baseline tier for a held-out task is: the tier of the TRUTH's
suggested profile when truth is `switch_profile`; the HIGHEST tier
the router actually engaged when truth is `no_change_recommended`
(tiers resolved from the set's persisted profile-policy
declarations, decision 11). Highest, because a chain is a
COMPOSITION, not a menu — a delegated task ran
[tier1 orchestrator, tier2 delegate] and recommending the tier2
profile DROPS the tier1 leg; taking the lowest would make every
delegated task structurally incapable of a false downgrade, which
is exactly the arc §12 targets, and it also restores symmetry with
the truth-switch branch. A prediction counts as a false downgrade
iff it is `switch_profile` to a profile of a LOWER tier than that
baseline. So kNN predicting Tier 2 while truth switches within
Tier 1 IS a false downgrade.

The denominator is JUDGED RECOMMENDATIONS only, and every
exclusion is reported separately: `unevaluable` (no label or no
features), `refused` (the recommender returned
`insufficient_data` — a refusal is not a recommendation, so
counting it would let an all-refusing recommender report 0.0 and
pass the gate), and `unresolved_tier` (a switch whose tier
comparison cannot resolve — unjudged, never judged safe).
`compared` = predictions produced; `evaluated` = compared minus
`unresolved_tier`; the rate is `false_downgrades / evaluated`,
None when nothing was judged. Refusals likewise do not count
toward G3 coverage — G3 asks how much of the corpus was actually
evaluated held-out.
