---
page_type: decision
slug: merge-require-green-ci-was-never-read
title: merge.require_green_ci was never read
status: stable
last_reviewed: 2026-07-14
sources:
  - path: specs/auto-build-loop-merge-profile/spec.md
    sha: a24a00e
  - issue: gosha70/code-copilot-team#80
---

## Decision

In the context of the merge profile, we chose to delegate green-CI enforcement to `merge.require_green_ci` and GitHub branch protection. We chose it over a driver-side CI gate. The reason: the driver should arm auto-merge and let GitHub enforce checks.

Chosen: `merge.require_green_ci` in the merge profile spec.

## Context

Requirement: autonomous merge gated on green CI.

Applies when: an autonomous merge is gated on green CI through the merge profile.

Does not apply when: a driver-side CI gate is reintroduced or the merge profile changes.

## Alternatives considered

- Driver-side CI polling: rejected at the time as redundant.

## Consequences

Revisit when: a driver-side CI gate is reintroduced or the merge profile changes.

Tests: none.

Confidence: high.
