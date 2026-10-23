---
spec_mode: full
feature_id: wiki-studio-0-6-0
risk_category: feature
justification: "Changes the write path of the only module that writes into the wiki, adds an OS lock and a receipt artifact, adds an optional key to the published patch-set format and fields to the public API, and rewrites published guarantees; a full spec pins each behaviour before an unattended build."
status: draft
date: 2026-10-23
collaboration_mode: single
origin:
  urls:
    - https://github.com/gosha70/wiki-studio/blob/41cfe5433a1e2097d615eb62ffbe4b8ace18ee24/src/wiki_studio/promoter.py
    - https://github.com/gosha70/wiki-studio/blob/41cfe5433a1e2097d615eb62ffbe4b8ace18ee24/src/wiki_studio/querier.py
    - https://github.com/gosha70/wiki-studio/blob/41cfe5433a1e2097d615eb62ffbe4b8ace18ee24/SECURITY.md
  origin_claim: |
    Owner's product proposal of 23 October 2026 (Wiki_Studio_Product_Proposal.docx),
    Release A "Safe changes", adopted with the review of the same date (revision 3).
    Five defects reproduced on main at 41cfe54: concurrent promotes revert each
    other's pages (commit writes back every staged page that differs); no revision
    precondition on replacements; containment incomplete (symlinked page written
    through, absolute and escaping links accepted, `find` follows an outside file);
    the citation check accepts a fabricated fragment and an answer without
    evidence; "atomic" means exception rollback. Release A: commit only the
    patch-set's paths; serialise cooperating writers with an OS advisory lock
    keyed to the resolved wiki; record a base revision per replacement, captured
    where the author read the page, and check it under the lock; refuse unguarded
    replacements unless a compatibility option is passed (creates and appends
    stay safe); three containment boundaries; citation fragments validated against
    the prompt snapshot; receipts separate from submitted bytes; honest guarantees;
    version 0.6.0 (optional format keys belong to a minor), with a defined 0.5.1
    subset if it slips. Settled owner decisions: per-operation legacy policy,
    exit 9 for conflicts and 10 with reason lock_timeout, lock beside the resolved
    wiki with a 30-second default, `../` source references inside the root legal.
---

# Plan: wiki-studio 0.6.0 — safe changes (Release A)

The owner's product proposal and its revision-3 review are the shaping record.
Every file and line the spec relies on was checked on `main` at 41cfe54 on
23 October 2026; the reproductions in the review are the acceptance tests.

## Architecture decisions

- **ADR-1: Commit writes the patch-set, not the stage.** The stage stays a
  full copy because the structural linter needs a whole tree to check
  reachability, but `_commit_stage_to_wiki` writes back only the edits' paths
  and this proposal's archive. Writing back "whatever differs" is what let one
  promote revert another.
- **ADR-2: An OS advisory lock, owned by a descriptor.** `flock` on POSIX and
  `msvcrt.locking` on Windows behind `WikiLock`. A PID file with stale
  reclamation lets two contenders both judge a lock stale and one delete the
  other's fresh lock; the OS lock has no such window. The file is a sibling of
  the resolved wiki so it is outside staging and lint, and keyed to the
  resolved path so aliases share it. PID data is diagnostic only.
- **ADR-3: The base revision is captured where the page was read.** Ingest
  hashes its captured candidate pages; `read` returns content and digest from
  one read; `propose --from` takes hashes from a manifest the agent wrote and
  never from the live page at propose time. Filling a hash later would
  legitimise a stale draft, which is the defect being fixed.
- **ADR-4: Legacy policy by operation.** memkernel's bridge emits creates and
  appends only, so requiring a base revision for replacements costs its export
  path nothing. Creates are checked for absence and appends applied to current
  content under the lock; an unhashed replacement is refused unless the caller
  opts into compatibility mode, which is recorded and never described as safe.
- **ADR-5: Receipts beside immutable submissions.** The archived plan and
  previews keep their bytes and digests; outcome, overrides and software
  identity go in `receipt.json`. The archive name carries the plan digest so
  same-named proposals cannot collide, and retries are answered from the
  receipt without re-running appends.
- **ADR-6: Three containment boundaries.** Wiki for page writes and navigation
  reads, proposal directory for preview reads, root or allowed source root for
  source references. One boundary would either break source citations or let
  previews escape. Index entries outside the wiki are lint violations, so
  promote rejects what `find` would otherwise have to filter.
