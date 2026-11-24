---
page_type: decision
slug: mk-memkernel-0-8-untrusted-memory-spec-07
title: 'Not in this spec'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-8-untrusted-memory/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

A lint or health finding for stored memories that look like instructions.
It needs a detection rule that will have false positives, and it belongs with #59's Phase 2 capture rules, where
prompt-injection handling at capture is already listed. The roadmap's 0.3 item "Prompt-injection sanitising of
recalled content" stays open; this spec marks injected text, it does not sanitise it.
