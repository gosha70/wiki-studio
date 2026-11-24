---
page_type: decision
slug: cct-wiki-studio-adoption-plan-10
title: 'Doctor reports the actual execution boundary'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-studio-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`cct doctor` uses D3's resolver and reports expected/installed version,
interpreter path, package state, project schema source/fingerprint, and
legacy/manifest state. Missing venv, missing distribution, version mismatch and
schema drift have separate outcomes and remedies. System Python is irrelevant
unless it is the selected managed interpreter (which this design forbids).
