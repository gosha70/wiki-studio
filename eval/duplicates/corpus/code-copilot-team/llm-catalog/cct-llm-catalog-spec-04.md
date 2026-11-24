---
page_type: decision
slug: cct-llm-catalog-spec-04
title: 'Parser'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/llm-catalog/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Extract the line lexer of `routing-config.sh` into
`scripts/lib/cct-toml.sh`, shared by both registries (bash 3.2).
Alternatives: a second bash parser; Python `tomllib` (3.11+, which
the launchers cannot assume). Recommended: extraction.
**Ruled 2026-11-10 by the owner: accepted as recommended.** Condition: the extraction is its own commit with the existing routing-config tests passing unchanged.
