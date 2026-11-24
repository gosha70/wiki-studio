---
page_type: decision
slug: mk-memkernel-0-15-harness-foundations-spec-05
title: 'Three slices'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-15-harness-foundations/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

, each its own spec amendment and build PR:
**H1, receipts and correlation** (FR-002, FR-003, FR-006): it extends the recall log, changes no retrieval, and
gives the measurements the other two need.
**H2, scope and abstention** (FR-001, FR-005): the data-model change.
**H3, the context diff** (FR-004).

Order: **H1 first** (the owner: it changes no retrieval and gives the measurements the other two slices need), then
H2, then H3. #119 asks that the three areas be evaluated together, which this spec does; it leaves the number of
PRs to the plan.
