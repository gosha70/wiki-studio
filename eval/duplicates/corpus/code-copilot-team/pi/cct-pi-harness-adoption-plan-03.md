---
page_type: decision
slug: cct-pi-harness-adoption-plan-03
title: 'Dedicated non-recursive `peer-reviewer` profile + adapter script'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-harness-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Context

a CCT-enforced session reviewing another CCT-enforced session
would recurse gates; shell redirection in `providers.toml` is unsafe.

## Decision

built-in `peer-reviewer` profile (read-only tools, ephemeral
session, no SDD/teams/subagents/write, strict budgets) invoked via
`pi-review-provider {review_request}`; runner remains the artifact writer;
print-mode first, JSON/RPC typed contract later; exact flags validated
against the pinned Pi version.

## Consequences

provider capability stays `disabled` until this passes
acceptance (FR-028).
