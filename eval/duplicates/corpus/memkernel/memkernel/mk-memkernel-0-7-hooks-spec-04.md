---
page_type: decision
slug: mk-memkernel-0-7-hooks-spec-04
title: 'SessionEnd'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-hooks/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

The 1.5-second budget cannot load the embedding model.
`session-end.py` writes a spool line without opening the store: `session_id`, `reason`, `transcript_path` and
the time. The spool is in the same memkernel state directory as memkernel-0-7's ledger, `MEMKERNEL_STATE_DIR`
(default `.memkernel/state`, resolved like `MEMKERNEL_CHROMA_PERSIST_PATH`), under `session-spool/<project_id>/`.
**The rule is "no checkpoint during that session"**, not "no checkpoint newer than the end". The `SessionStart`
hook also writes a spool line, `started`, with the `session_id` and the time, for every `source`: `startup`,
`clear`, and **also `resume` and `fork`**, although it injects nothing for those two. **A session's window runs
from its first `started` line to its last `ended` line**, so a session resumed several times is one window. Agents' checkpoints cannot carry Claude Code's session id:
the MCP server never sees it.
The next `startup` drains the spool. A session counts as checkpointed when it has a checkpoint whose timestamp
falls inside its window, or a compact-summary checkpoint tagged `session:<its id>`. For each ended session with
neither, one line is added: "The previous session (<reason>, <time>) ended without a saved checkpoint." A session
with an end but no start line gets no line, since its window is unknown.
The spool is the hook point for #59's Phase 2 transcript capture, which is not built here.
