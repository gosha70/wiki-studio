---
page_type: decision
slug: judge-statistics-and-charts-stay-in-the-stdlib
title: Judge statistics and charts stay in the stdlib
status: stable
last_reviewed: 2026-05-20
sources:
  - path: specs/benchmark-llm-judge/origin-alignment-2026-05-20-0238.md
    sha: dafbc5b
  - path: scripts/benchmark_runner/calibration/spearman.py
    sha: dafbc5b
  - issue: gosha70/code-copilot-team#34
  - pr: gosha70/code-copilot-team#48
---

## Decision

In the context of judge calibration and report charts, we chose stdlib Spearman and pure-string SVG. We chose it over scipy, matplotlib and a templating engine. The reason: the existing harness is stdlib-only and the corpus is small.

Chosen: `scripts/benchmark_runner/calibration/spearman.py` and the pure-string SVG renderers in `scripts/benchmark_runner/report.py`.

## Context

Requirement: per-dimension Spearman correlation and static report charts under the harness's stdlib-only posture.

Applies when: computing per-dimension Spearman correlation and rendering static report charts under the stdlib-only posture.

Does not apply when: the calibration corpus grows beyond a few hundred labels or the charts need features pure-string SVG cannot express.

## Alternatives considered

- scipy: unnecessary for a few hundred labels.
- matplotlib: a plotting dependency for static charts.
- A templating engine: the report is generated strings.

## Consequences

Revisit when: the calibration corpus grows beyond a few hundred labels or the charts need features pure-string SVG cannot express.

Tests: `scripts/benchmark_runner/tests/test_spearman.py::test_wikipedia_iq_tv_example` and `::test_ties_on_both_sides_hand_computed`.

Confidence: high: the origin record states the choice and the current modules match it.
