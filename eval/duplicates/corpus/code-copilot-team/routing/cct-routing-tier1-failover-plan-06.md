---
page_type: decision
slug: cct-routing-tier1-failover-plan-06
title: 'Launch wiring'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier1-failover/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

A profile launches via its backend:
`claude-code`: child env gains `ANTHROPIC_BASE_URL` (from
`base_url` or the value behind `base_url_env`) and
`ANTHROPIC_API_KEY` (value behind `credential_env`) — read at
spawn into the child environment ONLY; never echoed, journaled,
persisted, or checkpointed. `credential_mode: claude-login`
wires nothing. The supervisor journals which VARIABLE NAMES were
wired, never values.
`pi`: the existing pi build backend path, unchanged.
Requested model comes from the profile; model verification is
explicitly TRI-STATE, preserving increment A's never-assumed rule:

reported effective == requested → verified match, recorded;
reported effective != requested → FAIL CLOSED with the named
reason `routing_model_identity_mismatch`, park/terminate — a
gateway silently substituting models is an identity violation,
never rerouted around (Scenario 10);
effective model unavailable → recorded null and journaled as
UNVERIFIED; requested is never synthesized as effective.

Per-adapter executability, stated not implied: the claude-code
backend's result carries model identity (states 1 and 2 are
executable); the pi backend currently does not (its attempts are
always state 3, journaled unverified). Checkpoints, journal, and
analytics always retain requested and effective SEPARATELY. No
registry field changes (A is frozen); a per-profile
"require verified identity" knob, if ever wanted, follows the
refused→implemented→tested promotion path.
