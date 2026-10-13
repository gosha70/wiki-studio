# Origin alignment check — wiki-studio-0-1-0

Gate: phase complete (Gate 3), 2026-10-13 20:00 local, after the second rename of the package (wikiforge → wiki-studio, because PyPI rejects `wikiforge` as too similar to the existing `wiki-forge`).

Origin: https://github.com/gosha70/memkernel/blob/main/docs/roadmap.md (step 2), corroborated by https://github.com/gosha70/memkernel/blob/main/docs/adr/ADR-008-llm-wiki-as-semantic-layer.md and https://github.com/gosha70/code-copilot-team/blob/master/specs/wiki-ingest-pipeline/spec.md; all read in full from local checkouts in this build session. The two earlier records (2026-10-12-2240, 2026-10-13-1200) cover the same sources.

Origin claim:
> Create a new repository for extracting and enhancing the LLM Wiki (owner decision, confirmed in the memkernel planning session and recorded as step 2 of memkernel's docs/roadmap.md): move code-copilot-team's knowledge/wiki/schema, its linter and scripts/wiki_ingest (ingest, promote, query, health-lint, 240 tests, stdlib-only) into gosha70/wiki-studio as a standalone package that code-copilot-team, memkernel and document-assistant consume. Build it the fastest, most automated way with code-copilot-team's build loop and DeepSeek as the code reviewer. The repository was created as ai-wiki and renamed wiki-studio because `ai-wiki` is taken on PyPI, `wikiforge` is too similar to the existing `wiki-forge`, and the name should say knowledge, not memory. 0.1.0 is the extraction with the paths decoupled; an MCP server and memkernel's extra come later.

Working claim:
> The branch delivers the Poetry project `wiki-studio` (import `wikistudio`, console script `wiki-studio`, `WIKISTUDIO_*` variables, no runtime dependencies): every module of scripts/wiki_ingest moved with behaviour, verbs, flags and exit codes unchanged; one WikiPaths resolver with defaults identical to the old layout; the six linter checks in Python; the pi capability lookup replaced by WIKISTUDIO_ENABLE_PI; schema documents as package data with a per-document project override; a library API; a fixture wiki pinning memkernel's exported page shape; a consumer guide; CI on 3.11–3.13 and a trusted-publishing release workflow. 240 tests moved, 148 added.

Mismatches:
  - none. Package, script, distribution, variable and repository names match the renamed spec; the import name differs from the distribution only because module names cannot contain hyphens (ADR-5).

Verdict: aligned
Confidence: high
