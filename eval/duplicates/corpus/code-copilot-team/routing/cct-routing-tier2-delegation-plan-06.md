---
page_type: decision
slug: cct-routing-tier2-delegation-plan-06
title: 'Verifier-decided success + bounded repair + thrash detection'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier2-delegation/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Success is decided ONLY by the driver re-running the packet's
verifier commands (in the packet worktree) plus the scope check —
the model's self-report is evidence, never a verdict. A failing
round may repair: `RC_MAX_REPAIR_ROUNDS` (default 2) fresh
sessions, each fed the packet plus the driver's verifier output.
THRASH ends the loop early with its own named reason, each a
distinct journaled value: `packet_thrash_repeated_failure` (the
normalized failure signature of round N equals ANY prior round —
this subsumes A/B/A oscillation), `packet_thrash_rewrite` (an
allowed file's diff replaces more than `RC_REWRITE_FRACTION`
(default 0.8) of its lines), `packet_thrash_no_reduction` (the
failing-verifier count did not decrease). The changed-line budget
`RC_MAX_CHANGED_LINES` (default 400) is CUMULATIVE from the
immutable packet base — `changed_lines = diff(packet.base_commit,
current worktree)`, measured after every modifying phase — never a
per-round allowance (two legal rounds cannot double the effective
scope); exceeding it refuses as `packet_budget_exceeded`. Every
repair round (and every reconciliation launch, decision 9) is a
FRESH B-style supervised attempt with its own attempt id, result
envelope, and checkpoint under B's frozen crash ordering —
worktree state persists across rounds; agent sessions never do.
There is no C-only execution lifecycle. All `RC_*` numerics are
NAMED IMPLEMENTATION DEFAULTS journaled when applied — not
configuration, not compatibility surface (a knob takes the
refused→implemented→tested promotion path). Terminal packet
reasons form a closed enum in `routing-packet.sh`, sibling of
B's `routing_*` enum; no dynamic assembly.
