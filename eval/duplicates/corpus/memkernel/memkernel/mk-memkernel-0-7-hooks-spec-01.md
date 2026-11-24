---
page_type: decision
slug: mk-memkernel-0-7-hooks-spec-01
title: 'What context to inject'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-hooks/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

A floor against today's fixed generic queries
("decisions conventions active work", "decisions conventions architecture") would measure nothing: the queries
are not about the task. So there is **no floor on those queries**. Instead:
**Startup:** the long-term context is chosen **without a query**: live long-term memories ordered by type
(decision, convention, procedure, fact, then the rest), then importance, then recency, cut to
`SESSION_START_CONTEXT_TOP_K`. At the start of a session there is no task text to match, so a semantic query
would only rank by chance.
**Compact:** the long-term context is recalled with **the latest own checkpoint's text as the query** (the work
in progress), cut to `POST_COMPACT_CONTEXT_TOP_K`. Without a checkpoint, the startup selection is used.
**No absolute floor in this spec.** A floor is calibrated later on the hooks' real queries, the checkpoint
texts, from a measured run, and the result is recorded as a follow-up in #59. The alternative of calibrating
now has no data to calibrate on.
`recall` itself is unchanged.
