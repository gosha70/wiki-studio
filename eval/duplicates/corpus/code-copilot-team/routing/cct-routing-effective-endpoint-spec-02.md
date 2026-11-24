---
page_type: decision
slug: cct-routing-effective-endpoint-spec-02
title: 'is REJECTED as architecturally insufficient, not merely expensive'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-effective-endpoint/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

A proxy between CCT's CLI and `localhost:8787` proves the
CLI connected to `localhost:8787`. It cannot see the *later* hop the
gateway makes to Anthropic, DeepSeek or OpenAI. Making O2 literal would
require CCT to instrument the gateway's outbound connection too, which
for an arbitrary remote gateway is impossible. It is not a general
solution at any price.
