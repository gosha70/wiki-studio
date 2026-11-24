---
page_type: decision
slug: cct-pi-sandbox-hardening-plan-04
title: 'Handoff mechanism'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-sandbox-hardening/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

CLI-computed unset list (`pi-code env scrub-list`),
single TS pattern source, fail-closed when the call fails while scrub is
enabled.
