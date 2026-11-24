---
page_type: decision
slug: mk-copilot-memory-mvp-plan-02
title: 'ChromaDB for MVP with application-level BM25'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/copilot-memory-mvp/plan.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Context

Need a vector store with hybrid search support. Options: ChromaDB (zero-config, embedded), Qdrant (production-grade, native sparse vectors), pgvector (relational). ChromaDB provides dense vector search but does not natively expose a BM25 sparse index.

## Decision

ChromaDB for MVP — embedded mode, no infrastructure dependency, fast iteration. BM25 sparse search is implemented as an **application-level side index** in `retrieval/sparse.py` using `rank_bm25`, maintained alongside ChromaDB. Plan migration path to pgvector when relational metadata queries become critical.

## Consequences

The BM25 index is a separate in-memory structure. ChromaDB is the authoritative store; the BM25 index is a derived, rebuildable cache. Consistency model:
**`retain`**: write to ChromaDB first (authoritative). If ChromaDB succeeds, add to BM25 index. If the BM25 add fails, log the error — the record exists in ChromaDB and will be picked up on next rebuild. Dense search still works; sparse search misses the entry until rebuild.
**`forget`**: delete from ChromaDB first (authoritative). If ChromaDB succeeds, remove from BM25 index. If the BM25 remove fails, log the error — the BM25 index may return a stale hit whose `get(ref_id)` will return "not found", which the caller handles. The stale entry is cleaned on next rebuild.
**Rebuild**: The BM25 index is fully rebuilt from ChromaDB on server startup and can be triggered via an admin endpoint (`POST /admin/rebuild-index`). This is the consistency recovery mechanism — any drift between the two stores is resolved by rebuild.
**Design invariant**: ChromaDB is always correct. BM25 may lag but never contradicts ChromaDB in a way that produces incorrect data — at worst it produces stale refs that resolve to "not found".
RRF fusion lives in `retrieval/search.py` (service layer, not the storage adapter) — it receives ranked lists from both backends and merges them. This separation means neither ChromaDB adapter nor BM25 index knows about the other; `HybridSearchService` orchestrates both.
