# Origin alignment check — wiki-studio-0-3-0-path-frame

Gate: phase complete (Gate 3), 2026-10-16 17:00 local. Built in one phase plus one note-fix commit; DeepSeek correctness review PASS twice (seven non-blocking notes the first time, four fixed, three kept with evidence; second pass over the whole diff PASS). The plan-time record (2026-10-16-1500) is kept as written.

Origin: https://github.com/gosha70/wiki-studio/issues/11 and the owner's instruction that 0.3.0 is not released until #10 and #11 are addressed.

Origin claim:
> State the path frame in the response instructions; strip only the exact configured label prefix, then run all existing path-safety validation; tests with a one-word and a nested label; expose the resolved layout through `lint` or an `info` command with `--version` machine-readable; page types and directories fixed; second eval run separate.

Working claim:
> Delivered on `fix/11-path-frame`: the multi-page response instructions name the configured label and the rule, and the response schema's `path` carries it; `WikiPaths.strip_wiki_label` removes exactly one `<label>/` and the multi-ingestor applies it before the unchanged validators (file-back inherits it); `wiki-studio info` (and `--json`) prints layout default/custom (custom when root, wiki or proposals is overridden), each location with its source and existence, the logs and the schema copy as `packaged`/`project`; `--version` unchanged; tests for the strip cases, stub backends with labels `wiki` and `knowledge/wiki`, the double prefix still rejected, prompts with and without wiki state, `api.ingest` end to end at `<root>/wiki`, and `info` in default, custom, flag, JSON and empty-directory cases; README and CHANGELOG (Fixed, Added; run 1 kept as measured on 0.2.0). 442 tests, 92 percent coverage.

Mismatches:
  - `layout: custom` also when only the root is overridden (reviewer note): broader than the plan-time "wiki or proposals", because a moved root moves everything; the spec text was updated.
  - One review note kept without change: an empty-string flag value counts as unset in `info`; `WikiPaths.resolve` uses the same falsy test (`root or environ.get(...)`), so the two agree.
  - No second evaluation run in this feature, by design; it needs the owner's hook isolation and a new fixture name.

Verdict: aligned
Confidence: high
