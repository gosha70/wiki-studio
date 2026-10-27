---
page_type: concept
slug: retry-backoff
title: Retry Backoff
status: draft
last_reviewed: 2026-10-27
sources:
  - url: "https://example.com/retry-backoff"
    retrieved: 2026-10-27
---

# Retry Backoff

## Summary

Start at 250 ms, double each attempt, cap at 8 s.

## Jitter

Add random jitter so clients do not retry in lockstep.
