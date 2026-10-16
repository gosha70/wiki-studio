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
