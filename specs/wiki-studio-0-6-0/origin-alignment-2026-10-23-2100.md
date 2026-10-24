# Origin alignment check — wiki-studio-0-6-0

**Superseded.** This record covers the bundle as approved at PR #37 head 7d0e4cd. The bundle returned to `draft` at 0e3e1c2 for the plan-review revisions; a new record against the re-approved head replaces this one before the build.

Gate: spec, plan and tasks reviewed twice on PR #37 and approved by the owner (Gate 1, at plan approval), 2026-10-23 21:00 UTC, against `main` at 41cfe54 and the bundle at PR #37 head 7d0e4cd. Written by hand from the review record; the automated gate re-runs before the build.

Origin: the owner's product proposal of 23 October 2026 (`Wiki_Studio_Product_Proposal.docx`, "Release A — Safe changes"), its revision-3 review of the same date, and the two spec reviews on PR #37. The proposal's own evidence register pins wiki-studio at 41cfe54 and memkernel at 2d41062.

Working claim:
> wiki-studio 0.6.0 fixes the five defects reproduced on 41cfe54 and states its guarantees as they are: commit writes only the patch-set's paths; cooperating writers are serialised by an OS advisory lock keyed to the resolved wiki, taken by promote, propose, the ingest-log append and audit-flush; every replacement carries the base revision of the page its author read, checked under the lock, with creates and appends from older proposals still safe and unguarded replacements refused unless an explicit compatibility option is passed and recorded; receipts carry a full-payload submission identity and a committing/committed marker so a failure between commit and archive is recovered without replaying appends, and any mixed state fails closed; one canonical containment check guards every read and write surface across three boundaries (wiki, proposal directory, configured source roots), the link collector covers every local target, and `find` never lists a file outside the wiki; citation fragments are validated against the prompt snapshot and a non-empty answer needs evidence; "atomic" leaves the documentation and memkernel's outer rollback is named as a limitation. Released as 0.6.0 (optional format keys and additive API belong to a minor), with a defined 0.5.1 subset if it slips.

Release A items of the proposal, mapped:
  - Commit only patch-set paths; serialise cooperating writers with a lock keyed to the canonical wiki — FR-001, FR-002, US1.
  - Require the revision used to draft each replacement, captured at read, compared under the lock; creates require absence; stale replacements conflict without mutation — FR-005..FR-009, FR-011, US2.
  - Apply containment consistently to page writes, candidate reads and preview reads, including symlinks; keep legitimate source citations legal — FR-012, FR-013, US3.
  - Verify cited fragments and require evidence or abstention; describe the fact checker as a heuristic — FR-014, FR-015, US4, US5.
  - Coordinate audit-log writes — FR-002 (ingest-log append and audit-flush under the wiki lock), US1.
  - Acceptance cases (disjoint concurrent edits, conflicting edits, concurrent creation, shared appends, simultaneous audit records, stale drafting, symlink escapes, forged citations, failure during commit, separate proposal directories, both entry points) — tasks 7, 14, 19, 22 and Final Verification.
  - Honest guarantees (validation, conflict detection, serialised managed writes, exception rollback; no crash-safe multi-file transactions) — FR-015, FR-016, US5.
  - Release this patch before schema expansion or promotion campaigns — the bundle's "Not in Release A" list and the launch sequence.

Mismatches (each deliberate and recorded):
  - **memkernel's side is deferred.** The proposal's Release A item 5 includes coordinated memkernel changes: its outer whole-wiki snapshot and rollback can undo another writer's committed changes, and must hold the same wiki lock across its lifecycle or remove that workaround. This bundle changes nothing in memkernel. It names the limitation in the release notes (FR-016), makes no combined safety claim, and records the combined integration gate (memkernel bridge compatibility: creates and appends through `api.propose`, receipt and `.applied/` layout, lock coordination) as the first item of Release B. The deferral must not be forgotten: Release B cannot ship a combined claim without it.
  - **Receipts, `read`, `--source-root` and the compatibility option are additions beyond the proposal's text.** Each came out of the reviews as the concrete form of a proposal requirement (identity and evidence, "the hash must represent what the author read", "legitimate source citations may resolve inside an allowed source root", "explicit compatibility opt-in"). Recorded in the spec's requirements and the plan's ADR-3, ADR-5 and ADR-6.
  - **Platform.** The proposal does not mention Windows. The package is classified OS independent while CI runs on Ubuntu, so FR-002 either adds a Windows lock backend with a CI job or narrows the classifier in this release. Owner's call at build time; both outcomes keep the claim honest.
  - **Version.** The proposal called this a "patch"; the format's own stability rule makes it 0.6.0, with a 0.5.1 subset defined (FR-017).

Verdict: aligned
Confidence: high
