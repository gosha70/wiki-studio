---
page_type: decision
slug: cct-api-host-origin-guard-plan-01
title: 'Host + Origin only.'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/api-host-origin-guard/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Host + Origin only. `Sec-Fetch-Site` is NOT part of
the contract (unverified on the real browser path); no local token.
*(Pre-set by the maintainer 2026-07-19; recorded, not re-litigated.)*
