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
  - path: eval/navigation/corpus/docs/architecture/memory-tiers.md
    sha: 8b7f14d
---

# MemKernel tiered memory model

## Summary

MemKernel is a code-aware MCP memory server that gives AI coding copilots persistent memory across sessions and context compactions. Memories live in three tiers with different persistence rules: working memory (hours), short-term memory (decays unless recalled) and long-term memory (never decays and is replaced only by supersession). Recall ranks results by a weighted mix of relevance, recency and importance. The rationale is recorded in ADR-007. The design document `docs/architecture/memory-tiers.md` maps each mechanism to the literature it comes from and to the code that implements it.

## Key ideas

- **Why tiers**: a harness running many sessions over one repo loses three kinds of knowledge: what the agent is doing now (lost to compaction mid-task), what happened recently (rediscovered by the next session), and what the project *is* (re-derived or contradicted). MemKernel 0.1 kept all three in one flat store with a single `episode` TTL.
- **Framing**: the tiers use the CoALA vocabulary (working, episodic, semantic and procedural memory; Sumers et al. 2023). They also adopt the central correction from Roynard 2026 (*The Missing Knowledge Layer*): **facts are superseded, never decayed; experiences decay; working state is ephemeral.**
- **Callers pick a type, not a tier**: every `MemoryType` belongs to exactly one tier (`TYPE_TIER` in `core/models.py`), and the default importance and decay policy follow from the type. This keeps the MCP surface small.
- **Working tier**: `task` memories hold the current goal, plan state and open questions. Default importance is 0.5, the TTL is 24 hours (`MEMKERNEL_TASK_TTL_HOURS`) and the recency half-life is 12 hours.
- **Short-term tier**: `episode` memories (session events and compaction checkpoints, stored with `checkpoint=true`; importance 0.4, 30 days) and `observation` memories (findings and tool outputs; importance 0.3, 7 days). Both have a 7-day recency half-life.
- **Long-term tier**: the types are `decision` (0.9), `convention` (0.9), `fact` (0.7), `procedure` (0.8), `code` (0.6) and `document` (0.6). None of them expires. To replace one, retain a new memory with `supersedes=<ref_id>`, which hides the old one from recall. `procedure` makes procedural memory a first-class type (after Voyager's skill library and Agent Workflow Memory), and it maps to wiki `workflow` pages.
- **Supersession is durable**: from 0.4, retaining a changed file automatically supersedes every live `code` snapshot of that `source` path. Every superseded record carries a `superseded_by` marker, which recall, listing, consolidation and the wiki exporter honour regardless of the search window.
- **Slow state and fast state (HRM/TRM analogy)**: the working tier is the fast state, which churns within a task and may be reset at a task boundary. The long-term tier is the slow state, which changes only through an explicit `promote` of the *settled* result of a short-term phase. Consolidation is a refinement pass that repeats at every session boundary and compaction, not a one-shot write.
- **JEPA-style low-surprise proxy**: MemKernel trains no predictor. A new memory that is near an existing one is treated as low-surprise and deduplicated (`find_by_hash` today; merging by embedding distance is on the roadmap).
- **Retention formula**: `ttl = base_ttl × (1 + access_boost × access_count)`, and a memory is expired when `now − max(timestamp, last_accessed) > ttl`. Each recall therefore extends a short-term memory's life (MemoryBank-style rehearsal; `MEMKERNEL_ACCESS_BOOST`, default 0.5). Expired memories are hidden from `recall` immediately and are deleted by `forget_expired()` or `consolidate()`.
- **Reads track access**: `recall` and `get` update `access_count` and `last_accessed` (`_touch`). Maintenance paths pass `touch=False` so they do not extend lifetimes.
- **Recall scoring**: `relevance` is the min-max normalised RRF of dense cosine and BM25 over the fused candidates. `recency = exp(-ln2 · age_days / half_life(tier))`, measured from last access as in Generative Agents, and it is 1.0 for long-term memories. `final = w_rel·relevance + w_rec·recency + w_imp·importance`, with defaults 1.0, 0.3 and 0.3 (`MEMKERNEL_RECALL_WEIGHT_*`). Setting the last two weights to zero gives pure relevance.
- **Code-aware retrieval**: tree-sitter AST chunking splits files at function and class boundaries, and hybrid search combines dense embeddings, BM25 and reciprocal rank fusion (`MEMKERNEL_RRF_K`, default 60). This handles both semantic queries and exact identifier lookup.
- **Moving knowledge to long-term**: `consolidate` purges expired short-term memories and ranks promotion candidates by `importance × (1 + access_count)` (after Letta's sleep-time compute and LangMem's background manager). `promote(ref_id, type, content)` then writes a distilled long-term memory that records its origin in `promoted_from` (after Reflexion and ReasoningBank).
- **Server bookkeeping, agent synthesis**: MemKernel has no LLM in the loop. The server does the deterministic, cheap work: scoring, decay, dedup, provenance, purging, ranking candidates and compiling drafts. The agent, which is already an LLM, decides what a memory means and writes the distilled content. An optional `SummarizerPort` for background consolidation is on the roadmap as an opt-in extra, never a requirement.
- **Backward compatibility**: the tier metadata (`tier`, `importance`, `access_count`, `last_accessed`, `tags`, `supersedes`, `promoted_from`) is optional on read, so 0.1.x records load with derived defaults.
- **Documents**: `retain(type="document")` stores a large artefact's body in a document store and indexes it in chunks. `ask(ref_id, question, mode)` answers questions through a `ReasonerPort`: `local` (hybrid search over the chunks, no LLM) or `rlmstudio`. Do not call `get` on a document to read it.
- **Session protocol**: at session start (hook), run `consolidate()`, recover the latest checkpoint, `recall(tier=long_term)` for the task and point at the wiki index. While working, retain tasks at plan changes and observations for findings, and retain long-term types only for things true beyond this session (or `promote` later). Before compaction, retain a checkpoint episode and run consolidate. After compaction, the checkpoint, long-term context and candidates are injected and the agent promotes the keepers. Periodically, run `wiki_export`, review the drafts, then `wiki_import`. `MemoryLifecycle` packages this protocol for embedding harnesses.
- **Non-goals for now**: a knowledge-graph layer (HippoRAG-style PPR), deferred until the flat store shows multi-hop failures on real sessions; training a JEPA/Titans-style predictor, which is a research direction only; and replacing Claude Code's auto-memory. Auto-memory is the per-user notebook, and MemKernel is the per-project, multi-agent, queryable store.

## Where this shows up

- `eval/navigation/corpus/README.md`: the sections "Memory types and tiers", "Session protocol", "Configuration" and "Documents and `ask`".
- `eval/navigation/corpus/docs/adr/ADR-007-tiered-memory.md`: the decision record for tiers, supersession, decay and agent-driven promotion.
- `eval/navigation/corpus/docs/architecture/memory-tiers.md`: the design document (marked implemented in memkernel 0.2, revised 2026-10-11). It contains the tier diagram, the mechanism → literature → code table, the scoring and forgetting formulas, the session protocol and the non-goals. Its literature review lives at `docs/research/memory-literature-review.md` in the memkernel repo.
- Implementation points named in the design document: `core/models.py` (`MemoryTier`, `TYPE_TIER`, `DEFAULT_IMPORTANCE`), `memory/lifecycle.py::effective_ttl_days`, `retrieval/search.py::rescore`, `MemoryService.consolidate`, `MemoryService.promote`, `MemoryService.revalidate`, `MemoryService.health`, `_filter_live` (hides superseded records) and `templates/hooks/{pre-compact,post-compact,session-start}.py`.
- MCP tools (9, under the FR-013 limit of 10): `retain`, `recall`, `get`, `forget`, `promote`, `consolidate`, `ask`, `wiki_export` and `wiki_import`.
- Package layout: `src/memkernel/core/` (models, `MemoryService`, ports), `memory/` (TTL and decay policies), `retrieval/` (chunking, hybrid search), `lifecycle.py` (`MemoryLifecycle`) and `factory.py` (`build_service()`, the supported embedding entry point).

## Related

- [ADR-007: tiered memory with supersession for facts and decay for experience](../decisions/memkernel-tiered-memory-decision.md)
- [ADR-008: an LLM wiki is the human-readable form of long-term memory](../decisions/memkernel-wiki-semantic-layer-decision.md)
- [Register MemKernel with Claude Code](../workflows/memkernel-claude-code-setup.md)
- [MemKernel LLM-wiki bridge and store health](memkernel-wiki-bridge-and-health.md)
- [MemKernel install troubleshooting](../playbooks/memkernel-install-troubleshooting.md)
