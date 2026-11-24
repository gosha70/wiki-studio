---
page_type: decision
slug: cct-routing-tier2-delegation-plan-01
title: 'Task route metadata is a constrained artifact, validated like everything else'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier2-delegation/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`specs/<feature>/routing-tasks.yaml` uses the
same constrained two-level YAML dialect as `verification.yaml`
(reject-never-approximate; `schema_version: 1` the sole root
scalar beside `tasks:`). Per task: `id` (stable, unique),
`route_class` (closed: `primary_only|tier1_only|tier2_fallback|
tier2_preferred`), `outcome` (one line, non-empty), `allowed_files`
(exact repo-relative paths or single-directory globs; must resolve
inside the repo root), `fr_refs` (each must exist in the feature's
`verification.yaml` with at least one deterministic `test`
verifier), `depends_on` (task ids in the same file; acyclic),
`forbidden_categories` (subset of the safety-floor vocabulary,
additive narrowing only), `reorderable` (bool). A new
`scripts/lib/routing-tasks.sh` (`rk_*`) owns parse + validation +
lookup; `cct routing validate` gains the artifact when present. A
task absent from the file, or the file absent entirely, resolves
`tier1_only`. Unknown keys, unknown route classes, dangling
`fr_refs`, unknown `depends_on`, dependency cycles, and
path-escaping `allowed_files` are named refusals.
