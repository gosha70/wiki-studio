---
page_type: decision
slug: retry-policy
title: Retry Policy
status: stable
last_reviewed: 2026-10-27
sources:
  - url: "https://example.com/retry-policy"
    retrieved: 2026-10-27
---

# Retry Policy

## Decision

Retry outbound calls with exponential backoff, starting at 250 ms, at most five times.

## Context

Agreed with the platform team.

## Alternatives considered

A fixed 1 s delay.

## Consequences

Long outages wait at most 8 s between tries.
