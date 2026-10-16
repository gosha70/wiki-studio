# Proposal: 2026-10-16-ADR-008-llm-wiki-as-semantic-layer

**Rationale:** Gate passes. (1) Reusable: ADR-008 explains why MemKernel's long-term tier has two representations, a vector store and a wiki, and which one is the source of truth. It also gives the type mapping between them and the reason the wiki tooling moves into a standalone repo. Future contributors to memkernel, ai-wiki and code-copilot-team will need this. (2) Citable: it is a repo file in the eval corpus. (3) Non-duplicative: the existing concept page memkernel-wiki-bridge-and-health describes how export and import work, taken from the README. It only points to ADR-008 by path and does not record the decision, the alternatives or the consequences. No decision page covers it, so this patch creates one, matching how ADR-007 got its own decision page. (4) New-contributor-relevant: anyone working on the wiki bridge or the ai-wiki extraction needs this rationale. Patch-set: create decisions/memkernel-wiki-semantic-layer-decision.md. Update the concept page with what the ADR adds beyond the README: the memory-type to page-type mapping, the import tags, skipping deprecated pages, the memkernel_ref frontmatter, imported memories carrying the page path as source, and the citation to ADR-008. Append a log entry and link the new page from index.md under Decisions.

## decisions/memkernel-wiki-semantic-layer-decision.md
**Action:** create  
**Rationale:** No existing page records ADR-008's decision, context, alternatives or consequences. A decision page matches the page type and mirrors the ADR-007 page.

```markdown
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
```

## concepts/memkernel-wiki-bridge-and-health.md
**Action:** update  
**Rationale:** The page gains what ADR-008 adds beyond the README: the source-of-truth split, both type mappings, the import tags, skipping deprecated pages, memkernel_ref and the source back-link. It also cites ADR-008 and links the new decision page.

```markdown
---
page_type: concept
slug: memkernel-wiki-bridge-and-health
title: MemKernel LLM-wiki bridge and store health
status: draft
last_reviewed: 2026-10-16
sources:
  - path: eval/navigation/corpus/README.md
    sha: 8b7f14d
  - path: eval/navigation/corpus/docs/adr/ADR-008-llm-wiki-as-semantic-layer.md
    sha: 8b7f14d
---

# MemKernel LLM-wiki bridge and store health

## Summary

MemKernel's long-term memory has a human-readable twin: a git-versioned markdown wiki that follows the Karpathy LLM-wiki pattern. It uses the same page schema as ai-wiki and `code-copilot-team/knowledge/wiki`. Under ADR-008, the wiki is the source of truth for curated knowledge, and the vector store is its index plus the home of everything not yet curated. `wiki_export` drafts pages from long-term memories, and `wiki_import` indexes curated pages back into long-term memory. Separately, revalidation and health passes keep the store honest about stale code snapshots and broken links.

## Key ideas

- **Two representations, one truth**: the vector store is for finding things and holds content that is not wiki-worthy (episodes, observations, working state). The wiki holds curated, cited, human-reviewed knowledge. The bridge needs no LLM.
- **Export**: `wiki_export` compiles each long-term memory that has no page yet into a **draft** page under `decisions/`, `concepts/` or `workflows/`.
  - Each draft has the required sections, placeholder text for anything the memory does not record, a `memkernel://<project>/<ref_id>` citation and a `memkernel_ref` frontmatter key.
  - Existing pages are never overwritten, and `index.md` and `log.md` are updated.
- **Export mapping**: `decision` → `decision`, `convention` and `fact` → `concept`, `procedure` → `workflow`. `code` memories are never exported, because code lives in the repo.
- **Import**: `wiki_import` indexes the curated pages as long-term memories so that `recall` returns the reviewed version.
  - Imported memories are tagged `wiki`, `page:<slug>` and `page_type:<type>`, and carry the page path as their `source`.
  - Import is idempotent: unchanged pages create no new memory, a changed page supersedes the memory created from its earlier version, and deprecated pages are skipped.
- **Import mapping**: `concept`, `overview`, `glossary`, `incident` and `open-question` → `fact`. `workflow` and `playbook` → `procedure`.
- **Curation loop**: export, have a human or agent review the drafts, then import. `MEMKERNEL_WIKI_DIR` (for example `knowledge/wiki`) or a `wiki_dir` argument selects the wiki. The page schema is the shared contract defined in ADR-008.
- **Revalidation**: `revalidate()` hashes each `code` memory's whole source file.
  - A changed file flags the memory `needs_review` (`changed`), a missing file flags it `missing`, and a matching file clears the flag.
  - Flagged memories drop out of default recall until the file is retained again.
- **Revalidation triggers**: `consolidate(revalidate=true)`, every session start (through `MemoryLifecycle.on_session_start()`) and `POST /revalidate`. Sources resolve under `MEMKERNEL_PROJECT_ROOT`, and nothing outside that root is ever read.
- **Health audit**: `health()` reports problems without changing anything. It checks for:
  - orphaned chunk and document records;
  - dangling supersession and provenance links;
  - missing code sources and flagged memories;
  - expired memories that have not been purged;
  - in full mode, near-duplicates (cosine ≥ `MEMKERNEL_HEALTH_DUPLICATE_THRESHOLD`, default 0.95).

  The quick report is part of every `consolidate()`. The full report is at `GET /health/store`.

## Where this shows up

- `eval/navigation/corpus/README.md`: the sections "LLM wiki bridge" and "Revalidation and store health".
- `eval/navigation/corpus/docs/adr/ADR-008-llm-wiki-as-semantic-layer.md`: the decision record for the two representations, the type mapping and the ai-wiki extraction.
- memkernel package: `src/memkernel/wiki/` (page model, `WikiExporter`, `WikiImporter`) and the admin API in `src/memkernel/api/`.
- The optional `memkernel[wiki]` extra, which depends on the standalone ai-wiki package for the operations that need an LLM.

## Related

- [ADR-008: an LLM wiki is the human-readable form of long-term memory](../decisions/memkernel-wiki-semantic-layer-decision.md)
- [MemKernel tiered memory model](memkernel-tiered-memory.md)
- [Register MemKernel with Claude Code](../workflows/memkernel-claude-code-setup.md)
```

## log.md
**Action:** append-log  
**Rationale:** This is the required dated log entry for the new page and the concept update.

```markdown
- 2026-10-16 — create memkernel-wiki-semantic-layer-decision (decision): ADR-008 rationale for the wiki as source of truth of curated long-term memory, the bridge mapping and the ai-wiki extraction; update memkernel-wiki-bridge-and-health (concept) with the type mappings, import tags and memkernel_ref traceability from ADR-008
```

## index.md
**Action:** append-index  
**Rationale:** This links the new decision page from the Decisions section so it can be reached from index.md.

```markdown
- [ADR-008: an LLM wiki is the human-readable form of long-term memory](decisions/memkernel-wiki-semantic-layer-decision.md): wiki is the source of truth for curated knowledge, the store is its index; export/import mapping; extract the wiki tooling into ai-wiki; rejected alternatives
```
