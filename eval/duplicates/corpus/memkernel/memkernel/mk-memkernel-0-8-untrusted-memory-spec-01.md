---
page_type: decision
slug: mk-memkernel-0-8-untrusted-memory-spec-01
title: 'What is data'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-8-untrusted-memory/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

Every piece of text that memkernel injects but did not write itself is quoted as data:
the checkpoint's text;
each context line's preview;
each promotion candidate's preview;
each "Needs review" item's source path and reason;
each curation-debt example's page path (it comes from the wiki).

memkernel's own lines stay outside: headings, the checkpoint's age line, counts, hints, the store-health line,
the previous-sessions lines, and the wiki pointer, which comes from settings. The `ref_id` and type tags on a
line stay outside too, so the agent can still `get(ref_id)`.
