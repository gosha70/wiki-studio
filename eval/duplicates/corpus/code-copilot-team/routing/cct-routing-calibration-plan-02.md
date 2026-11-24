---
page_type: decision
slug: cct-routing-calibration-plan-02
title: 'The gate contract: five §12 conditions, executable, versioned'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-calibration/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`benchmarks/schema/calibration-report.schema.json`,
`schema_version: 1`. Per gate: `{id, status:
pass|fail|insufficient_data, measured, threshold, evidence_refs,
reason}`; overall `calibrated = every gate pass`. The gates:
**G1 telemetry-complete**: over the corpus, the fraction of
router records with measured (non-insufficient) cost AND verified
effective-model identity; invalid_evidence sets are excluded from
the corpus and their count reported beside it. Threshold:
`min_sufficiency`.
**G2 labeled-volume**: counted over LABELED evidence only — a
(set, task) pair counts iff its E2-derived label is DEFINED
(outcome is not insufficient_data). Requires at least
`min_tasks` distinct labeled tasks, each reaching `min_trials`
trials WITHIN at least one single evidence set (trials never
aggregate across sets — cross-set aggregation would mix
fingerprints), across at least `min_sets` distinct contributing
sets. A corpus whose labels are all insufficient_data cannot
pass.
**G3 heldout-evaluated**: a CURRENT evaluation report exists —
current means BOTH its `corpus_id` and its `policy_id`
(decision 3) match the present corpus and configuration — and it
covers at least `min_coverage` of the labeled corpus tasks.
**G4 false-downgrade**: the current evaluation report's
false-downgrade rate (decision 7) is below
`max_false_downgrade_rate`.
**G5 floors-authoritative**: structural, three conjuncts — (a)
the operator's CURRENT effective policy (decision 8: tier floor
AND the security/role policy source) parses and declares a tier
floor; (b) the current evaluation report records zero
floor-violating or policy-violating kNN recommendations (the
recommender filters candidates against the CURRENT policy before
ranking — decision 5; a violation reaching a report is a bug
surfaced, never dropped); (c) the report's `policy_id` embeds the
digest of that same policy, so a policy change stales every
report (decision 3).
A gate whose inputs do not exist (no evaluation report, empty or
unlabeled corpus, stale report) is insufficient_data. Nothing
anywhere auto-acts on a gate.
