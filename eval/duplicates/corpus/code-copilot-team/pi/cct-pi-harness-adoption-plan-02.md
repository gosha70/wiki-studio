---
page_type: decision
slug: cct-pi-harness-adoption-plan-02
title: 'In-process trust gating; launcher stays trust-ignorant'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-harness-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Context

Pi 0.79.0 exposes `project_trust` and `isProjectTrusted()`
publicly; global/CLI extensions load before project trust resolves; the
first extension answering `project_trust` owns the decision.

## Decision

launcher never reads project CCT config; runtime observes
trust (defers ownership by default), gates every project-config load on
`isProjectTrusted()`, fails closed on unknown, requires restart after
mid-session `/trust`, warns on `defaultProjectTrust: "always"`.

## Consequences

no dependency on `trust.json` internals; minimum Pi
pinned at 0.79.0.
