---
page_type: decision
slug: cct-wiki-studio-adoption-plan-01
title: 'Pin the artifact, not only the version'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-studio-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Install the base `wiki-studio==0.9.0` universal wheel with its published
SHA-256 and binary-only selection. PyPI's Trusted Publisher attestation
(gosha70/wiki-studio, `release.yml`) ties that wheel to upstream commit
`b66b3be82e0bfe17747907b30d71975fcf9d9f81`, which is what annotated tag
`v0.9.0` resolves to (`refs/tags/v0.9.0^{}`; the tag object itself is
`249e508…`). Task 1 records the commit beside the lock by reading the
attestation, so the number stays attributable. A version-only floor would let
upstream change CCT behavior without a CCT commit; a version-only exact pin
would still leave the selected artifact implicit. The optional MCP extra is
forbidden because it requires MCP 2.x while Session Analytics targets MCP 1.x.
