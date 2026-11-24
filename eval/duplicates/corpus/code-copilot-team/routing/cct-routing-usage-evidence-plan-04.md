---
page_type: decision
slug: cct-routing-usage-evidence-plan-04
title: 'aliases are fixed by observation'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-usage-evidence/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The accepted key names come
from the three shipped backend parsers, not from what an API might
plausibly emit. Codex reports `cached_input_tokens` and no USD; Claude
Code reports `total_cost_usd` and `cache_creation_input_tokens`; pi
reports `cache_read_tokens`. Guessing extra aliases would be inventing
contract.
