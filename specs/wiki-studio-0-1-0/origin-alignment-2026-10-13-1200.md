# Origin alignment check — wiki-studio-0-1-0

Gate: phase complete (Gate 3), 2026-10-13 12:00 local, after merging main's rename of the bundle (commit 11f650a) into the feature branch.

Origin: https://github.com/gosha70/memkernel/blob/main/docs/roadmap.md (step 2), corroborated by https://github.com/gosha70/memkernel/blob/main/docs/adr/ADR-008-llm-wiki-as-semantic-layer.md and https://github.com/gosha70/code-copilot-team/blob/master/specs/wiki-ingest-pipeline/spec.md; all read in full from local checkouts in this build session. The earlier record (origin-alignment-2026-10-12-2240.md) covers the same sources at build entry.

Origin claim:
> Create a new repository for extracting and enhancing the LLM Wiki (owner decision, confirmed in the memkernel planning session and recorded as step 2 of memkernel's docs/roadmap.md): move code-copilot-team's knowledge/wiki/schema, its linter and scripts/wiki_ingest (ingest, promote, query, health-lint, 240 tests, stdlib-only) into gosha70/wiki-studio as a standalone package that code-copilot-team, memkernel and document-assistant consume. Build it the fastest, most automated way with code-copilot-team's build loop and DeepSeek as the code reviewer. Distribution name was `aiwiki` (chosen because `ai-wiki` is taken on PyPI) and was renamed `wikistudio` by main's commit 11f650a. 0.1.0 is the extraction with the paths decoupled; an MCP server and memkernel's extra come later.

Working claim:
> The branch delivers the Poetry project `wikistudio` (import `wikistudio`, console script `wiki-studio`, `WIKISTUDIO_*` variables, no runtime dependencies): every module of scripts/wiki_ingest moved with behaviour, verbs, flags and exit codes unchanged; one WikiPaths resolver with defaults identical to the old layout; the six linter checks in Python; the pi capability lookup replaced by WIKISTUDIO_ENABLE_PI; schema documents as package data with a per-wiki override; a library API; a fixture wiki pinning memkernel's exported page shape; a consumer guide; CI on 3.11–3.13 and a trusted-publishing release workflow. The 240 tests moved and 148 were added.

Mismatches:
  - none. The package, script, distribution and variable names now match the renamed spec; the GitHub repository was renamed to gosha70/wiki-studio after the merge, matching the origin URL in plan.md.

Verdict: aligned
Confidence: high
