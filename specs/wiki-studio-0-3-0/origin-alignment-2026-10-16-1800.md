# Origin alignment check — wiki-studio-0-3-0 (amendment: run 2)

Gate: plan amended (Gate 1 for US5), 2026-10-16 18:00 local. Owner instruction of 2026-10-16: run 2 gates the release, after the issue #11 fix passes review and merges; amend the spec before ingest with the same frozen questions and corpus, a separate fixture directory, run 1 unchanged, Claude hooks isolated and the isolation verified before any attempt is consumed, model and settings pinned, the one-attempt rule preserved, both runs published side by side with denominators and caveats; the gate is a completed, reproducible measurement, not improved scores; #10 stays open for layer 2. Earlier records (2026-10-15-2230, 2026-10-16-1200) are kept as written.

Origin: https://github.com/gosha70/wiki-studio/issues/10, https://github.com/gosha70/wiki-studio/issues/11 and the owner's two instructions on 2026-10-16 ("no release until those issues are addressed"; the run 2 conditions above).

Origin claim:
> as in plan.md, plus: run 2 under a revised protocol gates 0.3.0; same questions and corpus; separate fixture; run 1 untouched; hooks isolated and verified first; pinned model and settings; one attempt per document; both runs published with denominators and caveats; completed and reproducible, not improved.

Working claim:
> US5 and FR-013 to FR-016 add `eval/navigation/run2/` with its own wiki, proposals, manifest, gold, results, logs and notes while the corpus, questions and stop list are run 1's files used in place and checksum-asserted; an isolation probe (one trivial `claude -p` call, before/after byte comparison, recorded as `isolation_probe`) that must pass before the first attempt and consumes none; pinned commit (descendant of the #11 merge), versions, model, timeout, variables and command; FR-003's one-attempt rule unchanged; `run.py --shared`; determinism test over both runs; README table with both runs and per-run denominators and caveats, run 1 unchanged; the tag only after a complete, reproducible run 2.

Mismatches:
  - none against the instruction. Layer 2 remains out of scope and #10 stays open, as instructed.

Verdict: aligned
Confidence: high
