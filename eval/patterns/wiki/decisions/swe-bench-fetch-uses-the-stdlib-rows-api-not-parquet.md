---
page_type: decision
slug: swe-bench-fetch-uses-the-stdlib-rows-api-not-parquet
title: SWE-bench fetch uses the stdlib rows API, not Parquet
status: stable
last_reviewed: 2026-05-18
sources:
  - path: specs/benchmark-adapters-backends/spec.md
    sha: 13eb704
  - path: benchmarks/adapters/swe_bench_verified/fetch.py
    sha: 13eb704
  - issue: gosha70/code-copilot-team#33
---

## Decision

In the context of fetching SWE-bench Verified under a no-new-dependencies constraint, we chose the Hugging Face datasets-server JSON rows API with `urllib` and `json`. We chose it over `pyarrow` or `datasets`. The reason: the dataset is published as Parquet and the constraint forbids those libraries.

Chosen: Python stdlib `urllib` and `json` at `benchmarks/adapters/swe_bench_verified/fetch.py`.

## Context

Requirement: pin and fetch SWE-bench Verified tasks into a content-addressed JSONL cache.

Applies when: fetching SWE-bench Verified tasks into a content-addressed JSONL cache under the no-new-dependencies constraint.

Does not apply when: the HF rows API changes or the no-new-deps constraint is lifted.

## Alternatives considered

- `pyarrow` or `datasets`: forbidden by the no-new-deps constraint.
- Parquet download: stdlib cannot parse it.

## Consequences

Revisit when: the HF rows API changes or the no-new-deps constraint is lifted.

Tests: none found for this adapter.

Confidence: high: the spec records the alternative and the current fetch code matches.
