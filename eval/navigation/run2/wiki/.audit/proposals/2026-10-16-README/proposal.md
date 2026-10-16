# Proposal: 2026-10-16-README

**Rationale:** Gate passed. (1) Reusable: the README describes MemKernel's memory model, MCP tools, setup, configuration and wiki bridge, and contributors will need these in later sessions. (2) Citable: repo file eval/navigation/corpus/README.md at 8b7f14d. (3) Non-duplicative: the wiki is empty apart from index and log. (4) New-contributor-relevant: anyone using or integrating MemKernel needs the tier model, the setup procedure and the install fixes. The source covers four separate topics, so this patch creates four pages, links each from index.md and adds one log line per page: the tiered memory model (concept), registering MemKernel with Claude Code (workflow), fixing install and first-connection problems (playbook), and the LLM-wiki bridge with revalidation (concept).

## concepts/memkernel-tiered-memory.md
**Action:** create  
**Rationale:** This is the core mental model of the source: tiers, types, retention and the recall scoring formula. It is durable knowledge rather than a procedure, so it is a concept page.

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
---

# MemKernel tiered memory model

## Summary

MemKernel is a code-aware MCP memory server that gives AI coding copilots persistent memory across sessions and context compactions. Memories live in three tiers with different persistence rules: working memory (hours), short-term memory (decays unless recalled) and long-term memory (never decays and is replaced only by supersession). Recall ranks results by a weighted mix of relevance, recency and importance.

## Key ideas

- **Working tier**: `task` memories hold the current goal, plan state and open questions. Default importance is 0.5 and the TTL is 24 hours (`MEMKERNEL_TASK_TTL_HOURS`).
- **Short-term tier**: `episode` memories (session events and compaction checkpoints; importance 0.4, 30 days) and `observation` memories (findings and tool outputs; importance 0.3, 7 days).
- **Long-term tier**: the types are `decision` (0.9), `convention` (0.9), `fact` (0.7), `procedure` (0.8), `code` (0.6) and `document` (0.6). None of them expires. To replace one, retain a new memory with `supersedes=<ref_id>`, which hides the old one from recall.
- **Retention formula**: `ttl = base_ttl × (1 + access_boost × access_count)`, measured from the later of creation and last access. Each recall therefore extends a short-term memory's life (`MEMKERNEL_ACCESS_BOOST`, default 0.5).
- **Recall scoring**: a weighted sum of hybrid-search relevance (weight 1.0), recency (0.3, with a 7-day half-life on the short-term tier) and importance (0.3). All three weights are configurable through `MEMKERNEL_RECALL_WEIGHT_*`.
- **Code-aware retrieval**: tree-sitter AST chunking splits files at function and class boundaries, and hybrid search combines dense embeddings, BM25 and reciprocal rank fusion (`MEMKERNEL_RRF_K`, default 60). This handles both semantic queries and exact identifier lookup.
- **Moving knowledge to long-term**: `consolidate` purges expired short-term memories and ranks promotion candidates by importance × recall count. `promote(ref_id, type, content)` then writes a distilled long-term memory that records where it came from in `promoted_from`.
- **Documents**: `retain(type="document")` stores a large artefact's body in a document store and indexes it in chunks. `ask(ref_id, question, mode)` answers questions through a `ReasonerPort`: `local` (hybrid search over the chunks, no LLM) or `rlmstudio`. Do not call `get` on a document to read it.
- **Session protocol**: at session start, recall long-term context and the latest checkpoint. While working, retain tasks and observations. Before compaction, retain a checkpoint episode and run consolidate. Afterwards, promote the candidates worth keeping. `MemoryLifecycle` packages this protocol for embedding harnesses.

## Where this shows up

- `eval/navigation/corpus/README.md`: the sections "Memory types and tiers", "Session protocol", "Configuration" and "Documents and `ask`".
- MCP tools: `retain`, `recall`, `get`, `forget`, `promote`, `consolidate`, `ask`, `wiki_export` and `wiki_import`.
- Package layout: `src/memkernel/core/` (models, `MemoryService`, ports), `memory/` (TTL and decay policies), `retrieval/` (chunking, hybrid search), `lifecycle.py` (`MemoryLifecycle`) and `factory.py` (`build_service()`, the supported embedding entry point).
- The design document the README points to: `docs/architecture/memory-tiers.md` in the memkernel repo.

## Related

- [Register MemKernel with Claude Code](../workflows/memkernel-claude-code-setup.md)
- [MemKernel LLM-wiki bridge and store health](memkernel-wiki-bridge-and-health.md)
- [MemKernel install troubleshooting](../playbooks/memkernel-install-troubleshooting.md)
```

## workflows/memkernel-claude-code-setup.md
**Action:** create  
**Rationale:** The install and registration procedure is a numbered, end-to-end path, so it is a workflow page.

```markdown
---
page_type: workflow
slug: memkernel-claude-code-setup
title: Register MemKernel with Claude Code
status: draft
last_reviewed: 2026-10-16
sources:
  - path: eval/navigation/corpus/README.md
    sha: 8b7f14d
---

# Register MemKernel with Claude Code

## When to use this

Use this when you want a Claude Code project, or any MCP-compatible copilot, to keep decisions, conventions and code understanding across sessions and context compactions by using MemKernel as a stdio MCP server.

## Steps

