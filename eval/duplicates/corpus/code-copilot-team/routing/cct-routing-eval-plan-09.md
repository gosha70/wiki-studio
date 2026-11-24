---
page_type: decision
slug: cct-routing-eval-plan-09
title: 'Insufficiency is a first-class outcome'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-eval/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

An arm that cannot run
records `insufficient_evidence` with a reason and is carried
through to the report as such. It is never rendered as zero, never
silently dropped from the Pareto set, and never allowed to satisfy
decision 6's control requirement.
