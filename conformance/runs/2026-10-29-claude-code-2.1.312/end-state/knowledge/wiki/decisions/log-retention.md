---
page_type: decision
slug: log-retention
title: Log Retention
status: stable
last_reviewed: 2026-10-27
sources:
  - url: "https://example.com/log-retention"
    retrieved: 2026-10-27
---

# Log Retention

## Decision

Keep request logs for thirty days, then delete them.

## Context

Support needs a month of history to answer a ticket.

## Alternatives considered

Ninety days, which costs three times the storage.

## Consequences

A ticket older than a month cannot be traced from the logs.
