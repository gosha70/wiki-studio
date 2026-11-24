---
page_type: decision
slug: cct-routing-profile-foundation-plan-07
title: 'Inertness proof'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-profile-foundation/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

No edits to `auto-build-loop.sh`,
`cooldown-supervisor.sh`, or any reviewer path in this increment.
The sweep must show the driver suite byte-identical in behavior
(its suite passes unpinned-unchanged), and the new tests live in a
new `tests/test-routing-config.sh` with its own count pin.
