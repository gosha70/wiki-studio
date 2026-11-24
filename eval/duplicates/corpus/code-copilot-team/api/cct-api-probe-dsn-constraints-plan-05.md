---
page_type: decision
slug: cct-api-probe-dsn-constraints-plan-05
title: 'the allowlist is loopback + the host parsed from the CONFIGURED DSN only.'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/api-probe-dsn-constraints/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

the allowlist is loopback + the host parsed from the
CONFIGURED DSN only. Config-declared extra hosts are deliberately deferred
until someone needs them. *(Recommend — matches the recorded decision.)*
