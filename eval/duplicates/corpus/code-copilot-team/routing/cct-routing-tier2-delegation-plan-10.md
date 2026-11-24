---
page_type: decision
slug: cct-routing-tier2-delegation-plan-10
title: 'Task-addressed explain closes A''s recorded deviation'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier2-delegation/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`cct routing explain --feature <id> --task <task-id>` resolves
route class + safety-floor evaluation from `routing-tasks.yaml`
and renders A's candidate table for that route class. It stays
PURE configuration resolution (A's must-not list: no network, no
state writes — proven by the same PATH-shim + byte-identity
harness); it reads the two artifacts read-only. `--task` without
`--feature`, an unknown task id, or a missing artifact are named
refusals.
