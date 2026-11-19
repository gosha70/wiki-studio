---
page_type: index
slug: index
title: Patterns Study Wiki Index
status: stable
last_reviewed: 2026-11-18
---

# Patterns Study Wiki Index

The fixture for the reusable-patterns study. Owner: gosha70. Assembled 2026-11-18.

## Patterns

The fourteen pattern pages: the twelve decision records of memkernel's corpus plus the two successors.

- [Trace archive reuses the ingest redaction path](decisions/trace-archive-reuses-the-ingest-redaction-path.md)
- [Benchmark step reuses the one correlate scan seam](decisions/benchmark-step-reuses-the-one-correlate-scan-seam.md)
- [SWE-bench fetch uses the stdlib rows API, not Parquet](decisions/swe-bench-fetch-uses-the-stdlib-rows-api-not-parquet.md)
- [Judge statistics and charts stay in the stdlib](decisions/judge-statistics-and-charts-stay-in-the-stdlib.md)
- [Never bypass a git lock with an alternate index](decisions/never-bypass-a-git-lock-with-an-alternate-index.md)
- [Never archive raw JSONL](decisions/never-archive-raw-jsonl.md)
- [Benchmark UI was backend-free, one-shot and Studio-only](decisions/benchmark-ui-was-backend-free-one-shot-and-studio-only.md)
- [merge.require_green_ci was never read](decisions/merge-require-green-ci-was-never-read.md)
- [The clusters view is not an explorer](decisions/the-clusters-view-is-not-an-explorer.md)
- [Config redaction is not free-text redaction](decisions/config-redaction-is-not-free-text-redaction.md)
- [Destructive git commands require confirmation](decisions/destructive-git-commands-require-confirmation.md)
- [Balanced profile denies destructive git commands](decisions/balanced-profile-denies-destructive-git-commands.md)
- [Benchmark explains itself; linking runs is a pipeline step](decisions/benchmark-explains-itself-linking-runs-is-a-pipeline-step.md)
- [merge.require_green_ci was never read and was removed](decisions/merge-require-green-ci-was-never-read-and-was-removed.md)

## Background

The twenty pages copied from code-copilot-team's `knowledge/wiki/` at the pin.

- [Wiki Overview](overview.md)
- [Cross-Session State Must Be File-Backed](concepts/cross-session-state-must-be-file-backed.md)
- [Multi-Round Spec Review](concepts/multi-round-spec-review.md)
- [Phase-Scoped Build Prompts](concepts/phase-scoped-build-prompts.md)
- [Spec-Driven Development](concepts/spec-driven-development.md)
- [Treat Infra Verification as a Gate, Not a Guideline](decisions/infra-verification-as-gate.md)
- [Use an LLM Wiki as the Project Knowledge Layer](decisions/use-llm-wiki-as-knowledge-layer.md)
- [Glossary](glossary/index.md)
- [Executable Artifacts Shipped Without Being Executed](incidents/executable-artifacts-shipped-unexecuted.md)
- [Git Safety Bypasses — `GIT_INDEX_FILE` Empty-Tree Incident](incidents/git-safety-bypasses.md)
- [Plan Agent Contract Contradiction — "Emit" vs "Forbidden from Writes"](incidents/plan-agent-contract-contradiction.md)
- [Spec/Code Coherence Drift — Three Instances Across Three Review Rounds](incidents/spec-code-coherence-drift.md)
- [Drive Claude Code With a Local vLLM Model](playbooks/drive-claude-code-with-local-vllm.md)
- [Grep-Based Acceptance Criteria](playbooks/grep-based-acceptance-criteria.md)
- [Recover After a Bad AI Git Operation](playbooks/recover-after-bad-ai-git-op.md)
- [Respond to a Production-Readiness Review Without Scope Creep](playbooks/respond-to-production-readiness-review.md)
- [30-Day Doc Coverage Audit](workflows/doc-coverage-audit.md)
- [Run the Origin-Alignment Gate](workflows/origin-alignment.md)
- [Promote a Lesson to the Wiki](workflows/promote-lesson-to-wiki.md)
- [Run the Wiki Ingest Pipeline](workflows/run-wiki-ingest.md)
