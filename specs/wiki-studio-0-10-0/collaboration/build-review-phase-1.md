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

The nightly pass is a clean, read-only addition that correctly avoids backend resolution, locking, and wiki writes. The main correctness concerns are around `check_report_path`/`write_report` being decoupled (the safety check is not enforced by the writer), a TOCTOU gap in the atomic write, and a few smaller issues around `needs_curator` semantics and error handling in `_pending_proposals`.

## Findings

- [warning] f-66f4591d: `write_report` does not call `check_report_path`, so a caller can write the report inside the wiki directory, violating FR-005's intent that the report must lie outside the wiki. The safety check is only advisory. (src/wiki_studio/nightly.py)
- [warning] f-e3e89372: `target = Path(path).resolve()` is computed before `mkdir`, but `os.replace` uses the resolved path while the temp file is created in `target.parent`. If `path` is a symlink or its parent is a symlink that changes between resolve and replace, the write can land elsewhere than validated. Also, `resolve()` on a non-existent path with a symlinked parent is fine, but the resolved target is not re-checked against the wiki after `mkdir`. (src/wiki_studio/nightly.py)
- [warning] f-6a6ef54b: Only `FileNotFoundError` is caught. `NotADirectoryError`, `PermissionError`, or `OSError` from a broken proposals dir will propagate and abort the whole nightly run, contradicting the "reads only, report what you can" spirit and the docstring's implication that unreadable proposals are tolerated (edits=None). (src/wiki_studio/nightly.py)
- [warning] f-107f8ee5: `needs_curator` is set to *all* findings, so the "Needs a curator" section duplicates the "Findings" section verbatim (minus severity/description). The spec (FR-003) implies a curated subset; if all findings are curator-relevant, the duplication is at best confusing and at worst a spec mismatch. (src/wiki_studio/nightly.py)
- [note] f-b05ad4f4: `read_text` can raise `UnicodeDecodeError` (a `ValueError` subclass, so caught) but also `IsADirectoryError` (an `OSError`, caught) — fine. However, a `plan.json` that is a symlink pointing outside the proposals dir is followed; combined with `entry.is_dir()` on the proposal dir, a symlinked proposal dir could cause reads outside the proposals tree. Low risk but worth noting. (src/wiki_studio/nightly.py)
- [note] f-2c1fd9bb: The deferred import is justified, but `api.nightly` calls `_nightly_run(paths)` which re-imports `api` — a circular import that works only because of the deferred import. If `nightly.run` is ever called before `api` is fully initialized (e.g., from a module-level import in `api`), this will fail. The current wiring is safe but fragile. (src/wiki_studio/nightly.py)
- [note] f-a7b10b36: `datetime.datetime.now(datetime.UTC)` requires Python 3.11+. If the project supports 3.10, this raises `AttributeError`. Verify the minimum supported version. (src/wiki_studio/nightly.py)
- [note] f-052b466e: Tests cover the happy path, lint failure, and audit errors, but do not cover: (a) `check_report_path` refusing a path inside the wiki, (b) `write_report` atomicity/cleanup on failure, (c) `_pending_proposals` with a malformed `plan.json`, (d) `_pending_proposals` with a missing proposals dir, (e) `write_report` creating missing parents. These are the riskiest new code paths. (tests/test_nightly.py)
- [note] f-6684ea01: The comment says the format is "advertised in FORMATS only when it ships (FR-033)", but `NIGHTLY_FORMAT_VERSION` is defined and `FORMATS` is not updated in this diff. If the intent is to advertise now, `FORMATS` should include `"nightly": NIGHTLY_FORMAT_VERSION`; if not, the constant is dead until a later phase. Clarify which phase adds it to `FORMATS`. (src/wiki_studio/contract.py)
- [note] f-9bf65b49: `warnings` is always `()` in `run` and never populated, yet it is part of the JSON form and markdown (implicitly, via `as_dict`). Either populate it (e.g., when `_pending_proposals` hits an unreadable dir) or remove it to avoid a dead field in the public format. (src/wiki_studio/nightly.py)
