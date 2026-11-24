---
page_type: decision
slug: cct-routing-eval-plan-03
title: 'The matrix is `task × profile × trial`, and its reuse is fingerprint-gated'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-eval/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

This is the decision that makes E1 affordable,
with three constraints that make it *valid*:

**Trials are a dimension, not an average.** One cell per
task/profile cannot support FR-E1-6's multiple trials. Cells are
keyed `(task, profile, trial)`, and trial seeds and injected-event
identity are paired across arms so every arm sees the same trial
under the same conditions.
**Only independent measures may be derived.** Control arms come
from independent cells, so they carry only per-task-independent
measures: verifier outcome, regressions, cost, elapsed time.
Sequence-dependent measures — reconciliation rework ratio, Tier-2
accepted unchanged, failback behaviour, switch-induced rollbacks —
exist only along a stateful run and are reported
`not_applicable` for derived arms, measured only for
`cct_router`.
**Reuse requires an exact match on every component of the
fingerprint**, which is the closed list:
`registry_digest` — the routing registry as parsed. Any
registry edit invalidates reuse.
`preset_digest` — covers trial count, trial seeds, the
injected event stream, and the arm set. Changed seeds cannot
reuse cells keyed by the same trial index.
`execution_identity` per profile — id, backend, provider,
requested model, effective model, tool profile, sanitized
endpoint identity.
`task_set_revision` — the pinned snapshot revision.
`toolchain_digest` — tool and environment fingerprint.

A mismatch in any component refuses reuse; stale cells are never
silently carried forward. The schema requires all five, and a
mismatch test exists per component.

Control arms are derived from a matching matrix exactly as
§Control selectors defines; only `cct_router` executes live,
because its choices depend on the event stream and real failure
classification.
