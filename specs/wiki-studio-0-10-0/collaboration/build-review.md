---
feature_id: wiki-studio-0-10-0
date: 2026-11-17
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-10-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-10-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The release bump to 0.10.0 is consistent across `pyproject.toml`, `__init__.py`, README, quickstart, and tests. The contract additions (`nightly: 1` format, `nightly` capability) are wired correctly and the advertised-contract test covers them. The main correctness concern is that the diff only shows the version/contract/docs surface of the feature — the actual `nightly` implementation (`api.nightly`, CLI verb, `NIGHTLY_FORMAT_VERSION` constant) is not visible in this diff, so I cannot verify the substantive behavior described in the docs.

## Findings

- [warning] f-cbf434a4: `NIGHTLY_FORMAT_VERSION` is referenced in `FORMATS` but its definition is not shown in the diff; if it is not defined (or defined in a module not imported here), `contract.py` will raise `NameError` at import time, breaking every entry point. (src/wiki_studio/contract.py)
- [warning] f-6b61f369: The `nightly` capability is advertised in `info`, and `test_info_contract.py` asserts `callable(api.nightly)` and `"nightly" in _VERBS`, but the diff does not show `api.nightly` or the CLI verb being added. If those are missing, the advertised-contract test will fail and the capability is a lie. (src/wiki_studio/contract.py)
- [warning] f-619b2c07: The README documents a precise precedence order for `nightly` exit codes (6 report > 10 lock > 6 proposal write > 1 lint > 3/4 draft) and states "the report is still written" on lint failure, but no test in the diff exercises this precedence. The docs are the only spec for this behavior. (README.md)
- [warning] f-82c85eef: The contract says `edits` is `null` when `plan.json` cannot be read, but the JSON example shows an integer. Consumers reading `edits` as int will break on `null`. This is a documented-but-untested edge. (docs/knowledge-contract.md)
- [note] f-d1326439: The four states are documented but the transition rules (when `skipped` vs `stopped` vs `off`) are not spelled out, and no test in the diff pins them. Ambiguity here is a correctness risk for downstream consumers. (docs/knowledge-contract.md)
- [note] f-92993c6a: `_readme_nightly_section` will raise `ValueError` (not a clean assertion) if the heading or the next `### ` is missing, producing a confusing failure. Also `remainder.index("\n### ")` fails if the nightly section is the last `###` section in the README. (tests/test_nightly_recipe.py)
- [note] f-9f3e4a67: The test asserts the exact ordered list of flags in the synopsis line. This is brittle: reordering flags in the README (a harmless doc edit) will fail the test, and it does not verify the flags are actually accepted by the parser (that is covered by the run test, but only for the lines shown). (tests/test_nightly_recipe.py)
- [note] f-2ec03ba4: The changelog claims "No new exit code, MCP tool, page-schema, patch-set, `findings` or `lint` change" but the README exit-code table adds `nightly`-specific meanings to codes 1, 2, 3, 4, 6, 10. That is not a new code, but the phrasing could mislead a reader into thinking exit-code semantics are unchanged. (CHANGELOG.md)
- [note] f-a54b6713: The contract says "Keys may be added within `nightly_version: 1`" — this is a good forward-compat stance, but it means consumers must tolerate unknown keys. Confirm the JSON schema (if any) or the `NightlyResult` dataclass does not reject unknown keys on read. (docs/knowledge-contract.md)
