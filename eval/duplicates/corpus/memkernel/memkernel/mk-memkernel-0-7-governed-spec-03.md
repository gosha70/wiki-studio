---
page_type: decision
slug: mk-memkernel-0-7-governed-spec-03
title: 'Bounded export batches'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-governed/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

A new setting `MEMKERNEL_WIKI_EXPORT_BATCH` (default 10; 0 means no limit):
`wiki_export` writes at most that many new pages per call: by the memory's `importance`, highest first, then by
`timestamp`, oldest first, then by `ref_id`, so the order is deterministic.
The response gains `remaining`: the eligible memories still without a page after this call's successful writes.
A rejected batch writes none, so all remain: a 10-page batch from 12 that the gate rejects reports
`remaining: 12`. A `governed` refusal by the preflight reads nothing of the wiki, so `remaining` is `null` there
too (amended during the build; confirmed by the owner on 2026-11-04). A negative batch is refused as a setting. When the gate's outcome is
uncertain (`uncertain_outcome` is set, `GateUncertainError`: some
pages may be on disk), `remaining` is `null`: unknown, so nothing invites a blind retry; the
`uncertain_outcome` hint says how to reconcile. One reviewable batch per curator
pass, and a small gate proposal.
