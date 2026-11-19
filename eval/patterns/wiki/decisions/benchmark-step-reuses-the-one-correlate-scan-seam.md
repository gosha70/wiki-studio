---
page_type: decision
slug: benchmark-step-reuses-the-one-correlate-scan-seam
title: Benchmark step reuses the one correlate scan seam
status: stable
last_reviewed: 2026-09-08
sources:
  - path: specs/session-analytics-benchmark-step/spec.md
    sha: 2325480
  - path: scripts/session_analytics/api/server.py
    sha: 2325480
  - pr: gosha70/code-copilot-team#321
---

## Decision

In the context of a pipeline step that links benchmark runs to sessions, we chose the existing `correlate.run` scan. We chose it over a second scanner in the pipeline layer. The reason: one commit-at-the-end contract must serve both the CLI and the step.

Chosen: `session_analytics.correlate.run` at `scripts/session_analytics/correlate.py`, called from `scripts/session_analytics/api/server.py:_correlate`.

## Context

Requirement: a Link benchmark runs step that scans a runs folder and stores outcomes, with progress and one transaction.

Applies when: a pipeline step scans a runs folder and stores outcomes through the existing scan seam.

Does not apply when: the step needs a different transaction or progress contract from the CLI scan.

## Alternatives considered

- A pipeline-local scanner: duplicates counters, commit semantics and progress behavior.
- A second scan contract: would drift from the CLI.

## Consequences

Revisit when: the step needs a different transaction or progress contract from the CLI scan.

Tests: `scripts/session_analytics/tests/test_pipeline_jobs.py::test_correlate_is_a_step_right_after_ingest` and `scripts/session_analytics/tests/test_api.py::test_benchmark_payload_names_the_runs_root_and_the_link_step_runs_it`.

Confidence: high: the spec states the one seam, the API runner calls it, and two tests pin the step.