1. Check that Python 3.11–3.13 is available. The package declares `Requires-Python >=3.11,<3.14`.
2. Install the package in isolation with `pipx install memkernel`, adding `--python python3.11` if pipx's default interpreter is outside that range. MemKernel is a PyPI package only: any suggestion to install it with `npx` is a hallucination. Do not `pip install` it into a shared or system interpreter, because it pins `chromadb` 1.x and a recent `cffi` and can break other tools.
3. Verify the install with `which memkernel` or `pipx list`. `memkernel --version` and `--help` print and exit; running `memkernel` with no arguments starts the server on stdio.
4. Add an entry under `mcpServers.memkernel` in the project's `.claude/settings.json`. Use the **absolute** command path (the output of `which memkernel`), and set `MEMKERNEL_PROJECT_ID` (memories are isolated per project) and an absolute `MEMKERNEL_CHROMA_PERSIST_PATH` outside the repository.
5. Copy `templates/claude-memory-instructions.md` into the project's `CLAUDE.md` so the agent knows when to call the memory tools.
6. Optional: copy `templates/hooks/` into `.claude/hooks/` and register `session-start.py` (`SessionStart`), `pre-compact.py` (`PreCompact`) and `post-compact.py` (`PostCompact`). Each one is a thin wrapper over `MemoryLifecycle`.
7. For Kiro, copy the three files under `templates/kiro/` instead: `settings/mcp.json`, `steering/memory.md` and `hooks/memkernel.json`.
8. Expect the first connection to be slow. `build_service()` downloads the roughly 90 MB embedding model (`all-MiniLM-L6-v2`) when the server starts, before any tool call runs.

## Verification

- `which memkernel` prints the path you put in `settings.json`.
- Once the first startup finishes, a `retain` call returns a `ref_id`, and a matching `recall` returns that memory.
- Optional: `uvicorn memkernel.api.app:app --port 8766`, then `GET /health`, reports server health and the memory count.

## Related

- [MemKernel install troubleshooting](../playbooks/memkernel-install-troubleshooting.md)
- [MemKernel tiered memory model](../concepts/memkernel-tiered-memory.md)
```

## playbooks/memkernel-install-troubleshooting.md
**Action:** create  
**Rationale:** The README's troubleshooting block describes recurring failures and their fixes, which matches the playbook type.

```markdown
---
page_type: playbook
slug: memkernel-install-troubleshooting
title: MemKernel install troubleshooting
status: draft
last_reviewed: 2026-10-16
sources:
  - path: eval/navigation/corpus/README.md
    sha: 8b7f14d
---

# MemKernel install troubleshooting

## Symptom

One of the following happens:

- `pipx install memkernel` reports "No matching distribution found", or pip reports "from versions: none".
- The shell prints `No such file or directory` for an old `memkernel` path after a reinstall.
- `memkernel --help` hangs.
- The first MCP connection is slow or times out.
- Another tool, such as `langchain-chroma`, breaks after a global pip install.

## Recovery steps

1. **No matching distribution**: the installing interpreter is outside 3.11–3.13. Pass a supported one explicitly, for example `pipx install --python /opt/homebrew/opt/python@3.11/bin/python3.11 memkernel`.
2. **Stale path after a reinstall**: the shell has cached the old location. Run `hash -r` (bash) or `rehash` (zsh), then `which memkernel`.
3. **`--help` hangs**: versions before 0.4.0 had no flags and started the server instead. Press Ctrl-C and upgrade; from 0.4.0 on, `--help` and `--version` print and exit.
4. **Slow first connection**: the server is downloading the embedding model at startup. Wait for it to finish once, or pre-warm the cache in the same environment with `python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"`.
5. **A global pip install broke another tool**: uninstall memkernel from that interpreter, reinstall the versions the other tool needs (for example `chromadb < 0.6`), then install memkernel with pipx.

## Verification

`which memkernel` resolves to the pipx-managed binary, `memkernel --version` prints and exits, the MCP client connects without timing out, and the previously broken tool imports cleanly again.

## Prevention

- Always install MemKernel with pipx or into a project virtual environment, never into Homebrew's or the system's `python3`.
- Put the absolute command path in the MCP config, because Claude Code may not see PATH changes made in your shell profile.
- Pre-warm the embedding model on new machines before the first connection.

## Related

- [Register MemKernel with Claude Code](../workflows/memkernel-claude-code-setup.md)
```

## concepts/memkernel-wiki-bridge-and-health.md
**Action:** create  
**Rationale:** The wiki bridge is the integration point with this project's page schema and deserves its own concept page. Revalidation and health are closely related store-integrity mechanisms, so they are grouped on the same page.

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
```

## index.md
**Action:** append-index  
**Rationale:** Links all four new pages from index.md so they are reachable.

```markdown

## Concepts

- [MemKernel tiered memory model](concepts/memkernel-tiered-memory.md): working, short-term and long-term tiers; retention; recall scoring
- [MemKernel LLM-wiki bridge and store health](concepts/memkernel-wiki-bridge-and-health.md): wiki_export and wiki_import, revalidation, health audit

## Workflows

- [Register MemKernel with Claude Code](workflows/memkernel-claude-code-setup.md): install with pipx, configure the MCP server, add CLAUDE.md instructions and hooks

## Playbooks

- [MemKernel install troubleshooting](playbooks/memkernel-install-troubleshooting.md): interpreter range, stale PATH, hanging --help, slow first connection
```

## log.md
**Action:** append-log  
**Rationale:** Adds one dated log line for each page created.

```markdown
- 2026-10-16 — create memkernel-tiered-memory (concept): tiers, types, retention and recall scoring from the MemKernel README
- 2026-10-16 — create memkernel-claude-code-setup (workflow): install and MCP registration procedure from the MemKernel README
- 2026-10-16 — create memkernel-install-troubleshooting (playbook): install failures and their fixes from the MemKernel README
- 2026-10-16 — create memkernel-wiki-bridge-and-health (concept): wiki export/import, revalidation and health audit from the MemKernel README
```
