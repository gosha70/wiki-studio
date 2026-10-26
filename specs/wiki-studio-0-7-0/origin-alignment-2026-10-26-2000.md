# Origin alignment check — wiki-studio-0-7-0

Gate: spec, plan and tasks reviewed on PR #46 over three review rounds after the pitch's seven, with every finding resolved, CI green on 01fa75e, and approved by the owner on 2026-10-26 ("Approve PR #46 at commit 01fa75e") for implementation. Written by hand from the review record against PR #46 head 01fa75e, based on `main` at df0337a; the automated gate re-runs before the build.

Origin: wiki-studio issue #38 (Releases B and C), the Release B section of `docs/roadmap.md`, the owner's product proposal of 23 October 2026 (`docs/proposals/2026-10-23-product-proposal.md`: Identity and evidence; Retention and review are separate; Close the round trip; Make curation affordable), the bet pitch `specs/pitches/38-release-b-governed-curation/pitch.md` (cycle 02), and memkernel issue #48 for the bridge side. The close target for the build PR is #45; #38 stays open.

Working claim:
> wiki-studio 0.7.0 delivers the wiki-studio side of Release B: a combined integration gate with memkernel's bridge that is test-only here (memkernel removes its whole-wiki snapshot); a versioned knowledge contract (a root manifest with `wiki_id`, packaged rules identified by `schema.version`, a fingerprint over the loaded project overrides read by one contained loader, drift refused only on a governed wiki, `api.info` with the shipped build's formats and capabilities, unknown schema ids refused); optional `page_id` and actor attribution recorded as attribution; approval bound to the revision and judged against the current approver policy, with immutable records in `id/` and `path/` namespaces, a manifest required, self-declared approval refused, auto-approval as a separate post-promotion operation validated per page against the receipt; `superseded_by` through ADR-0002 with memkernel's `corrects` key registered and its grammar pending; and findings without a model call. Released as 0.7.0, additive, exit codes unchanged.

Release B items, mapped:
  - Combined integration gate deferred from 0.6.0 — FR-001..FR-005, US1.
  - Versioned knowledge contract (schema identity and version, format versions and capabilities through `info`, root manifest from `init`, project-schema fingerprint, compatibility matrix) — FR-006..FR-013, US2.
  - Identity and evidence (stable page identity, asserted actor attribution, approver recorded separately) — FR-014..FR-019, US3; FR-024, US4.
  - Approval bound to the revision and the policy; revalidation after a manual edit; frontmatter never approval — FR-020..FR-032, US4.
  - `superseded_by` through a decision record; review state separate from memory tier — FR-033..FR-036, US5.
  - Findings without a model call — FR-037..FR-038, US6.
  - Release and circuit breaker — FR-039..FR-040, US6.

Mismatches (each deliberate and recorded):
  - **memkernel's side is not built here.** Snapshot removal, approved-only import, withdrawal, sync state and raw-memory reconciliation are memkernel #48's work. If they are not merged by the end of the cycle, 0.7.0 ships with the limitation and Release B stays open (FR-040). The `memkernel-loop` CI job is labelled expected to fail until then.
  - **Recreation of a path-keyed page with identical bytes keeps its approval.** wiki-studio has no delete action and cannot observe a deletion; recreation safety comes from a fresh `page_id` (FR-027, owner decision 2026-10-26).
  - **An acknowledged schema change reopens no approval.** `approved` attests a revision under the approver rule, not validity against the latest schema (FR-020, owner decision 2026-10-26).
  - **The roadmap's two quickstarts are deferred** to a follow-up once the joint correction loop passes, as the pitch records.
  - **Circuit-breaker checkpoints are manual cycle gates** applied by the owner at the build-PR review; the unattended run has no milestone pause (FR-040, owner decision).

Verdict: aligned
Confidence: high
