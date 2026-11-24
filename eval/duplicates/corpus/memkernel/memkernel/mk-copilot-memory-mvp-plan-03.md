---
page_type: decision
slug: mk-copilot-memory-mvp-plan-03
title: 'Embedding model selection'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/copilot-memory-mvp/plan.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Context

Need embeddings for code and natural language memories. Options: sentence-transformers (local, free), Voyage Code (code-specific, paid), OpenAI text-embedding-3-small (general, paid).

## Decision

Default to `all-MiniLM-L6-v2` via sentence-transformers for MVP (local, zero-cost, fast). Make the embedding model configurable via settings so users can swap to Voyage Code or OpenAI.

## Consequences

Local-first means no API key required for basic use. Code-specific models may improve retrieval quality — measure in eval before recommending a switch.
