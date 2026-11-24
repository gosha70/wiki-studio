---
page_type: decision
slug: cct-wiki-audit-flush-spec-03
title: '3 — Pathspec commit, never `git add -A`'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-audit-flush/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`git -C <repo_root> commit -m "audit: flush N pending ingest-log
line(s)" -- knowledge/wiki/.audit/ingest-log.md` commits exactly that
file's working state and leaves the user's index and every other file
untouched. **Argument order is load-bearing: `-m <msg>` MUST come
before `--`; anything after `--` is a pathspec, so `git commit --
<path> -m <msg>` fails with `pathspec '-m' did not match` (verified).**
This guarantees a "focused commit" and avoids the classic footgun of
sweeping unrelated changes. No `--no-verify`, no `GIT_INDEX_FILE`/
`GIT_DIR` overrides (explicitly forbidden by repo safety rules) — it is
an ordinary commit.
