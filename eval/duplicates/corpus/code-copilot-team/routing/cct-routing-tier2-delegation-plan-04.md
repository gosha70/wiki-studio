---
page_type: decision
slug: cct-routing-tier2-delegation-plan-04
title: 'Packet execution rides B''s supervisor machinery — one new bounded mode, legacy and B byte-identical without it'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier2-delegation/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`cooldown-supervisor.sh <feature> --routing --delegate <task-id>`
runs exactly one packet, and the packet is its ONLY authority —
the frozen point-of-use sequence:

validate the closed/versioned envelope (unknown key /
version → named refusal),
verify `packet_digest` over the envelope bytes,
create the DEDICATED packet worktree from the packet's
recorded `base_commit`,
point-of-use provenance check: recompute the digests of
`routing-tasks.yaml` and `verification.yaml` and compare to
the packet's recorded `routing_tasks_sha256` /
`verification_spec_sha256` — ANY drift is the named refusal
`packet_provenance_drift` (never a silent rebuild, never a
downgrade; the operator regenerates a new packet),
execute from the packet alone — the run never rereads the
mutable artifacts and reinterprets them; route class, scope,
floor categories, and verifier commands come from the
envelope.

Selection uses `rt_select` over the packet's route class
(decision 8), then B's frozen chain unchanged — fresh child
session, `rt_launch_env` env wiring, `rt_scrub_out` secret
scrubbing, the 5-step crash ordering with
`started/result/checkpoint` documents, attempt-id idempotency,
recorded-decision recovery, tri-state model identity. The child is
launched with the profile's `tool_profile` (minimal:
read/edit/bash-test only; no MCP, no browser, no network tools
beyond the endpoint itself) and a packet-only prompt rendered from
the envelope. The child never touches the main tree; the driver
retains sole git ownership. Without `--delegate`,
`--routing` behavior is byte-identical to B (proven by the B suite
unmodified); without `--routing`, `--delegate` is a named refusal.
