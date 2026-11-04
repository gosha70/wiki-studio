# The correction loop, demonstrated

One scripted run shows a wrong decision corrected through a reviewed proposal
and gone from the next session's answer: three processes on one memkernel
store and one wiki. The script is
[`examples/correction-loop/demo.py`](../examples/correction-loop/demo.py);
its recorder is `record.py` beside it, and the protocol is the
[README](../examples/correction-loop/README.md) in the same directory.

## What the run shows

**Session 1.** The wrong decision is retained under a neutral first line that
names the topic — `Deploy window`, then `Deploy on Fridays after 17:00 UTC.` —
and a `recall` returns it: the wrong rule is the current answer. The decision
is exported through wiki-studio's gate as one `status: draft` page, with the
export's `submission_digest` in the report.

**The curator.** The curator reads the draft with `wiki-studio read --json`,
replaces the rule in the title, the heading and the body, sets
`status: stable` and `corrects: <memkernel_ref>`, and proposes the guarded
update (`.base.json`) with `--promote`. The promote is committed under the
wiki lock, and its receipt records the proposal, the submission digest, the
actor and both times. The curator then runs `wiki-studio approve`, and the
approval record names the approver and its timestamp, bound to the live
page's sha256.

**Session 2.** A new process on the same store runs memkernel's governed
`wiki_import`: the approved revision is imported, and the wrong memory's
`ref_id` is reported in `corrections`. A `recall` of the same question returns
the corrected rule; the answer's page carries a `page_sha:` tag equal to the
page's `approved_sha256`, beside the receipt's `submission_digest` and
`committed_at` and the approval record's `approver` and `timestamp`. The wrong
rule appears in no current answer, and the old memory is kept, visible only
with `include_superseded=True`, marked `superseded_by` the page's memory.

## The evidence

The demo runs on every push as the blocking CI job `demo-correction-loop`
(`.github/workflows/ci.yml`), through the same `record.py` used for a recorded
run. The recorder binds a run to the commit, the wheel's sha256, the memkernel
distribution's sha256 checked against the one PyPI publishes, the embedding
revision, the script's sha256 and a hash of the end state (the wiki and the
proposals with their receipts).

### The recorded run

One run, never retried, is committed at [`examples/correction-loop/runs/2026-11-04-wiki-studio-0.8.1-memkernel-0.6.0/`](../examples/correction-loop/runs/2026-11-04-wiki-studio-0.8.1-memkernel-0.6.0/),
recorded from a clean tree at `a0bd609` (the merge of the 0.8.1 build), with
wiki-studio 0.8.1 built from that commit (wheel sha256 `2eaf7e1f…`),
memkernel 0.6.0 (sha256 `11fb3699…`, equal to the one PyPI publishes) and
the embedding model at revision `1110a243…`; its
[`manifest.json`](../examples/correction-loop/runs/2026-11-04-wiki-studio-0.8.1-memkernel-0.6.0/manifest.json) holds the full hashes and an
end-state hash of `315cf068…`. Every one of the run's checks printed `ok`,
and the last lines of session 2 in
[`transcript.txt`](../examples/correction-loop/runs/2026-11-04-wiki-studio-0.8.1-memkernel-0.6.0/transcript.txt) are the answer and its provenance:

```text
answer: Deploy on Tuesdays before noon; never on Fridays.
page: decisions/deploy-window.md
page_sha: 5ae74db850f60ffcd31a47d550cb72d29d3c98ce117e715a97a75336ee40b2d9
approved_sha256: 5ae74db850f60ffcd31a47d550cb72d29d3c98ce117e715a97a75336ee40b2d9 (equal)
submission_digest: 0a3cf9737e3b2481d1d81f9c9c1af9d787570ad78919dc7bb4dd97f187bcb2eb
committed_at: 2026-11-04T01:56:24Z
approver: curator
timestamp: 2026-11-04T01:56:24.793112Z
old record: 83706b22-97c0-440b-a282-3c34a58b8c72 superseded_by 40c9e325-511b-4d64-ab22-498067ee0090
demo: every check passed
```

Session 1 exported the wrong rule as a draft (`page-names-the-wrong-memory`);
the curator replaced it through a reviewed proposal and approved the page
(`receipt-is-committed`, `approval-bound-to-the-page`); session 2 imported
only that approved revision (`import-governed`, `one-page-imported`), and
the wrong rule is in no current answer (`wrong-rule-not-current`) while the
old record is kept, superseded by the page's memory (`old-record-kept`,
`old-record-superseded-by-the-page`). The manifest records 124.8 seconds from
the start of the install to the first approved revision and 129.0 seconds to
the corrected recall: machine time on a scripted path, not a measure of human
adoption (D15).

## What it does not show

It shows what one scripted run shows, not how often a correction happens or
what a person's day looks like. Correction is by replacement only: the
corrected page supersedes the wrong memory. Deprecation and deletion wait for
memkernel 0.7 (D11). No model backend is on any path; the only model is
memkernel's local embedding model. Wall times from a recorded run are machine
time on a scripted path, not a measure of human adoption (D15).

The model-free path is [`quickstart.md`](quickstart.md); the same loop built
by hand, with every command executed in CI, is
[`quickstart-memkernel.md`](quickstart-memkernel.md).
