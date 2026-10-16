# Origin alignment check — wiki-studio-0-3-0-path-frame

Gate: plan approved (Gate 1), 2026-10-16 15:00 local. Owner instruction: no release until issues #10 and #11 are addressed; #11 is this feature.

Origin: https://github.com/gosha70/wiki-studio/issues/11, filed 2026-10-16 from run 1 of the navigation evaluation, with the reviewer's two refinements (strip only the exact configured label, then run all existing validation; keep `--version` machine-readable and expose resolved paths through `lint` or a dedicated `info` command) and the owner's instruction to keep the fix separate from the 0.3.0 evidence PR.

Origin claim:
> The ingest prompt shows `<wiki-label>/…` file headings but requires wiki-relative edit paths and never says so; 8 of 10 ingests failed with a one-word label. Fix: state the frame in the response instructions; strip only the exact configured label prefix, then run all existing path-safety validation; tests with a one-word and a nested label; expose the resolved layout through `lint` or an `info` command with `--version` unchanged; page types and directories stay fixed; second eval run separate.

Working claim:
> The spec adds the instruction (multi-page mode only) and a schema `description`; `WikiPaths.strip_wiki_label` removing exactly one `<label>/`, applied in the multi-ingestor before the unchanged validators (file-back inherits it); a read-only `info` verb with `--json` printing layout default/custom, each location with its source and existence, and the schema copy in use; tests for all of it; README and CHANGELOG updates. No other normalisation, no change to the five verbs, flags, exit codes or help text, no second run.

Mismatches:
  - `info` is chosen over a `lint` line (the issue allowed either): `lint` needs a wiki and may exit non-zero, `info` is read-only and exits 0.
  - A sixth verb is additive to the frozen five-verb contract; the contract tests gain it rather than change.

Verdict: aligned
Confidence: high
