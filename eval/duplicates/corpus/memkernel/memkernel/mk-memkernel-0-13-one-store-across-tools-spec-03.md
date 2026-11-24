---
page_type: decision
slug: mk-memkernel-0-13-one-store-across-tools-spec-03
title: 'Where a hook replaces the instruction'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-13-one-store-across-tools/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

**Codex: hook and `AGENTS.md`.** Its `SessionStart` is documented, takes plain stdout, and matches Claude
Code's JSON shape.
**Cursor: the `alwaysApply` rule only.** Its `sessionStart` is fire-and-forget and loses its context on the
first request in the Agents Window (staff-confirmed, unfixed). Cursor can also load Claude Code's hooks; the
README says so, without relying on it.
**Antigravity: the `always_on` rule only**, until its `injectSteps` shape is verified in a live session (the
docs' examples disagree).
