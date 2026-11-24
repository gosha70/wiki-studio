---
page_type: decision
slug: cct-llm-catalog-spec-05
title: 'Bindings'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/llm-catalog/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Explicit bindings only; `<llm>` resolves through
the one explicit binding for `(harness, llm)`, `<llm>@<binding>`
disambiguates. Inferred bindings were rejected in review because
records and stamps need a stable binding key. Recommended:
explicit only. **Ruled 2026-11-10 by the owner: accepted as recommended.**
