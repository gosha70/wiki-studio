---
page_type: decision
slug: cct-routing-tier2-delegation-plan-02
title: 'The safety floor is structural, evaluated twice, and cannot be annotated away'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier2-delegation/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

A closed category vocabulary, defined once in
`routing-tasks.sh` with one named path-pattern set per category:
`architecture`, `auth`, `crypto`, `security_policy`,
`db_migrations`, `dependency_manifests`, `public_api`,
`ci_verification_tooling`, `routing_artifacts` (the routing/
verification artifacts and their tests are always in-floor). A
task whose `allowed_files` intersect any floor category cannot
carry a `tier2_*` route class: metadata ADMISSION refuses it by
name (validator error, never a silent downgrade), and PACKET BUILD
re-evaluates the same predicate against the artifacts as frozen at
build time — a floor violation introduced after admission is a
second named refusal. The floor vocabulary and patterns are
implementation surface with tests, not user configuration;
`forbidden_categories` lets metadata NARROW further, never widen.
