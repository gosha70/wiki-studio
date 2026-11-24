---
page_type: decision
slug: cct-routing-eval-plan-08
title: 'Redaction is a property of the writer, not the reader'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-eval/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Secret
values, authorization headers, API keys, connector inventories, and
sensitive absolute paths are scrubbed at the point the record is
written, so a leaked artifact cannot contain them regardless of who
reads it. Virtual environments, caches, bytecode, and generated
runtime noise are excluded from the changed-file measure by the
same writer.
