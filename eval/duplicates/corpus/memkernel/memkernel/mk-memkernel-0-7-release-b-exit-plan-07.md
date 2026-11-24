---
page_type: decision
slug: mk-memkernel-0-7-release-b-exit-plan-07
title: 'The upgrade run'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-release-b-exit/plan.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

(the owner's decision: a separate run with its own directory, not before session 1).
`run.py --upgrade` records its own attempt, under
`runs/<date>-upgrade-memkernel-0.6.0-to-<0.7.x>-wiki-studio-<v>/`, in a fresh environment:
**On memkernel 0.6.0 from PyPI:** retain, export through the gate, then the curator marks the pages stable
and approves them, and a 0.6 import brings them in. This is a store that 0.6.0 itself wrote.
**Upgrade** the same environment to the released 0.7.x wheel, with sha256 checked, and set
`MEMKERNEL_WIKI_MODE=governed`.
**The first 0.7 import** lists every page under `ambiguous` (`legacy owner unproven`) and writes nothing.
The check is that no memory is written or changed: the same records, tags and markers before and after. Chroma's files are not compared byte for byte, because SQLite may rewrite them.
**`wiki_import(adopt_legacy=true)`** adopts each page's record, which then carries the wiki's identity. The
check is that it adopts and does not duplicate.
**One correction through the 0.7 loop:** correct, approve, import, then recall in a new session. The check
is that the adopted store behaves as a 0.7 store.

After steps 4 and 5, the upgrade run applies the same convergence checks as the main run: no page key with two
live memories, no duplicate page or receipt, and no unfinished ledger entry.

The upgrade run is recorded by the same protocol and under the same rules as the main run.
