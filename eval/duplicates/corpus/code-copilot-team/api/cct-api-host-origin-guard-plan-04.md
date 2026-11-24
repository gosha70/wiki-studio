---
page_type: decision
slug: cct-api-host-origin-guard-plan-04
title: 'the Origin check applies to ALL non-GET methods (POST/PUT/PATCH/DELETE), not a hand-maintained route list.'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/api-host-origin-guard/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

the Origin check applies to ALL non-GET methods
(POST/PUT/PATCH/DELETE), not a hand-maintained route list. *(Recommend —
a list would drift as routes are added; method-based is closed by
default.)*
