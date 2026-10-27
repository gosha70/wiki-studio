# Origin alignment check — wiki-studio-0-8-0

Gate: spec, plan and tasks reviewed on PR #52 over three review passes after the pitch's four on PR #50, with every finding resolved and CI green on 5e2b0f1, the reviewed head. The bundle merged as 066a778 while still `status: draft`, before the approval step; this record and the `approved` statuses follow in a separate commit, so the record approves exactly the bundle the reviewer read (the approval commit resolves the five "owner to confirm" marks into recorded decisions and changes nothing else). Written by hand from the review record; the automated gate re-runs before the build.

Origin: wiki-studio issue #38 (Releases B and C), its close target for this release #51, the Release C section of `docs/roadmap.md`, the owner's product proposal of 23 October 2026 (`docs/proposals/2026-10-23-product-proposal.md`: Improve discovery with SQLite FTS5; Add an optional MCP adapter; Keep delivery small; Measure the complete workflow; Launch sequence), and the bet pitch `specs/pitches/38-release-c-discovery-portability/pitch.md` (cycle 03, building). The close target for the build PR is #51; #38 stays open.

Working claim:
> wiki-studio 0.8.0 delivers Release C: ranked discovery with SQLite FTS5 (standard-library `sqlite3`) behind the index-first workflow, keeping the five-page cap, with a byte budget, a runtime probe and a fallback to today's selector, chosen by flag, variable or default; a rebuildable search cache outside the wiki, refreshed by hashing every eligible page on every call, with tested recovery and the wiki byte-identical; discovery evidence on the development set and on a held-out set from a fresh corpus (the eight mapatlas READMEs at 7c3a8de) ingested once under a preregistered, state-machine-enforced protocol, every results file reproducible under its own recorded configuration, FTS5 the default only if no worse than index-first with the D8b and D8c floors holding, and the CHANGELOG stating the basis; an optional MCP adapter extra on the official SDK with the core still standard library, eight tools over stdio bound to configured roots, a fixed launch actor, `--disable-tool` to narrow the surface, auto-approval honoured with a warning, `page_id` on creates; and a conformance suite run in CI at the minimum and latest SDK with one recorded Claude Code host run as exit evidence. Released as 0.8.0, additive, exit codes unchanged, with a structural rule that every page is UTF-8 and its upgrade note.

Release C items (roadmap and pitch), mapped:
  - Discovery: FTS5 ranking behind the index-first workflow and the five-page cap, a byte budget, eligible pages only, the probe and fallback — FR-001..FR-011, US1.
  - A rebuildable cache with a content manifest, stale-index recovery, and the cache outside the wiki — FR-012..FR-018, US2.
  - Evidence: frozen runs untouched, the development set, the held-out corpus and protocol, the floors and the basis of the default, versioned results — FR-019..FR-030, US3.
  - Portability: the MCP extra on the official SDK, the standard-library core proved, the tool contract and boundary, errors and the trace — FR-031..FR-042, US4.
  - Conformance suite, host run, compatibility, release, circuit breaker — FR-043..FR-048, US5.
  - Exit evidence: versioned retrieval results on declared fixtures (FR-020, FR-021, FR-028); cache recovery tests (FR-017); one non-memkernel runtime passing the conformance suite (FR-043, FR-045).

Mismatches (each deliberate and recorded):
  - **The evidence PR comes after the build PR.** The unattended build ships the tooling and the guards with `DEFAULT_RANKER = index-first` and merges on review; the held-out ingest, tuning, the one held-out run, the default decision, the CHANGELOG basis and the host run land in a separate evidence PR merged before the v0.8.0 tag (FR-048, owner decision 2026-10-27).
  - **The D8b and D8c floors may leave FTS5 opt-in** without a measured loss (fewer than 15 gold questions, or fewer than ten eligible pages in the frozen held-out wiki); the CHANGELOG then names the floor and the counts (FR-029, owner decisions 2026-10-27).
  - **memkernel's quickstart and the memkernel integration measurement are not in this release**; they wait for memkernel #48, as the pitch's no-gos record.
  - **Release C closes only when all three exit-evidence items exist on the tag.** The circuit breaker can ship 0.8.0 without the adapter or with a preview of it (FR-048); the build PR still closes #51, and Release C stays open in #38 and the roadmap until the evidence is complete.
  - **The code overruled the pitch in three places**, stated in plan.md: a cache path inside the wiki exits 1, not 2; D7 is met by filtering the selector's full ranked list rather than editing the selector; the `lint` and `review_state` tools define their own JSON.

Verdict: aligned
Confidence: high
