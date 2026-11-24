---
page_type: decision
slug: mk-memkernel-0-14-capture-signals-spec-07
title: 'A recall limit per origin session'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-14-capture-signals/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

at most 3 captured records per origin session in one recall result, so
one heavy session cannot fill it (FR-008).
