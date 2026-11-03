# Origin alignment check — wiki-studio-0-8-1

Gate: the bet pitch was reviewed on PR #68 over three passes, all findings resolved. The spec, plan and tasks were reviewed on PR #73 over two passes. The reviewer's second pass read head a3576ae and found one leftover: the US5 scenario's "When" line still had the build filing issues. That line was reworded at e4aa795, and so was the same phrase in plan.md's justification; nothing else changed. The owner approved the bundle at e4aa795 on 3 November 2026.

This approval commit does four things:
- sets `spec.md` and `plan.md` to `status: approved`;
- adds `automation.json`, using the `pr` profile, DeepSeek as the gating reviewer, the 0.8.0 gate plus `examples/` once it exists, and `pr.closes: [10]`;
- adds this record;
- changes nothing else.

The record was written by hand from the review record, as for 0.8.0. The automated gate runs again before the build.

Origin:
- wiki-studio issue #10 (mirror of memkernel #17) and its condition: "this issue closes when that run's results are published and linked here";
- the Evidence section and Launch sequence step 2 of `docs/roadmap.md` ("the two quickstarts, the compatibility matrix, and a short demonstration of an obsolete decision corrected through a reviewed proposal and absent from the next session");
- the owner's product proposal of 23 October 2026, `docs/proposals/2026-10-23-product-proposal.md` ("Measure the complete workflow", "Launch sequence");
- the cooldown report `specs/retros/cooldown-after-03.md` (candidate 1);
- the bet pitch `specs/pitches/10-release-b-launch-and-measurement/pitch.md` (cycle 04, building), with owner decisions D1–D6 recorded on 3 November 2026.

The build PR's close target is #10. It closes by restatement, with a successor issue.

Working claim:
> wiki-studio 0.8.1 publishes Release B's launch items and an honest account of the integration measurement. Nothing in it changes runtime behaviour or the API under `src/`; only the version constant moves.
>
> It ships two quickstarts, standalone and with memkernel 0.6.0, whose run blocks are extracted from the pages and executed on clean installs in blocking CI jobs.
>
> It ships an obsolete-decision correction demonstration. A wrong decision is retained, exported through the gate, corrected through a reviewed proposal carrying `corrects`, approved, and imported. The next session's recall omits the wrong answer, and the revision and the receipt are shown beside the answer. The demo runs as a blocking CI job, and once as a recorded run bound to the executed bytes.
>
> It ships a measurement design explaining why memkernel's published 0.5.0 run sits at ceiling on `lc-wiki`, and what a discriminating governed-composition arm and task set would need. memkernel-side changes are listed as dependencies and not built.
>
> Issue #10 is closed by restating what the 0.5.0 run shows and does not show, with a successor issue.

Origin items, mapped:
- The standalone quickstart, executed: FR-001..FR-005, US1.
- The memkernel composition quickstart, executed, with the commit policy and the handoff: FR-006..FR-010, US2.
- The obsolete-decision demonstration, the CI job and the recorded run: FR-011..FR-017, US3.
- The measurement design, as a stretch cut first: FR-018..FR-021, US4.
- #10 restated, the README, roadmap and compatibility text, the issue texts, release 0.8.1, the invariants and the circuit breaker: FR-022..FR-028, US5.
- The compatibility matrix from Launch sequence step 2: FR-024.

Mismatches, each deliberate and recorded:
- **The integration measurement is not run.** The pitch's circuit breaker excludes the measured run: memkernel's suite, its preregistration and its budget. This release ships the design and the ceiling analysis. The roadmap will say that no governed-composition measurement able to discriminate the arms has been run (FR-023).
- **#10 closes by restatement, not by a discriminating run.** The issue's written condition is met by memkernel v0.5.0. The successor issue carries the measurement forward (D6, FR-025).
- **Public GitHub actions are not done by the unattended build.** The build writes the memkernel issue's text, the successor issue's text and the #10 comment. One interactive step after the build files them in that order, before the PR merges, with the design linked by a permalink at its commit (FR-025, review of PR #73).
- **The recorded run is an owner step in an evidence PR** before the `v0.8.1` tag, because its commit order cannot happen inside the driver. CI runs the same recorder on every push (FR-014, FR-028).
- **Correction by replacement only.** Withdrawal on deprecation or deletion waits for memkernel 0.7 (D11).
- **The code overruled the pitch in five places, stated in plan.md and verified at review:**
  - `approve` refuses `status: draft`, so quickstart pages are `stable`;
  - the conformance runner names the actor through `WIKI_STUDIO_ACTOR`, so the tested launch line carries no `--by`;
  - the receipt exists only in the proposals' `.applied/` archive, so memkernel's proposals directory points at `doc_internal/proposals`;
  - memkernel has no embedding-revision setting, so the pin is a local snapshot path;
  - CI's lint job skips `eval/` and `examples/`, so FR-017 adds both.
- **memkernel citations are by name at tag `v0.6.0`.** Line numbers are kept only where they were verified at the tag. The build re-verifies every memkernel call against the installed 0.6.0 wheel (FR-007).

Verdict: aligned
Confidence: high
