# Origin alignment check — wiki-studio-0-3-0 (US5 complete: run 2)

Gate: phase complete (Gate 3 for US5), 2026-10-16 23:00 local. Run 2 executed by the owner with `eval/navigation/run2_protocol.py all --commit` (f8419a5): probe passed (hooks isolated by `HOOK_SKIP=1`, nothing under `run2/` changed during the call, no pytest under the probe), commit 61b3d9b pinned (descends from the #11 merge 4d224df), model `claude-opus-5-5` pinned by full name, ten documents, one attempt each, no retries, seven promoted, lint clean; gold assigned by the owner from the frozen wiki (3d12519, 21 of 29 answerable questions with gold); results, README and CHANGELOG by the build. Earlier records are kept as written.

Origin: the owner's instructions of 2026-10-16 (run 2 gates the release; same frozen questions and corpus; separate fixture; run 1 unchanged; hooks isolated and verified before any attempt; model and settings pinned; one-attempt rule preserved; both runs published with denominators and caveats; the gate is a completed, reproducible measurement, not improved scores; #10 stays open for layer 2), and the protocol review on PR #13.

Working claim:
> `eval/navigation/run2/` holds the frozen run 2 wiki (nine content pages), proposals, logs, notes, a manifest with the passed probe and the pinned settings, `gold.json` and `results.json`; the shared corpus, questions and stop list are run 1's files used in place and checksum-asserted; run 1's files are byte-identical. `run.py --shared` reproduces run 2 and CI asserts both runs. The README shows the two runs side by side with per-run denominators (29 answerable; 3 and 21 with gold; 3 and 21 in the ratio) and caveats; run 1's column and text are unchanged; run 2's paragraph records the model-name difference, the isolation evidence and the three failures on a new contract gap (`index.md` returned as a full page instead of an `append-index` line), which the CHANGELOG lists under known issues for a later release.

Mismatches:
  - Run 2's model is recorded as the full name `claude-opus-5-5` while run 1 recorded the alias `opus`; both are stated, the protocol asked for a concrete identifier when the CLI accepts one, and the README's run 2 paragraph carries this as a caveat next to the numbers.
  - The gate is met as defined (complete, reproducible, both runs published); the scores themselves (hit at 1 of 3 in 21, hit at 5 of 10 in 21) are published as measured and are not part of the gate.

Verdict: aligned
Confidence: high
