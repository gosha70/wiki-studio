---
page_type: decision
slug: cct-wiki-studio-adoption-plan-02
title: 'Share the venv physically; separate dependency ownership logically'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-studio-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The repo `.venv` remains the one managed environment, but a dedicated
`scripts/wiki-requirements.txt` owns the one-package hash lock. It is not
appended to Session Analytics' ranged requirements, because one hashed entry
would either force that entire transitive graph into `--require-hashes` or make
the provenance boundary misleading.

An adapter-neutral setup helper owns installing/checking this lock. The root
setup calls it for every checkout adapter. Session Analytics remains free to
install its requirements into the same venv, and neither readiness check may
mistake the other's packages for its own. A wiki dependency failure does not
undo adapter files already copied, but it is a distinct incomplete result in
the summary. Exit status follows the owner's 2026-11-10 ruling: an
unavailable interpreter or a failed hashed install gets a warning naming the
cause and the remedy, and exit 0, matching how setup treats every other
optional Python part today; the command exits non-zero only when the wiki was
explicitly requested and could not be made ready. On a host with only Python
3.10 or only 3.14, non-wiki
CCT remains usable but wiki tooling is unavailable; setup says so and does not
claim full readiness or destructively replace an existing venv.
