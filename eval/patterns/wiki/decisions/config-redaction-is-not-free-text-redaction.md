---
page_type: decision
slug: config-redaction-is-not-free-text-redaction
title: Config redaction is not free-text redaction
status: stable
last_reviewed: 2026-09-17
sources:
  - path: scripts/lib/analytics_layers.py
    sha: 8dbceaf
  - issue: gosha70/code-copilot-team#214
  - pr: gosha70/code-copilot-team#362
---

## Decision

In the context of printing configuration values, we chose `analytics_layers.redact` keyed by credential-marker names. We chose it over redaction at each call site. The reason: one helper can decide what a config key may show.

Chosen: `analytics_layers.redact` at `scripts/lib/analytics_layers.py`.

## Context

Requirement: never print a credential-bearing configuration value from `cct config` or the generated reference.

Applies when: printing configuration values from `cct config` or the generated reference, keyed by credential-marker names.

Does not apply when: the two redaction helpers are unified or `analytics_layers.redact` gains content-pattern redaction.

## Alternatives considered

- Per-call-site redaction: the third leak showed it drifts.
- A value-preserving mask: the whole value is withheld.

## Consequences

Revisit when: the two redaction helpers are unified or `analytics_layers.redact` gains content-pattern redaction.

Tests: none cited by value.

Confidence: medium-high: both helpers and their scopes are explicit in the code, but the later task is a constructed replay, not a historical commit.

Related record: [Trace archive reuses the ingest redaction path](trace-archive-reuses-the-ingest-redaction-path.md) — the free-text case this helper does not cover.
