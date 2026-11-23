---
feature_id: wiki-studio-0-11-0
date: 2026-11-23
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-11-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-11-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

This phase-7 change is documentation-only plus a test addition: it updates the packaged `citation-rules.md`, README, knowledge contract, nightly recipe, patterns doc, and CLI/MCP help text to describe the revision check (`source-not-at-revision`, `source-revision-changed`, `revision_check`), and adds a test asserting both nightly workflows use `fetch-depth: 0`. The diff is internally consistent with the spec's described behavior, and the new test is a reasonable guard. I found no blocking correctness issues; a few notes on documentation accuracy and test robustness.

## Findings

- [note] f-557c60d4: The arithmetic "about three calls when its repository is second" is loose: with two repositories probed, a commit found in the second costs one lookup in the first (miss) + one in the second (hit) + one `diff-tree` = three, which matches, but the phrasing "about" plus the earlier "one lookup per repository probed" could confuse readers computing the cap. Minor clarity issue only. (docs/knowledge-contract.md)
- [note] f-4f404d1c: The doc admits the anchor rule matches inside longer words (`test` in `latest`) and that a bare filename yields its last dotted part as an anchor. These are documented as known limits, which is good, but the `citation-rules.md` packaged schema text does not mention them, so a curator reading only the schema override may be surprised by false positives. (docs/knowledge-contract.md)
- [note] f-545b6336: The test asserts `lines[step + 1] == " " * indent + "with:"` and `lines[step + 2].strip() == "fetch-depth: 0"`, which is brittle to YAML formatting (e.g., a comment line between `uses:` and `with:`, or `with:` on the same line as `uses:`). It also does not verify the `with:` block belongs to the checkout step rather than a later step if indentation coincidentally matches. (tests/test_nightly_recipe.py)
- [note] f-db536384: The prose says "with the default shallow checkout no cited `sha:` is checked", which is accurate, but the drafting workflow's `fetch-depth: 0` is added without noting that the drafting variant also benefits (it runs `findings` too). Minor: the sentence reads as if only the non-drafting workflow needed it. (docs/nightly.md)
- [note] f-9ddaad94: The packaged schema now says `findings` checks a `path:` with a `sha:` and lists the two kinds, but it does not mention the `WIKI_STUDIO_GIT_CALL_LIMIT` cap or that a shallow clone is skipped — both of which a curator running `findings` locally in a shallow checkout would want to know. The knowledge contract covers it, but the schema is the file curators read first. (src/wiki_studio/schema/citation-rules.md)
- [note] f-abdb6237: The CHANGELOG says "the fingerprint covers overrides only, so no manifest drifts" — this is a claim about behavior that is not verifiable from this diff (the fingerprint logic is not shown). If the packaged schema change does not affect the fingerprint, this is correct, but the reviewer cannot confirm from the diff alone. (CHANGELOG.md)
- [note] f-1190b411: The README says `--json` prints `revision_check` "whether the revision check ran, each repository used or skipped, the sources not checked by reason", which matches the contract's `revision_check` object shape. Consistent; no action needed — noted only to confirm the cross-reference is accurate. (README.md)
