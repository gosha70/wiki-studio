# Proposal: 2026-10-16-roadmap

**Rationale:** Gate passed. (1) Reusable: the roadmap gives the release plan for memkernel 0.2 to 0.5 and the order of work across seven repositories, gated on dependencies. Contributors to memkernel, ai-wiki, rlm-studio, haa and CCT will need this in future sessions. (2) Citable: repo file eval/navigation/corpus/docs/roadmap.md, grounded at the corpus SHA the other pages use. (3) Non-duplicative: no page covers the roadmap or the order of work across repos. The existing pages only mention a few roadmap items in passing, such as the 'roadmap CLI' and 'roadmap 0.3' in harness-integration, and the open follow-ups in ADR-007. (4) New-contributor-relevant: it answers what is shipped, what is next and what blocks what. One new concept page is created and linked from index.md, and log.md gets an entry. Existing pages are not rewritten. Instead, the new page says which of their statements the roadmap confirms or updates: in harness-integration, MemoryLifecycle and the ports are still open 0.3 items, and PyPI and the CHANGELOG are still open 0.2 items.

## concepts/memkernel-roadmap.md
**Action:** create  
**Rationale:** No page covers the roadmap or the release sequence across repositories. Its subject is the project's direction and dependencies, which is durable orientation knowledge, so it is a concept page.

