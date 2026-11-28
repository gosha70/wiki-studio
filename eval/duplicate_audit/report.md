# The duplicate-audit study: report (issue 121)

This report gives the measurements that `README.md` in this directory defines
and that `protocol.json` freezes. The candidates, the index and query rule,
the restatement rule, the bar and the development stage's stop rule were
committed, signed off by the owner and pinned by sha256
(`tests/test_duplicate_audit_frozen.py`) before the audit script existed.
Every figure here is copied from `results/development.json` as recorded.

## How to rerun both sets

```
python -m eval.duplicate_audit.audit --set development
python -m eval.duplicate_audit.audit --set held-out
```

Each run first checks the set's frozen inputs and refuses, exiting 1 and
writing nothing, on any difference. The development set is cycle 10's frozen
corpus and labels (`eval/duplicates/`). The held-out set runs only once
`held-out/freeze.json` exists; it does not, so the second command refuses.
The script runs no git, calls no model, opens no network connection and reads
nothing outside the repository, so CI reruns it:
`tests/test_duplicate_audit_development.py` writes its output to a temporary
directory (`python -m eval.duplicate_audit.audit --set development --out-dir DIR`)
and checks that `development.json` equals the committed file byte for byte.
That is a reproduction of the committed bytes, not a new reading.
`development-timing.json` is checked for its keys only, since a rerun's wall
time never matches.

## The development stage

At the pause after the audit script, the main session ran the development
stage once and committed `results/development.json` and
`results/development-timing.json` as written, as their own commit. The set
holds 299 decision pages; the frozen labels hold 8 true pairs, 5 `redundant`
and 3 `supersedes`. The ranker configuration recorded at run time is
tokenizer `porter unicode61`, weights path 4, title 4, headings 2, body 1,
`min_match_tokens` 1, configuration hash
`c4b6576a6bc57e3c1b8c7f70ef6bb19b5dcf44d0ea0c30ab7dc0192965a43521`.

Each candidate, as recorded. "Restatements" counts pairs that meet a
restatement rule; on this corpus only rule (a), one spec directory, can
apply.

| Candidate | k | Flagged | True found | False | False `companion` | False `distinct-by-precondition` | False `unrelated` | Flagged per 100 pages | True per 100 pages | False per 100 pages | Flagged restatements | True found, restatements | True found, not restatements |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `mutual-top-1` | 1 | 51 | 4 of 8 | 47 | 19 | 3 | 25 | 17.06 | 1.34 | 15.72 | 38 | 4 | 0 |
| `mutual-top-3` | 3 | 169 | 5 of 8 | 164 | 43 | 10 | 111 | 56.52 | 1.67 | 54.85 | 113 | 4 | 1 |
| `mutual-top-5` | 5 | 284 | 6 of 8 | 278 | 53 | 17 | 208 | 94.98 | 2.01 | 92.98 | 172 | 5 | 1 |

The stop rule per candidate (trigger 0): the held-out stage goes ahead only
if at least one candidate's false pairs do not outnumber its true pairs found.

| Candidate | False | True found | False not above true |
|---|---|---|---|
| `mutual-top-1` | 47 | 4 | no |
| `mutual-top-3` | 164 | 5 | no |
| `mutual-top-5` | 278 | 6 | no |

Every candidate's false pairs outnumber its true pairs found, so the stage
line, as recorded, is:

Development stage: stop

These counts never decide a pass. The candidates are not run on this corpus
again for any reading.

**The caveat.** Cycle 10's 8 true pairs have been read by three cycles and
are development data. The pitch's finding 7 did arithmetic on published ranks
while shaping. The held-out set is the only binding evidence.

## The held-out stage

The held-out stage has not run: no held-out page has been extracted, no
label written and no candidate run on a held-out set. With the stage line at
`stop`, the bet stops here (trigger 0): no held-out set is built, the
`possible-duplicate` kind is not built, and issue 121 stays open.
