---
page_type: decision
slug: the-clusters-view-is-not-an-explorer
title: The clusters view is not an explorer
status: stable
last_reviewed: 2026-09-04
sources:
  - path: specs/session-analytics-similarity-ui/plan.md
    sha: 15438b2
  - issue: gosha70/code-copilot-team#293
---

## Decision

In the context of showing session clusters, we chose a minimal read-only clusters list and similar-sessions panel. We chose it over an explorer with filtering, drill-down or graph visualization. The reason: nobody had looked at a cluster list yet and an explorer would be designed against imagined usage.

Chosen: the read-only clusters view and similar panel in `specs/session-analytics-similarity-ui/plan.md`.

## Context

Requirement: surface the already-computed clusters without re-deriving or re-ranking anything.

Applies when: surfacing the already-computed clusters without re-deriving or re-ranking anything.

Does not apply when: cluster quality is validated on real data and the owner reopens the explorer question.

## Alternatives considered

- An explorer: explicitly out of scope.
- Filtering or drill-down: explicitly out of scope.
- Graph visualization: explicitly out of scope.

## Consequences

Revisit when: cluster quality is validated on real data and the owner reopens the explorer question.

Tests: none.

Confidence: high: the plan's origin claim states the exclusion in the owner's words.
