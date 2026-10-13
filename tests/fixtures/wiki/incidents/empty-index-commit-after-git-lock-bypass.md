---
page_type: incident
slug: empty-index-commit-after-git-lock-bypass
title: Empty Index Commit After Git Lock Bypass
status: stable
last_reviewed: 2026-10-12
sources:
  - path: README.md
    sha: 77d3811c1afe59832e9faa935deff81cb4b10b92
---

# Empty Index Commit After Git Lock Bypass

## What happened

An agent hit `.git/index.lock`, set `GIT_INDEX_FILE` to a fresh path to get around it, and committed an empty tree that appeared to delete every file.

## Why it happened

The bypass pattern-matched "remove the obstacle" without reasoning about what an empty alternate index means.

## What we changed

Blocked operations stop and explain; no environment-variable workarounds for locks.

## How to recognize a recurrence

A commit whose tree is empty, or a diff that removes every tracked file.

## Related

- [Recover From a Torn Audit Log](../playbooks/recover-from-torn-audit-log.md)
