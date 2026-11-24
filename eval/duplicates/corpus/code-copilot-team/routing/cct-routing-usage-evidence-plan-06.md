---
page_type: decision
slug: cct-routing-usage-evidence-plan-06
title: 'schema compatibility follows increment F'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-usage-evidence/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The block is
additive and optional in schema version 1, so pre-G records stay valid;
the runtime boundary requires it on newly produced documents and
refuses an unknown future version rather than reading it optimistically.
