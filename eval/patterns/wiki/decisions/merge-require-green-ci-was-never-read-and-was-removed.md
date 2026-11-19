---
page_type: decision
slug: merge-require-green-ci-was-never-read-and-was-removed
title: merge.require_green_ci was never read and was removed
status: stable
last_reviewed: 2026-10-29
sources:
  - path: specs/auto-build-loop-merge-profile/spec.md
    sha: e39969f
---

## Decision

In the context of the merge profile, we chose GitHub branch protection over `merge.require_green_ci`, which no code ever read.

Chosen: GitHub branch protection with `gh pr merge --auto`. The key was removed from the shipped template on 2026-10-29.

## Context

Requirement: autonomous merge gated on green CI.

Applies when: the driver arms GitHub auto-merge on a branch-protected base.

Does not apply when: the base branch is not protected.

## Alternatives considered

- `merge.require_green_ci` as the enforcement point: it was never read and was removed on 2026-10-29.
- A driver-side CI gate: rejected in the original spec as redundant.

## Consequences

Revisit when: not recorded in the source record.

Tests: not recorded in the source record.

Confidence: high: the correction says the key was never read and was removed, with the commit to prove it.
