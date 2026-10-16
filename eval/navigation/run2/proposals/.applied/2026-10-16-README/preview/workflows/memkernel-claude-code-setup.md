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
