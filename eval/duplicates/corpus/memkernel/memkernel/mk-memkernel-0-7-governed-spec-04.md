---
page_type: decision
slug: mk-memkernel-0-7-governed-spec-04
title: 'Source revision and content hash on exported pages'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-governed/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

A `path:` source gains `sha:`, the git commit the page is grounded at, as wiki-studio's citation rules define it
(`git log -1 --format=%h -- <path>`), when the file is tracked and unmodified: `git status --porcelain -- <path>`
prints nothing (no staged or unstaged change). A modified, staged or untracked file, a path git reports no commit
for (outside the repository, or inside a submodule), or no git, gets no `sha:`: no commit grounds it. A file
counts as tracked only when the project's own `git ls-files -- <path>`, run from the project root, lists exactly
that path (equality, not a prefix or a pattern): a
file inside a submodule is not listed by the superproject, so it never takes the submodule's commit. git is run as a subprocess, read-only, with a
short timeout; no new dependency.
The page gains `memkernel_sha256: <the memory's content hash>`, memkernel's own key beside `memkernel_ref` and
`memory_type`, so a curator, or a later revalidation, can tell which revision of the memory the page drafted.
**Rejected:** a `sha256:` key inside a source entry. wiki-studio's citation rules do not define it.
