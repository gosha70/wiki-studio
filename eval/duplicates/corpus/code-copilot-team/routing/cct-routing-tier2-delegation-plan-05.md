---
page_type: decision
slug: cct-routing-tier2-delegation-plan-05
title: 'Scope enforcement is driver-owned, post-hoc, CUMULATIVE, and phase-universal'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier2-delegation/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

After EVERY modifying phase — the initial
Tier-2 implementation, each Tier-2 repair round, AND Tier-1
reconciliation changes — the driver diffs the packet worktree
against the packet's `base_commit` (the cumulative diff, never a
per-round delta). Any path outside `allowed_files` — including ANY
verifier/test file and any path matching a floor category, which
are protected even when listed — fails that phase with the named
violation `packet_scope_violation` and reverts the worktree diff.
Scope failure is terminal for the round even if every verifier
passes. The ordering is frozen for all three phases:
scope/safety → verifiers → (for reconciliation only) verdict.
`accepted_with_changes` is NOT a path around scope — a Tier-1
reconciler's edits obey the same allowlist and protections as the
Tier-2 builder's. The scope check runs BEFORE verifiers in every
phase (never execute out-of-scope code).
