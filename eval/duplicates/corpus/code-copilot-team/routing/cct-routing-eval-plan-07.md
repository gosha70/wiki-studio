---
page_type: decision
slug: cct-routing-eval-plan-07
title: 'New artifact: `routing-run.schema.json`, versioned from day one'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-eval/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

It carries `schema_version`, preset digest, registry digest,
pinned task-set revision, the injected event stream, and per-task
routing decisions in the vocabulary `explain` already speaks
(candidates considered with per-candidate verdict and reason,
selected profile, requested and effective model, sanitized upstream
endpoint, failure classification, provisional/reconciliation
outcome). The three existing schemas are extended by reference, not
edited.