```markdown
---
page_type: concept
slug: memkernel-roadmap
title: MemKernel roadmap and the cross-repository release sequence
status: draft
last_reviewed: 2026-10-16
sources:
  - path: eval/navigation/corpus/docs/roadmap.md
    sha: 8b7f14d
---

# MemKernel roadmap and the cross-repository release sequence

## Summary

The MemKernel roadmap was updated on 2026-10-11. It is ordered by dependency, not by date. It groups work into releases: 0.2 (tiered memory), 0.3 (documents through RLM Studio, lifecycle components and hardening), 0.4 (code revalidation and store health, already shipped), 0.5 (ecosystem) and a research backlog. It also sets out an eight-step sequence across memkernel, ai-wiki, rlm-studio, haa, code-copilot-team (CCT) and a future ragkit. Under that sequence, a step may start only when the step it depends on has a *published* artefact.

## Key ideas

- **Ordered by dependency, not by date**: release numbers are not a timeline. 0.4 is marked shipped while most 0.3 items are still open.
- **Publication is the gate between repositories**: a step starts when the step it depends on has a tag or a PyPI release. A merge is not enough.
- **0.2, tiered memory (the branch the roadmap was written on)**: these are done:
  - the working, short-term and long-term tiers, with the `fact`, `procedure`, `observation` and `task` types (ADR-007);
  - retention reinforced by access, and scoring by relevance, recency and importance;
  - `promote`, `consolidate`, `forget_expired` and `supersedes`;
  - the wiki bridge, `wiki_export` and `wiki_import` (ADR-008);
  - `memkernel.factory.build_service()` and `session-start.py`.

  Still open: a CHANGELOG, a CONTRIBUTING file and the `0.2.0` PyPI release.
- **0.3, documents, lifecycle and hardening (open)**:
  - `DocumentStorePort` and `ReasonerPort` in `core/ports.py`, plus a `document` type with a local fallback (chunking and hybrid search);
  - an rlm-studio adapter behind the `memkernel[rlm]` extra, with an `ask(ref_id, question, mode="auto")` tool whose modes are Direct, RAG, RLM and auto;
  - an opt-in `consolidate(synthesize=True)` that uses the reasoner;
  - `memkernel.lifecycle.MemoryLifecycle` (`on_session_start`, `on_pre_compact`, `on_post_compact`, `on_session_end`), so hooks and haa call one component;
  - `procedure` memories as executable Voyager-style skills, with the metadata `language`, `entrypoint`, `verified` and `verification_cmd`, which haa runs in its sandbox.
- **0.3 hardening, adapted from sibling projects (open)**:
  - from document-assistant: BM25 index persistence, recording the embedding model in Chroma collection metadata (and refusing to mix vector spaces), and prompt-injection sanitising of recalled content;
  - from rlm-studio: token-budgeted hook output;
  - merging near-duplicates by embedding distance at `retain` time (the cheap "surprise" gate). 0.4 already reports near-duplicate pairs read-only in `health()`, but the merge gate is still open;
  - an optional cross-encoder reranker behind a port;
  - a `memkernel retain|recall|consolidate --json` CLI for non-MCP harnesses (Pi, Codex, haa scripts);
  - LongMemEval-style eval categories for knowledge updates and abstention.
- **0.4, code revalidation and store health (shipped)**:
  - `revalidate()` checks a hash of each `code` snapshot's whole file and sets a `needs_review` flag that excludes the memory from recall;
  - code identity is `(source, hash)`, and code is superseded automatically by path, leaving a durable `superseded_by` marker;
  - `health()` reports orphans, dangling links, unmarked supersessions, stale sources, flagged memories, expired-but-present memories and near-duplicates.

  Still open: a health fix mode, whose first action backfills `superseded_by` for links from 0.2 and 0.3, and invalidation of individual chunk ranges (0.4 hashes whole files).
- **0.5, ecosystem (open)**:
  - extract ai-wiki as a package that uses only the standard library, with a `memkernel[wiki]` extra that exposes `wiki query` and `wiki lint --health`;
  - build a new `ragkit` from `document-assistant/src/rag/` without langchain;
  - move CCT's hooks onto the factory and set `MEMKERNEL_WIKI_DIR=knowledge/wiki`;
  - add `harness/tools/memory.py` and lifecycle hooks to haa.
- **Cross-repository sequence**:
  1. memkernel 0.2.0 on PyPI, which unblocks CCT's `setup.sh --memkernel` without a path and lets haa pin a version.
  2. ai-wiki 0.1.0, extracted from CCT: the schema, `lint-wiki.sh` and `scripts/wiki_ingest`, an `ingest`/`promote`/`query`/`lint` CLI, and backends `claude`, `codex`, `cursor` and `test`.
  3. rlm-studio 1.0.0, published as is, which freezes `interact()`, the mode names, `StoragePort`, `EmbeddingPort` and `RLMKitClient` as its public contract.
  4. memkernel 0.3.0, which depends on steps 1–3.
  5. rlm-studio 1.1.0, a hybrid mode designed from `ask()` traces.
  6. haa memory and lifecycle wiring, which depends on step 4.
  7. CCT consumes ai-wiki and memkernel 0.3, which depends on steps 2 and 4.
  8. document-assistant is relicensed and becomes ragkit, which waits on a licensing decision. memkernel 0.4 is expected to depend on ragkit.

  Steps 2 and 3 run in parallel with step 1. Step 8 comes last because nothing is blocked on it.
- **Research backlog (opt-in or conditional)**:
  - a background `SummarizerPort` (Letta sleep-time consolidation), never required;
  - bi-temporal `valid_from`/`valid_to` intervals (Zep/Graphiti);
  - a graph layer with personalised PageRank (HippoRAG 2), only if flat recall shows multi-hop failures;
  - a JEPA-style next-state predictor, as research only.

  Git-diff-driven invalidation is marked shipped, as the 0.4 whole-file hash check, which does not depend on git.
- **How this relates to other pages**: as of 2026-10-11, the roadmap still lists `MemoryLifecycle`, `DocumentStorePort`, `ReasonerPort`, `ask`, PyPI publication and the CHANGELOG as open. This matches the statements the harness-integration page flags as possibly stale, and it conflicts with the README-based pages, which describe them as existing. Check the current release before relying on either.

## Where this shows up

- `eval/navigation/corpus/docs/roadmap.md`: the roadmap itself, with release checklists, the cross-repository table and the research backlog.
- `docs/research/sibling-projects.md` and ADR-009 in the memkernel repo, which the 0.3 section cites. Neither is in this corpus.
- The memkernel targets the roadmap names: `core/ports.py`, `memkernel/adapters/rlmstudio.py`, `memkernel.lifecycle.MemoryLifecycle` and `memkernel.factory.build_service()`.
- The extras: `memkernel[rlm]` and `memkernel[wiki]`.

## Related

- [Integrating MemKernel into agent harnesses (code-copilot-team and haa)](memkernel-harness-integration.md)
- [MemKernel tiered memory model](memkernel-tiered-memory.md)
- [MemKernel LLM-wiki bridge and store health](memkernel-wiki-bridge-and-health.md)
- [ADR-007: tiered memory with supersession for facts and decay for experience](../decisions/memkernel-tiered-memory-decision.md)
- [ADR-008: an LLM wiki is the human-readable form of long-term memory](../decisions/memkernel-wiki-semantic-layer-decision.md)
- [Agent-memory literature behind MemKernel's design (2024–2026 review)](memkernel-memory-literature-review.md)
```

## index.md
**Action:** append-index  
**Rationale:** Links the new page from index.md so it is reachable. It joins the Concepts list that ends the index.

```markdown
- [MemKernel roadmap and the cross-repository release sequence](concepts/memkernel-roadmap.md): 0.2–0.5 release status (0.4 shipped, 0.3 open), hardening adapted from sibling projects, the eight-step order of work across repositories gated on published artefacts, and the research backlog
```

## log.md
**Action:** append-log  
**Rationale:** Required log entry for the new page.

```markdown
- 2026-10-16 — create memkernel-roadmap (concept): release checklists for 0.2–0.5, the order of work across repositories gated on published artefacts, and the research backlog from the MemKernel roadmap
```
