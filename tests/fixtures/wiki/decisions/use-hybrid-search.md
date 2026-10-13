---
page_type: decision
slug: use-hybrid-search
title: Use Hybrid Search Before Graph Traversal
status: stable
last_reviewed: 2026-10-12
sources:
  - path: README.md
    sha: 77d3811c1afe59832e9faa935deff81cb4b10b92
---

# Use Hybrid Search Before Graph Traversal

## Decision

Retrieval runs vector plus keyword search first and only then expands through the knowledge graph.

## Context

Graph traversal alone misses pages whose vocabulary differs from the question; vector search alone misses exact identifiers.

## Alternatives considered

- Graph-first traversal: fast when the entry node is right, brittle otherwise.
- Vector-only: no exact-match guarantees.

## Consequences

Two retrieval passes per query; a reranking step assembles the final context.

## Related

- [Spec-Driven Development](../concepts/spec-driven-development.md)
