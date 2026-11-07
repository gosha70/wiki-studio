# Origin alignment check — wiki-studio-0-9-0

Gate: the bet pitch was reviewed on PR #85 and passed at 462e679 with two points deferred to the spec. The spec, plan and tasks were reviewed on PR #87 over two passes. The reviewer's first pass read head 1c63064 and found one error: FR-007's last sentence had the superseded-page case backwards. That sentence was rewritten at 16ceaed, and nothing else changed; main was then merged in at 7da1f99, which retargeted the PR to main and ran full CI (17 checks green). The reviewer passed the bundle at 7da1f99. The owner approved the bundle at 7da1f99 on 2026-11-07.

This approval commit does four things:
- sets `spec.md` and `plan.md` to `status: approved`;
- adds `automation.json`, using the `pr` profile, DeepSeek as the gating reviewer, the 0.8.1 gate with `examples/` (which exists since 0.8.1), and `pr.closes: [71]`;
- adds this record;
- changes nothing else.

The record was written by hand from the review record, as for 0.8.0 and 0.8.1. The automated gate runs again before the build.

Origin:
- wiki-studio issue #71, "conflict callouts" (no comments on 2026-11-05), whose acceptance lines are: a matched pair gives exactly one `open-conflict`; a one-sided and a dangling callout are each reported with their kind; no callout gives no finding; a page with an open conflict can still be approved;
- the cooldown report `specs/retros/cooldown-after-04.md` (candidate 3);
- the bet pitch `specs/pitches/71-conflict-callouts/pitch.md` (cycle 05, building), with owner decisions D1-D7, D9, D11 and D14 recorded on 5 November 2026, every default;
- the PR #85 review's two deferred points: the other page's link sits on the marker line itself; repeated callouts naming the same page count once;
- ADR-0001 as the precedent for an optional body convention reported through `findings` and not refused by lint.

The build PR's close target is #71. The pitch PR (#85), the bet PR (#86) and the spec PR (#87) use no closing keyword.

Working claim:
> wiki-studio 0.9.0 gives a disagreement between sources a fixed form and a model-free report. The form is a `> [!conflict]` callout on both pages, each linking the other on its marker line and naming the sources each side cites; it is optional, documented in the packaged `citation-rules.md` and recorded in ADR-0004, and it reaches the ingest prompts through the schema excerpts with no prompt code change.
>
> The report is three kinds in `findings`: `open-conflict` (one per matched pair), `conflict-one-sided` and `conflict-dangling`, all `warning`, under `findings_version: 1`, discovered through `counts`. A callout is open while it is present; resolving removes both callouts in one promoted patch-set, cites the deciding source in `sources:` and appends one `log.md` line.
>
> Nothing else moves: no frontmatter key, no `schema.version` or `findings_version` bump, no new verb, flag, exit code, MCP tool, capability or dependency, no structural-lint or `approve` rule about callouts, no model on any path from `findings`, `approve` or `review_state`, no memkernel edit. A page in a matched pair still approves, and memkernel 0.6.0's parser keeps the callout in the body.

Origin items, mapped:
- The form, documented, and ADR-0004: FR-001..FR-004, US1.
- The model-free check, the three kinds, the fixture and the acceptance cases, the PR #85 points, the executable example, the resolution rule: FR-005..FR-014, US2.
- The surfaces and the reference docs: FR-015..FR-018, US3.
- "A page with an open conflict can still be approved" and the memkernel evidence: FR-019..FR-021, US4.
- Release 0.9.0 (D14), the compatibility row, the circuit breaker and the invariant audit, `Closes #71`: FR-022..FR-025, US5.

Mismatches, each deliberate and recorded:
- **The other page is the first `.md` link on the marker line, not the callout's first link.** The pitch said "its first wiki-page link"; the PR #85 review narrowed it so a sources line linking a document cannot be misread as the other page (FR-010a).
- **Three kinds, not one.** The issue's "for example" wording allowed one kind with the case in the description; the owner chose three kinds (D5) so a host can count by case.
- **"Dangling" covers more than a missing target.** The issue words it as a missing page; through the gate that case is caught first by the fatal link rule, so the kind also covers a non-page target, the page itself, a superseded target and a marker line with no page link (D6, FR-007), and the fixture that carries a missing target is read in place, never promoted (FR-011).
- **A superseded page is targeted, not scanned.** The pitch left it open; the spec skips a superseded page's own callouts so one stale disagreement is one finding (plan.md fact 2, FR-006).
- **The live memkernel import case is cut first.** The copied `v0.6.0` parser test is the core evidence and stays pinned to the tag even if the live case is cut (D13, FR-020, FR-021).
- **Curators write callouts; ingest is not asked to.** A scope choice (D9): the form is in the prompt's schema excerpts, so a model may propose one, reviewed like any content.
- **Issue #71 closes by the build PR's merge**, not by the pitch, bet or spec PR (FR-025).

Verdict: aligned
Confidence: high
