---
page_type: concept
slug: memkernel-wiki-bridge-and-health
title: MemKernel LLM-wiki bridge and store health
status: draft
last_reviewed: 2026-10-16
sources:
  - path: eval/navigation/corpus/README.md
    sha: 8b7f14d
---

# MemKernel LLM-wiki bridge and store health

## Summary

MemKernel's long-term memory has a human-readable twin: a git-versioned markdown wiki in the Karpathy LLM-wiki pattern, using the same page schema as ai-wiki and `code-copilot-team/knowledge/wiki`. `wiki_export` drafts pages from long-term memories, and `wiki_import` indexes curated pages back into long-term memory. Separately, revalidation and health passes keep the store honest about stale code snapshots and broken links.

## Key ideas

- **Export**: `wiki_export` compiles each long-term memory that has no page yet into a **draft** page under `decisions/`, `concepts/` or `workflows/`. Each draft has the required sections and a `memkernel://<project>/<ref_id>` citation. Existing pages are never overwritten, and `index.md` and `log.md` are updated.
- **Import**: `wiki_import` indexes the curated pages as long-term memories so that `recall` returns the reviewed version. Import is idempotent, and a changed page supersedes the memory created from its earlier version.
- **Curation loop**: export, review the drafts, then import. `MEMKERNEL_WIKI_DIR` (for example `knowledge/wiki`) or a `wiki_dir` argument selects the wiki. The page schema is the shared contract defined in ADR-008.
- **Revalidation**: `revalidate()` hashes each `code` memory's whole source file. A changed file flags the memory `needs_review` (`changed`), a missing file flags it `missing`, and a matching file clears the flag. Flagged memories drop out of default recall until the file is retained again.
- **Revalidation triggers**: `consolidate(revalidate=true)`, every session start (through `MemoryLifecycle.on_session_start()`) and `POST /revalidate`. Sources resolve under `MEMKERNEL_PROJECT_ROOT`, and nothing outside that root is ever read.
- **Health audit**: `health()` reports without changing anything: orphaned chunk and document records, dangling supersession and provenance links, missing code sources, flagged memories, unpurged expired memories and, in full mode, near-duplicates (cosine ≥ `MEMKERNEL_HEALTH_DUPLICATE_THRESHOLD`, default 0.95). The quick report is part of every `consolidate()`; the full report is at `GET /health/store`.

## Where this shows up

- `eval/navigation/corpus/README.md`: the sections "LLM wiki bridge" and "Revalidation and store health".
- memkernel package: `src/memkernel/wiki/` (page model, export, import) and the admin API in `src/memkernel/api/`.
- Decision record: `docs/adr/ADR-008-llm-wiki-as-semantic-layer.md` in the memkernel repo.

## Related

- [MemKernel tiered memory model](memkernel-tiered-memory.md)
- [Register MemKernel with Claude Code](../workflows/memkernel-claude-code-setup.md)
