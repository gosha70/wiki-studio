---
page_type: decision
slug: cct-wiki-studio-adoption-plan-04
title: 'Installation coverage is explicit, not implied by adapter support'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-studio-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Root setup from a checkout manages wiki-studio for every selected adapter.
Plugin-only or copied-adapter installations lack the checkout, venv and setup
helper, so this slice does not claim automatic installation parity for them.
Their generated guidance names the exact external prerequisite, verifies the
version before lint, and refuses rather than silently skipping validation.

This is the owner-approved initial boundary. A portable plugin tool environment
is a successor, not something hidden inside this package swap.
