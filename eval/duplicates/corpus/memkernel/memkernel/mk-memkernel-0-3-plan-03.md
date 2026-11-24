---
page_type: decision
slug: mk-memkernel-0-3-plan-03
title: '`forget_expired` leaves the MCP surface'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-3/plan.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Context

`ask` is the tenth tool; the ceiling is ten exclusive.

## Decision

remove the `forget_expired` tool (consolidate already purges); keep the service method.

## Consequences

noted in CHANGELOG as a removal in a pre-1.0 release.
