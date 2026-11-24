---
page_type: decision
slug: cct-api-host-origin-guard-plan-03
title: 'tests point `TestClient` at `http://127.0.0.1:<port>` rather than adding `testserver` to the production default allowlist.'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/api-host-origin-guard/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

tests point `TestClient` at
`http://127.0.0.1:<port>` rather than adding `testserver` to the
production default allowlist. *(Recommend — keeps the shipped allowlist
tight; `testserver` in production config would be a small but real
widening, and a needless one.)*
