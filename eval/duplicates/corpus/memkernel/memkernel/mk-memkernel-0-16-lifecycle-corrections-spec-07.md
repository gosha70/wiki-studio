---
page_type: decision
slug: mk-memkernel-0-16-lifecycle-corrections-spec-07
title: 'The chain count: plan on 12 chains'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-16-lifecycle-corrections/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

Eight reach significance only when every chain favours one arm (FR-006's
arithmetic: 8 of 8 gives p ≈ 0.008, 7 of 8 p ≈ 0.07; with 12, 10 of 12 gives p ≈ 0.04). The four added chains
follow #90 §2.1 and are written before the calibration; the preregistration states the final count.
