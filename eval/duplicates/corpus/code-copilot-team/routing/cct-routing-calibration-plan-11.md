---
page_type: decision
slug: cct-routing-calibration-plan-11
title: 'The two labeled E1 evidence additions'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-calibration/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Published evidence sets
gain two manifest-bound, schema'd, scrubbed-at-write artifacts,
derived at publication from the SAME sources the set already
binds:
`task-descriptors.json`: the scenario's declared trial count,
plus per task — the declared §12 task class (closed vocabulary:
one-file, multi-file feature, refactor, reproduced bug,
integration, negative control), the route class in force, and
the declared file-scope size; derived from the executed scenario
configuration (bound by `preset_digest`).
`profile-policy.json`: per profile of the executed registry —
`capability_tier` and roles; derived from the executed registry
at publication (bound by `registry_digest`).
Both are validated in staging, hashed into `manifest.artifacts`,
covered by `validate_evidence_set`'s binding checks, and served
through the E2 artifact surface (their locators become
followable). Sets published before this addition lack them: E3
treats such sets as UNLABELED for features/tiers (their tasks are
`insufficient_data` as queries and excluded from pools/G2) —
never guessed at. Existing E1 metric definitions, selectors, and
report semantics are untouched.
