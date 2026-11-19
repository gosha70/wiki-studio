---
page_type: decision
slug: destructive-git-commands-require-confirmation
title: Destructive git commands require confirmation
status: stable
last_reviewed: 2026-05-02
sources:
  - path: claude_code/.claude/rules/safety.md
    sha: 5ce94f2
  - path: shared/skills/safety/SKILL.md
    sha: 37e8417
---

## Decision

In the context of agent-issued destructive git commands, we chose a confirmation gate before `git reset --hard` or `git push --force`. We chose it over unrestricted execution. The reason: the agent must not act destructively without the user, but the user may authorize a recovery.

Chosen: the Confirmation Required Before section in `shared/skills/safety/SKILL.md`, originally `claude_code/.claude/rules/safety.md`.

## Context

Requirement: any copilot session that is about to run a destructive git command.

Applies when: a copilot session is about to run a destructive git command.

Does not apply when: the safety rule or the project permission profiles change.

## Alternatives considered

- Unrestricted execution: data-loss risk.
- Silent bypass: prohibited.

## Consequences

Revisit when: the safety rule or the project permission profiles change.

Tests: none.

Confidence: high on the facts, medium on the type. The two records apply at different layers, but they name the same commands in the same harness.

> [!conflict] Disagrees with [Balanced profile denies destructive git commands](balanced-profile-denies-destructive-git-commands.md)
