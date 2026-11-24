---
page_type: decision
slug: cct-wiki-studio-adoption-plan-14
title: 'Land one coherent boundary, in green internal stages'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-studio-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The PR is one slice because deleting the engine before its launcher, package and
CI replacement would leave master broken, while landing both engines would
extend the duplication the issue exists to end. Build in green commits:

artifact/setup/resolver and failure-path tests;
schema reconciliation and fingerprint proof;
thin round trip and workflow-semantic tests;
caller/doctor/catalogue/docs/CI retarget;
delete both duplicate implementations and close guards.

No commit may claim the new engine while production callers still select the
old one.
