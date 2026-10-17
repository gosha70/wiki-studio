---
feature_id: wiki-studio-0-4-0
date: 2026-10-17
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: fix/24-propose-allow-out-of-repo
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-4-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The fix is small and targeted: `propose` now accepts `--allow-out-of-repo` and forwards it to `api.promote`, matching the flag `promote` already exposes. The added test exercises both the refusal path (exit 7, no wiki mutation) and the allowed path (promotion succeeds, archive lands in the external proposals dir). I found no correctness or security issues in the change itself.

## Findings

- [note] f-9c38befc: `args.allow_out_of_repo` is read unconditionally; if any other caller constructs a `Namespace` for `_do_propose` without that attribute (e.g., a future internal caller or test harness), it will raise `AttributeError`. Currently safe because argparse always sets it, but the coupling is implicit. (src/wiki_studio/cli.py)
- [note] f-57c4dd89: The test asserts the refusal message contains `--allow-out-of-repo` but does not assert that the refusal happens *before* the proposal is written to the external dir (i.e., that no orphan proposal dir is left behind on refusal). The CHANGELOG says "It wrote the proposal and then exited 7" — worth pinning that the new behavior still writes the proposal (or not) consistently, so a future refactor doesn't silently change the side-effect ordering. (tests/test_agent_verbs.py)
- [note] f-475162e3: The README row says "refused with exit 7 otherwise, as by `promote`" — accurate, but does not mention that the proposal itself is still written before the refusal (per the CHANGELOG). Minor: users may be surprised to find a proposal dir on disk after a failed `--promote`. (README.md)
- [note] f-b2b3596b: The flag is only meaningful with `--promote`; passing it without `--promote` is silently accepted and ignored. This mirrors `promote`'s own semantics but is a small footgun. (src/wiki_studio/cli.py)
