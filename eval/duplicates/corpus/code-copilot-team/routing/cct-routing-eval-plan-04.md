---
page_type: decision
slug: cct-routing-eval-plan-04
title: 'owns its telemetry record, because the evidence does not exist upstream'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-eval/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

This was verified, not assumed:
`benchmarks/schema/stats.schema.json` fixes
`cost_reporting.enabled` to `"const": false` and carries **no cost
amount** at all; `score.schema.json` carries only
`derived.failed_commands` (an integer) and
`scores.human_interventions` (an integer) — not the commands, the
evidence, or the interventions. Sourcing cost or verifier evidence
from them, as an earlier draft of this plan did, is impossible.

The routing-run record therefore carries per attempt:
`tokens.{input, output, cache_read, cache_write}`;
`cost.{value, provenance, estimator, inputs}` where provenance is
the closed set `measured | estimated | unavailable`, and
`estimator`/`inputs` are required whenever it is `estimated`;
`verifiers[]` — each execution's command, exit status, and an
addressable evidence reference (not a count);
`repair_cycles[]` with repeated-failure signatures;
`interventions[]` — records, not a count.

Quality outcomes still come from `score.schema.json`; elapsed time
still comes from `stats.schema.json`. Only what is genuinely
missing is added. A measure whose provenance is `unavailable`
propagates as `insufficient_evidence` and is never defaulted to
zero — which is what makes `always_cheapest` and the cost axis
honest rather than fabricated.
