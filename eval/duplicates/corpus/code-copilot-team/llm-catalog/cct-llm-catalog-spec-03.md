---
page_type: decision
slug: cct-llm-catalog-spec-03
title: 'Three files'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/llm-catalog/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`llms.toml` is new and separate; `routing.toml`
references it in G; `providers.toml` stays the reviewer profile.
Recommended: separate. **Ruled 2026-11-10 by the owner: accepted as recommended.**
