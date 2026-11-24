---
page_type: decision
slug: cct-wiki-studio-adoption-plan-11
title: 'CI installs what production runs'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-studio-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Retarget `wiki-ingest-tests.yml` from a stdlib-only 3.10–3.12 internal suite to
the exact wheel and thin contract on **3.11–3.13**. This is the wiki feature's
range, not a declaration that unrelated CCT features cease supporting 3.10;
setup and the catalogue expose that distinction. Path filters name every
contract input.

Retarget `wiki-lint.yml` to the same artifact and launcher but preserve its
current nonblocking status. The dependency swap does not silently change merge
policy.
