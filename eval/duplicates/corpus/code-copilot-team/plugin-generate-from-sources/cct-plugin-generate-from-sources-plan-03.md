---
page_type: decision
slug: cct-plugin-generate-from-sources-plan-03
title: 'duplicate hooks when both installs exist'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/plugin-generate-from-sources/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Each event would run
both copies. Recommended: a three-line guard at the top of the five
non-safety hook sources (`auto-format`, `verify-after-edit`,
`verify-on-stop`, `notify`, `reinject-context`):

```
if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" && -x "$HOME/.claude/hooks/$(basename "$0")" ]]; then
  exit 0
fi
```

It only fires for the plugin copy, and only when `setup.sh`'s copy is
installed. `protect-files` and `protect-git` get **no** guard: if
someone has the file on disk but removed the registration from
`settings.json`, a guarded plugin copy would defer to a hook that never
runs. They are fast and deterministic, so running twice costs a
duplicate block message and nothing else. The alternative is
documentation only ("pick one install for hooks"), which leaves
`verify-on-stop` (180 s timeout) and notifications doubled.
