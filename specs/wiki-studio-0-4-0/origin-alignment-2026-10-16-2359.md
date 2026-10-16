# Origin alignment check — wiki-studio-0-4-0

Gate: plan approved and built (Gates 1 and 3), 2026-10-16 23:59 local.

Origin: https://github.com/gosha70/wiki-studio/issues/10 (layer 2) and the owner's decision on 2026-10-16: route B, "build this, I will take care for MEMKERNEL adopt and run the benchmark/rubric".

Working claim:
> wiki-studio 0.4.0 adds `init` (scaffold, never overwrites, in the single writer), `propose --from DIR [--promote]` (agent-written pages through the existing validators and gate, no model), and `find` (the querier's model-free selection, no query log), with library equivalents, tests on the lc-wiki fixture shape, and `docs/agent-arm/` holding a ready `wiki_studio` arm for memkernel's lifecycle suite (config in memkernel's format, an instruction within 5 percent of memkernel's block, and the list of memkernel changes the owner applies). Nothing in memkernel's repository is changed from here; no harness is built here.

Mismatches:
  - Layer 2's evidence itself (the run) is outside this repository by the owner's decision; #10 stays open until that run is published.

Verdict: aligned
Confidence: high
