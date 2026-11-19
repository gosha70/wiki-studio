---
page_type: decision
slug: never-archive-raw-jsonl
title: Never archive raw JSONL
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

In the context of durable trace retention, we chose parsed, redacted text only. We chose it over copying source JSONL files verbatim. The reason: a raw copy bypasses the redaction and opt-out gate.

Chosen: the archive path in `scripts/session_analytics/archive.py` that calls `redact_text` behind the opt-in gate.

## Context

Requirement: store full trace content durably without widening the privacy surface.

Applies when: storing full trace content durably without widening the privacy surface.

Does not apply when: a raw-copy path can prove the same redaction and opt-out guarantees, or the redaction gate becomes lossless.

## Alternatives considered

- Verbatim JSONL copy: bypasses redaction and opt-out.
- Unredacted storage: a privacy incident.

## Consequences

Revisit when: a raw-copy path can prove the same redaction and opt-out guarantees, or the redaction gate becomes lossless.

Tests: `scripts/session_analytics/tests/test_trace_archive.py::test_not_opted_in_produces_zero_rows` and `::test_opted_out_produces_zero_rows_even_with_trace_archive_true`.

Confidence: high: the shaping doc calls the raw copy a no-go and the implementation follows the redaction path.
