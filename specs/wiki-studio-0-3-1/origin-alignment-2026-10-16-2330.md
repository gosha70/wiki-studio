# Origin alignment check — wiki-studio-0-3-1

Gate: plan approved and built (Gates 1 and 3 together for a bug fix), 2026-10-16 23:30 local.

Origin: https://github.com/gosha70/wiki-studio/issues/15 and the owner's go-ahead for 0.3.1 with the scope #15 + py.typed + tag-pinned banner, no third run.

Working claim:
> `prompt.INDEX_LOG_ACTION_RULE` states that index.md / log.md change only via one-line append-index / append-log edits and that create/update are for the promotable types (listed from the schema module); the multi-page response instructions include it, the wiki-state text names the actions and marks index/log as reference only, the patch-set schema's action and new_content carry it; the legacy prompt is unchanged; the validator is unchanged and a full-page index edit still fails with exit 4; py.typed ships; the banner points at the v0.3.1 tag; version 0.3.1 and CHANGELOG.

Mismatches:
  - none.

Verdict: aligned
Confidence: high
