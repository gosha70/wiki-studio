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

The literature review the ADR cites (`docs/research/memory-literature-review.md` in the memkernel repo; summarised on the literature-review concept page) points three ways:

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
- [Agent-memory literature behind MemKernel's design (2024–2026 review)](../concepts/memkernel-memory-literature-review.md)
- [MemKernel LLM-wiki bridge and store health](../concepts/memkernel-wiki-bridge-and-health.md)
- [Register MemKernel with Claude Code](../workflows/memkernel-claude-code-setup.md)
