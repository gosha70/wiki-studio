---
page_type: decision
slug: mk-memkernel-0-16-lifecycle-corrections-spec-02
title: 'Arms for this comparison'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-16-lifecycle-corrections/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

`memkernel`, `memkernel_governed` (with the oracle curator as an upper bound),
`fs_grep`, **`claude_md`** and `bare`. `claude_md` stays: writing a corrected rule into CLAUDE.md is the most
common real-world way to handle a correction, so it is the comparison readers will ask about. `protocol` and
`placebo` are left out. `claude_md` stays unless the budget (D5) rules it out.
