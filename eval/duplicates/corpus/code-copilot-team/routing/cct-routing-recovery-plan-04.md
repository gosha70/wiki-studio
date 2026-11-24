---
page_type: decision
slug: cct-routing-recovery-plan-04
title: '`cct routing tick --due --once` — the scheduled impure command'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-recovery/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`validate | status | explain` stay pure; scheduled `tick` and the
explicit operator action `enable` write, and help says so. Contract
per tick: acquire a dedicated global scheduler lock for the whole
pass (held means named immediate refusal — no queueing), while B's
short state lock still makes each publication atomic;
select profiles/pools whose `next_probe_at` is due; set `probing`;
run the probe; apply the result atomically (pass →
`consecutive_probe_successes`+1, threshold reached → `healthy` +
`healthy_since`; fail → reset successes, backoff reschedule);
journal every transition. Idempotency: a second immediate run
finds nothing due — proven as a byte-level state no-op.
A live supervisor that reaches a selection boundary blocked only by
due recovery markers invokes this same command without `--wake`,
then reselects. Cron/launchd remains useful for parked-run wake and
background failback, but is not a prerequisite for a live run to
recover from its own cooldown. With no ledger-root override, the
CLI discovers ledgers in this repository's registered worktrees;
`--ledger-root` is documented and names an explicit shared root.
The real wake launch exports the exact registry and ledger root that
passed these checks; the child never re-resolves them from defaults.
Wake is EXPLICITLY opt-in (`--wake`) and is an IDEMPOTENT
CLOSED RECONSTRUCTION (T3 review round 2 — AMENDMENT, see
below), never a shell string and never a ledger-supplied
command. A routed supervisor records the STRUCTURED invocation in
the ledger at startup (`routing_wake`: backend, profile, mode,
on-incomplete, caps, generation, claim/ack — additive field;
unrouted ledgers unchanged); wake rebuilds argv from a FIXED flag
list, taking the
executable from its own installation and re-validating every
value it reads. Before launching, wake REVALIDATES: recorded
disposition == `routing_no_eligible_profile` paired with the
status an unattended refusal actually writes (`failed`); the run
was unattended; repo `recovery.wake_enabled` is not false; no
live run lock; the recorded worktree still OWNS this ledger; the
backend is offered by a candidate in the run's own effective
policy; both persisted cap views agree and contain exactly four
non-negative integers; and at
least one candidate is PROBE-QUALIFIED healthy — a wake is the
consequence of recovery, not a retry timer. Durable
idempotency: each park carries a wake GENERATION, minted in the
SAME write as the park disposition; wake claims the generation
atomically (under the run lock, same-directory rename) BEFORE
launch, and any replay of a claimed generation is a journaled
no-op/refusal. A launch that is never ACKNOWLEDGED (the child
never takes the run lock and the ledger never moves) journals
`wake_launch_failed` and releases the claim, leaving the park
retryable
(retryable); a stale unconfirmed claim is retryable ONLY when no
live run lock exists — a live lock always refuses, so a
successfully-woken run can never be double-woken.
