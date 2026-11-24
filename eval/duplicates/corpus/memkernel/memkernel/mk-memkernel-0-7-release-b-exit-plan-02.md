---
page_type: decision
slug: mk-memkernel-0-7-release-b-exit-plan-02
title: 'Where it lives'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-release-b-exit/plan.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

memkernel's `eval/release-b-exit/` (`run.py`, `record.py`, `runs/`). Recommended,
because #48 is memkernel's tracker and the run covers memkernel 0.7. The alternative extends wiki-studio's
`examples/correction-loop/` from that repository.
