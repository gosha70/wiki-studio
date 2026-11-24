---
page_type: decision
slug: cct-api-probe-dsn-constraints-plan-04
title: '`sqlite://` / `sqlite:///` (in-memory) is accepted: it touches no filesystem path and is what the test suite uses.'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/api-probe-dsn-constraints/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`sqlite://` / `sqlite:///` (in-memory) is
accepted: it touches no filesystem path and is what the test suite uses.
*(Recommend.)*
