---
page_type: decision
slug: cct-wiki-studio-adoption-plan-09
title: 'Preserve the assistant workflows'' semantics'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-studio-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`/promote-lesson` remains a free-text manual-curator procedure. It does not
reinterpret its argument as a source file or create a proposal implicitly.
Its final validation invokes package lint when the prerequisite is available.

`wiki-first-query` continues to read the index and selected pages directly. It
does not call `wiki-studio query` (a backend/model operation) or `find` (a new
retrieval contract). Source and generated adapter tests pin both facts. A future
UX slice can adopt package-native discovery or promotion deliberately.
