---
page_type: decision
slug: memkernel-wiki-semantic-layer-decision
title: "ADR-008: an LLM wiki is the human-readable form of long-term memory"
status: stable
last_reviewed: 2026-10-16
sources:
  - path: eval/navigation/corpus/docs/adr/ADR-008-llm-wiki-as-semantic-layer.md
    sha: 8b7f14d
---

# ADR-008: an LLM wiki is the human-readable form of long-term memory

## Decision

MemKernel accepted this decision on 2026-10-11:

1. **The long-term semantic tier has two representations, and they must agree.** The vector store is queryable and keeps scores and provenance. The wiki is readable, versioned in git and cited. **The wiki is the source of truth for curated knowledge. The store is the wiki's index and also holds everything that has not been curated yet.**
2. **`memkernel.wiki` bridges the two without an LLM.**
   - `WikiExporter` turns each long-term memory that has no page yet into a *draft* page. A draft has `status: draft`, the required H2 sections, placeholder text for anything the memory does not record, and a `memkernel://<project>/<ref_id>` citation. The exporter also adds entries to `index.md` and `log.md`. It never overwrites an existing page.
   - `WikiImporter` indexes curated pages as long-term memories tagged `wiki`, `page:<slug>` and `page_type:<type>`. Importing an unchanged page creates no new memory. A changed page supersedes the memory made from its earlier version. Deprecated pages are skipped.
   - Pages follow code-copilot-team's (CCT) page schema, so the drafts the exporter writes pass CCT's linter.
3. **Type mapping.**
   - Export: `decision` → `decision`, `convention` and `fact` → `concept`, `procedure` → `workflow`. `code` memories are never exported, because code lives in the repo.
   - Import: `concept`, `overview`, `glossary`, `incident` and `open-question` → `fact`. `workflow` and `playbook` → `procedure`.
4. **Repository recommendation.** The wiki maintainer should be extracted from CCT into a new standalone repository, working name `gosha70/ai-wiki`. It covers the schema, the linter and the ingest/promote/query/lint CLI. It would be published as a Python package that uses only the standard library at runtime, with an optional LLM backend.
   - memkernel depends on that package through an optional extra, `memkernel[wiki]`, for the operations that need an LLM.
   - The bridge itself stays in memkernel because it needs the store.
   - CCT and document-assistant use the same package.

## Context

Karpathy's LLM Wiki pattern (gist, April 2026) stops re-deriving knowledge on every query. Instead, the LLM maintains a persistent, interlinked markdown wiki made of these parts:

- `raw/`: immutable sources;
- `wiki/`: the pages the LLM writes;
- a schema of conventions;
- an `index.md` that is read first on every query;
- an append-only `log.md`;
- three operations: ingest, query and lint.

Vellum Labs measured the pattern on a 1,200-line library. It produced 21 pages in about 12 minutes for $6.96. Their conclusion was that the wiki is not a cheaper RAG. It is where decisions, rules and measured results that *are not in the source* get recorded.

code-copilot-team already runs this pattern:

- `knowledge/wiki/` with nine page types;
- YAML frontmatter with mandatory citations;
- a structural linter;
- `scripts/wiki_ingest/`, which provides ingest, promote, query and health-lint. It is stdlib-only, has 117 tests and calls the LLM through a subprocess backend.

CCT's own decision record says the wiki is *not* session memory, and that recall in the style of memkernel complements it.

The ADR splits the work between the two stores:

- A vector store is the right home for content that is not wiki-worthy (episodes, observations, working state) and for *finding* things.
- Markdown in git is the right home for curated, cited, human-reviewed knowledge.

## Alternatives considered

- **Put the wiki tooling inside memkernel.** Rejected: it would tie a memory server to markdown maintenance and to an LLM backend, and CCT would then depend on memkernel for something unrelated to memory.
- **Leave the tooling inside CCT.** It works today, but memkernel and document-assistant could not reuse it. CCT's own decoupling principle (shared sources produce generated adapters) also argues for extracting it.
- **Vector store only, no wiki.** Simplest, but it gives up human review, citations, git history and index-first navigation. The measured results favour index-first navigation for decisions and rules.
- **Wiki only, no vector store.** Works for curated knowledge up to a few hundred pages. It cannot handle episodic memory, scoring, decay or scratch state shared between agents.

## Consequences

- **New tools and setting.** memkernel gains two MCP tools, `wiki_export` and `wiki_import`, and a `MEMKERNEL_WIKI_DIR` setting.
- **A curation loop.** Export drafts, have a human or agent curate them, then import. Until `ai-wiki` exists, CCT's `scripts/wiki promote` acts as the curator.
- **Traceability both ways.** Exported pages carry `memkernel_ref` in their frontmatter, so a page can be traced back to the memory it came from. Imported memories carry the page path as their `source`.
- **The page schema becomes a shared contract** between memkernel, ai-wiki and CCT.
- **Follow-up work.**
  - Create the `ai-wiki` repo through an extraction PR against CCT.
  - Add the `memkernel[wiki]` extra, which exposes `wiki query` and `wiki lint --health` as tools.

## Related

- [MemKernel LLM-wiki bridge and store health](../concepts/memkernel-wiki-bridge-and-health.md)
- [MemKernel tiered memory model](../concepts/memkernel-tiered-memory.md)
- [ADR-007: tiered memory with supersession for facts and decay for experience](memkernel-tiered-memory-decision.md)
