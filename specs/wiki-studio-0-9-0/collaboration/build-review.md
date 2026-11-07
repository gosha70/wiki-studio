---
feature_id: wiki-studio-0-9-0
date: 2026-11-07
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-9-0
rounds_completed: 4
attempt_count: 2
bypass: false
---

# Peer Review: wiki-studio-0-9-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 4
**Verdict**: PASS

## Summary

The Round 4 diff resolves the two prior blocking findings by reframing the ADR's Implementation section as "planned for 0.9.0" and by explicitly naming the round-trip test as "added in US4 of this feature" rather than as an existing artifact. The link-reading amendment (drop title, skip non-`.md`, treat URL-scheme `.md` as outside the wiki) is coherent across spec.md, tasks.md, and the origin-alignment record. Remaining issues are documentation-level: the ADR still contains a forward reference that will rot, the `open-questions/` marker-line guidance is still inconsistent between the ADR and `citation-rules.md`, and the log-line format remains unparseable by design.

## Findings

- [warning] f-953d6790: The ADR's Decision bullet still says "The first `.md` link on the marker line names the other page" without the `open-questions/` caveat that appears in Consequences and in `citation-rules.md`. A reader of the Decision section alone will not learn that an `open-questions/` entry linked first is read as the other page and usually reported `conflict-one-sided`. (docs/adr/0004-conflict-callout.md)
- [warning] f-030692f4: The Consequences paragraph says "A callout may link such an entry on a sources line" and then "An entry linked first on the marker line is read as the other page … usually reported `conflict-one-sided`." This still reads as two different verdicts on the marker-line case (permitted vs. usually-one-sided) and does not match `citation-rules.md`'s "Link an `open-questions/` entry on a sources line instead" (which is prescriptive, not merely descriptive). (docs/adr/0004-conflict-callout.md)
- [warning] f-97eaf5b3: The log line `- YYYY-MM-DD — resolve <slug> (<page-type>): conflict with <other-slug>, decided by <source>` is ambiguous when `<source>` is `path: docs/a, b.md` or `url: https://x/y:z` — the comma after `<other-slug>` and the colon after `decided by` collide with the source's own punctuation. The doc says "Nothing parses it," but the ADR's resolution rule is a contract for curators and future tooling; an unparseable format is a latent correctness trap. (src/wiki_studio/schema/citation-rules.md)
- [warning] f-454ed887: The doc documents that "a marker line inside [an HTML block] is read like any other line" but does not warn the curator that a `[!conflict]` marker inside a `<details>` or `<pre>` block will be misread as a live callout, producing a spurious `open-conflict`/`conflict-one-sided`/`conflict-dangling` finding. A curator who writes a marker inside HTML will get a finding they did not intend and cannot suppress. (src/wiki_studio/schema/citation-rules.md)
- [warning] f-c1ad256a: The sub-bullet says "mark both pages with the conflict callout pair in one patch-set" and only then adds "For a page outside this wiki, see Escalation below." A curator reading only the sub-bullet's first sentence will not see the cross-wiki caveat before acting. The caveat is present but buried after the imperative. (src/wiki_studio/schema/WIKI_MAINTAINER.md)
- [warning] f-252fd312: The Follow-up section says "Tracking: no memkernel issue is open yet. The owner opens it … and links it here." There is no issue number and no named owner. A deferred follow-up with no tracking link is a lost follow-up; the ADR is the durable record and will be read long after this cycle. (docs/adr/0004-conflict-callout.md)
- [note] f-35806723: The Decision bullet forward-references `citation-rules.md`'s "When sources disagree" section by name. If that section is renamed, the ADR's reference rots. The ADR is the durable record; it should not depend on a section heading in a mutable doc. (docs/adr/0004-conflict-callout.md)
- [note] f-5a94e387: The doc tells curators that `fact_warnings` "are expected and advisory, and they never block promote." This is an unverified prediction about linter behavior presented as fact. If the linter's behavior changes, the doc will be wrong and curators will be told to ignore a warning that may matter. (src/wiki_studio/schema/citation-rules.md)
