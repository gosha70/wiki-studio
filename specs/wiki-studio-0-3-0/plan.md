---
spec_mode: full
feature_id: wiki-studio-0-3-0
risk_category: feature
justification: "Published numbers about the tool's own efficiency; the design must be fixed before the data exists so the measurement cannot be shaped by the result."
status: approved
date: 2026-10-15
collaboration_mode: single
origin:
  issue: 10
  urls:
    - https://github.com/gosha70/wiki-studio/issues/10
    - https://github.com/gosha70/memkernel/issues/17
    - https://github.com/gosha70/memkernel/blob/feature/memkernel-0-5/specs/memkernel-0-5/spec.md
    - https://github.com/GiulioDER/agent-memory-bench
  origin_claim: |
    Owner question (2026-10-15, wiki-studio build session): should wiki-studio
    consider, find and run benchmark or rubric evaluations proving the
    efficiency of the wiki, similar to memkernel issue #17? Agreed design from
    that discussion and the independent review session: two layers. Layer 1
    (this feature): deterministic component metrics in CI for the querier's
    model-free page selection, on a frozen corpus (memkernel docs at a tagged
    commit, attributed) and a wiki the tool itself produced once; a
    preregistered question set written from the sources before ingest, with
    gold pages assigned after freezing and questions without a page counted as
    ingest coverage; hit rate at 1 and at max pages; words loaded against a
    written-down grep rule as the negative control; ingest cost per transcript
    as primary and amortised as secondary; no citation-validity metric (needs a
    model); a gate suite only as a generated mutation corpus or not at all; no
    LLM judge, no runner of our own, no README claims beyond component numbers
    with the vocabulary-alignment caveat. Layer 2 (separate issue): an arm in
    agent-memory-bench after memkernel's adapter run lands.
---

# Plan: wiki-studio 0.3.0 — navigation evidence (layer 1)

## Summary

The querier chooses pages without a model: it scores every index-linked page
by token overlap with the question and loads the top five. That makes
navigation measurable in CI with no cost and no judge, provided the fixture
cannot be shaped by the measurer. The plan freezes a corpus (memkernel's docs
at `v0.4.0`), commits the question set before the wiki exists, has the tool
build the wiki once through its own gate, assigns gold by reading the result,
and reports three numbers with a grep baseline and a determinism test. The
README gets an evidence section that says exactly what was measured.

## Technical Context

**Language/Version**: Python 3.11–3.13, stdlib only in `eval/`
**Corpus**: `gosha70/memkernel` tag `v0.4.0`, `README.md` + `docs/**/*.md` (ten files)
**Backend for the one-time ingest**: a copilot-CLI backend (`claude`), recorded in the manifest; never run in CI
**Testing**: `tests/test_navigation_eval.py` asserts script output equals `results.json`
**Constraints**: no runtime dependency; `eval/` outside the wheel and coverage; querier unchanged

## Constitution Check

| Rule file | Concern | Status |
|-----------|---------|--------|
| `coding-standards.md` | No magic numbers; stop list and grep rule are data | OK — `stopwords.txt`, `max_pages` named in the spec and the script |
| `safety.md` | Third-party content copied into the repo | OK — Apache-2.0 corpus, attributed in NOTICE, pinned commit |
| `copilot-conventions.md` | Minimal, proportional evidence | OK — three numbers, no framework; US4 drops if it needs hand-written data |

## Architecture Decisions

### ADR-1: Measure selection, not answers

Only the page-selection step is model-free. Answer quality, citation validity
and anything needing a model belong to layer 2. The README says so.

### ADR-2: Preregister the question set by commit order

Layer 1 has no external timestamp authority; the cheap form is commit order
checked by the manifest (`questions_commit` an ancestor of the wiki commit)
and a rule that the file is never edited afterwards.

### ADR-3: The tool builds the wiki; gold is read from the result

Hand-written pages would fit the scorer. Ingest through the gate produces
the wiki once; gold is whatever committed page contains the answer, and
questions with no such page measure ingest coverage, not navigation.

### ADR-4: Grep rule as the negative control

A ratio against all raw sources flatters the wiki. The baseline is what an
agent with grep would read: matching lines with two lines of context, for
the question's content words, over the corpus. The rule is code in the
script and prose in the README.

### ADR-5: Determinism gate instead of thresholds

The numbers are facts about the shipped querier, not targets. CI asserts
equality with the committed results so that any change to selection shows
its effect in the diff; no pass/fail threshold is set.

## Project Structure

```
eval/navigation/corpus/**            memkernel v0.4.0 docs, verbatim
eval/navigation/questions.json       preregistered (committed before the wiki)
eval/navigation/stopwords.txt        the grep rule's stop list
eval/navigation/wiki/**              frozen wiki with its .audit/ tree (WIKI_STUDIO_WIKI_DIR)
eval/navigation/proposals/**         every proposal, promoted ones under .applied/ (WIKI_STUDIO_PROPOSALS_DIR)
eval/navigation/manifest.json        corpus pin, ingest record (one attempt per document), commits
eval/navigation/gold.json            assigned after freezing
eval/navigation/run.py               the three metrics (stdlib)
eval/navigation/results.json         committed output
eval/gate/mutate.py                  US4, conditional
tests/test_navigation_eval.py
README.md (Evidence), NOTICE, CHANGELOG.md, pyproject.toml, __init__.py
```

## Scope

### Task 1: Corpus and question set (US1 part, US2)
Copy and pin the corpus; NOTICE; write and commit `questions.json` and
`stopwords.txt` in their own commit before any ingest.

### Task 2: Frozen wiki (US1)
One-time ingest + promote per document with root, wiki dir and proposals dir
all set explicitly; one attempt per document (one retry only when the backend
returned nothing, recorded), nothing edited by hand, rejections recorded;
manifest; commit the tree.

### Task 3: Gold, script, determinism test, README (US2 part, US3)
`gold.json`; `run.py`; `results.json`; the test; README Evidence section;
CHANGELOG and version.

### Task 4: Mutation gate suite (US4, conditional)
Only as generated variants of the archived patch-sets; otherwise dropped.

### Task 5: Run 2 (US5, amendment of 2026-10-16, release gate)
Same questions and corpus, separate `run2/` fixture, hooks isolated and
verified by a probe before any attempt, model and settings pinned, one
attempt per document; `run.py --shared`; both runs in the README. The gate
is a completed, reproducible run, not a score. Run 1 is never touched.

## Risks

- **Vocabulary alignment.** memkernel's docs share the wiki's words; hit rates
  may not transfer to ordinary prose. No memkernel tag predates the bridge
  (ADR-008 is in every tag from `v0.2.0`), so the latest tag is used and the
  caveat is stated in the README; a second corpus is a later feature.
- **Absent questions rarely yield an empty selection.** The querier keeps any
  page sharing one token with the question, so `absent_empty` will be low by
  construction; it is reported as a fact about the shipped heuristic together
  with the pages loaded, not as a target.
- **Author familiarity.** The question writer knows the scorer. Mitigated by
  writing from the sources before ingest and by the commit-order rule; not
  eliminated, and said so.
- **Backend cost reporting.** The copilot CLI may not expose tokens; the
  manifest then records wall time and the README says tokens were unavailable.
- **Hook isolation can silently fail.** Run 1's contamination came from a
  user Stop hook inside the backend subprocess. Run 2 verifies isolation with
  a recorded probe before any attempt is consumed; a failed probe is fixed
  and repeated, never an ingest.
- **Corpus licence.** Apache-2.0 with attribution in NOTICE; the copied files
  are unmodified.
