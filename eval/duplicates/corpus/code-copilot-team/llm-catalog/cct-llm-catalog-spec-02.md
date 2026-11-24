---
page_type: decision
slug: cct-llm-catalog-spec-02
title: 'User home'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/llm-catalog/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`~/.code-copilot-team/` for the catalog, the
compatibility records and the stamps, through one helper so #411
moves them together. Alternative: wait for #411. Recommended:
proceed now. **Ruled 2026-11-10 by the owner: accepted as recommended.**
*Amended 2026-11-14:* #411 landed before slice A started, so the home
is `${CCT_HOME:-~/.cct}` through #411's resolver (FR-1 as amended).
