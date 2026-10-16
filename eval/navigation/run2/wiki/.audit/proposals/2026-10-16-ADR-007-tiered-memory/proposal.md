# Proposal: 2026-10-16-ADR-007-tiered-memory

**Rationale:** Gate passes. (1) Reusable: ADR-007 records why MemKernel splits memory into tiers, uses supersession for facts and decay for experience, and keeps the LLM out of the server. Anyone changing retention, recall or consolidation needs this. (2) Citable: repo file eval/navigation/corpus/docs/adr/ADR-007-tiered-memory.md at 8b7f14d. (3) Non-duplicative: concepts/memkernel-tiered-memory already describes how the tiers work (from the README), but not the decision, its context, the rejected alternatives or the consequences. So I am adding a new decisions/ page and updating the concept page with what the ADR refines, without restating it: the 0.4 automatic supersession of code memories by source, the durable superseded_by marker, the exact consolidation ranking importance × (1 + access_count), recall/get writing access stats with touch=False on maintenance paths, and backward-compatible metadata. (4) New-contributor-relevant: a newcomer asking 'why not one TTL / LLM consolidation / a graph / separate collections?' should find the answer here. Edits: create the decision page, update the concept page, add an index link, add a log line.

## decisions/memkernel-tiered-memory-decision.md
**Action:** create  
**Rationale:** No existing page records the rationale, context, rejected alternatives or consequences of the tiered design. A decisions/ page is the schema's home for an ADR. Status and date live in the frontmatter, so there are no Status/Date H2s.

```markdown
---
page_type: decision
slug: memkernel-tiered-memory-decision
title: "ADR-007: tiered memory with supersession for facts and decay for experience"
status: stable
last_reviewed: 2026-10-16
sources:
  - path: eval/navigation/corpus/docs/adr/ADR-007-tiered-memory.md
    sha: 8b7f14d
---

# ADR-007: tiered memory with supersession for facts and decay for experience

## Decision

MemKernel (accepted 2026-10-11) gives every memory a `MemoryTier` derived from its `MemoryType`:

- **long-term**: `decision`, `convention`, `fact`, `code`, `procedure`
- **short-term**: `episode`, `observation`
- **working**: `task`

The tiers follow different rules:

1. **Long-term memories never expire.** You replace one with `retain(supersedes=<ref_id>)`, and recall hides the superseded record. From 0.4 (spec memkernel-0-4, FR-008), `code` memories are superseded automatically by `source`: retaining a changed file supersedes every live snapshot of that path. Every superseded record, of any type, carries a durable `superseded_by` marker. Recall, listing, consolidation and the wiki exporter all honour that marker independently of the search window.
2. **Short-term and working memories expire.** Their TTL grows with every recall, `base × (1 + access_boost × access_count)`, and is measured from the later of creation and last access.
3. **Recall re-scores the fused hybrid result** as `w_rel·relevance + w_rec·recency + w_imp·importance`. Long-term memories have no recency decay.
4. **The agent drives promotion.** `promote(ref_id, type, content)` creates a new record with `promoted_from` provenance. `consolidate()` purges expired memories and ranks promotion candidates by `importance × (1 + access_count)`. MemKernel itself has no LLM dependency.
5. **New metadata is optional on read.** The fields `tier`, `importance`, `access_count`, `last_accessed`, `tags`, `supersedes` and `promoted_from` get derived defaults, so records written by 0.1.x still load.

## Context

MemKernel 0.1 kept four memory types in one flat store with a single TTL rule: `episode` expired after 30 days and everything else never did. Retrieval used hybrid relevance only. Three things were missing:

- nothing promoted a short-lived observation into durable knowledge;
- nothing told a replaced decision apart from a current one;
- a frequently useful episode expired on the same schedule as noise.

The literature review the ADR cites (`docs/research/memory-literature-review.md` in the memkernel repo) points three ways:

- facts and experiences need different persistence rules (Roynard 2026; Zep's bi-temporal invalidation);
- recall should strengthen retention, and recency should be measured from last access (MemoryBank, Generative Agents);
- consolidation is a repeated pass in which the LLM does the synthesis (Letta, Mem0, A-MEM).

The ADR also notes that ADRs 1–6 predate the `docs/adr/` directory and live only as code comments. One example is ADR-5: deduplicate on content hash + type.

## Alternatives considered

- **Keep one tier and add more TTLs.** Simpler, but facts would still decay and there would be no path from observation to knowledge.
- **LLM-driven consolidation inside the server** (Mem0-style ADD/UPDATE/DELETE). Each pass would be higher quality, but it puts an LLM client inside an MCP server whose client is already an LLM. That doubles token cost and ties MemKernel to one provider. It stays on the roadmap as an optional extra.
- **A knowledge graph with personalised PageRank** (HippoRAG 2, Graphiti). Strongest for multi-hop questions. Deferred until the flat tiered store shows multi-hop failures on real coding sessions. The `supersedes` link is the minimal bi-temporal edge in the meantime.
- **A separate collection per tier.** Cleaner isolation, but it breaks cross-tier recall and the idempotent dedup key. The chosen design filters on metadata within one collection.

## Consequences

- The MCP surface grows from 4 to 9 tools, under the FR-013 limit of 10.
- `recall` and `get` now write, because they track access. Maintenance paths pass `touch=False` so they do not inflate access counts.
- Hooks become consolidation points. `templates/hooks/` gains `session-start.py`, and the existing hooks surface promotion candidates.
- Code that embeds MemKernel should build the service with `memkernel.factory.build_service`.
- Open follow-ups: merging near-duplicates by embedding distance, persisting BM25, an eval category for knowledge updates and abstention, and an optional background summariser.
- The ADR's long-term list does not include `document`; the README does list `document` as a long-term type (see the concept page).

## Related

- [MemKernel tiered memory model](../concepts/memkernel-tiered-memory.md)
- [MemKernel LLM-wiki bridge and store health](../concepts/memkernel-wiki-bridge-and-health.md)
- [Register MemKernel with Claude Code](../workflows/memkernel-claude-code-setup.md)
```

## concepts/memkernel-tiered-memory.md
**Action:** update  
**Rationale:** The ADR refines the concept page with facts the README did not give. Added: automatic code supersession by source and the durable superseded_by marker (0.4); access tracking on recall/get, with touch=False on maintenance paths; no recency decay for long-term memories; the exact candidate ranking importance × (1 + access_count), which replaces 'importance × recall count'; no LLM inside the server; backward-compatible metadata. Also added the ADR as a source and a Related link to the new decision page.

```markdown
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
```

## index.md
**Action:** append-index  
**Rationale:** Makes the new decision page reachable from index.md under a new Decisions section.

```markdown
## Decisions

- [ADR-007: tiered memory with supersession for facts and decay for experience](decisions/memkernel-tiered-memory-decision.md): why tiers, supersession and access-boosted decay; rejected alternatives (more TTLs, in-server LLM consolidation, graph/PPR, per-tier collections)
```

## log.md
**Action:** append-log  
**Rationale:** One dated log entry, as the log format requires, recording the create and the related update.

```markdown
- 2026-10-16 — create memkernel-tiered-memory-decision (decision): ADR-007 rationale, alternatives and consequences for tiered memory; update memkernel-tiered-memory (concept) with code auto-supersession, access tracking and the consolidation ranking from ADR-007
```
