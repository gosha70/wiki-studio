---
page_type: decision
slug: mk-memkernel-0-3-plan-01
title: 'Two ports, both with LLM-free defaults'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-3/plan.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Context

ADR-009 adopts RLM Studio as the document layer, but memkernel must keep working with no extra dependency and no LLM.

## Decision

`DocumentStorePort` and `ReasonerPort` are protocols in `core/ports.py`; `LocalDocumentStore` (ChromaDB) and `LocalReasoner` (hybrid search over chunks) are the defaults; `RLMStudioReasoner` is opt-in via `MEMKERNEL_REASONER=rlmstudio`.

## Consequences

`ask` always answers; quality improves when RLM Studio is present. The adapter is tested with a fake module, not the real package.
