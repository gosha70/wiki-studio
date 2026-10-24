---
feature_id: wiki-studio-0-6-0
date: 2026-10-24
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-6-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-6-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

This is a documentation-and-metadata release (0.6.0) that mostly rewrites prose to state guarantees honestly (dropping "atomic", adding lock scope, heuristic caveats) plus a coverage-gate bump from 80 to 92 and version bumps. The code changes are minimal (docstrings/comments only in `fact_diff.py`, `health_lint.py`, `promoter.py`, `proposal.py`), so correctness risk is low; the main concerns are the coverage-gate jump and a few documentation consistency points.

## Findings

- [warning] f-395ed76c: Coverage gate raised from 80 to 92 in one step; if the suite does not actually hold 92% on all supported Python versions (3.11–3.13) and platforms, CI will fail on the release tag. The CHANGELOG claims "matching the level the suite holds" but no evidence is shown in the diff. (.github/workflows/ci.yml)
- [note] f-ac74c551: The `[Unreleased]` compare link was updated to `v0.6.0...HEAD` and a `[0.6.0]` link added, but the `[0.1.0]` link remains and there is no `[0.5.0]`/`[0.4.0]`/... link. This is pre-existing but the new `[0.6.0]` link style (`compare/v0.5.0...v0.6.0`) differs from `[0.1.0]` (`releases/tag/...`). (CHANGELOG.md)
- [note] f-75fa887f: README says "on an exception during the commit every touched file is restored to its exact previous bytes" — this is a strong claim. Confirm the rollback path in `promoter.py` truly restores exact bytes for every touched file (including newly created files, which must be deleted, and the archive under `.audit/proposals/`). If any touched path is not covered, soften the wording. (README.md)
- [note] f-1ba31aa4: SECURITY.md now claims "every read and write of a wiki page, a proposal file or a local link target passes one containment check that resolves the path and refuses an escape or a symlink (`wiki_studio.paths.contain`)". This is a strong universal claim; ensure `paths.contain` is actually invoked on every such surface (including `find`, `query`, `lint`, `preview` pointer, `.ingest-snapshot/`, and the archive write path). (SECURITY.md)
- [note] f-df194037: The doc now says a patch-set is applied "in one promotion: validated, serialised ... rolled back on failure, and not crash-safe across files." Good. But the CHANGELOG "Upgrade notes" mention a leftover `receipt.json` resolution procedure "in `docs/patch-set-format.md`" — verify that section actually exists in the file (the diff only shows the opening paragraph change). (docs/patch-set-format.md)
- [note] f-96a9d85d: Docstring now correctly says the check verifies path existence, not revision currency. Good. Ensure the corresponding README `--health` row and any user-facing help text for `lint --health` match this wording (README was updated; verify CLI `--help` text too). (src/wiki_studio/health_lint.py)
- [note] f-bea6b5c9: Docstring change only; behavior unchanged (`os.rename`). Note that `os.rename` is atomic only within the same filesystem — the docstring says "a reader sees no archive or the whole one", which holds only if `tmp` and `target` are on the same filesystem. Since `tmp` is a "hidden temporary sibling" this is presumably guaranteed, but worth a one-line comment. (src/wiki_studio/promoter.py)
- [note] f-238f132a: This is mentioned under Upgrade notes but the `pyproject.toml` diff does not show the classifier removal. Confirm the classifier change is actually in `pyproject.toml` (it may be in an earlier commit in the range). (CHANGELOG.md)
- [note] f-45af8d22: The release note claims it "closes #39" and references `docs/roadmap.md` Release A. Ensure the roadmap and issue are actually updated/closed as part of this release; otherwise the claim is stale. (CHANGELOG.md)
