---
page_type: decision
slug: cct-pi-team-controller-plan-03
title: 'Identity'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-team-controller/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

→ **declared** `{teamId, memberId}`, **both mandatory** (attribution,
**NOT** authentication — documented limitation); actor never from args; session
state = ids only; declared `teamId` validated against `ledger.teamId` (team
binding).
