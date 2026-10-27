---
page_type: decision
slug: cache-policy
title: Cache Policy
status: stable
last_reviewed: 2026-10-27
sources:
  - url: "https://example.com/cache-policy"
    retrieved: 2026-10-27
---

# Cache Policy

## Decision

Keep read-cache entries for ten minutes.

## Context

Pages change rarely during a session.

## Alternatives considered

No cache at all.

## Consequences

A hand edit shows up within ten minutes.
