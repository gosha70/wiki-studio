# Proposal: 2026-10-16-memory-literature-review

**Rationale:** Gate passes. (1) Reusable: the review is the evidence base behind ADR-007 and the memory-tiers design. It records which external mechanisms MemKernel adopted, deferred or treated as speculative, and anyone extending the memory model will need that. (2) Citable: it is a repo file at eval/navigation/corpus/docs/research/memory-literature-review.md. (3) Non-duplicative: the existing pages only mention it in passing ('lives at docs/research/memory-literature-review.md in the memkernel repo'). No page holds the per-system comparison, the benchmark landscape, the contested status of HRM, the arXiv 2604.11364 correction or the eight adopted design implications. (4) New-contributor-relevant: it explains why MemKernel looks the way it does and which literature claims are weak. One new concept page is created. ADR-007 is updated to point at it, because the ADR cites this review as its context. The index and log are appended.

## concepts/memkernel-memory-literature-review.md
**Action:** create  
**Rationale:** No existing page covers the literature review itself. This page records the per-source adoption decisions, the contested and speculative status of several sources, the Roynard misattribution trap, the benchmark caveats and the eight adopted implications.

```markdown
---
page_type: concept
slug: memkernel-memory-literature-review
title: Agent-memory literature behind MemKernel's design (2024–2026 review)
status: draft
last_reviewed: 2026-10-16
sources:
  - path: eval/navigation/corpus/docs/research/memory-literature-review.md
    sha: 8b7f14d
---

# Agent-memory literature behind MemKernel's design (2024–2026 review)

## Summary

The memkernel tiered-memory redesign rests on a literature review compiled on 2026-10-11. It covers hierarchical reasoning models (HRM, TRM), JEPA and the "missing knowledge layer" critique, about a dozen agent-memory systems, the memory benchmarks, and cognitive-science framings (CoALA, forgetting curves). For each source it records what MemKernel takes, defers or treats as only an analogy. From this the review derives eight design implications, which ADR-007 and `docs/architecture/memory-tiers.md` adopt. The review marks numbers taken from secondary summaries, and it says plainly which transfers to memory are speculative.

## Key ideas

- **The central correction comes from Roynard 2026, and it is easy to misattribute.** arXiv 2604.11364 is *not* a JEPA paper. It is Roynard, *The Missing Knowledge Layer in Cognitive Architectures for AI Agents* (v2 June 2026). The paper proposes four layers: Knowledge (indefinite supersession, never decays), Memory (Ebbinghaus decay), Wisdom (evidence-gated revision) and Intelligence (ephemeral orchestration). It is a single-author preprint and has no independent evaluation. MemKernel nevertheless adopts its supersession-vs-decay split directly (ADR-007).
- **The HRM/TRM transfer is analogy only, and HRM's own result is contested.** The ARC Prize team reproduced HRM's numbers. They found that the outer refinement loop with per-pass supervision drove the gains, not the two-timescale hierarchy (arcprize.org/blog/hrm-analysis, Aug 2025). The lesson MemKernel draws is that repeated consolidation passes matter more than storage hierarchy. The TRM figures (44.6–45% on ARC-AGI-1) come from secondary summaries.
- **JEPA-style next-state prediction is established for planning (V-JEPA 2-AC) but speculative for text memories.** No published agent-memory system trains such a predictor over harness traces. MemKernel uses only cheap proxies:
  - near-duplicate means redundant, so merge;
  - poorly predicted means novel, so keep (Titans' surprise gate).
- **What MemKernel takes from each agent-memory system:**
  - MemGPT/Letta: compaction as the page-out event, and the working tier as the editable block.
  - Letta sleep-time compute: `consolidate()` as the deterministic half of background rewriting.
  - Mem0: explicit `supersedes` as its UPDATE operation. Note that Mem0's README now describes an ADD-only single pass (2026).
  - A-MEM: tags and provenance links (`promoted_from`, `supersedes`).
  - Zep/Graphiti: invalidate, don't delete; fusion of cosine + BM25.
  - Generative Agents: three-axis rescore (relevance + recency + importance), with recency measured from last access.
  - MemoryBank: Ebbinghaus-style retention that strengthens with `access_count`.
  - LangMem: the semantic/episodic/procedural type taxonomy, with hooks as the background path.
  - Reflexion, Voyager, AWM and ReasoningBank: `procedure` as a first-class type, promoted only after the agent judges the outcome.
  - Claude Code memory (a `MEMORY.md` index plus topic files, reloaded after compaction): the wiki `index.md` is the "MEMORY.md" of project knowledge, and hooks run on SessionStart, PreCompact and PostCompact.
- **Benchmarks are not comparable across vendors, and the coding-specific ones are immature.**
  - LoCoMo vendor scores of 90+ use different judges.
  - LongMemEval's *knowledge-update* and *abstention* categories are where memory systems diverge most.
  - MemBench also scores efficiency and capacity degradation as the store grows.
  - SWE-Bench-CL, VibeMemBench and SWE-MeM are early.
  - The review's recommendation is that memkernel's `eval/run_eval.py` gain knowledge-update and abstention categories before any headline retrieval number is trusted.
- **CoALA + ReAct + Voyager serve as the harness blueprint.** CoALA's working/episodic/semantic/procedural memory maps onto:
  - `task`;
  - `episode`/`observation`;
  - `fact`/`decision`/`convention` plus the wiki;
  - `procedure`.

  ReAct's context blow-up is the reason for tiers and for `ask` over `get`. Voyager's need for isolated execution is why skills run in haa's sandbox and never in memkernel.
- **The eight design implications adopted:**
  1. Persistence semantics differ by record kind: facts are superseded, episodes decay, working state is ephemeral.
  2. Facts are invalidated, never deleted (`supersedes`).
  3. Recency is measured from last access, and recall strengthens retention.
  4. Scoring combines relevance, recency and importance with configurable weights.
  5. Consolidation is a repeated pass at session boundaries and compaction.
  6. Procedural memory is a first-class type, promoted only after judged success.
  7. A small, always-loadable index (the wiki `index.md`) leads to on-demand detail.
  8. The server does the bookkeeping and the agent does the synthesis; there is no LLM in memkernel.
- **Explicitly deferred:**
  - a graph layer with personalised PageRank (HippoRAG 2);
  - surprise-gated writes (Titans);
  - bi-temporal validity intervals beyond a single `supersedes` link;
  - knowledge-update and abstention eval categories.

## Where this shows up

- `eval/navigation/corpus/docs/research/memory-literature-review.md`: the review itself, with its per-system table (§3), benchmarks (§4), the CoALA/ReAct/Voyager mapping (§5a), the adopted implications (§6) and the primary links.
- `eval/navigation/corpus/docs/adr/ADR-007-tiered-memory.md`, which cites the review as its context.
- `eval/navigation/corpus/docs/architecture/memory-tiers.md` §3, which turns the implications into the mechanism → literature → code table.
- memkernel `eval/run_eval.py`, the target for the recommended knowledge-update and abstention categories.

## Related

- [MemKernel tiered memory model](memkernel-tiered-memory.md)
- [ADR-007: tiered memory with supersession for facts and decay for experience](../decisions/memkernel-tiered-memory-decision.md)
- [ADR-008: an LLM wiki is the human-readable form of long-term memory](../decisions/memkernel-wiki-semantic-layer-decision.md)
- [Integrating MemKernel into agent harnesses (code-copilot-team and haa)](memkernel-harness-integration.md)
```

## decisions/memkernel-tiered-memory-decision.md
**Action:** update  
**Rationale:** ADR-007 cites this review as its context. The update points the Context section and the Related list at the new literature-review page so readers can follow the evidence. All other content is unchanged.

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
```

## index.md
**Action:** append-index  
**Rationale:** Makes the new concept page reachable from the index. The line is appended under the trailing Concepts section.

```markdown
- [Agent-memory literature behind MemKernel's design (2024–2026 review)](concepts/memkernel-memory-literature-review.md): what MemKernel takes from MemGPT, Mem0, Zep, Generative Agents, MemoryBank and others; Roynard's supersession-vs-decay split; contested HRM results; benchmark caveats; eight adopted implications and what is deferred
```

## log.md
**Action:** append-log  
**Rationale:** Adds the required dated log entry for this patch-set.

```markdown
- 2026-10-16 — create memkernel-memory-literature-review (concept): per-system adoption table, contested/speculative transfers, benchmarks and the eight design implications from the memkernel literature review; update memkernel-tiered-memory-decision (decision) with a pointer to it
```
