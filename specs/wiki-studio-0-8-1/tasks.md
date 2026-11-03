# Tasks: wiki-studio 0.8.1 — Release B launch and the integration measurement (wiki-studio side)

<!-- One `## US<n>:` group = one auto-build phase. [US#]/FR tags trace to spec.md. US<n> is pitch scope S<n>. -->
<!-- Read first: CLAUDE.md, spec.md, plan.md, specs/pitches/10-release-b-launch-and-measurement/pitch.md. -->
<!-- Run per phase: poetry run ruff check src/ tests/ eval/ conformance/ && poetry run ruff format --check src/ tests/ eval/ conformance/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=92 -->
<!-- From US3 on, also: poetry run ruff check examples/ && poetry run ruff format --check examples/ -->
<!-- Every new .py and .yml file starts with the two-line EGOGE / Apache-2.0 header. No runtime behaviour or API change under src/: only the version line in src/wiki_studio/__init__.py moves, in US5. No new exit code. No dependency in pyproject.toml; memkernel, huggingface_hub and the embedding model only in the clean-install CI jobs and record.py's virtual environment. No model backend on any executed path; ingest and query are shown, never run. promoter.py stays the single writer. Never edit docs/agent-arm/config.frozen.json, docs/agent-arm/instruction.md, eval/navigation/, conformance/runs/ or a recorded run. No memkernel code or doc edits. No runner, statistics, event-schema or task code. No commit, push or branch change inside the session; the driver owns git. A src/ defect found by a quickstart stops the phase (D13). -->

## US1: The standalone quickstart, executed

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 1 | | Run-block helper: parse a markdown page into its fenced blocks with info string `bash run` / `python run` plus optional `exit=<N>` (default 0) and `contains=<token>`, in page order, and the `bash server-cmd` block; run each in one fresh resolved temporary project directory, each its own process (`bash -euo pipefail` over the text; a `python run` block as a script file run by `sys.executable`), with `Path(sys.executable).parent` first on `PATH`, every `WIKI_STUDIO_*` and every `MEMKERNEL_*` except `MEMKERNEL_EMBEDDING_MODEL` removed, a per-block timeout; assert the exit code and the `contains` token and report index, first line, exit code, stdout, stderr; refuse a page with no run block and a run block containing `wiki-studio ingest`, `wiki-studio query`, `--backend`, `api.ingest` or `api.query` (FR-002) | `tests/helpers/quickstart_blocks.py` | build | [ ] |
| 2 | | The page: install (shown); `init`; a draft directory outside the wiki (decision page with `status: stable`, one index line, one log line); `propose --from <dir> --promote --by you`; the `api.review_state` block printing `state:<value>`, `reason`, `live_sha256`, `approved_sha256` (`contains=state:unapproved`); `approve <page> --by you`; the same block (`contains=state:approved`); `find`; `read --json`; the guarded update with `.base.json` (`exit=0`); the same draft again (`exit=9`, stale); `lint`; `findings`; the `server-cmd` block `wiki-studio-mcp --root "$PWD"`; `claude mcp add --env WIKI_STUDIO_ACTOR=you wiki-studio -- wiki-studio-mcp --root "$PWD"`, propose-only mode, `.mcp.json`, Kiro by link, and the `ingest` aside, each marked "not executed in CI" with a link to the recorded Claude Code host run (FR-001, FR-003, FR-004) | `docs/quickstart.md` | build | [ ] |
| 3 | | Tests: the page's run blocks pass through task 1's runner; the `claude mcp add` line's command after `--` equals the `server-cmd` line; that line with `$PWD` replaced by `{root}` passes `python -m conformance.mcp.run --server-cmd` from the repository root with exit 0 (skipped with the reason when `mcp` is not importable); parser unit tests: info-string grammar, `exit=` and `contains=`, a block without `run` never executed, the empty-page refusal, the `ingest`/`query`/`--backend` refusal (FR-002..FR-005) | `tests/test_quickstart.py` | build | [ ] |
| 4 | | CI job `quickstart` (blocking, Python 3.11, `timeout-minutes: 30`): `poetry build`; fresh venv; `pip install "$(ls dist/*.whl)[mcp]" pytest`; `pip check`; import check of `mcp` and `wiki_studio.api`; `python -m pytest -q -p no:cacheprovider -rs tests/test_quickstart.py` (FR-005) | `.github/workflows/ci.yml` | build | [ ] |
| 5 | [P] | README Install links `docs/quickstart.md` (FR-005) | `README.md` | build | [ ] |

**Checkpoint US1** — verify before continuing:
- [ ] `poetry run pytest -q -p no:cacheprovider -rs tests/test_quickstart.py` passes with the conformance check not skipped
- [ ] Editing one `exit=` value in a scratch copy of the page makes the test fail naming that block (then discard the copy)
- [ ] `git diff --stat main -- src/ docs/agent-arm/config.frozen.json docs/agent-arm/instruction.md eval/navigation/ conformance/runs/` is empty
- [ ] Full gate green

---

## US2: The memkernel composition quickstart, executed

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 6 | | The page: install `memkernel[wiki]==0.6.0` and `wiki-studio[mcp]==0.8.1` (shown); one `.mcp.json` with memkernel's server entry and `wiki-studio-mcp --root <project> --disable-tool promote`, Kiro by link (shown); the setup run block (`git init -q`; `.gitignore` with `.wiki.wiki-studio.*`, `.memkernel/`, `.env`; `.env` with absolute `MEMKERNEL_PROJECT_ROOT` (`$PWD`), `MEMKERNEL_PROJECT_ID`, `MEMKERNEL_CHROMA_PERSIST_PATH`, `MEMKERNEL_WIKI_DIR`, `MEMKERNEL_WIKI_PROPOSALS_DIR` = `$PWD/doc_internal/proposals`); `wiki-studio init`; session 1 (`build_service()`, `retain` of a neutral-first-line wrong decision, `recall`: the wrong rule is current); `wiki_export` through `WikiExporter` constructed as 0.6.0's tool does; the curator (`read --json`, the edit to `status: stable` with the rule replaced in title, heading and body and `corrects: <memkernel_ref>`, `.base.json`, `propose --from … --promote --by curator`, `lint`, `approve --by curator`); `wiki_import` through `WikiImporter`; `recall` (right answer current, wrong rule in no current memory); memkernel's tools named as tool calls beside each executed Python block (FR-006, FR-007) | `docs/quickstart-memkernel.md` | build | [ ] |
| 7 | | Commit policy table on the page, path by path: commit `knowledge/wiki/.wiki-studio.json`, pages, `index.md`, `log.md`, the whole `knowledge/wiki/.audit/` (ingest log, `proposals/`, `approvals/`, with the reason), `doc_internal/proposals/` with `.applied/` (the receipts exist only there); ignore only the lock and the search cache (`.wiki.wiki-studio.*`); memkernel's `.memkernel/` and `.env` stay out of git as memkernel's own files (FR-008) | `docs/quickstart-memkernel.md` | build | [ ] |
| 8 | | The handoff run blocks: `git add -A`, `git -c user.name=quickstart -c user.email=quickstart@example.invalid commit -q`, `git clone -q . ../teammate`; in the clone, its own `.env`, then checks that exit non-zero naming the check: lock, cache, `.memkernel/` and `.env` absent; every page the original approved reads `approved` through `api.review_state`; `wiki_import` imports exactly those pages with each `page_sha:` tag equal to `approved_sha256`; `recall` returns the right answer and no current memory has the wrong rule (FR-009) | `docs/quickstart-memkernel.md` | build | [ ] |
| 9 | | Verify every memkernel call on the page against the installed 0.6.0 package (constructor keywords, `retain` return, `recall`, `get(..., touch=False)`, `list_memories(include_superseded=True)`, report fields) and write each as 0.6.0 accepts it (FR-007) | `docs/quickstart-memkernel.md` | build | [ ] |
| 10 | | Test: the page's run blocks through task 1's runner; skipped with the reason when memkernel is not installed (FR-010) | `tests/integration/test_quickstart_memkernel.py` | build | [ ] |
| 11 | | CI job `quickstart-memkernel` (blocking, Python 3.11, `MK_VERSION: "0.6.0"`, `timeout-minutes: 30`): `poetry build`; fresh venv with the wheel, `memkernel==${MK_VERSION}` and pytest; `pip check`; import check of `memkernel.wiki.sync` and `wiki_studio.api`; `actions/cache` of the Hugging Face cache keyed on the revision; `snapshot_download("sentence-transformers/all-MiniLM-L6-v2", revision="1110a243fdf4706b3f48f1d95db1a4f5529b4d41")`, a check that the snapshot directory is that revision, `MEMKERNEL_EMBEDDING_MODEL=<path>` and `HF_HUB_OFFLINE=1` exported to the test step; run the test with `-rs` (FR-007, FR-010) | `.github/workflows/ci.yml` | build | [ ] |
| 12 | [P] | Links: README Install to `docs/quickstart-memkernel.md`; `docs/consumers.md` memkernel section (58) points to it and keeps its recipes as reference (FR-010) | `README.md`, `docs/consumers.md` | build | [ ] |

**Checkpoint US2** — verify before continuing:
- [ ] In a venv with the wheel and `memkernel==0.6.0`, `python -m pytest -q -p no:cacheprovider -rs tests/integration/test_quickstart_memkernel.py` passes (or the session reports plainly that it could not install memkernel, and the CI job is the first run)
- [ ] The page's `.gitignore` lists exactly `.wiki.wiki-studio.*`, `.memkernel/` and `.env`
- [ ] Every Python block on the page imports only `memkernel`, `wiki_studio` and the standard library, and none names `ingest`, `query` or a backend
- [ ] Full gate green

---

## US3: The obsolete-decision demonstration

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 13 | | `demo.py` orchestrator and steps: `--workdir DIR [--summary PATH]` runs `session-1`, `curator`, `session-2` as `sys.executable demo.py <step> --workdir DIR` subprocesses with memkernel's settings in their environment; stops at the first failure; exit 0 / 1 (a named failed check) / 2 (cannot run); explicit checks, no `assert`; the curator's `wiki-studio` beside `sys.executable` (FR-011) | `examples/correction-loop/demo.py` | build | [ ] |
| 14 | | `session-1`: `api.init`; retain the neutral-first-line wrong decision; recall, check the wrong rule is current; export (gated, one draft page); print `ref_id`, page, `submission_digest`. `curator`: `read --json`; corrected draft outside the wiki (`status: stable`, `corrects: <memkernel_ref>`, rule replaced in title, heading, body); `.base.json`; `propose --from … --promote --by curator`; `approve <page> --by curator`; print the receipt (`proposal`, `submission_digest`, `actor`, `started_at`, `committed_at`) and the approval record (`approver`, `timestamp`) through `review_state`'s `record_path` (FR-012) | `examples/correction-loop/demo.py` | build | [ ] |
| 15 | | `session-2`: `wiki_import` (governed, page imported, wrong `ref_id` in `corrections`); recall; print answer, page, `page_sha` beside `approved_sha256` (equal), `submission_digest`, `committed_at`, `approver`, `timestamp`; wrong rule in no current answer (`get(..., touch=False)` of each recalled ref and `list_memories()`); old record from `list_memories(include_superseded=True)` with `superseded_by` equal to the page memory's `ref_id`; `--summary` JSON with versions, values, every check and the UTC times of the approval and the corrected recall (FR-013) | `examples/correction-loop/demo.py` | build | [ ] |
| 16 | | `record.py` (standard library only): refuse unless `git status --porcelain` is empty and `--out` does not exist (exit 2); record `HEAD`; `git archive HEAD` into a temp dir and `poetry build` there, wheel name and sha256; `pip download memkernel==0.6.0 --no-deps --only-binary :all:`, sha256, compare with `https://pypi.org/pypi/memkernel/0.6.0/json` (refuse on mismatch); fresh venv with both files, `environment.txt` from `pip freeze`; `snapshot_download` at `EMBEDDING_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"` (`--embedding-revision`), refuse unless the snapshot is that revision; run `demo.py` once with `MEMKERNEL_EMBEDDING_MODEL=<snapshot>` and `HF_HUB_OFFLINE=1`, output to `transcript.txt`, never retried; copy `end-state/` (wiki and proposals with `.applied/`; no lock, cache or store); `python -m conformance.mcp.run tree-hash end-state`; write `manifest.json` with FR-014's keys including `wall_time_seconds` and `wall_time_label`; exit with the demo's code (FR-014) | `examples/correction-loop/record.py` | build | [ ] |
| 17 | [P] | Protocol: the commit order (script, recorder and protocol first; clean tree; run once; run directory committed alone, never edited), the run directory layout and manifest keys, the real model at the pinned revision, a failed attempt kept and a second attempt a new directory, wall times as machine time on a scripted path (D15), what the end-state hash binds and that it does not reproduce across runs (FR-014) | `examples/correction-loop/README.md` | build | [ ] |
| 18 | | CI job `demo-correction-loop` (blocking, Python 3.11, `timeout-minutes: 45`): checkout, Poetry, `actions/cache` of the Hugging Face cache keyed on the revision, `python examples/correction-loop/record.py --out "$RUNNER_TEMP/demo-run"`, then print `transcript.txt` and `manifest.json` (FR-015) | `.github/workflows/ci.yml` | build | [ ] |
| 19 | [P] | The page: the story in about one screen with the CI job as evidence and the recorded run marked pending until the evidence PR quotes it; replacement only, deprecation and deletion wait for memkernel 0.7 (D11); wall times labelled (D15); none of "cheaper", "better", "faster", "prevents", "guarantees"; links to and from both quickstarts (FR-016) | `docs/demo-correction-loop.md`, `docs/quickstart.md`, `docs/quickstart-memkernel.md` | build | [ ] |
| 20 | [P] | Small fixes: the loop test's module docstring (11-15) says `memkernel-loop` is blocking since the 0.6.0 pin, no test body change; the CI `lint` job checks and format-checks `eval/` and `examples/`; `CLAUDE.md` format command and layout list `examples/` (FR-017) | `tests/integration/test_release_b_loop.py`, `.github/workflows/ci.yml`, `CLAUDE.md` | build | [ ] |

**Checkpoint US3** — verify before continuing:
- [ ] `python examples/correction-loop/record.py --out <tmp>/run` on a clean tree exits 0 and writes `manifest.json` with every FR-014 key (or the session reports plainly that PyPI or Hugging Face was unreachable, and the CI job is the first run)
- [ ] `python examples/correction-loop/demo.py --workdir <non-empty dir>` exits 2; a patched check failure exits 1 naming it
- [ ] `poetry run ruff check examples/ && poetry run ruff format --check examples/` passes
- [ ] `git diff main -- tests/integration/test_release_b_loop.py` touches only the docstring
- [ ] Full gate green

---

## US4: The measurement design (stretch, cut first)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 21 | | The ceiling, explained with links to memkernel at `v0.5.0`: exposure prompt, the shared-artifact copy for every arm, the evaluation prompt, the index-only fixture; every arm 25 of 25, +0.0 effects, "no gain claimed"; the two diagnostics only (0 of 177 Bash calls ran `ingest`/`query`; 0 of 9 `Write`/`Edit` under the wiki; `fs_grep` 52 of 78, `memkernel` 38 of 63); no gate claim and why; tokens not comparable (4,309,745 on 25 trials against about 19-20 million over 100, no per-group table) (FR-018) | `eval/composition/design.md` | build | [ ] |
| 22 | | Requirements for a task set that can discriminate (calibration showing `bare` fails; an obsolete decision per chain with an X / Y / other checker; the correction only through the arm's own workflow; competing pages); five to ten task sketches in prose, no code (FR-019) | `eval/composition/design.md` | build | [ ] |
| 23 | | The arms (memkernel alone, memkernel with governed wiki-studio, files plus grep, the negative control); a new versioned composition arm; the curator options (scripted with a preregistered policy, `auto_approve_on_promote`, oracle upper bound), what each measures, a recommendation; the gate's own records checked as an arm requirement; the 0.4.1 instruction's `status: draft` noted; one pointer note at the top of the agent-arm README; the arm's two hashed files untouched (FR-020) | `eval/composition/design.md`, `docs/agent-arm/README.md` | build | [ ] |
| 24 | | The six questions mapped to a measurement or existing evidence; memkernel's dependencies listed, not built (arm and curator step, task set and calibration, per-group token table, preregistration, budget, memkernel 0.7 for withdrawal); a line that the document preregisters, runs and budgets nothing (FR-021) | `eval/composition/design.md` | build | [ ] |

**Checkpoint US4** — verify before continuing:
- [ ] `git diff --stat main -- docs/agent-arm/config.frozen.json docs/agent-arm/instruction.md` is empty; `git diff main -- docs/agent-arm/README.md` is one note
- [ ] `eval/composition/` holds only `design.md`; no `.py` file was added under `eval/`
- [ ] The design contains no claim that the 0.4.1 arm stayed inside the gate
- [ ] Full gate green

---

## US5: Closing issue #10, the launch docs and release 0.8.1

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 25 | | Write, do not file: the successor issue's body and the #10 closing comment, committed under `eval/composition/` beside `design.md` (or its FR-028 cut form), each linking the design by a permalink placeholder `{design_permalink}` filled at filing. The filing is an interactive owner step after the build and before the PR merges, in order: memkernel issue (body: the committed design), successor issue, #10 comment; the PR body carries `Closes #10` (FR-025) | `eval/composition/successor-issue.md`, `eval/composition/issue-10-comment.md` | build | [ ] |
| 26 | | README Evidence: replace 654-656 with the 0.5.0 restatement (arm on `lc-wiki`, 25 of 25 like every arm including `bare`, a ceiling, no claim, tokens not comparable), linked to memkernel's report, the demo page, the design and the successor issue; no efficiency or superiority wording (FR-022) | `README.md` | build | [ ] |
| 27 | [P] | Roadmap: Launch sequence step 2 names the two quickstarts, the matrix and the demonstration with their evidence; Evidence says the published 0.5.0 run is at ceiling and no governed-composition measurement able to discriminate the arms has been run, pointing to the design and the successor issue; Release B's docs line records the quickstarts (FR-023) | `docs/roadmap.md` | build | [ ] |
| 28 | [P] | Compatibility: a row for 0.8.1 with memkernel 0.6.0 naming `memkernel-compat`, `memkernel-loop`, `quickstart-memkernel`, `demo-correction-loop` (and `quickstart` for the standalone path), status pending until a green run on `main` is named (FR-024) | `docs/compatibility.md` | build | [ ] |
| 29 | | Release: 0.8.1 in `pyproject.toml`, `src/wiki_studio/__init__.py`, `tests/test_cli_contract.py` and README Install together; CHANGELOG `[Unreleased]` entries move under `[0.8.1]` (undated) with Added, Changed and the Notes line (no runtime behaviour, API, exit code, page schema or dependency change), naming the memkernel and successor issue numbers; `CLAUDE.md` layout lists `examples/correction-loop/` and `eval/composition/` and Commands the quickstart tests; `SECURITY.md` unchanged (FR-026) | `pyproject.toml`, `src/wiki_studio/__init__.py`, `tests/test_cli_contract.py`, `README.md`, `CHANGELOG.md`, `CLAUDE.md` | build | [ ] |
| 30 | | Invariant and cut audit: `git diff main -- src/` is the version line only; no exit-code, dependency or `promoter.py` change; frozen files untouched; wording grep clean on the new pages, README Evidence and the roadmap; if US4 was cut, its cut form is what was filed and is marked as such in the CHANGELOG (FR-027, FR-028) | `CHANGELOG.md` | build | [ ] |

**Checkpoint US5** — verify before continuing:
- [ ] `poetry run wiki-studio --version` prints 0.8.1; `poetry build` succeeds
- [ ] `git diff main -- src/` shows only `__version__ = "0.8.1"`
- [ ] README Evidence, the roadmap and the CHANGELOG link the composition design and say the memkernel and successor issue numbers are added when they are filed (the interactive step after the build); nothing was filed by the build
- [ ] `grep -rniE "cheaper|better|faster|prevents|guarantee" docs/quickstart.md docs/quickstart-memkernel.md docs/demo-correction-loop.md` finds nothing, and README Evidence's new text and the roadmap's Evidence edit contain none of them
- [ ] Full gate green, with `examples/` checked

---

## Final Verification

- [ ] Type checker: 0 errors; linter and formatter: 0 errors on `src/ tests/ eval/ conformance/ examples/`
- [ ] Full suite green with coverage at or above 92 percent
- [ ] `quickstart`, `quickstart-memkernel`, `demo-correction-loop`, `memkernel-compat`, `memkernel-loop`, `mcp-min` and `mcp-latest` green on the PR
- [ ] No runtime behaviour or API change under `src/` (the version line only); exit codes unchanged (0, 2..11; 1 fatal lint)
- [ ] No dependency added; memkernel only in clean-install jobs and the recorder's environment
- [ ] No model backend on any executed path; `ingest` and `query` appear only in non-run blocks
- [ ] `promoter.py` is the only writer into the wiki; the single-writer scans pass unchanged
- [ ] `docs/agent-arm/config.frozen.json`, `docs/agent-arm/instruction.md`, `eval/navigation/` and `conformance/runs/` are byte-identical to `main`
- [ ] Each quickstart has one source: no script outside the page repeats its commands
- [ ] The recorded run is left to the evidence PR; nothing under `examples/correction-loop/runs/` was written by the build
- [ ] #10 is not closed by the session; the PR body carries `Closes #10`
