---
feature_id: wiki-studio-0-9-2
date: 2026-11-15
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-9-2
rounds_completed: 2
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-9-2 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 2
**Verdict**: PASS

## Summary

The Round 1 findings were addressed with substantial rewrites to the curator loop, and the new step 9 outcome tree is much clearer. However, the rewrite introduced a few new correctness issues: the outcome tree still has an unreachable/ambiguous branch for the "reserved + no manifest" case, the recovery instruction still authorizes approving content the agent did not author, and the propose-only detection still relies on tool introspection. A couple of the Round 1 findings were only partially resolved.

## Findings

- [warning] f-d76dc163: Outcome (2) requires "the policy approves on promote" and outcome (3) requires "the policy does not approve on promote — a missing manifest included." The preamble now says a missing manifest "counts as a policy that does not approve on promote," which resolves the fall-through. But outcome (2) still says "approval is reserved by the project's instructions and the policy approves on promote" — and the preamble's propose-only case ("the launch names `--disable-tool promote`") is folded into outcome (1), while the "instructions reserve approval" case is split across (2) and (3). The conditions are now exclusive, but outcome (1) says "Propose-only mode, or the project's instructions leave promotion to a person" — the second clause overlaps with (2)/(3) which also assume "promotion is yours to run." An agent whose instructions say "a person approves" but do not say "do not promote" matches (1) first and stops after propose, never reaching (2)/(3). That may be intended, but the wording "leave promotion to a person" is not the same as "reserve approval" and the two are conflated. (src/wiki_studio/schema/WIKI_MAINTAINER.md)
- [warning] f-6b6b3d07: The recovery instruction now says "Approve the new revision only if its content is still what you drafted and inspected; otherwise report the page and stop. Never approve a revision whose content you did not author in this turn." This is better than Round 1, but it still authorizes the agent to approve a revision it did not draft if the content happens to match its draft — which is exactly the concurrent-writer case the finding warned about. If another writer replaced the page with byte-identical content, approving is harmless; if the content differs at all, the agent must not approve. The instruction is now correct in spirit but the phrase "still what you drafted and inspected" is a content-equality test the agent cannot reliably perform (whitespace, ordering). (src/wiki_studio/schema/WIKI_MAINTAINER.md)
- [warning] f-c8addd45: The propose-only detection now says "the launch names `--disable-tool promote`, so the `promote` tool is missing, and a `promote` call that fails because the tool is unavailable means the same — treat the run as propose-only." This addresses the Round 1 note about tool introspection, but "a `promote` call that fails because the tool is unavailable" is only discoverable by attempting promote — which the agent is told not to do in propose-only mode. The instruction is circular: to know it is propose-only, attempt promote; but attempting promote in propose-only mode is the thing being avoided. (src/wiki_studio/schema/WIKI_MAINTAINER.md)
- [note] f-47e07f6d: The Round 1 finding about `--by you` is addressed: "never the placeholder name a quickstart shows — `--by you` there means you substitute your own name." This is clear. No action needed; noting for closure. (src/wiki_studio/schema/WIKI_MAINTAINER.md)
- [note] f-1c812bc7: The Round 1 note about exit 4 conflating "no manifest" and "multi-page `--revision`" is addressed: "Exit 4 covers both this and a multi-page `--revision`; the message on stderr names which." Good. But the agent is told to branch on exit code elsewhere; if it cannot read stderr reliably (MCP), the conflation remains. Minor. (src/wiki_studio/schema/WIKI_MAINTAINER.md)
- [note] f-7b55c75e: The Round 1 note about step 12 redundancy is addressed: "Step 11 already linted the staged tree; this run checks the wiki after the write — run both." Clear. No action needed. (src/wiki_studio/schema/WIKI_MAINTAINER.md)
- [note] f-87e7e46d: The Round 1 note about `.base.json` format is addressed: "a JSON object mapping each wiki-relative page path to the sha256 `read` printed for it (for example `{\"concepts/retry-backoff.md\": \"<sha256>\"}`)." Clear enough. No action needed. (src/wiki_studio/schema/WIKI_MAINTAINER.md)
- [note] f-0dbb2513: The Round 1 note about propose vs promote output formats is partially addressed: step 10 now describes propose output (`  create`/`  update`/`  append-index`/`  append-log`), step 11 describes promote output (`applied <n> edit(s)`, `  + <path>`, `  approved <path>`, `no-op: …`). The formats are documented but still differ and must be parsed separately. A `--json` flag would be safer, but this is a note, not a blocker. (src/wiki_studio/schema/WIKI_MAINTAINER.md)
- [note] f-77cb8dd8: The Round 1 note about nested `index.md` is addressed: "a nested `index.md` (for example `concepts/index.md`) is a content page and is approved like any other." Clear. No action needed. (src/wiki_studio/schema/WIKI_MAINTAINER.md)
- [note] f-de28c2f7: The Round 1 note about outcome (5) implying approve will succeed on a no-manifest wiki is addressed: outcome (5) now says "On a wiki with no manifest, approve exits 4 (step 13): stop after lint and report the promoted pages instead." Clear. No action needed. (src/wiki_studio/schema/WIKI_MAINTAINER.md)
- [note] f-ce63932a: The Round 1 note about the em-dash/trailing-period readability is addressed: the instruction is now a blockquote on its own line. Clear. No action needed. (src/wiki_studio/schema/WIKI_MAINTAINER.md)
