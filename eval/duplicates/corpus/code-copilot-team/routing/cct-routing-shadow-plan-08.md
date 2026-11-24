---
page_type: decision
slug: cct-routing-shadow-plan-08
title: 'Redaction: consume-verbatim, prove the chain'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-shadow/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

E1 artifacts are
write-time-scrubbed; E2 renders them verbatim and derives prose
only from figures and closed vocabularies, never from free text it
composes out of un-scrubbed sources. The regression chains E1's
boring-credential fixture (registry credential_env + echoed value)
through evidence-set publication into the analytics API and
asserts no payload carries the value; the API never serves the raw
registry, any absolute path, or any file outside the evidence set.
