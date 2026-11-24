---
page_type: decision
slug: cct-routing-shadow-plan-03
title: 'Report contract v1: versioned, schema''d, task-resolved, source-bound'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-shadow/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The
current report emits aggregate arm figures with no schema version,
no registry digest, no source identity, and no per-task
provenance — insufficient for E2 and unvalidatable under FR-E2-1.
The persisted report v1 ADDS (additively — no metric or gate
semantics change):
`schema_version: 1` and a NEW closed
`benchmarks/schema/report.schema.json` it validates against;
the FULL five-component fingerprint (registry digest, preset
digest, execution identity, task-set revision, toolchain
digest);
`source_artifacts`: sha256 of the canonical bytes of
`routing-runs.jsonl` and `outcome-matrix.json`, computed at
publication from the same bytes that were written — the binding
that makes an evidence set a SET (finding: co-location binds
nothing);
per-arm SELECTION provenance: the profile each control arm chose
per task (per `(task, trial)` for the oracle) — the selector
outputs build_report already verified, now emitted;
a per-task figure table: for every arm and task, the per-task
quality projection and per-task cost — AND the per-trial values
beneath them (each selected cell's quality projection and cost
per `(task, trial)`, and the router's per-trial equivalents) —
the intermediate values of E1's own declared aggregation
pipeline (per-cell → per-task → arm), emitted, not re-derived.
The per-trial values are what makes a non-hollow confidence
grade derivable (decision 5) without E2 computing anything;
the router per-trial values come from a NORMATIVE LIFECYCLE
FOLD (a labeled E1 correction — today router_cells_from_records
converts every record to a cell, so a delegated task's
provisional and reconciliation records double-weight that
task): each `(task, trial)` folds to EXACTLY ONE metric cell,
with a PER-COMPONENT contract — final-state evidence reduces
from the final leg, but process evidence unions across the
lifecycle (a clean reconciliation must never launder the
provisional leg's process signals out of Q):
| Component | Fold rule |
|---|---|
| verifier outcome (row 1) | the FINAL lifecycle outcome — the reconciled record's evidence for delegated tasks; the provisional leg never scores separately |
| lint/type/coverage/security regressions (rows 2–5) | FINAL-state semantics: the final leg's before/after evidence (they measure resulting state, not process) |
| scope violation (row 6) | UNION (OR) across all lifecycle legs |
| repeated repair (row 7) | computed over the CONCATENATED signature stream of all legs, then reduced — the same signature once per leg IS a lifecycle repeat |
| intervention (row 8) | UNION (OR) across all lifecycle legs |
| cost (row 12) | SUM across all legs under provenance homogeneity (any leg unpriced under the basis ⇒ the trial's cost is insufficient, never partial) |
| elapsed (row 13), where present | SUM across all legs, never silently one leg |
| routing chain | ordered concatenation across the legs |
Exact task × trial coverage — duplicate or missing folded
entries REFUSE the report. The SAME fold semantics govern
delegated `profile_sweep` cells, so cct_router and the
fixed-profile controls compare identical units. Pinned
discriminators: a provisional-leg intervention (or repeated
repair) with a clean reconciliation still lowers the folded Q;
the same repair signature once in each leg counts as a
lifecycle repeat (a per-leg-reduce-then-OR mutation
discriminates); the delegated task folds to ONE cell, not two.
