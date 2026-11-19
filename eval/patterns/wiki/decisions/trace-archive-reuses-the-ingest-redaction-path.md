---
page_type: decision
slug: trace-archive-reuses-the-ingest-redaction-path
title: Trace archive reuses the ingest redaction path
status: stable
last_reviewed: 2026-07-18
sources:
  - path: specs/session-analytics-trace-archive/shaping.md
    sha: 76beab2
  - path: scripts/session_analytics/archive.py
    sha: c776632
  - issue: gosha70/code-copilot-team#98
---

## Decision

In the context of a durable, redaction-safe archive of full turn text, we chose the existing `redact_text` helper. We chose it over a new archive-specific redactor. The reason: the archive must never store looser content than ingest already redacts.

Chosen: `session_analytics.ingest.redaction.redact_text` at `scripts/session_analytics/ingest/redaction.py`, called from `scripts/session_analytics/archive.py`.

## Context

Requirement: archive full agent traces durably while preserving the opt-in and redaction gate.

Applies when: a durable archive stores the full text of each turn for search and export.

Does not apply when: the archive needs a mode that `redact_text` does not implement.

## Alternatives considered

- A new archive redactor: would fork the privacy contract.
- Raw JSONL copy: bypasses redaction.

## Consequences

Revisit when: the ingest redaction contract changes or the archive needs a mode that `redact_text` does not implement.

Tests: `scripts/session_analytics/tests/test_trace_archive.py::test_redaction_floor_never_looser_than_ingested_mode` and `::test_adversarial_redaction_code_mode_strips_fences`.

Confidence: high: the shaping doc names the reuse, the code does it, and the tests pin the redaction floor.
