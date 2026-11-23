---
page_type: decision
slug: codex-backend-metadata-records-the-selected-provider-id
title: The codex backend records the selected provider id
status: stable
last_reviewed: 2026-05-18
sources:
  - path: specs/benchmark-adapters-backends/spec.md
    sha: 6529175
  - issue: gosha70/code-copilot-team#33
---

## Decision

In the context of the `codex` benchmark backend, we chose to record the resolved config path and the selected provider id in each run record. We chose it over recording any secret. The reason: a run record shows which provider answered and never holds a key.

Chosen: `backend_metadata` with the resolved `~/.codex/config.toml` path and the selected `model_providers.<id>`.

## Context

Requirement: the harness records provider settings and never sets them; no secret enters a run record.

Applies when: the benchmark harness drives `codex exec` headlessly and writes `backend_metadata`.

Does not apply when: a backend takes its provider from environment variables, where presence booleans are recorded.

## Alternatives considered

- Recording API keys: rejected, because run records hold presence booleans, the config path and the provider id only.

## Consequences

Revisit when: not recorded in the spec.

Tests: a recorded-transcript test with a fake `codex` shim on PATH; no live CLI and no network.

Confidence: medium: the spec states the contract for `backend_metadata`, and its verification record covers the invocation, not the provider id.
