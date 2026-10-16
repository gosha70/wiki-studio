# Origin alignment check — wiki-studio-0-3-0

Gate: phase complete (Gate 3), 2026-10-16 12:00 local. Owner tasks done in order (spec approved 7f6290f; questions c99be65 then pinned b42b5b7; one-time ingest 887cfa2; gold 40a336b); build tasks 5, 6, 7, 7a done; DeepSeek correctness review FAIL (13 non-blocking notes, 10 fixed, 3 disputed with evidence) then PASS in round 2. US4 (mutation gate suite) not built: the frozen run archived one patch-set, too few to generate a corpus from; recorded in the CHANGELOG as dropped for this release.

Origin: https://github.com/gosha70/wiki-studio/issues/10 and https://github.com/gosha70/memkernel/issues/17; the design was agreed with the independent review session on 2026-10-15 and recorded in plan.md's origin claim.

Origin claim:
> Layer 1: deterministic component metrics in CI for the querier's model-free page selection, on a frozen corpus (memkernel docs at a tagged commit, attributed) and a wiki the tool itself produced once; a preregistered question set written from the sources before ingest, gold assigned after freezing with a written reason, questions without a page counted as ingest coverage; hit rate at 1 and at max pages; words loaded against a written-down grep rule as the negative control; ingest cost per document primary; no citation-validity metric; gate suite only as a generated mutation corpus or not at all; no judge, no runner of our own, no README claims beyond component numbers with the vocabulary-alignment caveat. Layer 2 tracked separately.

Working claim:
> `eval/navigation/` holds the pinned corpus (memkernel v0.4.0, ten files, checksums, NOTICE), the question set committed before ingest (35 questions: 23 single, 6 competing, 6 absent; sha256 and commit in the manifest), the stop list copied from the querier, the frozen wiki produced by one attempt per document (1 promoted, 8 validation failures, 1 timeout, no retries, nothing edited), gold with a reason per entry, `run.py` (stdlib; hit@1, hit@5, words vs the grep rule with the querier's token pattern and stop list, absent/unreachable/index-only/grep-empty/distractor cases reported separately), `results.json` and a determinism test. README Evidence section states run 1's numbers (coverage 3 of 29; hit 3 of 3 at 1 and at 5; 2,286 vs 16,706 words, median ratio 0.16) in words with the caveats: one document in ten promoted because of a prompt path-prefix gap, vocabulary alignment, author familiarity, Stop-hook contamination of logs and wall time (`requires_review`). Ingest help text fixed. Version 0.3.0.

Mismatches:
  - Ingest cost per document is wall time only (the `claude` text-mode backend exposes no tokens) and that wall time is contaminated by the owner's Stop hook; reported as unavailable/not isolated rather than as a number. The protocol's primary cost figure therefore has no clean value in run 1.
  - US4 dropped for this release under the spec's own condition (generated corpus or nothing).
  - Run 1 is marked `requires_review`; a second run needs a revised, separately named protocol after the prompt fix, per `eval/navigation/ingest-notes.md`. This record covers run 1 as measured.

Verdict: aligned
Confidence: high
