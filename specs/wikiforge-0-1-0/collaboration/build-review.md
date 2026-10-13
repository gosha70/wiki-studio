---
feature_id: wikiforge-0-1-0
date: 2026-10-13
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wikiforge-0-1-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wikiforge-0-1-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The changes tighten validation ordering in the promoter (validate before staging), fix a nested-root `git show` path bug, make schema loading per-file, and broaden health-lint error tolerance. The direction is sound and the tests cover the new behaviors, but I found a few correctness concerns around the new containment guard, the `append-log`/`append-index` merge, and the `_validate_before_staging` ordering relative to `dry_run`.

## Findings

- [warning] f-713f0ec9: The guard uses `Path(os.path.normpath(target)).is_relative_to(Path(os.path.normpath(stage_dir)))`. `os.path.normpath` does not resolve symlinks, and `Path.is_relative_to` is purely lexical. A symlink inside the staged tree pointing outside (e.g. `stage/wiki/evil -> /etc`) would pass this check and `target.write_text` would follow the symlink. Since the staged tree is a fresh copy this is low-likelihood, but the guard is advertised as defense-in-depth and does not actually contain symlink escapes. (src/wikiforge/promoter.py)
- [warning] f-151fa44a: The two branches were merged, but the error message now interpolates `target.name` instead of the literal `log.md`/`index.md`. More importantly, the merged branch no longer distinguishes the two actions, so a future divergence in append semantics (e.g. index needing a trailing newline rule, or log needing a header) cannot be expressed. This is a design smell that will bite when the two formats diverge. (src/wikiforge/promoter.py)
- [warning] f-da7d9812: `_validate_before_staging(patch, paths)` is invoked unconditionally after the `dry_run` branch. If `dry_run=True` previously returned a preview without validating, callers relying on dry-run to surface validation errors will now get them (good), but callers relying on dry-run to *not* raise on a bad patch will break. Confirm the intended contract: the docstring of `_validate_before_staging` says "before a single byte is staged", which is consistent, but the placement relative to `dry_run` should be explicit in the code (e.g. a comment) and covered by a dry-run test. (src/wikiforge/promoter.py)
- [note] f-0db9d309: The new check `if not isinstance(raw, dict) or "path" not in raw or "action" not in raw` raises `PromoteValidationError` with `{raw!r}` in the message. If `raw` is a large nested structure this could produce a very long message; more importantly, `"path" not in raw` on a non-dict is short-circuited correctly, but the error message does not distinguish "not a dict" from "missing key", which will make debugging harder. (src/wikiforge/promoter.py)
- [note] f-1cdf3218: The fix `f"HEAD:./{log_rel}"` is correct for relative paths, but the `Path(log_rel).is_absolute()` branch is dead in practice because `log_rel` is derived from `paths.audit_log` relative to `paths.root` and should always be relative. If it ever is absolute, `HEAD:/abs/path` is not a valid git revision syntax and will fail with a confusing error. Consider asserting `not Path(log_rel).is_absolute()` or documenting why the absolute branch exists. (src/wikiforge/audit_flush.py)
- [note] f-87703ce8: Broadening the catch to `ContractViolationError` is reasonable, but the comment says "log nothing, move on" — silently swallowing a contract violation means a systematically broken backend will produce a health pass with zero contradiction findings and no signal. Consider emitting a `HealthFinding` of kind `backend-error` (or similar) so the operator can see the check was skipped. (src/wikiforge/health_lint.py)
- [note] f-a70e8533: The test asserts `"path must be relative"` for both `../escape.md` and `/tmp/wikiforge-escape.md`. The absolute path case likely fails a different validation (absolute path rejection) than the relative-escape case; asserting the same substring for both may mask a regression where one path is rejected for the wrong reason. (tests/test_promoter.py)
- [note] f-820e5a99: The new per-file fallback is a behavior change: previously a project `schema/` directory shadowed *all* packaged schemas; now it shadows only the files present. This is the stated intent, but it means a project that intentionally ships a partial `schema/` dir to override one file will now silently pick up packaged defaults for the rest. Confirm this matches the spec and document it in the schema docs. (src/wikiforge/prompt.py)
