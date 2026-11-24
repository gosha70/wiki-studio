---
page_type: decision
slug: cct-routing-eval-plan-02
title: 'Injection drives the existing test-only seams; production routing code is untouched'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-eval/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The named seams are
`CCT_SUPERVISOR_HARNESS_CMD` (documented at
`scripts/cooldown-supervisor.sh:57` as "override the child command
(a mock harness)") and `CCT_ROUTING_PROBE_CMD`
(`scripts/lib/routing-probe.sh:37`, "Test seam"). The benchmark
supplies the **child's output** through those seams — a transcript
shaped like a usage-limit response, with a stated reset instant —
and the real, unmodified classifier then does its real work on it.
E1 never injects at, patches, or bypasses the classification
boundary, and modifying any production routing file is out of
scope for this increment: a diff that touches one is a defect, not
a design choice. The event stream is preset-owned, recorded in the
artifact, and part of the preset digest, so two runs of one preset
see the same events in the same order. No leg depends on
wall-clock timing for correctness.
