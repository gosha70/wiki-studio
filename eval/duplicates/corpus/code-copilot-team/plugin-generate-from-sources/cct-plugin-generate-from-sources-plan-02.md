---
page_type: decision
slug: cct-plugin-generate-from-sources-plan-02
title: 'the six always-on skills'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/plugin-generate-from-sources/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`setup.sh` installs
coding-standards, copilot-conventions, copyright-headers,
origin-confirmation, safety and wiki-first-query as always-loaded rules.
A plugin cannot do that. Options:

(a) **Recommended.** Ship all 24 as ordinary plugin skills. The six
load when their description matches, not always. Say so plainly in
`docs/install.md`: the plugin is the quick path, `setup.sh` is the
full harness, and the two can be combined.
(b) Inject the six through a SessionStart hook. Not recommended: it
pushes tens of kilobytes into every session, is new machinery, and is
the "broad redesign" the owner ruled out.
(c) Leave the six out of the plugin. Not recommended: the agents and
commands refer to them.
