---
page_type: decision
slug: mk-memkernel-0-12-capture-core-spec-07
title: 'Rerun and pass'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-12-capture-core/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

**A rerun** is the same command, whitespace collapsed, after removing trailing `| tail …`, `| head …`,
`| grep …` and `2>&1` (the owner's words). This spec's reading: a trailing filter is a final pipeline segment that contains no other `|`, `;`, `&`, `<`
or `>`; removal repeats until none is left, so `cmd 2>&1 | tail -20` becomes `cmd`.
**A run counts as passed, or as failed,** only when its exit status is the command's own: the command has no
trailing filter pipe (a trailing `2>&1` alone does not change the status), or it sets `pipefail`
(`set -o pipefail`). The owner's decision for passes, extended to failures by the owner on 2026-11-16.
**"Same program and target" matching is not built** for now.
