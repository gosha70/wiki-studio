---
page_type: decision
slug: cct-routing-profile-foundation-plan-03
title: 'Credential and endpoint hygiene — structural first'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-profile-foundation/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The
security boundary is STRUCTURAL: no schema field exists that could
hold a literal credential; `credential_env` and `base_url_env`
carry environment-variable NAMES (validated `[A-Z_][A-Z0-9_]*`);
unknown fields fail; no A command ever needs, reads into output, or
logs the value behind those names (validate may report PRESENCE of
the variable, never contents). On top of that, as defense in depth
only — not presented as complete secret detection — values matching
obvious secret shapes (`sk-`-style keys, `Bearer` tokens, PEM
headers, long hex/base64 runs) are refused in every field to catch
operator mistakes early.
