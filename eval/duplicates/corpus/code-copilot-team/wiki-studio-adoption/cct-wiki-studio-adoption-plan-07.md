---
page_type: decision
slug: cct-wiki-studio-adoption-plan-07
title: 'Reconcile the schema by category, then pin it'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-studio-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Start from the wiki-studio 0.9 schema. For every current CCT/upstream diff hunk,
record one category:

deliberate CCT policy retained with rationale;
extraction drift replaced by upstream;
package behavior deliberately adopted.

Only category 1 remains as a post-reconciliation diff. A checked-in policy
record plus a mechanically complete upstream delta prove that every retained
line is classified. Then pin the resulting project fingerprint in the thin
contract. A fingerprint alone records bytes but not why they differ; the
classification is the ownership record.
