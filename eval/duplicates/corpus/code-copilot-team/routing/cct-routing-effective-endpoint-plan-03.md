---
page_type: decision
slug: cct-routing-effective-endpoint-plan-03
title: 'stays opportunistic'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-effective-endpoint/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

No standardized provider-reported
effective-upstream signal exists across these CLIs; the same gap is
visible upstream, where `codex exec --json` does not expose a
provider-reported served-model identity either. Nothing here depends on
O3, and it may become available later.
