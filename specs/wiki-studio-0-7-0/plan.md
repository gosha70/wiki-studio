---
spec_mode: full
feature_id: wiki-studio-0-7-0
risk_category: feature
justification: "Adds a root manifest and approval records that promoter.py writes into the wiki, a new write verb (approve) and three read surfaces (info, review_state, findings) to the public API and CLI, two optional keys to the page schema shared with memkernel (ADR-0002, schema version 2), optional keys to plan.json and the receipt, and new refusals on propose and promote; a full spec pins each behaviour, every record path and the cut order before an unattended build."
status: draft
date: 2026-10-25
collaboration_mode: single
origin:
  issue: 38
  urls:
    - https://github.com/gosha70/wiki-studio/blob/main/specs/pitches/38-release-b-governed-curation/pitch.md
    - https://github.com/gosha70/wiki-studio/issues/38
    - https://github.com/gosha70/memkernel/issues/48
    - https://github.com/gosha70/wiki-studio/blob/main/docs/roadmap.md#release-b-governed-curation-joint-with-memkernel
  origin_claim: |
    Issue #38 and memkernel #48, shaped by the bet pitch
    specs/pitches/38-release-b-governed-curation/pitch.md (cycle 02, building)
    from the Release B section of docs/roadmap.md. Problem, as the pitch states
    it: "0.6.0 made wiki-studio's own writers safe. It did not make the curation
    loop trustworthy, and it says so." Mixed-writer safety is not claimed,
    because memkernel's bridge restores a whole-wiki snapshot outside the wiki
    lock; nothing says which knowledge is approved ("A page's status is whatever
    its author wrote", the importer imports drafts, and "No record binds an
    approval to a revision"); nothing says which contract a wiki follows ("info
    prints paths, not versions or capabilities"). Solution shape: "Six
    additions, all standard library, all additive to the 0.6.0 API and formats.
    No new exit code and no new runtime dependency. promoter.py stays the only
    module that writes into the wiki directory." (S1) prove the bridge path with
    bridge-shaped tests, a concurrency test and a reproduction of the snapshot
    hazard; (S2) init writes a root manifest with wiki_id, schema identity and
    version and a fingerprint of the project schema, info and api.info report
    formats and capabilities, writers refuse a newer manifest; (S3) an optional
    page_id and --by attribution with its source, never authentication; (S4)
    approve records a decision for the exact sha256 under the current policy,
    review_state compares live page and policy with the record, "Frontmatter
    never makes a page approved"; (S5) an optional superseded_by key decided in
    an ADR and a superseded review state; (S6) findings without a model call in
    a versioned JSON shape. One 6w bet released as 0.7.0; core S1, S2, S4 never
    cut; cut S6, then page_id; memkernel's counterpart runs in the same cycle
    and on a slip 0.7.0 ships with the limitation and Release B stays open.
---

# Plan: wiki-studio 0.7.0 — governed curation (Release B, wiki-studio side)

The bet pitch `specs/pitches/38-release-b-governed-curation/pitch.md` is the
shaping record (seven review rounds on PR #44, three owner decisions adopted
on 25 October 2026). Its "Findings from the code" were re-checked against
the current tree on 25 October 2026: every wiki-studio citation holds at the
cited lines; the memkernel citations hold under `src/memkernel/wiki/` (the
pitch's `memkernel/wiki/` is shorthand for that path). Two facts found while
re-checking shape the spec: `info --json` already has a string key `schema`
(ADR-6), and `api.propose` already refuses a `create` of an existing page
(`proposal.py:364-371`), so the "second export" case has two refusal points
(FR-001).

Close target: `automation.json` has `pr.closes: [45]`, the Release B
tracking issue for the wiki-studio side (opened 2026-10-25). Issue #38 tracks
Release B and Release C together and must not be closed by 0.7.0.

## Architecture decisions

- **ADR-1: S1 is test-only; the snapshot is removed on memkernel's side.**
  The week-0 decision (owner, 24 October) removes memkernel's whole-wiki
  snapshot and scaffolds through `api.init`. wiki-studio's API does not
  change: no `lock=` keyword on `api.propose` or `api.promote`. The evidence
  is a copied reproduction of the hazard plus bridge-shaped tests here, and
  the real packages in a separate clean-install CI job, so memkernel never
  becomes a dependency and its `MemoryService` is never mocked here.
- **ADR-2: Schema identity is `schema.version`; the fingerprint covers only
  what a project overrides.** Packaged rules change with the package and are
  identified by a version that only an ADR bumps, so an ordinary upgrade
  never blocks a write. The only way a wiki's rules can differ from the
  packaged ones is the three overrides the prompts load, so the fingerprint
  hashes exactly those bytes, read once by one contained no-follow loader
  that also feeds the prompt. Drift is refused only where approval is
  required (governed); elsewhere it is a warning.
- **ADR-3: One root manifest, written only by `promoter.py`.** A dot-file at
  the wiki root stays out of page listing and lint; `init_wiki` already lives
  in `promoter.py`, so the single-writer rule holds. Creation is exclusive
  and no-follow; the only rewrite (`--update-schema`) goes through a
  temporary sibling and an atomic replace under the lock. `schema_source` is
  derived on read so it cannot go stale.
- **ADR-4: One file per decision, never replaced.** The approval record's
  path carries the whole decision tuple (page key, revision, policy,
  decision), in two namespaces (`id/` and `path/<digest>`), so records never
  collide or overwrite; publication is an exclusive link or create. Absence
  means "not approved", the safe reading. No ledger, no compaction, no new
  recovery protocol, no signatures.
- **ADR-5: Auto-approval is after the promotion, not inside it.** The
  receipt protocol stays exactly 0.6.0's. Auto-approval re-acquires the lock
  (`WikiLock` stays non-reentrant), validates each page against the
  receipt's post-commit hash, and never attributes bytes it did not promote.
  A failure there is a warning, never a failed promote.
- **ADR-6: New `info` keys never change old ones.** 0.6.0's `info --json`
  prints `schema` as the string `project`/`packaged` (judged by the schema
  directory's existence). The pitch both adds a `schema` object and requires
  existing keys to keep their names and meaning; the second rule wins, so
  the new object is `schema_contract` in `info --json` and in `InfoResult`,
  and the old `schema` and `schema_dir` keys are unchanged.
- **ADR-7: `load_schema_files` keeps its name.** "Replaces
  `load_schema_files`" is read as replacing its implementation: the CI wheel
  smoke test (`ci.yml:109-110`) and any external caller import it, so it
  becomes a thin wrapper over the shared loader with the same signature and
  return value; only its symlink behaviour changes (refused, exit 4).
- **ADR-8: Read-side modules, write-side in the promoter.** New read-only
  modules `contract.py` (manifest read, loader, fingerprint, compatibility,
  formats and capabilities), `review.py` (page key, path digest, policy
  hash, record verification, `review_state`) and `findings.py` keep
  `promoter.py`, already about 1,670 lines, to the writes it must own:
  manifest creation and update, approval publication, `approve`,
  auto-approval.
- **ADR-9: Capabilities are added by the phase that ships them.** Each phase
  appends its capability string and format entry, so a scope the circuit
  breaker cuts never appears, and one test asserts every advertised
  capability resolves.
- **ADR-10: Schema version 2 arrives with its ADR.** US2 introduces the
  manifest with `schema.version` 1 (the 0.6.0 schema). US3 writes ADR-0002
  and bumps the constant to 2 in the same phase, so no phase ships a version
  without its decision record. ADR-0002 is written once in US3 covering
  `page_id`, the reserved approval keys, `superseded_by` and `corrects`;
  US4 and US5 implement against it, and a cut edits it.

## Phases (one auto-build phase per `## US<n>:` group of tasks.md)

| Phase | Pitch scope | What | Main files |
|---|---|---|---|
| US1 | S1 | Bridge-shaped contract tests, combined concurrency test, snapshot-hazard reproduction, clean-install harness and its non-blocking CI job, memkernel consumer docs | `tests/test_bridge_contract.py`, `tests/test_snapshot_hazard.py`, `tests/helpers/memkernel_snapshot.py`, `tests/integration/`, `.github/workflows/ci.yml`, `docs/consumers.md` |
| US2 | S2 | Root manifest via `init`, shared contained schema loader, fingerprint, drift and `init --update-schema`, compatibility check, `api.info` and `info` keys, compatibility matrix, contract docs | `contract.py` (new), `promoter.py`, `prompt.py`, `api.py`, `cli.py`, `paths.py`, `schema/__init__.py`, `docs/compatibility.md` (new), `docs/knowledge-contract.md` (new) |
| US3 | S3 (+ ADR-0002) | `page_id` assignment and lint, page key, `--by` / `WIKI_STUDIO_ACTOR` attribution in `plan.json` and the receipt, ADR-0002 and schema version 2 | `review.py` (new: canonical path and page key only), `api.py`, `cli.py`, `ingestor_multi.py`, `proposal.py`, `promoter.py`, `lint.py`, `paths.py`, `schema/__init__.py`, `schema/page-types.md`, `docs/adr/0002-page-identity-and-review-keys.md` (new), README, SECURITY.md, `docs/patch-set-format.md` |
| US4 | S4 | Policy and `policy_sha256`, `approve` / `api.approve`, record layout and publication, `review_state`, reserved paths and keys, auto-approval, audit lint, acceptance tests, harness loop cases | `review.py`, `promoter.py`, `api.py`, `cli.py`, `proposal.py`, `audit_lint.py`, `docs/knowledge-contract.md`, `tests/integration/test_release_b_loop.py` |
| US5 | S5 | `superseded_by` lint and `superseded` state, `corrects` preserved with the cross-parser fixture | `lint.py`, `review.py`, `tests/fixtures/corrects/`, `docs/adr/0002-...` |
| US6 | S6 + release | `findings` verb and `api.findings`; release 0.7.0 (version, CHANGELOG, docs, CI gating rule) | `findings.py` (new), `api.py`, `cli.py`, CHANGELOG, `pyproject.toml`, `__init__.py`, README, SECURITY.md, `CLAUDE.md`, `.github/workflows/ci.yml`, `.github/workflows/release.yml` |

Order follows the pitch's dependencies: S3 needs S2's manifest, S4 needs S2's
policy and S3's attribution (and uses `page_id` when present), S5 needs S2,
S6 needs S4. US1 and US2 are independent; US1 first, as the tasks require.
If S6 is cut (circuit breaker step 1), US6 keeps only its release tasks.

## Unattended run

`specs/wiki-studio-0-7-0/automation.json`: profile `pr`, branch
`feature/wiki-studio-0-7-0` off `main`, six phases with no milestone pause (`milestone_every: 7`, above the phase count, so the driver finalises and opens the PR after phase 6 instead of pausing),
DeepSeek gating review (max 3 rounds per phase), test command as for
0.6.0, caps raised to 12 hours and $150 because the run has six phases and
about twice 0.6.0's work (owner decision, 2026-10-26; 0.6.0 spent $63.94
over five phases), `pr.closes: [45]` (see above). The bundle is a draft: an origin-alignment record is written
only after approval, before the build.

## Test strategy

- Every FR maps to at least one unit or CLI test (CLI in-process through
  `wiki_studio.cli.main(argv)`); new test files per phase are named in
  tasks.md.
- Concurrency and interleaving tests use the 0.6.0 pattern: subprocess
  children started through `tests/helpers/promote_bootstrap.py`, which patches
  a step before calling `cli.main`; no production pause hook. New
  interleavings: a CLI promote during a bridge-shaped `api.promote` (FR-002),
  a second writer between `take` and `restore` (FR-003), a second writer
  between the archive and auto-approval (FR-030).
- Containment tests plant symlinks at the manifest, the schema directory and
  each override, and at every level of `.audit/approvals/`, each pointing
  outside the wiki, and assert refusal with the target unread and untouched.
- The clean-install harness (`tests/integration/`) runs only in its own CI
  job against a pinned memkernel; locally it is skipped when memkernel is
  absent. The bridge-shaped tests are the always-on evidence.
- Regression: the single-writer tests, the CLI contract tests,
  `tests/test_schema.py` and both evaluation runs' determinism tests stay
  green; coverage stays at or above 92%.

## Risks

- **memkernel's schedule.** The exit evidence is a joint loop. Mitigation:
  the circuit breaker's step 4 ships 0.7.0 with the limitation and keeps
  Release B open; the `memkernel-loop` job is labelled expected-to-fail and stays
  non-blocking until memkernel's counterpart merges, while
  `memkernel-compat` turns blocking as soon as it is green.
- **Review depth.** S4 adds a record format and a new write path into the
  wiki; 0.6.0 needed five review rounds on one PR. Mitigation: the record
  path, digest recipe, verification and publication rules are pinned in
  FR-023..FR-025; a third review round on one scope escalates to the owner.
- **Exclusive publication portability.** `os.link` is unavailable on some
  filesystems; the fallback is `O_CREAT | O_EXCL` on the final name with the
  bytes written and fsynced through that descriptor, which also never
  replaces. A record torn by a crash on that path fails FR-024's
  verification, so it is skipped (the page reads as if unrecorded, the safe
  reading) and the audit lint reports it for removal by hand. Both paths are
  tested where the platform allows.
- **Staging cost.** Promote stages a full copy of the wiki, now including
  `.audit/approvals/`; acceptable at project-wiki size, noted for later.
- **Fingerprint brittleness.** Raw bytes make a line-ending change a schema
  change; documented, and on a managed wiki it is only a warning.
- **`page_id` cut.** Cutting it (step 2) keeps Release B open; approvals and
  findings key by path, which FR-023 already supports.

## Success criteria

1. The bridge's exact call sequence lands, recovers from its receipt and coexists with a concurrent CLI promote; the copied snapshot reproduces the hazard and its absence removes it.
2. `init` writes a contained manifest once; `info` and `api.info` report versions, fingerprints and the shipped capabilities; a newer manifest is exit 4; drift is exit 4 only on a governed wiki.
3. CLI and ingest creates carry a `page_id`; the bridge's bytes are unchanged; `--by` is recorded with its source.
4. Each of the four acceptance cases holds on this side; every record is immutable, contained and keyed by its full tuple; a reused path reads `stale`, never `approved`.
5. `superseded_by` is linted and reported `superseded`; `corrects` is preserved.
6. `findings` exits 0 with counts first and cannot reach a model; version 0.7.0; gate green at 92%.
