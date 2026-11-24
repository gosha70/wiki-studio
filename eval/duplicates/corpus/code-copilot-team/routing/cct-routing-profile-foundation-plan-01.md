---
page_type: decision
slug: cct-routing-profile-foundation-plan-01
title: 'Registry location and format — a constrained TOML dialect'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-profile-foundation/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`~/.code-copilot-team/routing.toml` (beside the existing
`providers.toml`, which is NOT touched — reviewer semantics and
build routing have different security and state requirements, per
the umbrella). Parsed by a new `scripts/lib/routing-config.sh`
following `providers-health.sh`'s no-dependency line-oriented
idiom, extended for `[[profiles]]` — but the accepted grammar is an
EXPLICIT subset: `routing.toml` accepts only the TOML subset CCT
implements; unsupported TOML constructs are REJECTED, never
approximated. Accepted: comments; bare keys; single-line basic
strings (no escapes beyond `\"`), integers, booleans; single-line
arrays of basic strings; `[table]`, `[table.sub]`, and
`[[profiles]]` headers. Rejected by name: duplicate keys within a
table, duplicate table declarations, dotted keys, inline tables,
multiline/literal strings, non-string arrays, malformed quoting,
and any line the grammar does not recognize. A closed schema over a
permissive or approximating parser would not actually be closed —
this file is policy surface, so the grammar fails closed with the
schema. Every consumer goes through this one parser.
