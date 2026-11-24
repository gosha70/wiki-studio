---
page_type: decision
slug: cct-routing-shadow-plan-11
title: 'adds no runtime authority'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-shadow/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

No new
key the router reads, no policy surface, no code path that
changes a routing decision. Everything E2 adds is downstream of
E1's artifacts, which are downstream of execution. This is what
keeps the #109 acceptance box — "learned routing remains
shadow-only until explicit calibration gates are met" — checked
by construction, and it is proven the same way E1 proved it:
routing suites pass unmodified, diff guard holds.
