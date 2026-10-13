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
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: ai-wiki-0-1-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The refactor extracts a clean library surface (`aiwiki.api`) from the CLI, with typed results, a single exception-to-exit-code mapping in `_report`, and a well-structured fixture wiki. The design is sound and the tests are thorough, but there are a few correctness issues around exception handling in `_report`, the `LintResult.passed` semantics under `--health` without `--strict`, and a subtle behavior change in `audit_flush` reporting.

## Findings

- [warning] f-db0cfdb7: `_report` only handles `IngestError` and `ValueError`; `AuditFlushError` is a subclass of `IngestError` (per errors.py) so it is caught, but the `_ERROR_PREFIXES` tuple does not include it, so the message is printed without the `error:` prefix consistency check — verify `AuditFlushError` inherits `IngestError` and that its `exit_code` (11) is preserved. If it does not inherit, `audit-flush` failures will escape `main`'s `except (IngestError, ValueError)` and crash. (src/aiwiki/cli.py)
- [warning] f-38974f5f: `passed` returns `True` when `strict=False` even if `health.findings` is non-empty. The CLI `_do_lint` returns `0 if result.passed else 1`, so `ai-wiki lint --health` (without `--strict`) exits 0 despite findings. The old CLI returned `structural_rc or audit_rc` in that case, which is also 0 — so behavior is preserved, but the docstring on `passed` says "audit and health findings fail only under strict", which is accurate. Confirm this is the intended contract; the fixture playbook `recover-from-torn-audit-log.md` tells users to run `ai-wiki lint --strict`, implying non-strict is advisory. No change needed if intended, but the semantics deserve a test asserting `lint --health` (non-strict) exits 0 with findings. (src/aiwiki/api.py)
- [warning] f-68a65939: `describe_flush` returns `None` after a real commit ("git already reported"), but `flush_state` does not print anything on commit — the old `flush` also did not print on commit, so this is preserved. However, `_do_audit_flush` in cli.py now calls `describe_flush` and prints only if non-None, meaning a successful commit produces no stdout. Verify this matches the prior CLI contract (the old `flush` returned 0 silently on commit). If any consumer script greps for output, this is a silent behavior change. (src/aiwiki/audit_flush.py)
- [warning] f-2da62963: `output_dir = proposals_root / f"{today}-{request.source_path.stem or 'source'}"` — two ingests of different sources with the same stem on the same day will collide, and `write_patch_set_dir` behavior on an existing dir is not shown here. The legacy path uses a slug-based filename which is also collision-prone but at least overwrites a single file. For multi-page, a collision could merge or overwrite a prior proposal dir. (src/aiwiki/api.py)
- [warning] f-85521fd9: In `_ingest_legacy`, the snapshot is written only when `not dry_run`, which matches the comment. But `_write_ingest_snapshot(proposal_path.parent)` is called with the proposal file's parent — for legacy that is `output_dir`, which may contain other proposals. The snapshot copies `plan.json` and `preview/` from that dir; for legacy single-source there is no `plan.json`/`preview/`, so the snapshot dir is created empty. This is harmless but creates a stray `.ingest-snapshot/` dir for legacy runs. Confirm this is intended (the docstring says "never on dry-run or check" but does not say "never for legacy"). (src/aiwiki/api.py)
- [note] f-e5032acc: `DefaultQuerier(resolved, paths, max_pages)` uses positional args while the `max_pages is None` branch uses keywords. If `DefaultQuerier.__init__` signature changes, the positional call silently misbinds. Minor, but inconsistent. (src/aiwiki/api.py)
- [note] f-a9f15f6b: `resolved: Backend = backend if backend is not None and not isinstance(backend, str) else resolve_backend(backend)` — when `backend` is a `str`, `resolve_backend(backend)` is called; when `backend` is `None`, `resolve_backend(None)` is called. Both are fine, but the `isinstance(backend, str)` check is redundant with the `else` branch since `resolve_backend` presumably accepts `str  (src/aiwiki/api.py)
- [note] f-dcd2d8f2: The test asserts `list(self.paths.proposals_dir.iterdir()) == []` after both legacy and multi check runs. This is a strong assertion that depends on `make_repo_layout` creating an empty proposals dir. If the layout helper ever pre-populates it, the test breaks for the wrong reason. Fine as-is, but consider asserting `not any(...)` on specific artifacts instead. (tests/test_api.py)
- [note] f-0c3ba8e3: The doc says "Sources and proposal directories are confined to `--root`" and that `--allow-out-of-repo` lifts that. But `api.ingest` also accepts `output_dir` and `api.query` accepts `output_dir`; the doc does not state whether those are confined. From the code, `output_dir` is not checked against root. This is a documentation gap that could surprise consumers writing proposals outside the repo. (docs/consumers.md)
- [note] f-c2828c12: The tuple is ordered most-specific-first (`BackendInvocationError`, `ContractViolationError`, then promote errors). If any of these inherit from each other, the first match wins. Verify none of `PromoteValidationError`/`PromoteApplyError` subclass `ContractViolationError` or `BackendInvocationError`, otherwise the wrong prefix is printed. (src/aiwiki/cli.py)
