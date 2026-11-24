---
page_type: decision
slug: cct-wiki-studio-adoption-plan-06
title: 'CCT proves its contract, not upstream internals'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-studio-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Rewrite `tests/test-wiki-ingest.sh` around disposable repositories and the
exact package launcher. It proves ingest, promotion, content-bearing query with
citations, structural lint, audit-flush dry/real behavior, alias compatibility,
legacy manifest-less mode, project-schema selection/fingerprint, and
missing/mismatch diagnostics.

The pre-build scratch check closes the earlier evidence gap: in legacy mode,
audit-flush dry-run reported one pending line without moving HEAD; the real run
committed only the ingest log; a second dry-run reported nothing pending; no
manifest appeared. The rewritten test makes this permanent rather than asking
Task 4 to discover whether the fifth verb belongs in the contract.

The ten package-internal Python test files leave with the engine. Locking,
parsers, backend classes and rollback algorithms remain upstream's unit-proof
responsibility. CCT tests their externally visible outcome only where CCT
depends on it.
