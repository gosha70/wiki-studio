# Origin alignment check — wiki-studio-0-1-0

Gate: phase complete (Gate 3), 2026-10-13 21:00 local. Owner decision (PR #3 review): the import name follows the hyphen-to-underscore convention. Distribution, command and repository stay `wiki-studio`; the Python package is `wiki_studio` and the variables are `WIKI_STUDIO_*`. No compatibility aliases for the unreleased names (`aiwiki`, `wikiforge`, `wikistudio`).

Origin: https://github.com/gosha70/memkernel/blob/main/docs/roadmap.md (step 2), corroborated by https://github.com/gosha70/memkernel/blob/main/docs/adr/ADR-008-llm-wiki-as-semantic-layer.md and https://github.com/gosha70/code-copilot-team/blob/master/specs/wiki-ingest-pipeline/spec.md; all read in full from local checkouts in this build session. The three earlier records (2026-10-12-2240, 2026-10-13-1200, 2026-10-13-2000) are kept as written and describe the names in use at the time.

Origin claim:
> Create a new repository for extracting and enhancing the LLM Wiki (owner decision, confirmed in the memkernel planning session and recorded as step 2 of memkernel's docs/roadmap.md): move code-copilot-team's knowledge/wiki/schema, its linter and scripts/wiki_ingest (ingest, promote, query, health-lint, 240 tests, stdlib-only) into gosha70/wiki-studio as a standalone package that code-copilot-team, memkernel and document-assistant consume. Build it the fastest, most automated way with code-copilot-team's build loop and DeepSeek as the code reviewer. The repository was created as ai-wiki and renamed wiki-studio because `ai-wiki` is taken on PyPI, `wikiforge` is too similar to the existing `wiki-forge`, and the name should say knowledge, not memory. 0.1.0 is the extraction with the paths decoupled; an MCP server and memkernel's extra come later.

Working claim:
> The branch delivers the Poetry project `wiki-studio` (import `wiki_studio`, console script `wiki-studio`, `WIKI_STUDIO_*` variables, no runtime dependencies): every module of scripts/wiki_ingest moved with behaviour, verbs, flags and exit codes unchanged; one WikiPaths resolver with defaults identical to the old layout; the six linter checks in Python; the pi capability lookup replaced by WIKI_STUDIO_ENABLE_PI; schema documents as package data with a per-document project override; a library API; a fixture wiki pinning memkernel's exported page shape; a consumer guide; CI on 3.11–3.13 and a trusted-publishing release workflow. 240 tests moved, 148 added.

Mismatches:
  - none. Package, script, distribution, variable and repository names match the spec as amended by this decision (FR-001, FR-004, FR-006, ADR-5); the import name is the conventional underscore form of the distribution name.

Verdict: aligned
Confidence: high
