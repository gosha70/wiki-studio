---
page_type: decision
slug: cct-routing-calibration-plan-04
title: 'Features are PRE-ROUTING only — the label''s ingredients never enter the query vector'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-calibration/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The E2 truth label derives from the
post-execution per-arm figures, so those figures (and any
post-execution outcome: costs, quality, regressions, reconciliation
state) are BANNED from the feature vocabulary. The closed,
versioned feature vector per (set, task) uses only information
available before routing, ALL of it from the decision-11
descriptors artifact: the declared task class (§12's closed
task-class vocabulary), the route class in force, the declared
file-scope size, and the scenario's DECLARED trial count (the
corpus property; the OBSERVED per-trial record count is an
execution observation and is never a feature).
Labels remain E2's own derivation (`derive_recommendations` outcome
suggested arm) — single-source ground truth. Feature
normalization is fitted on each training fold only (decision 6),
never on the full corpus.
