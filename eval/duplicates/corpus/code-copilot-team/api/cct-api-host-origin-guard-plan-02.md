---
page_type: decision
slug: cct-api-host-origin-guard-plan-02
title: 'a request with NO `Origin` header is ALLOWED even on state-changing routes.'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/api-host-origin-guard/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

a request with NO `Origin` header is ALLOWED even on
state-changing routes. Required: `TestClient`, `curl` and scripts never
send one. Documented limit: this does not stop a local non-browser
process, which already has code execution and is outside the threat
model. *(Recommend — the alternative breaks every non-browser client for
no gain against the rebinding threat, which is browser-borne and always
carries a forged-impossible `Host`.)*
