---
page_type: decision
slug: mk-memkernel-0-7-governed-spec-02
title: 'Curation debt at session start'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-governed/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

**When:** the full session-start block (`startup`, `clear`, and no source), not `compact`, `resume` or `fork`;
only when `MEMKERNEL_WIKI_DIR` is set, the configured mode is not `ungated`, and wiki-studio is available. In
`auto`, a `managed` or `legacy` wiki, a drifted one and one missing a capability are read as today's gated path
reads them (wiki-studio itself refuses drift only on a governed wiki). When `configured_mode` is
`governed`, only after the governed preflight (G1) passes: a `managed`, `legacy`, drifted or capability-incomplete
wiki is never read; the section is then the one unavailable line, naming the refusal.
**What:** a `### Curation debt` section:
one line of the nonzero counts from `api.findings` (`counts`), in memkernel's own order
(`CURATION_KIND_ORDER`, a constant: the review kinds `unapproved`, `approval-stale`,
`approval-policy-changed`, `superseded-still-indexed`, then `stale-claim`, `weak-orphan`,
`missing-cross-link`, `avoid-format`, `no-page-id`; a kind it does not know follows, by name), never
wiki-studio's dictionary order, plus memkernel's own: the sync ledger's unfinished entries for this wiki
(`pending`, `failed`);
up to `CURATION_DEBT_MAX_LINES = 3` example lines (`- <kind>: <page>`): findings whose kind is a review kind
first, then the rest, both in `CURATION_KIND_ORDER`;
one hint: run `wiki-studio findings` for the full list.

No debt: no section. A failure of `findings` gives one line, `Curation debt unavailable: <reason>`; the hook
never fails because of it.
**Budget (the reviewer's recommendation, 2026-11-03):** the section is at most `CURATION_DEBT_BUDGET = 500`
characters, and the context share lends only what the section actually uses: context gets
`CONTEXT_BUDGET - len(rendered section)`. No debt, no section: context keeps its full 2,500. `TOTAL_BUDGET`
stays 9,000, as `lifecycle.py` requires.
**The ledger is read, never touched.** A new read-only snapshot in `ledger.py` gives the unfinished counts. It
never creates, renames or saves a ledger file (it may create the empty lock file, as `run()` does).
`SyncLedger.run()` is not used: it moves a corrupt ledger aside and
saves a new one, which would destroy the evidence the next import recovers from.
**On disk** (in the child, below): an import holds the ledger's exclusive lock while it changes its entries
and saves only at the end, so an unlocked read could see a complete but stale file. The snapshot therefore
takes the **same lock file** `run()` takes, `<key>.json.lock`, with a **non-blocking shared** `flock`;
contention gives the unavailable line. The child closes that descriptor in a `finally`, and its exit, a kill
included, releases the lock in any case.
**The linearization point is the ledger directory's check.** If the project's ledger directory
(`<state>/wiki-sync/<project>/`) does not exist, no import has ever written a ledger: the counts are zero,
and an import that creates it later started after the snapshot. If it exists, the snapshot opens the lock
file with create-if-missing, exactly as `run()` does (an empty lock file is not ledger data), and takes the
shared lock before reading `<key>.json`. So an import holding the lock, its first one included, always
gives the unavailable line; there is no window between a check and a read. The snapshot creates nothing
else and never touches `<key>.json`.
Without `fcntl` the read is unlocked, as every other ledger access is there (memkernel-0-7-store-locks L4).
**In memory** (an in-memory store's ledgers are process-global dictionaries, `ledger.py:42`, invisible to a
child), a process-local `threading.Lock` per ledger, new, is held by `SyncLedger.run()` for its whole run and
taken by the snapshot **non-blockingly** in the parent: contention gives the unavailable line, and the
snapshot copies the counts under it. Each ledger's lock is created once, under one module-level guard, so two
threads never install two locks for one ledger. The lock is not re-entrant, and `run()` never calls the
snapshot. This is the only part of the debt that runs in the parent: it never waits, and it observes the same
monotonic deadline while it copies (checked every `CURATION_DEBT_DEADLINE_CHECK_EVERY = 100` entries); past
the deadline it releases the lock and gives the unavailable line (`timed out`).
A missing ledger counts nothing; a corrupt one gives the unavailable line.
**A hard time bound, by a process boundary.** Everything else runs in one child process (`multiprocessing`,
spawn context): detecting wiki-studio (`gate_available`), in `governed` the preflight, `findings`, and the
on-disk ledger snapshot. The parent only checks the settings (wiki directory set, mode not `ungated`) before
starting it.
**One deadline.** The parent takes a monotonic deadline, `CURATION_DEBT_TIMEOUT_SECONDS = 2.0`, once
`Process.start()` returns, before the in-memory snapshot (amended, below). A start that raises is the unavailable line, and the cleanup below still runs (both pipe
ends closed; a process object that reports itself alive goes through the bounded reap), so a partial start
leaks nothing. **Amended during the build (2026-11-04, the owner's decision):** `Process.start()` runs on the
calling thread and cannot be interrupted, so the deadline is taken once it returns: the 2.5 seconds bound the
check, not a fork or exec the operating system holds up. Allocating the pipe and every cleanup step are inside
the no-raise boundary, and each cleanup step runs whatever the one before it did.
**The result** is one plain, bounded dict (the counts as integers, at most `CURATION_DEBT_MAX_LINES` example
pairs, each string cut to `CURATION_DEBT_FIELD_CHARS = 200`, or an error string), sent over a one-way
`multiprocessing.Pipe(duplex=False)`, never a `Queue`. The parent keeps the read end and closes its copy of
the write end right after the start; the child closes its copy of the read end first and its write end in a
`finally`, so the parent sees EOF as soon as the child ends. The parent waits with `poll(remaining)` and
receives before joining, so a large result can never block a join. EOF (the child died or raised before
sending) is the unavailable line.
**Every wait is bounded, with the grace split in two.** Past the deadline: `terminate()`, then
`join(CURATION_DEBT_TERM_GRACE_SECONDS)` (0.3); if the child is still alive, `kill()`, then
`join(CURATION_DEBT_KILL_GRACE_SECONDS)` (0.2). Each interval is its own, so the post-kill reap always has its
0.2 seconds. The debt's total time once the child has started is at most 2.0 + 0.3 + 0.2 = 2.5 seconds, the in-memory snapshot
included, whatever the child does. A child still alive after that is left to the operating system, reported
as the unavailable line (`not reaped`), and not closed (`Process.close()` refuses a live process).
**Cleanup on every path:** both pipe ends are closed in a `finally`; a reaped child gets `Process.close()`. So
repeated session starts in one long-lived process accumulate no children, pipes or sentinels.
The build measures the time on a 200-page wiki, the child's start-up included, and reports it in the PR.
