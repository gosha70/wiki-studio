---
page_type: decision
slug: cct-pi-harness-adoption-plan-06
title: 'Behavioral parity via neutral schemas + contract tests'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-harness-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

capabilities, agent manifests, lifecycle events, permission
policies get provider-neutral schemas under `shared/`; Claude-specific
resources are imported/mapped, not rewritten; the same fixture features run
through Claude Code and Pi and must agree on classifications, gates,
artifacts, and analytics semantics.
