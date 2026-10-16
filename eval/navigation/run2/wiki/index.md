---
page_type: index
slug: index
title: Navigation evaluation index
status: stable
last_reviewed: 2026-10-16
---

# Navigation evaluation index

## Concepts

- [MemKernel tiered memory model](concepts/memkernel-tiered-memory.md): working, short-term and long-term tiers; retention; recall scoring
- [MemKernel LLM-wiki bridge and store health](concepts/memkernel-wiki-bridge-and-health.md): wiki_export and wiki_import, revalidation, health audit

## Workflows

- [Register MemKernel with Claude Code](workflows/memkernel-claude-code-setup.md): install with pipx, configure the MCP server, add CLAUDE.md instructions and hooks

## Playbooks

- [MemKernel install troubleshooting](playbooks/memkernel-install-troubleshooting.md): interpreter range, stale PATH, hanging --help, slow first connection
## Decisions

- [ADR-007: tiered memory with supersession for facts and decay for experience](decisions/memkernel-tiered-memory-decision.md): why tiers, supersession and access-boosted decay; rejected alternatives (more TTLs, in-server LLM consolidation, graph/PPR, per-tier collections)
- [ADR-008: an LLM wiki is the human-readable form of long-term memory](decisions/memkernel-wiki-semantic-layer-decision.md): wiki is the source of truth for curated knowledge, the store is its index; export/import mapping; extract the wiki tooling into ai-wiki; rejected alternatives
## Concepts

- [Integrating MemKernel into agent harnesses (code-copilot-team and haa)](concepts/memkernel-harness-integration.md): the build_service factory, MemoryLifecycle as a component, tier vocabulary and tags for phase agents, project/session namespaces, the wiki round-trip, haa in-process plan
- [Agent-memory literature behind MemKernel's design (2024–2026 review)](concepts/memkernel-memory-literature-review.md): what MemKernel takes from MemGPT, Mem0, Zep, Generative Agents, MemoryBank and others; Roynard's supersession-vs-decay split; contested HRM results; benchmark caveats; eight adopted implications and what is deferred
- [MemKernel roadmap and the cross-repository release sequence](concepts/memkernel-roadmap.md): 0.2–0.5 release status (0.4 shipped, 0.3 open), hardening adapted from sibling projects, the eight-step order of work across repositories gated on published artefacts, and the research backlog
