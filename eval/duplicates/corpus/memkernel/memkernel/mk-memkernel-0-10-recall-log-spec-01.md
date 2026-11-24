---
page_type: decision
slug: mk-memkernel-0-10-recall-log-spec-01
title: '`on_post_compact(session_id="")`: Claude Code''s hooks do not call it; a harness that does can pass a session id, and only then is its block logged.'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-10-recall-log/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

`on_post_compact(session_id="")`: Claude Code's hooks do not
call it; a harness that does can pass a session id, and only then is its block logged. The recall log, like the
store locks, is locked on POSIX only: on Windows it runs unlocked with one warning per process, and concurrent
writers there can lose records or pass the size limit. From the review: a record larger than the size limit gives
up query text, then trailing `ref_ids`, is marked `truncated`, and keeps `query_sha256`, by which the count pairs
tool records with transcript calls; a truncated record cannot show a miss, so such a miss is unknown; and the
count does not judge `include_needs_review`.
