---
page_type: decision
slug: cct-wiki-audit-flush-spec-04
title: '4 — No-op is success'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-audit-flush/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Absent file or `N = 0` prints `nothing to
flush` and exits 0. Flushing is idempotent: a second run immediately
after a successful flush is a no-op. This makes it safe to call
unconditionally at end of a session.
