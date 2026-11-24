---
page_type: decision
slug: mk-memkernel-0-7-hooks-spec-03
title: 'The pinned "Minimal setup" block'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-hooks/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

It must change: its checkpoint line is the relevance-ranked recall
(H2). The 0.5 suite's arms must not change, because the report was measured with them.
The test compares the arms with a **frozen copy** of the 0.5 block, kept in
`eval/lifecycle-suite/arms/` with its sha256 recorded, instead of the live template. The template can then
evolve, and the frozen arms stay byte for byte what was measured.
A future measured run decides which block its arms carry.
