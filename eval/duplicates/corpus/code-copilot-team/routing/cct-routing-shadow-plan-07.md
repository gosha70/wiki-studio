---
page_type: decision
slug: cct-routing-shadow-plan-07
title: 'No execution authority — enforced, not asserted'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-shadow/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Recommendations are derived at read time and served from the API;
when cached, the cache lives under the analytics store only. The
guard is executable, two ways: (a) E1's diff-guard test extends to
this branch (production routing files byte-unchanged); (b) a new
guard asserts no production routing script (`scripts/lib/routing-*`,
`routing-cli.sh`, `cooldown-supervisor.sh`) references the
recommendation schema, module, or storage paths, and that
`session_analytics.routing_evidence` writes only under the
analytics store.
