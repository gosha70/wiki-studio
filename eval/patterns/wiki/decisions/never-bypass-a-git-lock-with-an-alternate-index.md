---
page_type: decision
slug: never-bypass-a-git-lock-with-an-alternate-index
title: Never bypass a git lock with an alternate index
status: stable
last_reviewed: 2026-05-02
sources:
  - path: claude_code/.claude/rules/safety.md
    sha: 5ce94f2
  - path: shared/skills/safety/SKILL.md
    sha: 37e8417
---

## Decision

In the context of a commit blocked by a git lock, we chose to stop and explain the blockage. We chose it over setting `GIT_INDEX_FILE` or `GIT_DIR` or using `--no-verify`. The reason: an alternate empty index produced a commit that appeared to delete every file.

Chosen: the stop-and-explain rule in `shared/skills/safety/SKILL.md`, originally `claude_code/.claude/rules/safety.md`.

## Context

Requirement: committing safely when `.git/index.lock` or another block prevents the normal path.

Applies when: a commit is blocked by `.git/index.lock` or another block that prevents the normal path.

Does not apply when: not recorded in the source record.

## Alternatives considered

- `GIT_INDEX_FILE` or `GIT_DIR` override: created an empty-tree commit.
- `--no-verify` or `--no-gpg-sign`: bypasses hooks or signing.

## Consequences

Revisit when: not recorded in the source record.

Tests: none.

Confidence: high: the rule is explicit, the incident record explains the failure, and the current skill still carries the prohibition.

Incident record: [Git safety bypasses — the `GIT_INDEX_FILE` empty-tree incident](../incidents/git-safety-bypasses.md).