- **ADR-7: Citations are checked against the prompt snapshot.** Validating
  against files reread after the backend returns would fail a correct answer
  whose source changed during generation, or pass evidence the model never saw.
- **ADR-8: Say what the code does.** "Atomic" leaves the docs. The promote
  guarantee is validation, serialisation on one machine, exception rollback;
  not crash safety. The stack-level limitation (memkernel's outer rollback) is
  named in the release notes.

## Phases (one auto-build phase per `## US<n>:` group of tasks.md)

| Phase | What | Main files |
|---|---|---|
| US1 | Commit scope, `WikiLock`, receipts and archive naming, retry semantics, lock on the ingest-log append | `promoter.py`, `wikilock.py` (new), `audit.py`, `paths.py`, `docs/patch-set-format.md`, CI workflow (Windows lock job) |
| US2 | `base_sha256` in the edit model and `plan.json`, `api.read_page` and `wiki-studio read`, hash capture in ingest and `propose --from`, preconditions under the lock, compatibility option, `PromoteResult` fields, dry run on a snapshot | `proposal.py`, `ingestor_multi.py`, `ingestor.py`, `prompt.py`, `api.py`, `cli.py`, `promoter.py`, `docs/patch-set-format.md` |
| US3 | Symlink refusal, `resolve()`-based checks, preview-pointer rejection, link classification, index-entry rule shared by lint, `find`, `query` and the eval selector | `promoter.py`, `lint.py`, `querier.py`, `api.py`, `paths.py` |
| US4 | Citation fragments validated against the prompt snapshot; evidence required for a non-empty answer | `querier.py`, README |
| US5 | Honest guarantees in README, SECURITY.md and docstrings; CHANGELOG with per-operation upgrade notes and limitations; version 0.6.0 | README, SECURITY.md, `promoter.py`, CHANGELOG, `pyproject.toml`, `__init__.py`, `tests/test_cli_contract.py` |

US1 first: US2's precondition check and US3's `lstat` re-check both run
under the lock. US3 and US4 are independent of US2. US5 last.

## Unattended run

`specs/wiki-studio-0-6-0/automation.json`: profile `pr`, branch
`feature/wiki-studio-0-6-0` off `main`, five phases with no milestone pause,
DeepSeek gating review (max 3 rounds per phase), caps as for 0.5.0. The
origin-alignment record is written by the gate before the run; this bundle
does not carry one yet.

## Test strategy

- Every FR maps to at least one unit or CLI test (CLI in-process through
  `wiki_studio.cli.main(argv)`); the 22 October reproductions become
  `tests/test_promote_concurrency.py`, `tests/test_promote_preconditions.py`,
  `tests/test_containment.py` and `tests/test_query_evidence.py`.
- Concurrency tests of two kinds: the focused commit-scope test that stages
  both and commits sequentially with the promoter's internal steps; and
  subprocess tests whose child is started through a test bootstrap that patches
  the promoter's post-stage step before calling `cli.main`, so one child is
  held after staging while the other contends for the lock.
- Lock tests are parametrised over the available backends; the Windows CI job
  runs the `msvcrt` backend.
- Regression: the single-writer test, the CLI contract tests, `test_schema.py`
  and both evaluation runs' determinism tests stay green; coverage stays at or
  above 92%.

## Risks

- `flock` semantics differ across filesystems; the docs scope the lock to one
  machine and one local filesystem, and the tests use a temporary local
  directory.
- Adding a Windows CI job may surface unrelated platform differences; the
  fallback is to narrow the classifier to POSIX in this release.
- The archive rename changes a path consumers may have scripted against;
  recorded under Changed, and `.applied/` keeps the same parent.
- memkernel's outer snapshot can still revert a committed change until its own
  fix lands; stated as a limitation, not hidden.

## Success criteria

1. Two interleaved promotes keep both pages; each wrote only its own paths.
2. A replacement drafted from a page that has since changed exits 9 and writes nothing; an unhashed replacement exits 9 unless the compatibility option is passed, and is then recorded.
3. A symlinked page, an absolute or escaping link, an index entry outside the wiki and an escaping preview pointer are all refused before any read or write; `../` source references inside the root pass.
4. A forged fragment and an answer without citations exit 4; validation uses the prompt snapshot.
5. No published document says "atomic" without qualification; the CHANGELOG states the per-operation policy and the memkernel limitation; version 0.6.0.
6. Gate green; both evaluation runs byte-identical; single-writer test green.
