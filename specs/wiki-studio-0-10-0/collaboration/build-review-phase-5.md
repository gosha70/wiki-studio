---
feature_id: wiki-studio-0-10-0
date: 2026-11-17
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-10-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-10-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The changes add a `docs/nightly.md` recipe page, a persona paragraph for `nightly-*` proposals, an ingest-rules clarification, and tests that parse and execute the documented commands. The documentation is thorough and the test approach (parsing the page's own commands with the CLI parser and running them) is strong. I found a few correctness concerns around the test's assumptions and the recipe's claims that warrant attention.

## Findings

- [warning] f-593a2ab5: The test asserts that the *first* `--backend` line creates exactly one proposal and every subsequent `--backend` line creates none, but it does not verify that the non-backend lines (which run first, in page order) leave the proposals directory untouched. If a non-backend line accidentally drafted, the `before`/`after` comparison is skipped for it, so a regression where a no-backend run drafts would pass. Also, `drafted` is only assigned inside the `if not drafted` branch, so if the first backend line creates zero proposals the assertion fires but the failure message is less diagnostic than it could be. (tests/test_nightly_recipe.py)
- [warning] f-d29a0d1c: The doc claims "at most ten backend calls" for `--max-proposals 5`, implying a 2× relationship, but the test only exercises a single draftable finding and never verifies the cap or the call-count relationship. If the implementation's cap semantics differ (e.g., one call per finding vs. retries), the doc is unverified. This is a documentation claim with no test coverage in the diff. (docs/nightly.md)
- [warning] f-72c6c8f4: The doc states lint failure exits 1 *after* the report is written and *no draft is attempted*, but the recipe test only runs against a clean wiki (exit 0). The ordering claim (report written before exit 1) and the "no draft attempted" claim are load-bearing for the cron/CI recipe but untested here. (docs/nightly.md)
- [note] f-ec3bc57a: The doc asserts the refusal happens "before anything runs," but the test suite does not verify this ordering (e.g., that no lint output or partial report is produced). If the implementation validates the path late, the doc overstates the guarantee. (docs/nightly.md)
- [note] f-877d28a3: `PLACEHOLDER_RE.sub("PLACEHOLDER", line)` replaces every `<...>` token with the literal `PLACEHOLDER`, including `<project-dir>` and `<agent-name>`. For the wrapper script test this is fine (it does its own `.replace`), but for the `--by "<agent-name>"` argument the substituted value is `PLACEHOLDER`, which is then passed to `run_cli`. If `--by` validates the name format, this could mask a real failure or pass for the wrong reason. Worth confirming `--by PLACEHOLDER` is a valid proposer name. (tests/test_nightly_recipe.py)
- [note] f-63bac8b3: The workflow uploads `doc_internal/proposals/` but the report path is `reports/nightly.md`. If the proposals directory does not exist on a run that drafts nothing (or on a fresh checkout), `actions/upload-artifact@v4` will warn or fail depending on `if-no-files-found`. The doc does not mention this. Minor, but a reader copying the recipe may see a red step. (docs/nightly.md)
- [note] f-6d5e4b02: The paragraph says "on a wiki whose policy approves on promote you do not promote it and report the proposal directory for a person instead." This is a behavioral instruction to the agent that depends on the wiki's policy being discoverable; the paragraph does not say *how* the agent determines the policy. If the policy is not machine-readable, the agent may guess. Consider naming the policy source (e.g., the reservation line's presence). (src/wiki_studio/schema/WIKI_MAINTAINER.md)
