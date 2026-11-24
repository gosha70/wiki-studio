---
page_type: decision
slug: mk-copilot-memory-mvp-plan-01
title: 'MCP-first, FastAPI secondary'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/copilot-memory-mvp/plan.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Context

The server needs to be consumable by Claude Code, Cursor, and other MCP-compatible tools. It also needs admin/debug endpoints.

## Decision

MCP server is the primary interface (tools: retain, recall, forget, get). FastAPI serves admin endpoints only (collection stats, health, memory browser). Both share the same core services.

## Consequences

MCP tool definitions must be kept minimal. FastAPI routes are optional and don't need to mirror MCP tools exactly.
