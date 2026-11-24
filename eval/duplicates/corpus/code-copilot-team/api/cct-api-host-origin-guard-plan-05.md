---
page_type: decision
slug: cct-api-host-origin-guard-plan-05
title: 'Host mismatch → `400` (Starlette''s built-in); disallowed Origin → `403` with a short constant message, no echo of the offending value.'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/api-host-origin-guard/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Host mismatch → `400` (Starlette's built-in);
disallowed Origin → `403` with a short constant message, no echo of the
offending value. *(Recommend.)*
