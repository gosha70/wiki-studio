---
page_type: decision
slug: cct-llm-catalog-spec-08
title: 'Endpoint quirks'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/llm-catalog/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`quirks = ["rejects-dynamic-tools"]` on the
endpoint drives the three #399 variables for selected launches and
enters the launch-identity digest; the declaration is never evidence; the
#399 notice stays for native launches. Recommended.
**Ruled 2026-11-10 by the owner: accepted as recommended.**
