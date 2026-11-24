---
page_type: decision
slug: mk-memkernel-0-7-release-b-exit-plan-05
title: 'CI'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-release-b-exit/plan.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

An informational workflow, `.github/workflows/release-b-exit.yml`, runs `run.py` against a wheel
built from the PR and the newest wiki-studio release in range. It runs on `pull_request` to `main` only when
the PR changes `src/memkernel/**`, `eval/release-b-exit/**` or the workflow file itself (the owner's path
filter), weekly by `schedule`, and by `workflow_dispatch`. It is not a required check. A change
on wiki-studio's side shows up in the weekly run, which installs wiki-studio's newest release. A green
workflow run is a signal on a wheel built from the PR. The exit evidence is only the recorded run on released
wheels. The recorded run stays a manual owner step.
