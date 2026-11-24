---
page_type: decision
slug: cct-routing-calibration-plan-09
title: 'No execution authority — proven, not asserted'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-calibration/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

No production
routing script references `routing_calibration`, its schemas, or
its config keys; the standing E2 authority-guard test extends to
every new module; E3 writes only under `routing_calibration_root`;
routing shell suites pass unmodified at their pins and the
production-file diff guard holds at closure. Serving follows the
E2 sanitization floor (FR-E3-7); the `policy_source` path itself is
configuration and is never serialized into a payload.
