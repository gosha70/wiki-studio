---
page_type: decision
slug: cct-routing-profile-foundation-plan-02
title: 'Closed profile shape'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-profile-foundation/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Required: `id`, `backend`, `provider`,
`model`, `capability_tier` (`tier1|tier2`), `priority` (positive
integer), `quota_pool`, `roles` (subset of
`build|reconcile|land|bounded-build`), `tool_profile`,
`data_policy` (`approved-cloud|local-only`), and exactly one of
`credential_mode` | `credential_env`. Optional: `protocol`, and at
most one of `base_url` (absolute http(s)) | `base_url_env`.
`backend` must be one of the known harness backends
(`claude-code|codex|pi` — one constant list, exported by the lib,
aligned with the benchmark backend names). Unknown keys are refused
by name. Duplicate `id` is refused. `[policy]` and
`[route_classes.*]` are closed the same way; a route class's
`tier_order` may reference only known tiers.
