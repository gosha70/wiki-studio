---
page_type: decision
slug: balanced-profile-denies-destructive-git-commands
title: Balanced profile denies destructive git commands
status: stable
last_reviewed: 2026-07-14
sources:
  - path: adapters/claude-code/permissions/balanced.json
    sha: 88931a3
  - path: specs/init-permission-profiles/spec.md
    sha: 88931a3
  - issue: gosha70/code-copilot-team#76
---

## Decision

In the context of `claude-code init` permission profiles, we chose a `balanced` tier that sets `defaultMode: dontAsk` and denies `Bash(git push --force:*)` and `Bash(git reset --hard:*)`. We chose it over a prompt-per-command or allow-with-confirmation profile. The reason: dangerous operations must stay guarded when unmatched calls auto-deny.

Chosen: `adapters/claude-code/permissions/balanced.json`, applied by the init and switch commands.

## Context

Requirement: a project permission profile that removes routine prompts while keeping dangerous operations guarded.

Applies when: a project permission profile removes routine prompts while keeping dangerous operations guarded.

Does not apply when: the balanced deny list changes or the safety rule becomes an outright ban.

## Alternatives considered

- Prompt-per-command: the default tier, which still prompts.
- Allow-with-confirmation: the deny list is the guard.

## Consequences

Revisit when: the balanced deny list changes or the safety rule becomes an outright ban.

Tests: `tests/test-sync.sh` section 18b covers the balanced mode and deny list.

Confidence: high on the facts, medium on the type: the two records are layered, but they overlap in a balanced-profile project.

> [!conflict] Disagrees with [Destructive git commands require confirmation](destructive-git-commands-require-confirmation.md)
