# Origin alignment check — wikiforge-0-1-0

Gate: build entry (Gate 2), 2026-10-12 22:40 local.

Origin: https://github.com/gosha70/memkernel/blob/main/docs/roadmap.md (step 2 of the "0.3 — ecosystem" delivery table), corroborated by https://github.com/gosha70/memkernel/blob/main/docs/adr/ADR-008-llm-wiki-as-semantic-layer.md and https://github.com/gosha70/code-copilot-team/blob/master/specs/wiki-ingest-pipeline/spec.md. All three read in full from the local checkouts this session; https://github.com/gosha70/ai-wiki is the target repository itself (README: "Productized implementation of LLM Wiki for Memory and Context Management in Agentic Architecture").

Origin claim:
> Create a new repository for extracting and enhancing the LLM Wiki (owner decision, confirmed in the memkernel planning session and recorded as step 2 of memkernel's docs/roadmap.md): move code-copilot-team's knowledge/wiki/schema, its linter and scripts/wiki_ingest (ingest, promote, query, health-lint, 240 tests, stdlib-only) into gosha70/ai-wiki as a standalone package that code-copilot-team, memkernel and document-assistant consume. Build it the fastest, most automated way with code-copilot-team's build loop and DeepSeek as the code reviewer. Distribution name is `wikiforge` because `wikiforge` is taken on PyPI. 0.1.0 is the extraction with the paths decoupled; an MCP server and memkernel's extra come later.

Roadmap step 2 verbatim: "wikiforge | `0.1.0`: move `knowledge/wiki/schema`, `lint-wiki.sh` and `scripts/wiki_ingest` from CCT; `wikiforge` CLI (`ingest`, `promote`, `query`, `lint`); backends `claude`, `codex`, `cursor`, `test` | nothing in code (extraction) | CCT thin wrapper; `memkernel[wiki]`".

Working claim:
> spec.md delivers a Poetry project `wikiforge` (import `wikiforge`, console script `wikiforge`) with no runtime dependencies, into which every module of `code-copilot-team/scripts/wiki_ingest/` is moved unchanged except for import paths, licence headers and the decoupling the FRs name: one `WikiPaths` object (flags, `WIKIFORGE_*` variables, defaults identical to the old `knowledge/wiki` / `doc_internal` layout), the six checks of `lint-wiki.sh` ported to Python, the `pi` capability-file lookup removed, the six schema documents shipped as package data with a per-wiki override. The five verbs `ingest`, `promote`, `query`, `lint`, `audit-flush` keep their flags and exit codes. The 240 tests move with the code. It adds a library API (`wikiforge.api`), a fixture wiki that pins memkernel's exported page shape, a consumer guide for code-copilot-team, memkernel and document-assistant, CI on 3.11–3.13 and a PyPI trusted-publishing release workflow. Explicitly excluded: MCP server, HTTP API, schema changes, new backends, edits to the consumer repositories.

Mismatches:
  - none. The roadmap row lists four verbs; the source tree already has a fifth (`audit-flush`) that the spec preserves, which is a superset the "nothing in code (extraction)" column requires, not a deviation. The roadmap names `lint-wiki.sh` as something to move; the spec moves its checks (as Python) rather than the bash file, which the origin claim's "paths decoupled" and "standalone package" require, since a wheel cannot ship a bash linter anchored to a repository path. The memkernel extra and MCP server are deferred by the origin claim itself.

Verdict: aligned
Confidence: high
