---
page_type: decision
slug: cct-llm-catalog-spec-06
title: 'Probe reuse'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/llm-catalog/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Share the canary primitives and the tri-state
classification with `routing-probe.sh`; do not reuse routing's
accounting, caps or state runner. Recommended. **Ruled 2026-11-10 by the owner: accepted as recommended.**
