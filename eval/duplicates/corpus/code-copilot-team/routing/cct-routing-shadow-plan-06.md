---
page_type: decision
slug: cct-routing-shadow-plan-06
title: 'Versioned recommendation record'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-shadow/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`benchmarks/schema/recommendation.schema.json` — schema_version 1,
closed outcome vocabulary, evidence-reference shape, required
confidence grade + basis fields, additionalProperties false.
Derived records validate against it before serving (record_check).
Evidence references are `{evidence_set_id, artifact:
routing_runs|outcome_matrix|report, locator}` where locator is
record indices / cell coordinates / arm+task keys / a RELATIVE
ledger path for referenced evidence files. Absolute paths and any
`..` segment are rejected at validation; resolution enforces
containment under the set's root and regular-file-ness. No
filesystem path — relative or otherwise — identifies a set; the
opaque id does (finding: #261 prohibits sensitive absolute paths
reaching the surface).
