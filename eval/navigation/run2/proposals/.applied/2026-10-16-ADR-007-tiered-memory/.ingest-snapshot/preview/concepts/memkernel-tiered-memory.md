---
page_type: concept
slug: memkernel-tiered-memory
title: MemKernel tiered memory model
status: draft
last_reviewed: 2026-10-16
sources:
  - path: eval/navigation/corpus/README.md
    sha: 8b7f14d
  - path: eval/navigation/corpus/docs/adr/ADR-007-tiered-memory.md
    sha: 8b7f14d
---

# MemKernel tiered memory model

## Summary

MemKernel is a code-aware MCP memory server that gives AI coding copilots persistent memory across sessions and context compactions. Memories live in three tiers with different persistence rules: working memory (hours), short-term memory (decays unless recalled) and long-term memory (never decays and is replaced only by supersession). Recall ranks results by a weighted mix of relevance, recency and importance. The rationale is recorded in ADR-007.

## Key ideas

- **Working tier**: `task` memories hold the current goal, plan state and open questions. Default importance is 0.5 and the TTL is 24 hours (`MEMKERNEL_TASK_TTL_HOURS`).
- **Short-term tier**: `episode` memories (session events and compaction checkpoints; importance 0.4, 30 days) and `observation` memories (findings and tool outputs; importance 0.3, 7 days).
- **Long-term tier**: the types are `decision` (0.9), `convention` (0.9), `fact` (0.7), `procedure` (0.8), `code` (0.6) and `document` (0.6). None of them expires. To replace one, retain a new memory with `supersedes=<ref_id>`, which hides the old one from recall.
- **Supersession is durable**: from 0.4, retaining a changed file automatically supersedes every live `code` snapshot of that `source` path. Every superseded record carries a `superseded_by` marker, which recall, listing, consolidation and the wiki exporter honour regardless of the search window.
- **Retention formula**: `ttl = base_ttl × (1 + access_boost × access_count)`, measured from the later of creation and last access. Each recall therefore extends a short-term memory's life (`MEMKERNEL_ACCESS_BOOST`, default 0.5).
- **Reads track access**: `recall` and `get` update `access_count` and `last_accessed`. Maintenance paths pass `touch=False` so they do not extend lifetimes.
- **Recall scoring**: a weighted sum of hybrid-search relevance (weight 1.0), recency (0.3, with a 7-day half-life on the short-term tier) and importance (0.3). All three weights are configurable through `MEMKERNEL_RECALL_WEIGHT_*`. Long-term memories have no recency decay.
- **Code-aware retrieval**: tree-sitter AST chunking splits files at function and class boundaries, and hybrid search combines dense embeddings, BM25 and reciprocal rank fusion (`MEMKERNEL_RRF_K`, default 60). This handles both semantic queries and exact identifier lookup.
- **Moving knowledge to long-term**: `consolidate` purges expired short-term memories and ranks promotion candidates by `importance × (1 + access_count)`. `promote(ref_id, type, content)` then writes a distilled long-term memory that records where it came from in `promoted_from`. The agent does the synthesis; MemKernel has no LLM dependency.
- **Backward compatibility**: the tier metadata (`tier`, `importance`, `access_count`, `last_accessed`, `tags`, `supersedes`, `promoted_from`) is optional on read, so 0.1.x records load with derived defaults.
- **Documents**: `retain(type="document")` stores a large artefact's body in a document store and indexes it in chunks. `ask(ref_id, question, mode)` answers questions through a `ReasonerPort`: `local` (hybrid search over the chunks, no LLM) or `rlmstudio`. Do not call `get` on a document to read it.
- **Session protocol**: at session start, recall long-term context and the latest checkpoint. While working, retain tasks and observations. Before compaction, retain a checkpoint episode and run consolidate. Afterwards, promote the candidates worth keeping. `MemoryLifecycle` packages this protocol for embedding harnesses.

## Where this shows up

- `eval/navigation/corpus/README.md`: the sections "Memory types and tiers", "Session protocol", "Configuration" and "Documents and `ask`".
- `eval/navigation/corpus/docs/adr/ADR-007-tiered-memory.md`: the decision record for tiers, supersession, decay and agent-driven promotion.
- MCP tools: `retain`, `recall`, `get`, `forget`, `promote`, `consolidate`, `ask`, `wiki_export` and `wiki_import`.
- Package layout: `src/memkernel/core/` (models, `MemoryService`, ports), `memory/` (TTL and decay policies), `retrieval/` (chunking, hybrid search), `lifecycle.py` (`MemoryLifecycle`) and `factory.py` (`build_service()`, the supported embedding entry point).
- The design document the README points to: `docs/architecture/memory-tiers.md` in the memkernel repo.

## Related

- [ADR-007: tiered memory with supersession for facts and decay for experience](../decisions/memkernel-tiered-memory-decision.md)
- [Register MemKernel with Claude Code](../workflows/memkernel-claude-code-setup.md)
- [MemKernel LLM-wiki bridge and store health](memkernel-wiki-bridge-and-health.md)
- [MemKernel install troubleshooting](../playbooks/memkernel-install-troubleshooting.md)
