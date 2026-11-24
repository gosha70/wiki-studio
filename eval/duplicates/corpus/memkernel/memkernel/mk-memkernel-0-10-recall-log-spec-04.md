---
page_type: decision
slug: mk-memkernel-0-10-recall-log-spec-04
title: 'Which session a recall belongs to'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-10-recall-log/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

`hook` records carry the session id. For a `tool` record, the script
finds the transcript's own `recall` call: same query, within 5 seconds (the MCP server and Claude Code run on
the same computer), paired one to one, nearest first. No
match, or matches in more than one session: the session is unknown, never guessed. Session windows come from the
transcripts; the spool is not used (checked facts).
