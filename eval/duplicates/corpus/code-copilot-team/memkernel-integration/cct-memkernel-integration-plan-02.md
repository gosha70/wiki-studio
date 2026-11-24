---
page_type: decision
slug: cct-memkernel-integration-plan-02
title: 'Direct Python hooks with two-layer shell guards'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/memkernel-integration/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

hooks import memkernel internals for actual checkpoint save/recall, wrapped in shell scripts that check both `command -v memkernel` AND `python3 -c 'import memkernel'`. The two-layer check catches broken installs (CLI on PATH but package not importable).
