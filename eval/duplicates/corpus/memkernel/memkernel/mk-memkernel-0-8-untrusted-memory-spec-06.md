---
page_type: decision
slug: mk-memkernel-0-8-untrusted-memory-spec-06
title: 'The permissions example'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-8-untrusted-memory/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

A new `templates/claude-settings.example.json`, strict JSON:

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "deny": [
      "Edit(/.memkernel/**)",
      "Edit(/.claude/settings.json)",
      "Edit(/.claude/settings.local.json)",
      "Edit(/.claude/hooks/**)"
    ]
  }
}
```

**Why `Edit`:** `Edit` rules are the ones Claude Code matches for every file-editing tool. `Write(...)` rules
never match, as the docs say.
**Why these four, not all of `.claude/`** (the owner's decision): the settings files and the hook scripts decide
what runs at the next session start. The rest of `.claude/` (agents, commands, skills) stays editable, because
teams often have the agent maintain those. The README says that a team which does not can add
`Edit(/.claude/**)`.
**What the README says alongside it:**
the rules stop Claude's own file tools, recognised Bash file commands and redirections, but not a program that
writes files without naming them (a script, `python -c`), so sandboxing is the stronger boundary;
`.claude` is already a protected path, which prompts except in `bypassPermissions` mode, and the deny rules
make it a refusal;
memkernel's MCP server and hooks write `.memkernel/` themselves, not through Claude's tools, so they are
unaffected;
a project that keeps `MEMKERNEL_STATE_DIR` or the Chroma path elsewhere adjusts the first rule;
an "always allow" prompt that appears mid-session, especially one asking for broad Bash or file access,
deserves a second read: injected text can be what asked for it.
**The build checks,** in a live Claude Code session, that the rules load (`/status`, `claude doctor`), that the
agent's Edit and Write to `.memkernel/x` are refused, and that "Yes, and don't ask again" still saves its rule.
That last one matters because Claude Code itself writes `.claude/settings.local.json`, not Claude's Edit tool.
The PR records the Claude Code version.
**Rejected:** a `Read` deny on `.memkernel/**`. The agent may need to read the store's files when debugging,
and #85 asks to stop writes.
