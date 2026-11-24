---
page_type: decision
slug: cct-routing-effective-endpoint-plan-02
title: 'is rejected as ARCHITECTURALLY INSUFFICIENT, not merely disproportionate'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-effective-endpoint/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

a correction to this plan's first draft, which
called it "the only option that genuinely answers the gateway case".
It is not. A proxy between CCT's CLI and `localhost:8787` proves the
CLI connected to `localhost:8787`; it cannot see the later hop the
gateway makes to Anthropic, DeepSeek or OpenAI. Making it literal would
require instrumenting the gateway's outbound connection, which for an
arbitrary remote gateway is impossible. So O2 fails on generality
first, and cost second — and building it would have added credential
and networking risk in exchange for a guarantee it could not give.
