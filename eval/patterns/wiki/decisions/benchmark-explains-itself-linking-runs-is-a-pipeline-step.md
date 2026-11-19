---
page_type: decision
slug: benchmark-explains-itself-linking-runs-is-a-pipeline-step
title: Benchmark explains itself; linking runs is a pipeline step
status: stable
last_reviewed: 2026-09-08
sources:
  - path: specs/session-analytics-benchmark-step/spec.md
    sha: 2325480
---

## Decision

In the context of the Benchmark page, we chose a setting, a correlate pipeline step and a live payload over a backend-free one-shot view.

Chosen: `correlate.run` as the one scan seam, called by the CLI and by the `correlate` step right after `ingest`.

## Context

Requirement: a Benchmark page that explains what a benchmark run is and lets the user link runs from the page.

Applies when: the Benchmark page lacks explanation and actions, and an action on the page needs a step behind it.

Does not apply when: not recorded in the source record.

## Alternatives considered

- The 2026-07-18 backend-free, one-shot, Studio-only boundary: it cannot hold an action on the page, because an action needs a step behind it.
- A page action without a payload: a step needs a setting and a payload that says where it reads from.

## Consequences

Revisit when: not recorded in the source record.

Tests: unit tests cover FR-2, FR-3, FR-4 and the payload. The states script asserts every FR-7 state and the FR-8 polling transitions. `next build` and a doc-accuracy check stay green. A real-data walk runs on the owner's runs folder.

Confidence: not recorded in the source record.
