---
page_type: decision
slug: use-sqlite
title: Use SQLite
status: draft
last_reviewed: 2026-10-27
sources:
  - url: "https://example.com/use-sqlite"
    retrieved: 2026-10-27
---

# Use SQLite

## Decision

Keep the search cache in SQLite beside the lock file.

## Context

The standard library ships sqlite3.

## Alternatives considered

A JSON file.

## Consequences

FTS5 must be probed at runtime.
