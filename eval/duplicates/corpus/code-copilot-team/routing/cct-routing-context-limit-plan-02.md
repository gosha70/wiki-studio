---
page_type: decision
slug: cct-routing-context-limit-plan-02
title: 'an observation is an UPPER BOUND, never a capacity proof'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-context-limit/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

This is the correctness crux and the reason rules 2, 3 and 4 compose
soundly. `maximum context length is 32768` is emitted *while failing*.
It proves the ceiling is at most 32768; it does not prove that 32768
works. So an observed value is only ever applied ON TOP of a
declaration:

| declared | observed | effective | eligible for a task declaring a minimum? |
|---|---|---|---|
| absent | absent | UNKNOWN | no (rule 2) |
| absent | 32768 | **UNKNOWN** | **no** — nothing to narrow; an upper bound is not a grant |
| 200000 | absent | 200000 | yes iff 200000 ≥ minimum |
| 200000 | 32768 | 32768 | yes iff 32768 ≥ minimum |
| 200000 | 400000 | 200000 | observation never broadens (rule 4) |

Row 2 is the one a naive reading gets wrong. Treating a bare
observation as the effective limit would let an overflow *failure*
promote an undeclared profile into eligibility — evidence of a ceiling
misread as evidence of capacity.
