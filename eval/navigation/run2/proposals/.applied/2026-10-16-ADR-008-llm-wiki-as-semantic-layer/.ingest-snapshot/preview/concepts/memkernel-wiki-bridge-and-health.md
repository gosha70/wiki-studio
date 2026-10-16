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
