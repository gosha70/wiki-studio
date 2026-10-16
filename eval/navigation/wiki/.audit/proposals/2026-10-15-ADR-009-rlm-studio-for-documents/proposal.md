# Proposal: 2026-10-15-ADR-009-rlm-studio-for-documents

**Rationale:** Gate passed. (1) Reusable: ADR-009 sets a lasting architecture rule. memkernel keeps memories, and RLM Studio stores documents and answers questions about them through ask(). Future contributors need this when working on the document type, the ask tool, the memkernel[rlm] extra or consolidation. (2) Citable: repo file eval/navigation/corpus/docs/adr/ADR-009-rlm-studio-for-documents.md at 8b7f14d. (3) Non-duplicative: the wiki is empty apart from index and log. (4) New-contributor-relevant: it explains why get() on a document returns only a summary, and what 'hybrid mode' means. The source is an ADR, so I created one decision page and added the index link and a log entry. No concept or glossary pages were split out, because the decision page covers the topic and one source does not justify more pages.

## decisions/rlm-studio-document-layer.md
**Action:** create  
**Rationale:** This ADR is a decision record, so I created a new decision page for it. No existing page covers how documents are stored in memkernel versus RLM Studio.

```markdown
---
page_type: decision
slug: rlm-studio-document-layer
title: RLM Studio is the document layer; memkernel asks questions of documents instead of loading them (ADR-009)
status: stable
last_reviewed: 2026-10-15
sources:
  - path: eval/navigation/corpus/docs/adr/ADR-009-rlm-studio-for-documents.md
    sha: 8b7f14d
---

# RLM Studio is the document layer (ADR-009)

Accepted 2026-10-11. Implemented in memkernel 0.3 (`specs/memkernel-0-3`).

## Decision

- **Two stores, one index.** RLM Studio (`gosha70/rlm-studio`, MIT, 1.0.0rc1) stores *documents* through its `StoragePort`: files, specs, PDFs, transcripts and uploaded data, immutable, deduplicated by hash and indexed by chunk. memkernel's store keeps *memories*. When a memory refers to a document, it carries `source="rlm://<content_hash>"` and a short summary as its content. `recall` still finds it because the summary and tags are embedded.
- **New memory type `document`** (long-term tier, importance 0.6). `retain(type="document", ...)` stores the body through the document port and indexes its chunks. It keeps a memkernel record holding the first ~1,000 characters plus a generated outline. `get` on a `document` returns the summary and the `rlm://` id, never the body.
- **New MCP tool `ask(ref_id, question, mode="auto")`.** It resolves the document, or a non-document memory's own content, and calls `rlmstudio.interact(content, question, mode)`. It returns the answer, the mode actually used, token and cost usage, and the trace id. `mode` is one of `direct | rag | rlm | auto`.
- **"Hybrid mode"** means choosing per run between Direct (whole content in the prompt), RAG (chunk, embed, retrieve top-k) and RLM (content bound to a sandbox variable `P`, which the model explores with `peek/grep/chunk/outline_file/subcall` and never sees whole). `auto` picks `direct` under 8K tokens and `rlm` above that. This is the ADR's reading of the owner's request. If the owner meant something else, only the default `mode` changes.
- **Ports in core, not imports.** `core/ports.py` adds `DocumentStorePort` (`put`, `get`, `index`, `search`) and `ReasonerPort` (`ask(content, question, mode) -> Answer`). The adapter lives in `memkernel/adapters/rlmstudio.py` and ships as the optional extra `memkernel[rlm]`, because `rlm-studio` imports LiteLLM at import time. Without the extra, `document` falls back to memkernel's own store (`ASTChunker` or a token splitter). In that case `ask` runs `mode="rag"` over memkernel's hybrid search and returns the top chunks instead of a synthesised answer.
- **Consolidation may use the reasoner.** With `ReasonerPort` configured, `consolidate(synthesize=True)` distils short-term memories into candidate long-term statements (Letta-style sleep-time compute). The default is `False`, so the agent stays the synthesiser.
- **Embedder contributed upstream.** memkernel gives RLM Studio a sentence-transformers `EmbeddingPort` shim, so RLM Studio's RAG mode can run fully locally. It may later also give its `HybridSearchService` for `StoragePort.search_chunks`. This stands in for the "rag-core" that RLM Studio's own code anticipates, until `ragkit` exists (ADR-008).

## Context

`get(ref_id)` returns full content. For a 2,000-line file, a long transcript or a 40-page spec, that floods the agent's context window, which is exactly what memkernel is meant to prevent. The agent needs to *ask a question of* a large artefact instead of reading it. RLM Studio already provides the needed pieces: execution modes, a backend-neutral `StoragePort` (SQLite adapter today), an `EmbeddingPort`, a public `interact`/`compare_matrix` API with a `mock` provider for tests, budgets, traces, replay, and PDF/DOCX text extraction.

## Alternatives considered

- **Store documents as `code`/`fact` memories and chunk them.** This works for retrieval but fails for questions about the whole document, because the agent still has to read every chunk.
- **Call RLM Studio over HTTP (`rlm-studio studio`).** This keeps memkernel's process light, but adds a server to run and a session to manage for every hook. In-process `interact()` is simpler for a single user. An HTTP `ReasonerPort` can be added later.
- **Move memkernel's memories into RLM Studio's SQLite store.** Rejected: its `VectorStore` is a brute-force cosine loop with no metadata filtering, no BM25 and no tiers.

## Consequences

- The MCP surface grows to 10 tools and hits the FR-013 ceiling. The options are to raise the ceiling or to drop the standalone `forget_expired` tool, since `consolidate(purge=True)` already covers it.
- New extra `memkernel[rlm]` (`rlm-studio>=1.0.0rc1`). Core stays free of LiteLLM.
- `templates/claude-memory-instructions.md` gains this guidance: for anything longer than a screen, use `retain(type=document)` and `ask()` instead of `get()`.
- RLM Studio is not on PyPI yet, so the extra installs from git until it is published.
- Implementation order (roadmap 0.3): ports, then the `document` type with local fallback, then the RLM adapter and `ask`, then the embedder shim upstream, then reasoner-backed consolidation.
```

## index.md
**Action:** append-index  
**Rationale:** The new page must be reachable from index.md.

```markdown

## Decisions

- [RLM Studio is the document layer (ADR-009)](decisions/rlm-studio-document-layer.md): documents live in RLM Studio and memkernel answers questions about them with `ask()`; the `memkernel[rlm]` extra
```

## log.md
**Action:** append-log  
**Rationale:** Required dated log entry for the new page.

```markdown
- 2026-10-15 — create rlm-studio-document-layer (decision): ingest ADR-009; documents move to RLM Studio and memkernel adds the `document` type and the `ask` tool
```
