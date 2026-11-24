---
page_type: decision
slug: cct-routing-recovery-plan-02
title: 'The probe engine is a lib with honest per-backend canaries'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-recovery/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`scripts/lib/routing-probe.sh` (`rb_*`): `rb_probe <profile-json>`
runs (a) a small REAL inference — claude-code backend: one
bounded `claude -p` prompt through B's exact env wiring
(endpoint/credential refs, child-env only, output scrubbed);
pi backend: the pi one-shot equivalent — and (b) when the
profile's tool_profile implies tools (closed map, currently
full-cct and local-builder-minimal), a minimal tool canary (one
trivial Bash tool invocation) in a throwaway directory. Outcomes
are a CLOSED tri-state: `probe_pass | probe_fail |
probe_unverifiable` (a backend/harness that cannot run a real
canary is unverifiable — state stays `unknown`, never assumed).
`probe_fail` means ACTUAL negative canary evidence, never
absence of evidence. A tool-profiled builder passing inference
but failing the tool canary is `probe_fail` (SC-D2).
Positive inference evidence is a per-run nonce returned as the
parsed backend result, exact after surrounding whitespace is
normalized. The prompt, transcript, stderr, and user-message fields
are never searched for it; an echo cannot mint health. A non-JSON
notice line cannot suppress a valid structured result or measured
cost. The private probe directory is removed on every ordinary
return path.

Probes are NEVER an unmetered execution channel (review round 1);
the invocation ordering is FROZEN:
accounting debit/estimate via the EXISTING mechanism — a probe
that was actually launched is accounted for even if its result
is malformed, times out, crashes, or is later rejected;
bounded invocation (named timeout default; caps checked BEFORE
launch — a cap that blocks a due probe yields the named
non-health result `probe_deferred_caps`, never a cap bypass
and never a transition toward health; repeated cap deferrals
advance scheduling backoff without changing provider evidence);
output scrubbed with B's secret-taint discipline BEFORE any
journal/persistence;
result classification;
state transition.
The probe child receives credential VALUES in its environment
only (B's wiring), never in process argv. Active accounting, state,
registry, supervisor, and routing-artifact paths are rebound to a
private per-probe tree, so libraries sourced by the child cannot
fall back to the production files under `$HOME`; transcripts are
scrubbed and journaled with cost evidence. This is capability
hygiene, not an OS sandbox against a malicious same-user process
that independently guesses host paths. The test seam is
`CCT_ROUTING_PROBE_CMD` (a mock canary), mirroring B's harness
seam — the REAL default paths are exercised by executability
checks, not live providers.
