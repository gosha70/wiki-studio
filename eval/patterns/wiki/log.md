---
page_type: log
slug: log
title: Patterns Study Wiki Log
status: stable
last_reviewed: 2026-11-18
---

# Patterns Study Wiki Log

Append-only. One bullet per entry, newest at the top. Format:

`- YYYY-MM-DD — <verb> <slug> (<page-type>): <one-line why>`

- 2026-10-29 — add merge-require-green-ci-was-never-read-and-was-removed (decision): the key was never read and was removed
- 2026-09-08 — add benchmark-explains-itself-linking-runs-is-a-pipeline-step (decision): a setting, a pipeline step and a live payload replace the backend-free view
- 2026-09-17 — add config-redaction-is-not-free-text-redaction (decision): a key-name helper cannot redact prose
- 2026-09-08 — add benchmark-step-reuses-the-one-correlate-scan-seam (decision): one commit-at-the-end scan contract serves the CLI and the step
- 2026-09-04 — add the-clusters-view-is-not-an-explorer (decision): a minimal read-only view over an imagined explorer
- 2026-07-18 — add trace-archive-reuses-the-ingest-redaction-path (decision): reuse `redact_text` rather than fork the privacy contract
- 2026-07-18 — add never-archive-raw-jsonl (decision): a raw copy bypasses the redaction and opt-out gate
- 2026-07-18 — add benchmark-ui-was-backend-free-one-shot-and-studio-only (decision): the first Benchmark UI took the existing payload
- 2026-07-14 — add merge-require-green-ci-was-never-read (decision): green-CI enforcement was delegated to the key and branch protection
- 2026-07-14 — add balanced-profile-denies-destructive-git-commands (decision): the balanced tier denies destructive git commands
- 2026-05-20 — add judge-statistics-and-charts-stay-in-the-stdlib (decision): the harness stays stdlib-only
- 2026-05-18 — add swe-bench-fetch-uses-the-stdlib-rows-api-not-parquet (decision): the no-new-dependencies constraint forbids Parquet libraries
- 2026-05-02 — add never-bypass-a-git-lock-with-an-alternate-index (decision): an alternate index produced an empty-tree commit
- 2026-05-02 — add destructive-git-commands-require-confirmation (decision): the agent must confirm before destructive git commands
