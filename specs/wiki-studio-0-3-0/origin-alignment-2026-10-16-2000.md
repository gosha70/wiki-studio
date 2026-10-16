# Origin alignment check — wiki-studio-0-3-0 (amendment: run 2, protocol review fix)

Gate: plan amended (Gate 1 for US5, second pass), 2026-10-16 20:00 local. Review of the protocol (PR #13) found that run 2's root `eval/navigation/run2/` excludes the shared corpus in `eval/navigation/corpus/`, so the unchanged ingest command would refuse every source with `PathOutsideRootError` before any backend call. Reproduced without a model call (`--backend test --check`: exit 7 without the flag, exit 0 with `--allow-out-of-repo`, no file written). Earlier records are kept as written.

Origin: as in the 2026-10-16-1800 record, plus the reviewer's finding and its remedy (add `--allow-out-of-repo` to the pinned command and permit it in FR-015; keep the root inside `run2/` for log isolation).

Working claim:
> FR-015 now states that the pinned run 2 command differs from run 1 by the paths and by `--allow-out-of-repo`, why (sources outside run 2's root), what it records (the flag in the manifest; `source_repo_relative: false` in the audit records) and that the root stays inside `run2/` so the query and audit logs are run 2's own. Task 11 spells out the exact command. Nothing else in the protocol changes; the shared files are still used in place.

Mismatches:
  - none. The flag is the documented override for a deliberate external source; it does not loosen any other check (paths, placement, lint, the one-attempt rule).

Verdict: aligned
Confidence: high
