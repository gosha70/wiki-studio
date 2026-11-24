---
page_type: decision
slug: mk-memkernel-0-16-lifecycle-corrections-spec-05
title: 'Two steps'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-16-lifecycle-corrections/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

this spec's build ships the tasks, the runner change, the arm, the curator and the gate check,
all exercised with the stub agent in CI. The calibration and the measured run come after, each with a
preregistration and a budget the owner approves; approving this spec authorizes no paid run.
