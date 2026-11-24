---
page_type: decision
slug: cct-routing-context-limit-plan-07
title: 'the filter is wired to BOTH the delegate and reconcile paths'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-context-limit/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

This reverses an earlier decision, and the reversal is worth recording
because of *why* the first version was wrong. The filter was initially
wired to delegate only, on the argument that enforcing a builder's
minimum against reviewer profiles would strand `verified_provisional`
work behind reviewers that merely lack a declaration. That argument was
presented as supported by evidence: mutating the code to filter
reconcile produced 18 delegation-suite failures.
