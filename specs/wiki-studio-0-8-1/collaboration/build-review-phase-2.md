---
feature_id: wiki-studio-0-8-1
date: 2026-11-03
status: final
phase: build
mode: review
phase_num: 2
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
verdict: FAIL
bypass: true
breaker_type: driver_fix_sessions_exhausted
blocking_findings_open: 1
target_ref: feature/wiki-studio-0-8-1
rounds_completed: 3
attempt_count: 1
approved_by: gosha70 (owner)
---

# Peer Review: wiki-studio-0-8-1 — Build Phase 2 (bypassed by the owner)

DeepSeek reviewed phase 2 (US2, the memkernel composition quickstart) over three rounds; the driver's two fix sessions resolved or settled every finding but one, and the run parked on the fix-session limit.

## Why the bypass

Owner-approved bypass (review-decide approve, 2026-11-03). The only round-3 blocking finding, f-257947bc (the correction block's replace_once('Deploy window') finds zero hits), is disproved by execution: memkernel v0.6.0 WikiExporter._page_for (sync.py:285) writes the memory's full content, 'Deploy window' and the rule, into the first section, and tests/integration/test_quickstart_memkernel.py, including test_every_run_block_passes_in_page_order, passed 6/6 (9 subtests) against memkernel==0.6.0 from PyPI with the pinned embedding snapshot 1110a243 on the build host. The remaining warnings are a disagreement settled by the approved spec (FR-007: a failed download or revision mismatch exits 2) and requests to see test code outside the reviewed diff, which exists and ran in that execution.

## Findings open at the park (round 3)

- **f-257947bc** [blocking] `docs/quickstart-memkernel.md`: The exporter's page body is the memory's second line only (`Deploy on Fridays after 17:00 UTC.`); "Deploy window" appears in `title:` and `# Deploy window` but not in the body prose. The prior `replace_once` calls already consumed the title and H1 occurrences, so this call finds zero hits and raises `SystemExit("expected exactly one line 'Deploy window', found 0")`. The block aborts on a correct run. Round 2 marked this "disputed" but the code is unchanged and the reasoning in the Round 2 finding stands.
- **f-5c01f57b** [warning] `.github/workflows/ci.yml`: Round 2 f-3cd80859 was marked "disputed", but the code still routes `RepositoryNotFoundError`/`RevisionNotFoundError` from `model_info` and `snapshot_download` through `broken_pin`, which exits 2. A deleted or renamed upstream revision is a pin-correctness failure, not infra; classifying it as exit 2 means a broken pin passes CI as "infra" (the step fails, but with the wrong exit code, so the failure is not attributed to the pin). The comment claims "a broken pin never passes CI" — true only because the step fails, not because the exit code distinguishes it.
- **f-861ce6f5** [warning] `tests/integration/test_quickstart_memkernel.py`: Round 2 f-cfb91974 was marked "fixed" but the diff does not show the test body. The CI step sets `MEMKERNEL_EMBEDDING_MODEL` and `HF_HUB_OFFLINE=1` via `GITHUB_ENV`, which reaches the pytest process; the test must forward `os.environ` (or an explicit copy including these keys) into each block's subprocess `env`, and must not override `HOME`/`HF_HOME` per-block in a way that defeats the cache. Unverifiable from the diff.
- **f-83bb19dd** [warning] `tests/integration/test_quickstart_memkernel.py`: Round 2 f-d2bbfa71 was marked "fixed" but the diff does not show the test body. The test should parse the doc for `bash run`/`python run` markers and assert the set of executed blocks matches, so a future edit that flips a marker without updating the test fails.
- **f-3f06a93d** [note] `docs/quickstart-memkernel.md`: Round 2 f-18cfbb60 was marked "fixed" but the block still does `original = Path.cwd()` without verifying it is the project root (e.g. that `knowledge/wiki/decisions/deploy-window.md` exists in `original`). A block run from the wrong cwd would silently check the wrong tree. Low risk given the test runs blocks in one temp dir, but the block is not self-checking.
- **f-75127890** [note] `docs/quickstart-memkernel.md`: The §9 prose now says "`memkernel_ref` still names the memory the draft was exported from; `corrects:` names the same ref" — this is consistent with the code (both are the wrong ref, since the import never writes the page). The Round 2 blocking finding is resolved. Noting for closure; no action needed.

## Independent confirmation

The external reviewer rechecked phase 2 at 3fc4a60 without the phase-3 working tree: the finding f-257947bc is incorrect (memkernel 0.6.0 `WikiExporter._page_for` writes the memory's complete content into the first section), and the archived tree passed 6 tests and 9 subtests against memkernel 0.6.0 with embedding revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41. The shared `build-review.md` beside this file is overwritten by every later phase; this file is the durable phase-2 record, copied from commit a2b9077.
