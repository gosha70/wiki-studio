---
page_type: decision
slug: mk-memkernel-0-7-release-b-exit-plan-01
title: 'Order'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-release-b-exit/plan.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

Release memkernel 0.7.0 first, so the run uses released wheels as #48 asks: script PR, then the
0.7.0 release, then the recorded run. Recommended. The alternative records against a built wheel of `main`,
which would not be "released".
