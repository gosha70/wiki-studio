---
page_type: decision
slug: benchmark-ui-was-backend-free-one-shot-and-studio-only
title: Benchmark UI was backend-free, one-shot and Studio-only
status: deprecated
last_reviewed: 2026-07-18
superseded_by: decisions/benchmark-explains-itself-linking-runs-is-a-pipeline-step.md
sources:
  - path: specs/session-analytics-benchmark-ui/spec.md
    sha: 2325480
  - path: specs/session-analytics-benchmark-step/spec.md
    sha: 2325480
  - issue: gosha70/code-copilot-team#96
  - pr: gosha70/code-copilot-team#321
---

## Decision

In the context of the first benchmark comparison UI, we chose a backend-free, one-shot, Studio-only diff. We chose it over any API or pipeline change. The reason: the existing payload already held the comparison figures.

Chosen: the 2026-07-18 Benchmark UI spec.

## Context

Requirement: show benchmark outcomes in the Studio without changing the backend.

Applies when: the Studio shows benchmark outcomes from the existing payload without a backend change.

Does not apply when: the page needs explanation or actions that require a setting, a pipeline step or polling.

## Alternatives considered

- An API or pipeline change at that time: out of scope.
- Auto-refresh: out of scope.

## Consequences

Revisit when: the page needs explanation or actions that require a setting, a pipeline step or polling.

Tests: none.

Confidence: high: the old spec is explicitly marked superseded and the new spec states why.

Superseded by: [the successor record](benchmark-explains-itself-linking-runs-is-a-pipeline-step.md).
