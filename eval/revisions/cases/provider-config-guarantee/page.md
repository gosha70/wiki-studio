---
page_type: decision
slug: codex-runs-record-the-active-provider-from-config-toml
title: Codex runs record the active provider from config.toml
status: stable
last_reviewed: 2026-05-08
sources:
  - path: specs/provider-config/spec.md
    sha: 840119f
---

## Decision

In the context of benchmark run records, we chose to record which provider a Codex run used from its configuration file. We chose it over a provider router or proxy inside the harness. The reason: the harness records the routing and never sets it.

Chosen: the path to `~/.codex/config.toml`, the active provider id from its `[model_providers.<id>]` block and `wire_api`, with `provider_config_source = "toml"`.

## Context

Requirement: every backend with a configurable provider records it in `backend_metadata`; auth values are recorded as presence only.

Applies when: a benchmark backend drives Codex, which reads its provider from a file on disk.

Does not apply when: the copilot takes its provider from environment variables, as Claude Code and Aider do.

## Alternatives considered

- A provider router or proxy inside the harness: rejected, because the harness stays out of the connection path.

## Consequences

Revisit when: not recorded in the spec.

Tests: none recorded; the spec's acceptance criterion for the recording is unchecked at the cited commit.

Confidence: medium: the spec states the recording contract, and the Codex backend had not shipped when it was written.
