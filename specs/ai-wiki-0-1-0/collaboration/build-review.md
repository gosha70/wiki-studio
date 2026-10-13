---
feature_id: ai-wiki-0-1-0
date: 2026-10-12
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/ai-wiki-0-1-0
rounds_completed: 2
attempt_count: 1
bypass: false
---

# Peer Review: ai-wiki-0-1-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 2
**Verdict**: PASS

## Summary

Round 2 review of the ai-wiki-0-1-0 extraction. The builder's resolutions to Round 1 are largely sound: the disputed f-bd1250b8 is correctly refuted (the mutual-exclusion check is the first statement of `_do_ingest`, before the multi dispatch), and the deferred items are legitimately pre-existing behavior frozen by the extraction scope. I found one new correctness issue introduced by the Round 1 fix and one pre-existing correctness bug that the Round 1 findings missed.

## Findings

- [warning] f-6de6b4ef: The Round 1 fix for f-0f20dc94 (legacy shim) added a help short-circuit that returns `argv` unchanged when `-h`/`--help` is present and no verb is found. But `python -m aiwiki --help` now reaches `parser.parse_args(["--help"])` with `required=True` subparsers — argparse prints top-level help and exits 0, which is fine. However `python -m aiwiki foo.md --help` (legacy shape with help) also passes through unchanged, so argparse sees `foo.md` as an unknown positional and errors with exit 2 instead of showing ingest help. The pre-fix behavior injected `ingest --legacy-single-source foo.md --help` and showed the ingest help. This is a regression in the legacy shim's help UX. (src/aiwiki/cli.py)
- [warning] f-24375f5d: `target.relative_to(repo_root)` is called inside the f-string that builds the stale-claim description. If `cited_path` is absolute (e.g. `/etc/passwd`), `repo_root / cited_path` yields `/etc/passwd`, and `relative_to(repo_root)` raises `ValueError`, crashing the entire health-lint pass. This is the same class of bug as Round 1's f-b40606c2 (which was deferred for the stale-claim message in a different code path) but here it is in the primary stale-claims check, not the error path — a malformed frontmatter `sources[].path` aborts `lint --health` entirely. (src/aiwiki/health_lint.py)
- [note] f-89d5476c: Round 1's f-21b4bd3b was deferred as pre-existing. The deferral is defensible, but note that `detect_pending` calls `_count_data_lines(working_bytes)` on the working file *before* the malformed check has run in the same function — the malformed check is computed after `working_data`. If the working file lacks the marker, `_count_data_lines` silently misaligns and `pending` is wrong, but `malformed` will be True and `flush` raises before using `pending`. So the deferral is safe in practice; recording for 0.2 as the builder stated. (src/aiwiki/audit_flush.py)
- [note] f-85a6b8d1: Round 1's f-9634c43f was marked not-applicable with a correct trace. Confirming: `(1 if structural_rc == 0 else structural_rc) or audit_rc` returns 1 when structural is clean and health findings exist under `--strict`, returns `structural_rc` when structural failed, and returns `audit_rc` only when both are 0. The composition is correct. (src/aiwiki/cli.py)
- [note] f-bc8fc681: Round 1's f-9561399c was deferred as a comment-wording issue. The comment still says "Write atomically by replacing the file contents" while the code does `write_bytes` (truncate-and-write). The fail-closed detection the finding describes is real, so the deferral is acceptable, but the comment remains misleading. (src/aiwiki/audit.py)
