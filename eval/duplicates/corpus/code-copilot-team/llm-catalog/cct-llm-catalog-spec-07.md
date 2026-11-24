---
page_type: decision
slug: cct-llm-catalog-spec-07
title: 'Unverified launches'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/llm-catalog/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Refuse by default; `--allow-unverified`
launches with a notice, never records `supported`, and marks the
stamp; `cct llm test` is the one exempt path, or no first record
could ever exist. The earlier recommendation (launch with a notice)
was withdrawn: a notice is not a gate. Recommended: refuse by
default. **Ruled 2026-11-10 by the owner: accepted as recommended.**
