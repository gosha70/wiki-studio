---
page_type: decision
slug: cct-memkernel-integration-plan-06
title: 'Sync path upgraded'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/memkernel-integration/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`--sync` branch in setup.sh extended to copy hooks and merge settings, so existing installs pick up MemKernel on upgrade.
