---
page_type: decision
slug: cct-routing-profile-foundation-plan-06
title: 'cct integration — three narrowly pinned read-only commands'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-profile-foundation/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`cct routing validate|status|explain` dispatch from `scripts/cct`
to a new `scripts/routing-cli.sh`. Exit codes: 0 valid/clean, 1
named violations, 2 usage/no-registry (with guidance). Pinned
semantics:

| Command | A semantics |
|---|---|
| `validate` | parse + grammar + schema + semantic validation (registry, repo block, merge) |
| `status` | registry/policy state only — per-profile rows; may report credential-env PRESENCE, never contents |
| `explain` | pure effective-policy derivation for one route class |

`explain --route-class <class> [--role <role>]` is a PURE
configuration-resolution explanation, not a routing simulation. It
MUST NOT: probe a provider, inspect quota/cooldown state as if
authoritative, select a live backend, execute anything, or claim
"this request would run on X". It filters deterministically
(effective allowed set -> role -> tier membership per the class's
tier order), priority-sorts within tiers, and prints EVERY profile
with its verdict and reason; its output states that it explains
configuration. `status` renders
`~/.code-copilot-team/routing-state.json` per-profile state when
present (increment A never writes that file; absence renders every
profile `unknown`) and must not quietly become a second
providers-health: none of the three commands makes any network
call or invokes any provider/health command. The `--route-class`
form (vs the umbrella's `--feature/--task`) is deliberate: task
metadata is increment C's; the command stays extensible for it.
