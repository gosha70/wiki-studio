---
page_type: decision
slug: cct-routing-shadow-plan-02
title: 'gains ONE production orchestration entrypoint that publishes the complete evidence set — the labeled E1 change'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-shadow/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Today
`run_hybrid_scenario` publishes only `routing-runs.jsonl`;
`build_matrix` and `build_report` have no production callers, and
NO fixed-profile executor exists (`SupervisorRunner.run_task`
invokes the router and harvests `mode: "cct_router"` only). T1
adds, in `routing_eval`:
**`run_profile_cell(task, profile_id, trial, seed, events)`** —
the fixed-profile matrix executor. The launch BRIDGE is the
production supervisor itself under STAGE-SPECIFIC derived
registries — one profile per invocation, so "pinned" is
mechanically true rather than hoped: roles are not mutually
exclusive in the registry grammar, and a two-profile registry
can legally let the production selector pick the reconciler as
builder (both holding bounded-build), mis-attributing or
un-executing the cell. Instead: the BUILDER invocation runs
under a derived registry containing ONLY the pinned profile's
table entry (copied byte-for-byte from the declared full
registry) with route classes admitting exactly it; for
delegate-class cells the RECONCILIATION invocation runs
under a second derived registry containing ONLY the declared
Tier-1 reconciler's entry. Profile-to-environment translation
(provider endpoints, credential references, tool profiles) and
T2's event seam run through the same `cooldown-supervisor.sh`
code path production uses, never a reimplemented launcher.
Ordinary tasks execute as `build`; delegate-class tasks execute
the delegation lifecycle as `bounded-build` — matching the
eligibility authority's role split exactly — and the SEVEN-field
executed-identity parity assertion runs INDEPENDENTLY on each
lifecycle leg (builder leg against the pinned profile's
fingerprint entry; reconciliation leg against the reconciler's
declaration). Each cell gets a CLEAN context (fresh
worktree through the same adapter lifecycle — provision →
prepare_task → install_dependencies — and the same freshness
refusals the router arm gets). IDENTITY PARITY IS
PINNED BY TEST: the launch-environment wiring journaled for the
pinned profile equals production's for the same profile, and
ALL SEVEN executed identity fields (profile id, backend,
provider, requested model, effective model, tool profile,
sanitized endpoint) are verified against the matrix
fingerprint's execution_identity entry. The matrix fingerprint
continues to carry the DECLARED full registry's digest — the
derived registry is an execution mechanism whose profile entry
must match the full registry's declaration, verified. Harvest
is a `mode: "profile_sweep"` routing-run-shaped record converted
to the matrix `Cell` (verifier outcome, regressions, scope,
repair, intervention, cost with provenance).
**`publish_evidence_set(config, registry_path, runner, …)`** —
from ONE validated run context: (a) the hybrid scenario (the
router arm); (b) the matrix sweep via `build_matrix` with
`run_profile_cell` as executor — every ELIGIBLE
`(task, profile, trial)` executed, ineligible tuples
materialized as unexecuted cells exactly per `build_matrix`'s
existing contract (eligibility from the derived authority
context, the registry's role + tier_order predicate); (c) the
control selections with the declared selectors under that same
context; (d) `build_report`; then (e) SET-ATOMIC publication
with CLOSED crash and duplicate semantics: artifacts are written
into a HIDDEN sibling staging directory on the same filesystem
(a dot-prefixed name discovery structurally excludes), validated
there (schemas + manifest bindings + fingerprint agreement — the
same checks the E2 loader runs, manifest written last), then
published by ONE atomic rename to the set-id-named target. If
the target exists: byte-identical content verifies and returns
the existing set as an idempotent no-op; differing content at
the same id REFUSES — never an overwrite. Stale staging
directories are cleaned only after an owner check (age + no
live publisher). A failure at any step leaves no DISCOVERABLE
partial set and a rerun succeeds; fault-injection regressions
prove it after each publication step.
Per #261's own rule this is an E1 change, made here, explicitly
labeled, with its own tests. E2 reads persisted artifacts only and
NEVER calls selectors, quality_fn, or build_report.
