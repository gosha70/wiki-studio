---
spec_mode: full
feature_id: wiki-studio-0-3-1
risk_category: bugfix
justification: "A prompt contract fix that lost 3 of 10 ingests in a measured run; small, but specified so the review can check it against the evidence."
status: approved
date: 2026-10-16
collaboration_mode: single
origin:
  issue: 15
  urls:
    - https://github.com/gosha70/wiki-studio/issues/15
  origin_claim: |
    Issue #15 (filed from run 2 of the navigation evaluation): the multi-page
    ingest prompt shows the whole index.md and asks the model to "add a link
    from the appropriate section of index.md" but never says that index.md and
    log.md change only through one-line append-index / append-log edits; three
    of ten ingests returned index.md as a full page and were rejected. Fix in
    the next release: state the rule in the prompt and the response schema; no
    parser leniency; tests. The same release pins the README banner to the
    release tag (review note on PR #14). The owner approved scope 0.3.1 =
    #15 + py.typed (requested by the memkernel session) + tag-pinned banner,
    no third evaluation run.
---

# Plan: 0.3.1

One shared constant states the rule; the renderer and the schema use it;
the validator is untouched. `py.typed` is an empty marker added to the
package includes. The banner address moves from `main` to the `v0.3.1` tag.
Version bump and CHANGELOG. Tests as in the spec. Same process as #11:
gate, DeepSeek review, PR for the review session, owner merges and tags.
