---
page_type: concept
slug: memkernel-harness-integration
title: Integrating MemKernel into agent harnesses (code-copilot-team and haa)
status: draft
last_reviewed: 2026-10-16
sources:
  - path: eval/navigation/corpus/docs/integration/harness-integration.md
    sha: 8b7f14d
---

# Integrating MemKernel into agent harnesses (code-copilot-team and haa)

## Summary

MemKernel is meant to be embedded in agent harnesses, not only reached as an MCP server. The integration plan dated 2026-10-11 covers two targets. The first is code-copilot-team (CCT), which already has an experimental MCP-plus-hooks integration that moves to the 0.2 factory and tier vocabulary. The second is haa, a ReAct harness that will use MemKernel in-process as Python components. The plan sets out one rule: every MemKernel capability must be available as a small, stable Python component (`build_service()`, the ports and `MemoryLifecycle`), not only as MCP tools.

## Key ideas

- **One supported entry point**: harness code builds the service with `from memkernel.factory import build_service`. It should not assemble `ChromaVectorStore`, `SentenceTransformerEmbedding`, `BM25Index`, `HybridSearchService` and `ASTChunker` by hand. The 0.1 constructors still work in 0.2, so migrating is not urgent, but the factory is the only path that will be supported going forward.
- **Hooks are thin wrappers over a lifecycle**: `templates/hooks/` in memkernel is the upstream source for harness hook copies. CCT's `memkernel-recall` corresponds to `session-start.py`. `MemoryLifecycle` provides the same behaviour as a component:
  - `on_session_start() -> str`
  - `on_pre_compact(summary) -> str`
  - `on_post_compact() -> str`
  - `on_session_end(summary) -> None`
- **Tier vocabulary for phase agents**: use `task` for the current plan, `observation` for findings, and `fact` or `procedure` for durable knowledge. Call `promote` after a phase completes and `consolidate` at phase boundaries. In CCT's Research → Plan → Build → Review flow:
  - Plan retains `type=task`.
  - Build and Review retain `type=observation`.
  - The `phase-recap` agent promotes decisions and retains successful workflows as `procedure`.

  The handoff files (`specs/<id>/plan.md`, `collaboration/build-review.md`, `phase-*-recap.md`) stay authoritative. Memory supplements them and does not replace them.
- **Scope recall with tags**: tag every memory with `tags=["feature:<id>", "phase:<name>"]` so `recall` can be limited to a feature or phase.
- **Namespaces**: use one `MEMKERNEL_PROJECT_ID` per project root, derived as a slug plus a short hash of the root. Because haa and CCT use the same scheme, haa and Claude Code share memory for the same repo. Sub-agent scratch work is kept apart in two ways:
  - by `session_id`: the launcher should pass the Claude Code session id, not a checkpoint timestamp;
  - by the `working` tier, which expires after 24 hours.
- **The wiki round-trip in a harness**: set `MEMKERNEL_WIKI_DIR=knowledge/wiki`. Running `wiki_import` after CCT's `scripts/wiki promote` keeps recall in step with the curated wiki. `wiki_export` writes drafts for the promote flow to review. Exported pages pass CCT's `lint-wiki.sh` by construction.
- **Non-MCP harnesses**: Pi and Codex cannot use MCP. The plan proposes a thin roadmap CLI (`memkernel retain|recall|consolidate --json`) that they can call as a subprocess. Until it exists, CCT marks Pi as unsupported.
- **Component assembly (haa)**: haa's owner wants haa to become a component-assembly harness, where a developer picks memory, sandbox, tools, workflow and provider components, later through a UI. Memory is assembled as `MemoryLifecycle(build_service())` and called from the loop. A UI would build the same objects from configuration.
- **CoALA mapping**: haa's loop is the decision cycle and MemKernel is the memory module. Retrieval happens through `recall` and `ask`, and learning through `retain` and `promote`. `procedure` memories become a Voyager-style skill library once they carry executable metadata.
- **Host-side memory tools**: in a sandboxed harness, memory tools run on the host, like the filesystem tools. The sandbox cannot see host packages. Keep the Chroma store outside any bind-mounted workspace (for example `MEMKERNEL_CHROMA_PERSIST_PATH=.memkernel/chroma`).
- **AGENTS.md vs learned memory**: a human-edited rules file (`AGENTS.md`) stays the place for rules. Durable *learned* knowledge goes through `promote` and later `wiki_export`.
- **Statements that may be stale**: the plan predates some later releases. It describes MemKernel as not yet on PyPI (install with `pip install -e` or a git URL), lists PyPI publication, a CHANGELOG and `CONTRIBUTING.md` as missing for a release, and lists `MemoryLifecycle`, `DocumentStorePort` and `ReasonerPort` as roadmap 0.3. The README-based pages describe `pipx install memkernel` and an existing `lifecycle.py`. Check the current release before relying on these statements. The plan also records a relicensing to Apache-2.0 on 2026-10-11.

## Where this shows up

- `eval/navigation/corpus/docs/integration/harness-integration.md`: the integration plan, with sections for CCT, haa and open-sourcing.
- CCT (feature `memkernel-memory`, `specs/memkernel-integration`, maturity *experimental*):
  - `shared/skills/memkernel-memory/SKILL.md`;
  - the hooks `memkernel-recall`, `memkernel-pre-compact` and `memkernel-post-compact`;
  - a launcher that writes `mcpServers.memkernel` to `.claude/settings.local.json`;
  - `setup.sh --memkernel <path>`;
  - a Pi MCP backend declaration;
  - a benchmark adapter pinned to a memkernel SHA.

  Verification uses the guard tests in `tests/test-hooks.sh`, plus a session that retains an observation, runs `/compact` and sees the promotion candidate in the post-compaction injection.
- haa (planned changes):
  - `requirements.txt`: `chromadb>=0.5` is replaced by `memkernel>=0.2`.
  - `harness/tools/memory.py` registers `retain`, `recall`, `get`, `promote` and `consolidate` with the `@tool` registry.
  - `harness/cct.py` adds lifecycle calls:
    - session-start context after `load_agents_md()`;
    - a checkpoint `episode` plus `consolidate()` when `tool_rounds` reaches `MAX_TOOL_ROUNDS`;
    - a session summary plus `consolidate()` in the `finally` block.
  - `harness/resources/system-prompt.txt` gains a "# Memory management" block copied from `templates/claude-memory-instructions.md`.

  Verification is a pytest that uses an ephemeral Chroma client and memkernel's `MockEmbedding` (from `tests/conftest.py`), calls each tool function, and checks the `consolidate()` report after a forced budget overflow.
- memkernel templates: `templates/hooks/` (including `session-start.py`) and `templates/claude-memory-instructions.md`.

## Related

- [Register MemKernel with Claude Code](../workflows/memkernel-claude-code-setup.md)
- [MemKernel tiered memory model](memkernel-tiered-memory.md)
- [MemKernel LLM-wiki bridge and store health](memkernel-wiki-bridge-and-health.md)
- [ADR-007: tiered memory with supersession for facts and decay for experience](../decisions/memkernel-tiered-memory-decision.md)
- [ADR-008: an LLM wiki is the human-readable form of long-term memory](../decisions/memkernel-wiki-semantic-layer-decision.md)
