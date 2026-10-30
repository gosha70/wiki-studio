---
pitch_id: 38-release-c-discovery-portability
title: "Release C, discovery and portability: FTS5 ranking behind the index-first workflow with a rebuildable cache and a context budget, measured on a held-out set; an optional MCP adapter on the official SDK with a conformance suite"
appetite: 6w
bet_status: shipped
cycle: "03"
circuit_breaker: "Core is the discovery half, S1, S2 and S3: standard library only, measured, and it ships alone if the cycle runs out. End of week 2: if S1 and S2 are not downhill, stop S4 and S5 and shelve the adapter to a follow-up issue. Tuning starts only after the held-out set (ingested wiki, its manifest, questions and gold) is frozen. End of week 3: if it is not frozen, FTS5 ships untuned as an opt-in ranker and index-first stays the default. A held-out ingest that promotes few documents is a finding, not a reason to retry; if fewer than 15 held-out questions end with a gold page, or the frozen held-out wiki has fewer than ten eligible pages, FTS5 also stays opt-in. End of week 4: if S4 is not downhill, shelve S4 and S5; 0.8.0 ships discovery alone, no dependency is added, and Release C stays open. End of week 5: if no host run has passed S5, ship the extra as a preview on the protocol-level suite and keep Release C open. Never add a core dependency, change an exit code, write the cache into the wiki, edit a frozen run, retry or hand-edit the held-out ingest, tune on the held-out set, or put approve or a model-spawning verb on the default MCP surface to stay on schedule."
shaped_by: "pitch-shaper (Claude Code) for gosha70"
shaped_date: 2026-10-26
---

<!-- Shape-Up pitch. Origin: https://github.com/gosha70/wiki-studio/issues/38 (Releases B and C) -->
<!-- docs/roadmap.md (Release C, Evidence) and docs/proposals/2026-10-23-product-proposal.md are the origin. This pitch shapes them; it does not replace them. -->

# Pitch: Release C, discovery and portability

## Problem

0.7.0 made the curation loop governable. Two things still limit who can
use wiki-studio on its own.

1. **Discovery is weak and unbounded.** `find` and `query` pick pages by
   counting the question's words that also occur in a page's slug, path
   and first 400 characters. On the published fixture that puts the gold
   page first for 3 of 21 questions (14.3%) and within the top five for
   10 of 21 (47.6%). Five questions select nothing beyond the index, and
   a question the corpus cannot answer loads four pages on average. The
   five-page cap bounds the page count, not the size: five large pages
   can still fill a model's context.
2. **Only shell-capable agents can use it.** The surface is a CLI and a
   Python API. An agent host that speaks MCP (Claude Code, Kiro) has to
   wrap the CLI itself, and nothing tells it which operations are safe to
   give an agent. Each host that does this rebuilds the same boundary:
   no model calls, distinct proposal and promotion, and no approval.

The cost is the roadmap's adoption claim. "Can others adopt it" is
measured as time to the first accepted revision on a clean install.
Today that needs a shell wrapper and a selector that misses half the
time.

The owner chose all of Release C in one release, 0.8.0. Discovery-first
was offered and declined.

## Findings from the code

wiki-studio was read at main 0f64c3b on 2026-10-26. The MCP SDK was read
from the `mcp` 2.3.0 and `mcp-types` 2.3.0 wheels on PyPI the same day.
These facts drive the scopes and rabbit holes.

1. **Selection today.** `_select_query_candidates`
   (`querier.py:104-156`) reads `index.md`, takes the index links that
   stay inside the wiki (`_extract_index_links`, `querier.py:84-101`),
   reads **every** linked page in full, and scores token overlap with the
   slug, the path and the first 400 characters. Highest score first, ties
   by index order, then the first `max_pages`.
   `DEFAULT_MAX_QUERY_PAGES = 5` (`querier.py:53`). `api.find`
   (`api.py:1038-1058`) and `DefaultQuerier.query` (`querier.py:340-386`)
   both call it. There is no size limit.
2. **The frozen runs re-run the live selector.** `eval/navigation/run.py`
   imports `_select_query_candidates` and `DEFAULT_MAX_QUERY_PAGES`
   (`run.py:25`). `tests/test_navigation_eval.py` asserts runs 1 and 2
   against their committed `results.json` on every CI run. A change to that
   function that moves any number fails CI. The body of
   `_select_query_candidates` is therefore not edited. It becomes the
   named fallback ranker. The one change near it is in a helper it calls
   (finding 4), and it leaves every frozen number unchanged.
3. **The stop list is frozen too.** `test_stop_list_is_the_queriers`
   requires `wiki_state._STOPWORDS` to equal `eval/navigation/stopwords.txt`.
   If tuning wants another stop list, that list is a separate constant.
4. **A non-UTF-8 linked page breaks selection.** `_read_text_or_empty`
   (`wiki_state.py:147-152`) catches `OSError` only, and
   `UnicodeDecodeError` is a `ValueError`. The fix goes into that helper:
   it catches `UnicodeDecodeError` as it catches `OSError` and returns
   the empty string, so the selector's body is untouched. No frozen
   fixture has a non-UTF-8 page, so no frozen number moves. The helper
   has four callers, and the change reaches all of them:

   | Caller | Today, on a non-UTF-8 page | After the change |
   |---|---|---|
   | `querier._select_query_candidates` (index-first) | crash | the page reads as empty and is never selected |
   | `health_lint` (five call sites) | crash | the page reads as empty and is never checked |
   | `prose_lint` (two call sites) | crash | the page reads as empty and is never checked |
   | `wiki_state` (ingest's wiki state, the prompt) | crash | the model sees the page as empty; an update drafted against it fails its base-hash check at `promote`, so the wiki is safe |

   An empty read makes the page invisible without a word, and the
   structural lint (`lint.py:120`, `errors="replace"`) does not flag it
   either. So the helper change comes with one structural-lint rule: a
   wiki page that is not valid UTF-8 is a violation, reported once with
   its path (S1). Every caller is then safe, and the page is reported
   instead of disappearing.
5. **The single-writer scans are syntactic.** `tests/test_e2e.py:1054-1092`
   and `tests/test_audit.py:466-508` flag a write call on a line that
   mentions `wiki_dir`. A `sqlite3.connect(...)` under the wiki would pass
   both scans unnoticed. A cache location rule needs a behaviour test, not
   only the scan.
6. **There is a precedent for state beside the wiki.** The lock file is
   `<resolved-wiki-parent>/.<wiki-dir-name>.wiki-studio.lock`
   (`wikilock.py:127-128`). It is outside the wiki boundary, keyed to the
   resolved wiki, and already documented for `.gitignore`. The query log
   is root-relative (`paths.py:63`, `doc_internal/wiki-query-log.jsonl`).
7. **The capability test is strict.** `contract.CAPABILITIES`
   (`contract.py:97-115`) feeds `info`, and
   `tests/test_info_contract.py:161-190` requires a resolver for every
   advertised string. New capabilities need resolvers in the same change.
8. **The core has no dependencies or extras.** `pyproject.toml` declares
   only `python = ">=3.11,<3.14"` and one script. The CI `build-check` job
   already installs the wheel into a fresh virtual environment and imports
   the API (`ci.yml:157-185`). That job is where the standard-library proof
   belongs.
9. **The fixtures are small.** Run 2's wiki is nine content pages and
   53,178 bytes including the index. Its largest page is 9,359 bytes. The
   five largest pages together are about 38 KB. A context budget cannot
   be measured on this set and needs its own fixture.
10. **FTS5 is present locally but not guaranteed.** CPython 3.11.3
    (SQLite 3.40.1) and 3.13.2 (SQLite 3.48.0) on this machine both create
    an `fts5` table with the `porter unicode61` tokenizer. Python's
    `sqlite3` links whatever SQLite the build has, so availability needs a
    runtime probe.
11. **`promote` has escape hatches an agent must not reach.**
    `api.promote` takes `allow_out_of_repo`, `allow_unguarded_updates`
    and `entry_point` (`api.py:691-701`). The receipt records
    `entry_point` as `cli` or `api` (`promoter.py:169-170`,
    `docs/patch-set-format.md:195`).
12. **Auto-approval runs inside `promote`.** With the policy
    `auto_approve_on_promote`, a successful promotion approves the pages it
    wrote under the promoter's actor (`promoter.py:2478`, 0.7.0 CHANGELOG).
    An agent that can call `promote` on such a wiki therefore approves its
    own proposal indirectly. The owner decided (D14) that the adapter
    honours this policy and reports it, rather than refusing.
13. **The official MCP SDK.** `mcp` 2.3.0 (2026-10-02), MIT,
    `Requires-Python >=3.10`, repository
    `modelcontextprotocol/python-sdk`. 2.0.0 shipped on 2026-07-28. The
    1.x line is still maintained (1.30.0, 2026-09-07). In 2.x `FastMCP` was
    renamed `MCPServer`, and `mcp.server.fastmcp` now raises on import, so
    the major version matters. Its runtime dependencies are `anyio`,
    `httpx2`, `jsonschema`, `mcp-types==2.3.0`, `opentelemetry-api`,
    `pydantic>=2.12`, `pyjwt[crypto]`, `python-multipart`,
    `sse-starlette`, `starlette`, `typing-extensions`,
    `typing-inspection` and `uvicorn`, plus `pywin32` on Windows.
14. **Protocol versions the SDK speaks** (`mcp_types/version.py`).
    Handshake versions: 2024-11-05, 2025-03-26, 2025-06-18 and 2025-11-25.
    One "modern" version with a stateless per-request envelope:
    2026-07-28.
15. **Sync tools run off the event loop.** The SDK runs a synchronous tool
    function with `anyio.to_thread.run_sync`
    (`mcp/server/mcpserver/resolve.py:556`). A tool that waits up to 30 s
    for `WikiLock` therefore does not block other requests.

## Appetite

**6w**, one bet, released as **0.8.0** (owner decision: all of Release C
in one release). For an LLM executor the work content is about 36-48
hours across five scopes:

| Scope | Estimate |
|-------|----------|
| S1 Ranked discovery with a context budget | 6-8h |
| S2 The rebuildable cache | 6-8h |
| S3 Discovery evidence, including the held-out ingest | 10-14h |
| S4 The MCP adapter as an extra | 8-10h |
| S5 Conformance suite and a host run | 6-8h |

That is Release B's work content (33-44h, a 6w appetite) plus the
held-out ingest. The ingest itself is about eight model calls, one per
document, with the pinned model through the `claude` backend. Run 2
averaged 52 s per document, so the ingest takes about seven minutes of
wall time. The backend does not expose tokens, so cost is recorded as call
count and wall time, as in run 2. The hours are in the protocol script,
the isolation probe, the bookkeeping and the gold assignment. Four things
set the wall-clock budget rather than the hours:

- **Evidence has a fixed order.** The held-out questions are written from
  the source documents and committed before the ingest. The ingested wiki
  and its manifest are frozen, gold is assigned and reviewed, and all of
  it is frozen before any tuning. The held-out run happens once, after
  the ranker configuration is frozen. That sequence cannot be compressed
  by working faster.
- **The held-out ingest runs once.** One attempt per document, no
  retries, nothing edited by hand. A poor ingest is reported as measured,
  not repeated.
- **Two independent risks.** Discovery is standard library only and
  measured. The adapter adds the first dependency and depends on an
  external SDK and on host behaviour. Either can draw review rounds:
  0.6.0 needed five on one PR, and 0.7.0's build review found six
  defects (CHANGELOG 0.7.0, Fixed).
- **Two runs need the owner.** The held-out ingest and the Claude Code
  host run both use the owner's account and a model, so they run outside
  CI on the owner's schedule.

Why not two bets (discovery 4w, adapter 2-4w)? The halves share no code,
so a split stays possible at the scope boundary, and the circuit breaker
uses exactly that boundary. One bet is kept because the owner asked for
one release, and because the week-2 and week-4 checkpoints give the same
early signal a split would.

Cycle: Release B's pitch (cycle 02) stays `building` until memkernel #48
closes. This pitch becomes a new cycle when it is bet. Nothing here
depends on memkernel #48.

Planned order, as wall-clock weeks:

- **Week 1:** S1 untuned, S2 started. S3: the held-out sources pinned,
  the questions written from them and committed, the protocol script and
  the isolation probe. S4's packaging and the standard-library proof.
- **Week 2:** the held-out ingest, run once. The ingested wiki and its
  manifest are frozen, gold is assigned from the frozen wiki, and the
  owner reviews. Questions, gold, protocol and hashes are frozen before
  any tuning. S2 recovery tests. S4 tool surface.
- **Week 3:** tuning on the 21 development questions only, starting after
  the freeze; the ranker configuration is frozen at the end of the week.
  S5 protocol-level suite in CI.
- **Week 4:** the held-out run, once, and the default-ranker decision
  (D5). S5 host run.
- **Weeks 5-6:** docs, compatibility matrix, review, 0.8.0.

## Solution shape

Two halves that share no code. Both are additive to the 0.7.0 API and
formats. No new exit code, no page schema change, and `promoter.py` stays
the only module that writes into the wiki directory.

**Discovery (S1-S3).** A second ranker, FTS5 with bm25 over the same
candidate set the index-first selector uses: the pages linked from
`index.md` that stay inside the wiki. `index.md` is still read first and
always loaded, the cap stays five pages, and a byte budget limits what is
loaded. The FTS5 table is a cache outside the wiki. Every call rereads and
hashes the eligible pages, as today's selector already reads them, so the
cache can never return a page the wiki no longer has. When the runtime
lacks FTS5, selection falls back to today's selector, says so, and never
fails. The 21 published questions become the development set. A fresh
held-out corpus is ingested through the real pipeline under a frozen
protocol, as run 2 was. The ingested wiki and its questions are frozen
before tuning, and the single held-out run decides whether FTS5 becomes
the default.

```
question ─▶ index.md (always loaded)
              │ eligible links (inside the wiki, UTF-8, not superseded)
              ▼
         read + sha256 every eligible page ──▶ content manifest diff ──▶ FTS5 cache (outside the wiki)
              │                                                              │ bm25, ties by index order
              ▼                                                              ▼
         page text for the prompt  ◀──────────── top 5 ◀── byte budget ◀── ranked paths
         (from this call's reads, never from the cache)
```

**Portability (S4-S5).** A `wiki-studio[mcp]` extra on the official SDK
and a `wiki-studio-mcp` stdio server. The server is bound at launch to the
same roots the CLI resolves. Its eight tools are each one call into the
existing `api`: `find`, `read_page`, `propose`, `promote`, `lint`, `info`,
`findings` and `review_state`. `approve` and every model-spawning verb are
not on the surface. A conformance suite drives any MCP server command
through the SDK's client against a fixture wiki. CI runs it against this
adapter, and a Claude Code run, checked by the same suite, is the
non-memkernel runtime evidence.

## Scopes

Build order: S1 and S4 start at once. S2 needs S1's index builder. S3
needs S1, and its held-out freeze must come before any tuning. S5 needs
S4.

### S1: Ranked discovery with a context budget, ~6-8h

- **Modules.** `src/wiki_studio/discovery.py` holds the FTS5 probe,
  eligibility, ranking, the budget and selection.
  `src/wiki_studio/search_index.py` holds the FTS5 table, in memory here
  and on disk in S2. It is the only writer of the cache file.
  `_select_query_candidates` keeps its behaviour and becomes the
  `index-first` ranker. The frozen runs keep calling it directly.
- **Probe.** `fts5_available()` runs once per process. It creates an
  `fts5` virtual table with the chosen tokenizer in `:memory:`. On
  `sqlite3.OperationalError` it returns false, with the reason and
  `sqlite3.sqlite_version`.
- **Eligibility.** A page is eligible when it is linked from `index.md`,
  is accepted by `_extract_index_links(index_md, wiki_dir)` (inside the
  wiki, no symlink on the way), is a regular file, is valid UTF-8, and
  does not carry `superseded_by` (D7). `index.md` and `log.md` are never
  candidates. A non-UTF-8 page (finding 4) is ineligible and counted in
  the result. In the index-first path it reads as empty, through the
  helper fix in finding 4, rather than raising. The selector's body is
  not edited, the frozen numbers do not move, and `test_navigation_eval`
  proves it. Because that helper also serves the health checks, the
  prose lint and ingest's wiki state (finding 4), the structural lint
  gains one rule: a page that is not valid UTF-8 is a violation that
  names the path. It is fatal like every structural violation, and
  `promote` lints the whole staged wiki, not only the pages a patch set
  touches. So a non-UTF-8 page anywhere in the wiki makes `lint` fail
  and makes `promote` refuse every patch set, related or not, until the
  page is fixed; the error names the page. Today such a wiki promotes,
  because the structural lint reads with replacement characters, so
  this is an upgrade break for a wiki that already holds one.
- **Upgrade note (for the 0.8.0 CHANGELOG).** "0.8.0 adds a structural
  rule: every wiki page must be valid UTF-8. A wiki that holds a page
  that is not will fail `lint` and refuse every `promote` until the page
  is fixed. The error names the page. Remedy: re-encode the page as
  UTF-8, or remove it and its index entry. Run `wiki-studio lint` before
  upgrading a wiki's tooling to see whether any page is affected." The
  rule stays fatal: 0.6.0 handled its new link rule the same way, and
  the fix is quick.
- **Documents.** The columns are path (the slug and path segments as
  words), title (frontmatter), headings and body (frontmatter removed).
- **Query.** The question goes through the querier's tokenizer and the
  frozen stop list. Each remaining token is double-quoted with `"`
  escaped, and the tokens are joined with `OR`. Raw question text never
  reaches `MATCH`. No tokens means no selection.
- **Ranking.** bm25 with column weights from constants (tuned in S3),
  ties broken by index position, and an optional minimum-match rule for
  questions the wiki cannot answer (tuned in S3). Then the five-page cap.
- **Budget (D6).** `max_bytes` counts the UTF-8 bytes of `index.md` plus
  the selected pages. The default is 65,536. Pages are added in rank order
  and are never truncated. A page that does not fit is skipped, listed in
  `omitted`, and the next page is tried. If `index.md` alone exceeds the
  budget, no page is loaded and a warning says so. The budget applies to
  both rankers in `api.find` and `api.query`. The frozen runs call the
  selector directly, so they have no budget.
- **API (additive, with defaults).**
  `api.find(question, paths, *, max_pages=5, max_bytes=DEFAULT_MAX_CONTEXT_BYTES, ranker=DEFAULT_RANKER)`.
  `FindResult` gains `ranker`, `fallback_reason`, `bytes_loaded`,
  `max_bytes`, `omitted` and `ineligible`. `FoundPage` gains `sha256` and
  `bytes`. `api.query` and `DefaultQuerier` gain `max_bytes` and
  `ranker`. A query-log line gains `ranker` and `bytes_loaded`. The prompt
  and the citation check still use the text read in this call (FR-014
  unchanged).
- **CLI.** `find` and `query` gain `--ranker {fts5,index-first}` and
  `--max-bytes N`. The default ranker comes from `WIKI_STUDIO_RANKER`
  when set, else the shipped default (D5); the flag overrides both, as
  every other setting does. `find --json` gains the new keys. When FTS5 is missing,
  one notice goes to stderr. The exit code stays 0 (D4).
- **Contract.** `info` gains a `discovery` key: `fts5` (bool),
  `sqlite_version`, `default_ranker` and where it came from (`flag`,
  `env` or `default`), `cache` (path and state, from S2).
  New capabilities, each with a resolver: `ranked-discovery`
  (`api.find`'s `ranker` keyword) and `context-budget` (`max_bytes`).
  Both go into `docs/knowledge-contract.md`.
- **Tests.** The probe returns false, so selection falls back to
  index-first with a notice and the result equals `_select_query_candidates`.
  Questions that contain `"`, `NEAR`, `AND`, `-`, `*`, `:`, parentheses
  or non-ASCII never raise. A superseded page is never selected. An
  oversized-page fixture covers skip-and-continue and an index over
  budget. A non-UTF-8 page fixture: `find` with either ranker skips it
  and counts it, `lint` reports the one violation with its path, and
  `lint --health` and `lint --prose` complete without raising. An
  existing non-UTF-8 page blocks an unrelated promote (a patch set that
  only appends to `log.md`) with an error naming the page, and the same
  promote succeeds once the page is re-encoded. The cap and tie order hold. A link to a symlinked page or to
  `../` is never a candidate. `find` leaves the wiki tree byte-identical.

### S2: The rebuildable cache, ~6-8h

- **Location (D1).** `<resolved-wiki-parent>/.<wiki-dir-name>.wiki-studio.search.sqlite`,
  beside the lock file. `WikiPaths` gains `search_cache`, resolved in
  `paths.py` with `--search-cache` and `WIKI_STUDIO_SEARCH_CACHE`
  overrides. A path inside the wiki directory is a usage error (exit 2).
  The single-writer rule needs no exception: the cache is not in the
  wiki. One `.gitignore` pattern, `.<wiki-dir-name>.wiki-studio.*`, covers
  the lock and the cache. The README and `docs/consumers.md` say so.
- **Content manifest.** A table of `path`, `sha256`, `bytes`. A `meta`
  table holds `cache_format`, `ranker_config_hash`, the resolved wiki
  path, `wiki_id` when the wiki has a manifest, and the SQLite version.
  `PRAGMA user_version` carries `cache_format`.
- **Refresh on every call (D2).** Under one `BEGIN IMMEDIATE` transaction
  with a busy timeout: read `index.md`, compute the eligible set, read and
  hash each eligible page (the reads the selector already does), and diff
  against the manifest. A new path is inserted. A changed hash is
  replaced. A path that is gone, unlinked, now superseded or now
  non-UTF-8 is deleted. A rename is a delete plus an insert. Ranking then
  runs in the same transaction, over current paths only. The cache never
  supplies page text to a prompt.
- **Recovery (D3).** A different `cache_format`, configuration hash, wiki
  path or `wiki_id` drops the tables and rebuilds them. A
  `sqlite3.DatabaseError` on open or read (truncated, garbage, not a
  database) removes the cache file and rebuilds it, but only if the path
  is a regular file, not a symlink, outside the wiki. A symlink at the
  cache path, a symlinked parent, an unwritable directory, a read-only
  file system, or a lock held past the busy timeout makes this call use an
  in-memory index with one warning. Missing or broken cache state never
  makes `find` or `query` exit non-zero. Deleting the file is the
  documented manual reset.
- **Tests (exit evidence "cache recovery tests").**
  - A hand edit with the same size and a restored mtime (`os.utime`).
  - A `git checkout` of an older revision in a temporary repository.
  - A rename, a delete, a page unlinked from the index, an `index.md`
    edit, and a page that gains `superseded_by`.
  - A truncated file, random bytes, a wrong `user_version`, a changed
    configuration hash, and a cache copied from another wiki.
  - A symlink at the cache path (its target untouched) and a read-only
    directory.
  - Two processes refreshing at once.
  - A process killed during a refresh, after which the next call is
    consistent.
  - A property test: after any sequence of these operations, the cached
    ranking equals a fresh in-memory ranking.
  - A behaviour test that the wiki tree is byte-identical before and
    after every case (finding 5).
- **Measured, not assumed.** S3's latency block reports the cached path
  beside a fresh in-memory build with no cache, so the cache's value is
  a number. S2 stays whatever that number says, because the roadmap
  requires cache recovery tests; a cache that does not pay on small
  wikis is reported as such.

### S3: Discovery evidence, ~10-14h

- **Frozen and unchanged.** `run.py`, `run2_protocol.py`,
  `questions.json`, `gold.json`, `results.json`, `manifest.json`,
  `stopwords.txt`, `ingest-notes.md` and `run2/` are not edited.
  `test_navigation_eval` keeps passing. A new test pins their sha256. The
  README's 3 of 21 and 10 of 21 stay as the published baseline.
- **Runner.** `eval/navigation/discovery.py` imports `run.py`'s helpers
  (`count_words`, `grep_words`, `question_words`) and calls `api.find`
  with each ranker. For each question it reports both rankers: selection,
  hit at 1, hit at 5, distractor outranks gold, bytes and words loaded,
  omitted pages, and the grep negative control. It also reports:
  - **counts**, and beside every hit rate the number of eligible pages
    in that wiki and the random baseline for that set (`run.py` already
    computes it per question; the new runner reports it too). With a
    five-page cap over a small wiki, hit at 5 mostly measures the cap,
    and these two numbers say so;
  - **unanswerable-query behaviour**: the empty-selection rate, mean
    pages and mean bytes loaded for the `absent` questions;
  - **ingestion coverage**: inherited from run 2 for the development
    wiki (21 of 29, the same frozen wiki, not re-measured). For the
    held-out wiki it is measured: documents promoted out of those
    ingested, and answerable questions whose answer landed in some page;
  - **context size**: bytes and words;
  - **latency**: cold and warm `find` through the on-disk cache, and
    `find` with a fresh in-memory index and no cache, median and p95 over
    five repetitions, with the machine, Python and SQLite versions. The
    cache's benefit is then a number: D2 rereads and hashes every page on
    every call, so the cache saves only the FTS5 build, and on a small
    wiki that may be less than opening SQLite;
  - **parameters**: the ranker configuration hash, `max_pages`,
    `max_bytes`, the tokenizer and the SQLite version.

  CI asserts everything except the latency block against the committed
  file.
- **Development set** (`eval/navigation/run3/`): run 2's frozen wiki and
  the 21 questions with a gold page. `results-untuned.json` is committed
  before any tuning. `results.json` is committed after tuning. The tuning
  knobs are fixed in advance: tokenizer (`porter unicode61` or
  `unicode61`), column weights from a small grid, and the minimum-match
  rule. No learned ranking, no synonyms, no embeddings.
- **Held-out set** (`eval/navigation/heldout/`, D8, D8a, D8b, D9). It is
  a fresh corpus ingested the way run 2 was. A new
  `eval/navigation/heldout_protocol.py` does the bookkeeping. It may import
  `run2_protocol.py`'s helpers, but `run2_protocol.py` is not edited. The
  steps, in order, are pinned in `heldout/protocol.md` and recorded in
  `heldout/manifest.json`:
  1. **Sources.** The corpus repository, commit, file list, sha256 per
     file and licence are recorded (D8a). The files are copied into
     `heldout/corpus/`, with attribution in NOTICE.
  2. **Questions.** At least 35 answerable questions (some competing) and
     at least six the corpus cannot answer. They are written from the
     source documents by the procedure in D9 and committed with their
     sha256 **before the ingest**, as in runs 1 and 2. At run 2's
     coverage (72%), 35 answerable questions leave about 25 with a gold
     page.
  3. **Pins before the first attempt.** The wiki-studio commit and
     version, the backend (`claude`), the model by full name, the Claude
     Code version, the backend timeout and the environment. An isolation
     probe is recorded, as in run 2's `isolation_probe`.
  4. **Ingest.** `init` a fresh wiki. For each document: one `ingest`
     attempt, then `promote` if the gate accepts it. No retries and no
     hand edits. Each document's disposition, its wall time and the model
     call count are recorded. A failure in the environment before the
     first attempt (the probe, backend access) is fixed and the probe is
     re-run. Once the first attempt has started, nothing is re-run.
  5. **Freeze the wiki.** The ingested wiki's tree hash, the archived
     proposals and the manifest are committed and never edited
     afterwards. A test pins their sha256.
  6. **Gold.** Gold is assigned by reading the frozen wiki, with a reason
     per question, as in run 2. The owner reviews the questions and the
     gold (D9). Then everything is frozen by commit and sha256 **before
     tuning starts**.
  7. **Run.** One held-out run, after the ranker configuration hash is
     frozen. No tuning afterwards. Any later run is a new, labelled
     post-hoc version.
- **Default decision (D5).** The held-out results decide the default
  ranker, subject to D8b's and D8c's floors. The numbers go into the
  README Evidence section beside runs 1 and 2, and into the CHANGELOG:
  counts, eligible pages, random baselines, ingestion coverage,
  discordant pairs, absent behaviour, bytes and latency. The CHANGELOG
  says which basis the default rests on: the held-out measurement, or,
  when a floor holds, that FTS5 stays opt-in for want of evidence rather
  than from a measured loss. The caveats are stated: small sets, questions written by the author's
  tooling, and an ingest by one model in one attempt. These are no claims
  of superiority over other products.

### S4: The MCP adapter as an extra, ~8-10h

- **Packaging.** `mcp = {version = ">=2.3,<3", optional = true}`, extra
  `mcp`, also in the dev group so mypy, coverage and `pip-audit` see it.
  Console script `wiki-studio-mcp = "wiki_studio.mcp_adapter:main"` (D11).
  Without the extra the script prints `pip install 'wiki-studio[mcp]'`
  and exits 2, and `wiki-studio`'s exit codes are untouched.
- **Dependency review** (recorded in ADR-0003, D18):

  | Item | Finding |
  |---|---|
  | Package | `mcp`, the official Python SDK (`modelcontextprotocol/python-sdk`) |
  | License | MIT (wheel METADATA) |
  | Maintenance | 2.0.0 2026-07-28, 2.1.x late August, 2.2.0 2026-09-07, 2.3.0 2026-10-02; the 1.x line is still patched (1.30.0 2026-09-07) |
  | Python | `>=3.10`; covers 3.11-3.13 |
  | Transitive | `anyio`, `httpx2`, `jsonschema`, `mcp-types`, `opentelemetry-api`, `pydantic`, `pyjwt[crypto]` (pulls `cryptography`), `python-multipart`, `sse-starlette`, `starlette`, `typing-extensions`, `typing-inspection`, `uvicorn`; `pywin32` on Windows |
  | Pin | `>=2.3,<3`: the floor is the version reviewed, the ceiling is the next major (2.0 renamed `FastMCP`) |
  | Risk | API churn within 2.x, and a large transitive tree for a stdio server; the adapter only uses `MCPServer`, tool registration and the stdio transport |
  | Controls | `pip-audit` in CI over the dev group; an `mcp-min` job at `mcp==2.3.0` and an `mcp-latest` job at the newest `<3` (the proposal's "tested minimum and current version") |

  The spec phase checks the transitive licences again with the lock file
  and records them in the ADR.
- **Standard-library core, proved twice.**
  - An in-repo test parses every core module with `ast`, excluding
    `wiki_studio/mcp_adapter/`, and fails on any top-level import that is
    not in `sys.stdlib_module_names` and not `wiki_studio`.
  - CI's `build-check` job installs the wheel without extras into a fresh
    virtual environment. It imports every core module under `python -I`,
    asserts that every loaded module is standard library or `wiki_studio`,
    checks that every `Requires-Dist` in the wheel METADATA carries
    `extra == "mcp"`, and checks that importing the adapter fails with
    the install instruction.
- **Server.** `src/wiki_studio/mcp_adapter/` builds on `MCPServer` with
  the stdio transport only (D11). At launch it resolves `--root`,
  `--wiki-dir`, `--proposals-dir`, `--source-root`, `--lock-timeout`,
  `--search-cache`, `--ranker` and `--by`, and the matching
  `WIKI_STUDIO_*` variables, once, through `WikiPaths.resolve`. No tool
  takes a root, directory, backend, actor or escape-hatch argument, so
  an agent cannot retarget the server. Client-advertised MCP roots never
  widen the configured ones. A repeatable `--disable-tool NAME` removes
  a tool from the surface; it can only remove, never add (D12). A host
  that wants promotion to stay human starts the server with
  `--disable-tool promote` (propose-only mode, documented by that name),
  and the agent's proposals wait in the proposals directory for a person
  to `promote` and `approve`.
- **Tools** (the whole surface in 0.8.0, D12). Each tool is one `api`
  call, and all are synchronous, so they run in the SDK's worker thread
  (finding 15).

  | Tool | API call | Notes |
  |---|---|---|
  | `find` | `api.find` | question, optional `max_pages` (at most 5), `max_bytes` and `ranker` (per-call override of the launch default); returns ranker, pages with sha256 and bytes |
  | `read_page` | `api.read_page` | text and sha256; exit-7 and exit-4 errors as in the CLI |
  | `propose` | `api.propose` | edits `{path, action, content, base_sha256?}`, optional `name` (default `mcp-<utc>-<hex>`), rationale; calls `api.propose` with `assign_page_ids=True`, so every create gets a `page_id` as the CLI's `propose --from` does (D20); returns the name and warnings (a `DriftWarning` is captured, not printed) |
  | `promote` | `api.promote` | a proposal **name** resolved under the proposals directory by `propose`'s name rule, and `dry_run`; never `allow_out_of_repo`, `allow_unguarded_updates` or a caller-chosen `entry_point`; the receipt records `entry_point: "mcp"` (an additive value, documented in `docs/patch-set-format.md`); on a wiki with `auto_approve_on_promote` the result carries `approved_paths` and the auto-approval warning (D14) |
  | `lint` | `api.lint` | structural plus audit; `health` and `prose` booleans; never a backend, so the contradiction check cannot run |
  | `info` | `api.info` | plus an `adapter` block: adapter version, SDK version, the negotiated protocol version, the tool list |
  | `findings` | `api.findings` | read-only, model-free |
  | `review_state` | `api.review_state` | read-only, model-free |

  Not exposed, with no flag to add them in 0.8.0: `approve`, `ingest`,
  `query`, `audit-flush`, `init`. `--disable-tool` can narrow this
  surface further; nothing widens it.
- **Actor (D13).** Fixed at launch by `--by` or `WIKI_STUDIO_ACTOR`.
  Tools take no `by`, so an agent cannot record a person's name as the
  proposer or promoter.
- **Auto-approval (D14, owner decision).** The `promote` tool honours the
  wiki's `auto_approve_on_promote` policy and never refuses because of
  it. When the policy approves pages, the tool result carries
  `approved_paths` and a warning that names the policy and says these
  pages were approved by policy as part of this promotion. The approval
  records and the receipt attribute the approval to the server's fixed
  actor (D13), whose `source` is `flag`, `env` or `none`. The server logs
  the policy once at start. On such a wiki an agent's promote approves
  its own proposal (finding 12); that is the host's configured policy,
  and `docs/mcp-adapter.md` and `SECURITY.md` say so.
- **Errors.** Every `wiki-studio` exception becomes a tool error result
  `{error, exit_code, message}` using the existing class-to-code table.
  Anything else becomes a generic error with no traceback. stdout carries
  protocol frames only, and logs go to stderr. A test drives every tool
  through a subprocess and fails on any non-protocol byte on stdout.
- **Docs.** `docs/mcp-adapter.md` covers the tools, the boundary, the
  host configuration for Claude Code (`claude mcp add` or `.mcp.json`) and
  Kiro (`.kiro/settings/mcp.json`), and what the adapter does not do.
  `SECURITY.md` gets one paragraph on the agent surface. ADR-0003 records
  the first optional dependency and the tool contract.

### S5: Conformance suite and a host run, ~6-8h

- **The suite** (`conformance/mcp/`). A runner takes any server command
  (`--server-cmd`), copies a fixture wiki into a temporary root, and
  drives the server through the SDK's client over stdio. It runs once per
  tested protocol version (D17): 2025-06-18 and 2025-11-25 by handshake,
  and 2026-07-28 by the per-request envelope. It is adapter-agnostic, so
  another runtime's adapter can run it too. These are the "conformance
  fixtures" of the launch sequence. Cases:
  1. The server negotiates each tested version, or refuses one cleanly.
  2. `tools/list` is exactly the eight tools. No tool has a root,
     directory, backend, actor or escape-hatch argument. Started with
     `--disable-tool promote`, the list lacks `promote`, a `promote` call
     is an unknown-tool error, and the other seven work unchanged.
  3. `find` returns at most five index-linked pages within the budget
     and names its ranker.
  4. `read_page`'s sha256 equals the sha256 of the file's bytes. An
     absolute path, `../` or a symlink is an exit-7 error.
  5. `propose` writes a proposal and leaves the wiki byte-identical.
     Its create carries a `page_id` of the documented form.
  6. `promote` of that name lands it, with a `committed` receipt and the
     archive.
  7. An `update` carrying `read_page`'s sha256 lands. The same update
     after the page changed is an exit-9 error, and the wiki is unchanged.
  8. `promote` of `../x` or an absolute name is refused.
  9. On a wiki without `auto_approve_on_promote`, after the agent's
     promote, `review_state` of the promoted page is not `approved`.
  10. On a wiki with `auto_approve_on_promote`, the promote succeeds. Its
      result lists the page in `approved_paths` with the auto-approval
      warning, and the approval record's actor is the server's launch
      actor.
  11. `lint` with `health` makes no backend call (the test backend
      counts calls).
  12. stdout is clean.

  CI runs it against `wiki-studio-mcp` in the `mcp-min` and `mcp-latest`
  jobs. It is skipped locally when `mcp` is absent.
- **Trace.** The server takes an opt-in `--trace PATH`, a JSONL file with
  one line per request: method, tool name, negotiated protocol version,
  client name and version, and the outcome code. Page content is never
  traced. This lets the suite check a run it did not drive.
- **Host run (D16).** Claude Code at a pinned version runs headless
  (`claude -p` with `--mcp-config` for the fixture and a fixed scenario
  prompt): find a page, read it, propose an update with its hash, promote
  it, and confirm with `review_state`. The fixture wiki uses the default
  policy, without auto-approval. The suite's `check-host-run` step applies
  cases 2-9 to the trace and the fixture's end state. The run is
  recorded under `conformance/runs/<date>-claude-code-<version>/`, with a
  manifest of the versions, the model, the negotiated protocol and the
  trace, as run 2 was. It is not in CI, because it needs the owner's
  account. For Kiro: the configuration is documented and the same check
  runs if Kiro can run headless; otherwise a recorded manual run. Kiro is
  not exit-blocking.
- **Compatibility.** `docs/compatibility.md` gains an MCP table: adapter
  version, SDK version, protocol version, host and host version, and the
  evidence (CI job or recorded run).

## Exit evidence

| Roadmap item | Where it lands |
|---|---|
| Versioned retrieval results on declared fixtures | S3: `run3/results-untuned.json`, `run3/results.json`, and `heldout/results.json` over the frozen held-out ingest (`heldout/manifest.json`), beside runs 1 and 2, asserted in CI except latency |
| Cache recovery tests | S2's recovery suite, through `api.find` and the CLI |
| One non-memkernel runtime passing the adapter conformance suite | S5: the Claude Code run checked by `check-host-run`; the protocol-level suite in CI is supporting evidence, not a substitute |

Release C closes when all three exist on the 0.8.0 tag. If the circuit
breaker shelves part of it, 0.8.0 may still ship, and Release C stays open
in the roadmap.

## Decisions

D5, D8, D9, D14 and D16 change the build or the evidence materially. They
were put to the owner, who decided them on 2026-10-26: D5 and D16
confirmed, D8 and D14 overruled, and D9 kept as the owner's default. D8a
and D8b are sub-decisions that carry out D8; the owner approved D8b and
approved D8a with a correction (README files only) on 2026-10-27, and
decided D8c on 2026-10-27 after the pitch review. The rest are the pitch's proposals.
They follow from the repository's rules and can be overruled at the spec
review.

- **D1. The cache lives beside the lock file,** outside the wiki and
  keyed to the resolved wiki. `search_index.py` is its only writer.
  *Reason:* the single-writer rule and its scans stay untouched, two
  roots that share one wiki share one cache, and one `.gitignore` pattern
  covers both files. Root-relative `doc_internal/` was rejected because
  the wiki can live outside the root.
- **D2. Freshness by hashing every eligible page on every call;** no mtime
  or stat shortcut. *Reason:* today's selector already reads every linked
  page, so this costs no extra I/O, and it is correct for same-second
  edits, restored mtimes and checkouts.
- **D3. A cache that cannot be used falls back to an in-memory index for
  that call,** with a warning. A corrupt cache is removed and rebuilt.
  *Reason:* `find` and `query` are read verbs that work today without any
  cache. A cache must not make them fail.
- **D4. No new exit code and no error when FTS5 is missing:** fall back
  to index-first, print a notice, and report `ranker` and
  `fallback_reason`. A host that requires ranked discovery checks
  `info.discovery.fts5`.
- **D5 (owner decision, 2026-10-26: confirmed). FTS5 becomes the default
  ranker only if, on the held-out set, it is no worse than index-first at
  hit at 1 and at hit at 5,** and D8b's and D8c's floors hold. Otherwise
  it ships opt-in (`--ranker fts5`, `WIKI_STUDIO_RANKER=fts5`, or the
  server's `--ranker`), and the CHANGELOG says which basis the default
  rests on. *Reason:* it ties the user-visible change to a result that
  tuning could not see. Other tools pick a default by reasoning or by
  reputation, and the field prefers bm25 to plain word overlap, so a
  regression is unlikely in principle; the roadmap still asks for
  retrieval "measured, not asserted", and a one-setting switch lets a
  host follow the field's view without waiting.
- **D6. The budget is in UTF-8 bytes,** over `index.md` plus the selected
  pages, whole pages only, default 65,536. *Reason:* bytes are
  deterministic and model-agnostic with the standard library, while
  tokens would need a tokenizer. The default never binds on the current
  fixtures (finding 9), so it is a ceiling for oversized pages, not a
  tuned value.
- **D7. Pages carrying `superseded_by` are not discovery candidates,** in
  either ranker. They stay readable through `read`. *Reason:* the
  roadmap's claim that a replaced revision does not return as current
  knowledge. The frozen wikis have no superseded page, so their numbers
  do not move.
- **D8 (owner decision, 2026-10-26: overruled the proposed
  code-copilot-team wiki). The held-out corpus is a fresh corpus,
  ingested the way run 2 was:** a model ingest through the real pipeline
  under a frozen protocol. Ingestion coverage applies and is reported.
  The sources, their licence, the ingest backend and model, and the
  pinned versions are recorded in the frozen protocol. The ingest's model
  cost and time are in S3's estimate, the appetite and the circuit
  breaker. The ingested wiki and its manifest are frozen before any
  tuning and never edited afterwards.
- **D8a (owner decision, 2026-10-27, corrected). The sources are the
  user-facing README files of mapatlas** (`github.com/gosha70/mapatlas`,
  Apache-2.0) at commit `7c3a8de609fb8e2173a74a884afdc4029ff18ca5`
  (2026-09-24). That is eight files, 30,554 bytes (about 30.5 KB):
  `README.md`; the `README.md` of `packages/core`, `maplibre`,
  `offline-pmtiles`, `react`, `recorder-web` and `storage-idb`; and
  `apps/demo/README.md`. Excluded: `experiment/rubric.md` and
  `experiment/results.md` (agent-build evaluation records with Claude
  Code, prompt, gate, spec and scoring vocabulary, which would weaken
  the separation from the development corpus), and the contributor and
  agent files (`CLAUDE.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `SECURITY.md`, the PR template). Eight files are still enough for the
  preregistered 35 answerable questions. *Reason:*
  - None of these files is in the development set.
  - The domain differs: a TypeScript map and offline-tiles library,
    against the development set's memory server. That lowers the shared
    vocabulary with both the development corpus and the wiki schema.
  - The licence matches the development corpus, and the owner owns the
    repository, so redistribution and attribution are clear.
  - Eight documents of similar size to run 2's make the ingest cost
    known in advance.

  *Rejected:*
  - memkernel's docs at a later tag: the same project as the
    development set.
  - rlmkit's docs: Apache-2.0, but its subject is in the development
    corpus (ADR-009).
  - wiki-studio's own docs: they share the schema vocabulary and
    describe the system under test.

  Checked at shaping: the repository is public, the commit is on
  `main`, and its `LICENSE` is Apache-2.0.
- **D8b (owner decision, 2026-10-27). A floor for D5.** If fewer than 15
  held-out questions end with a gold page, the held-out result is
  reported as measured but is too thin to change the default, so FTS5
  ships opt-in. The ingest is not retried to reach the floor; a retry
  would be a new, labelled run. *Reason:* a one-attempt ingest can
  promote few documents. Run 1 promoted one of ten. A comparison over a
  handful of questions would pass D5 trivially.
- **D8c (owner decision, 2026-10-27). A page floor for D5.** If the
  frozen held-out wiki has fewer than ten eligible pages, the held-out
  result is reported as measured, with its eligible page count and
  random baseline, but does not change the default, so FTS5 ships
  opt-in. *Reason:* run 2's ingest produced nine content pages, and
  eight README files of similar size will likely produce about as many.
  With a five-page cap over about nine candidates, every ranker loads
  more than half the wiki, hit at 5 mostly measures the cap, and a tie
  is likely; D5 would then pass on a tie that says almost nothing. D8b
  counts questions, not pages, so it does not catch this. The risk is
  accepted: FTS5 may ship opt-in only because the corpus was small, and
  the CHANGELOG says so.
- **D9 (owner's default, 2026-10-26: kept as proposed).** A separate
  agent session that sees only the held-out corpus, not the ranker code
  or the development results, writes the questions. The owner reviews
  them before the freeze. Under D8 the session works from the held-out
  source documents, because the questions are committed before the
  ingest. Gold is then assigned from the frozen ingested wiki, as in
  runs 1 and 2, and the owner reviews it too.
- **D10. SDK pin `mcp>=2.3,<3`,** with floor and latest CI jobs.
- **D11. A separate `wiki-studio-mcp` entry point, stdio only.** *Reason:*
  the `wiki-studio` verb list and exit-code table stay untouched, and both
  target hosts launch stdio servers. HTTP would add authentication and a
  listening port.
- **D12. Default surface: find, read_page, propose, promote, lint, info,
  findings, review_state.** The read-only review tools are exposed: they
  are model-free and reveal only what `read_page` already can, and an
  agent can then see its own curation debt. `approve`, `ingest`, `query`,
  `audit-flush` and `init` are not exposed, and no flag adds them in
  0.8.0. An explicit approval is a human decision, and the other verbs
  spawn a model or reach outside the proposal flow. The one way an
  agent's call leads to an approval is the wiki's own
  `auto_approve_on_promote` policy (D14). A host that wants more calls
  the `api` itself. A host that wants less starts the server with
  `--disable-tool NAME`, which only removes tools: the problem statement
  names distinct proposal and promotion as part of the boundary hosts
  need, and propose-only mode (`--disable-tool promote`) keeps promotion
  human without a second code path.
- **D13. The actor is fixed at launch;** tools take no `by`.
- **D14 (owner decision, 2026-10-26: overruled the proposed refusal).
  MCP `promote` honours the wiki's `auto_approve_on_promote` policy and
  does not refuse.** The tool result carries a clear warning that the
  promotion was auto-approved by policy, with `approved_paths`. The
  receipt and the approval records attribute it to the server's fixed
  actor. There is no `--allow-auto-approve` flag. The risk is stated
  plainly (Rabbit holes, No-gos): on such a wiki, an agent's promote
  approves its own proposal. That is the host's configured policy.
- **D15. `promote` takes a proposal name, never a path, and never the
  escape hatches** (finding 11).
- **D16 (owner decision, 2026-10-26: confirmed). The evidence runtime is
  Claude Code, headless, at a pinned version,** checked through the trace
  and the end state. Kiro is documented and is not exit-blocking.
- **D17. Tested protocol versions: 2025-06-18 and 2025-11-25 (handshake)
  and 2026-07-28 (per-request).** 2024-11-05 and 2025-03-26 are left to
  the SDK. The host run records what each host actually negotiates.
- **D18. ADR-0003** records the first optional dependency, the
  standard-library boundary and the MCP tool contract. The page schema
  does not change, so ADR-0002 is untouched.
- **D19. Core capabilities `ranked-discovery` and `context-budget`, and a
  runtime `discovery` key in `info`.** The adapter is not a core
  capability. It reports itself through its own `info` tool, because the
  core build cannot tell whether the extra is installed where a host
  runs.

- **D20. The MCP `propose` tool assigns `page_id` to creates**
  (`assign_page_ids=True`), as the CLI's `propose --from` and `ingest`
  do. *Reason:* `api.propose` defaults to no, so that memkernel's creates
  land byte for byte until memkernel opts in (ADR-0002); an MCP agent
  has no such bytes-for-bytes contract, and a page without an id is a
  `no-page-id` finding the agent would then see in `findings`.

## Rabbit holes

- **Tuning on 21 questions.** It is easy to fit the development set and
  report a number that does not transfer. *Workaround:* a fixed, small
  set of knobs, the untuned results committed first, the held-out set
  frozen before tuning and run once, and D5 deciding the default from
  the held-out result alone.
- **Clever freshness.** Stat fast paths, mtime windows and racy-file
  rules each look cheap. *Workaround:* D2. Revisit only if S3's latency
  numbers on the held-out wiki show a real cost.
- **SQLite differences between builds.** FTS5 may be missing, Unicode
  tables differ between versions, and bm25 can tie. *Workaround:* a
  probe, ties broken by index position, the SQLite version recorded in
  every result, and CI asserting on its own matrix. The fallback is
  tested by patching the probe, not by building a Python without FTS5.
- **SQLite opens paths itself and follows symlinks.** It cannot take a
  no-follow descriptor the way 0.7.0's readers do. *Workaround:* `lstat`
  the cache path and its parent, refuse symlinks, and fall back to memory.
  The remaining check-then-open window is outside the wiki boundary and
  touches only derived data that never reaches a prompt. That is
  documented in `SECURITY.md`.
- **`MATCH` syntax from user text.** Quotes, `NEAR`, `-` and `*` in a
  question raise or change the query. *Workaround:* tokenize first and
  quote every token, with a test per operator.
- **The frozen stop list.** Changing `_STOPWORDS` for FTS5 fails the
  frozen-fixture test. *Workaround:* a separate constant, if one is
  needed at all.
- **SDK churn and transports.** 2.x has had four minors in ten weeks,
  and HTTP or SSE invite authentication work. *Workaround:* pin below 3,
  floor and latest jobs, stdio only, a thin adapter (one `api` call per
  tool), and no hand-written JSON-RPC.
- **The held-out ingest.** A one-attempt model ingest can promote few
  documents, can fail on the environment (run 1's Stop hook), and invites
  a "just one more" retry. *Workaround:* run 2's procedure. Pin
  everything and record an isolation probe before the first attempt. Make
  one attempt per document, never edit by hand, and report what landed.
  D8b covers a thin result. Only a failure before the first attempt is
  fixed and re-probed.
- **An agent's promote can approve its own proposal.** On a wiki whose
  policy sets `auto_approve_on_promote`, the MCP `promote` tool approves
  the pages it promotes, attributed to the server's actor (D14, owner
  decision). That is the host's configured policy, not a defect, and it
  is not worked around. *Workaround:* say it plainly. The tool's warning,
  `approved_paths`, the server's start-up log line, `docs/mcp-adapter.md`
  and `SECURITY.md` all state it, and conformance case 10 pins it. A host
  that wants human approval leaves the policy off, which is the default.
- **A host run that is not repeatable.** A model drives the host, and
  credentials live with the owner. *Workaround:* one scripted scenario, a
  checker on the trace and the end state rather than on the transcript,
  and pinned versions. A failed attempt is recorded, not hidden.

## No-gos

- No hosted collaboration, new runtime, required vector store or
  embeddings, mandatory semantic judges, prose auto-rewrite or crash-safe
  multi-file transactions (roadmap, by decision).
- No learned ranking, synonyms, query expansion or model reranking in
  discovery.
- No runtime dependency in the core. `mcp` is the only optional one, and
  only behind the extra.
- No new exit code. 0 and 2..11 keep their meaning, and 1 stays fatal
  lint.
- No page schema change. No cache, index or adapter state inside the wiki
  directory.
- No edit to the frozen runs or their stop list.
- No MCP resources, prompts, HTTP or SSE transport, or authentication.
  Tools over stdio only.
- No `approve`, `ingest`, `query`, `audit-flush` or `init` on the MCP
  surface, and no flag to add them in 0.8.0.
- No adapter override of the wiki's approval policy, and no
  `--allow-auto-approve` flag. On a wiki with `auto_approve_on_promote`,
  an agent's promote approves its own proposal. That is the host's
  configured policy (D14), and it is reported, not refused.
- No retry, re-run or hand edit of the held-out ingest once its first
  attempt has started, and no edit of the ingested wiki after it is
  frozen.
- No registry publication. Listing the adapter in registries is a launch
  step after Release C closes.
- Not in this pitch: the memkernel quickstart and the memkernel
  integration measurement (they need memkernel #48), and the standalone
  quickstart of Release B's Docs item. S4's host configuration pages are
  reference documentation, not that quickstart.

## Circuit breaker

Core is the discovery half: S1, S2 and S3. It is standard library only,
it is measured, and it carries two of the three exit-evidence items. If
the cycle runs out, discovery ships alone as 0.8.0 and the adapter is
shelved to a follow-up. The triggers, in order:

1. **End of week 2.** If S1 and S2 are not downhill, stop S4 and S5 and
   open a follow-up issue for the adapter. All effort goes to discovery.
2. **End of week 3.** Tuning does not start before the held-out set is
   frozen: the ingested wiki and its manifest, the questions, the gold
   and the protocol. If it is not frozen by the end of week 3, FTS5 ships
   untuned as an opt-in ranker, index-first stays the default, and the
   development results ship labelled "development set only". A held-out
   ingest that promotes few documents is a finding, not a reason to
   retry. If fewer than 15 held-out questions end with a gold page
   (D8b), or the frozen held-out wiki has fewer than ten eligible pages
   (D8c), the held-out result is reported and FTS5 stays opt-in.
3. **End of week 4.** If S4 is not downhill (the adapter passing S5's
   protocol cases through the SDK client, with the standard-library proof
   green), shelve S4 and S5. 0.8.0 ships discovery alone, no dependency is
   added, and Release C stays open.
4. **End of week 5.** If S4 passes in CI but no host run has passed, ship
   the extra marked as a preview in the README, with the protocol-level
   suite as its evidence. Release C stays open until a recorded host run
   passes.
5. **Never, to save time:** add a core dependency or a third-party import
   in the core; change an exit code; write the cache into the wiki; edit
   a frozen run; retry or hand-edit the held-out ingest, or edit its
   frozen wiki; tune on the held-out set or run it twice; expose
   `approve` or a model-spawning verb by default; weaken or skip a test.

"Exhausted" means six working weeks have passed. A third review round on
one scope is not exhaustion: it is an escalation to the owner, who
chooses a fix session, a cut from the list above, or a hold.

## Bet log

| Date | bet_status | Note |
|------|------------|------|
| 2026-10-26 | shaping | Pitch drafted from wiki-studio #38 (Release C), docs/roadmap.md and the 2026-10-23 product proposal. wiki-studio read at main 0f64c3b; MCP SDK read from the `mcp` 2.3.0 wheel. |
| 2026-10-26 | shaping → shaped | 5 scopes, 6w, one release (0.8.0, owner decision: all of Release C). Core S1-S3 (discovery); S4-S5 (adapter) shelve first. 19 proposed decisions; D5, D8, D9, D14 and D16 to confirm before the bet. New cycle when bet; cycle 02 (Release B) stays building until memkernel #48. |
| 2026-10-26 | shaped (revised) | Owner decisions on the five open items: D5 and D16 confirmed; D8 overruled (the held-out set is a fresh corpus ingested as in run 2 under a frozen protocol, with ingestion coverage reported; proposed sources mapatlas docs at 7c3a8de (D8a) and a 15-gold-question floor for D5 (D8b), both to confirm); D9 kept as the owner's default (questions written from the held-out source documents before the ingest); D14 overruled (MCP promote honours `auto_approve_on_promote` and warns, no `--allow-auto-approve`). S3 now 10-14h; total 36-48h; appetite stays 6w. bet_status unchanged. |
| 2026-10-27 | shaped (revised) | D8b approved. D8a approved with a correction: the held-out sources are the eight user-facing README files of mapatlas at 7c3a8de609fb8e2173a74a884afdc4029ff18ca5 (30,554 bytes); `experiment/rubric.md` and `experiment/results.md` removed. bet_status unchanged. |
| 2026-10-27 | shaped (revised) | PR #50 review. Owner decision D8c: a ten-eligible-page floor for D5, with the random baseline and eligible page count reported beside every hit rate; `WIKI_STUDIO_RANKER` and a server `--ranker` flag set the default ranker; the CHANGELOG states the basis of the default. Fixes: the cache is measured against an in-memory build in S3's latency block; `--disable-tool NAME` (propose-only mode) can remove MCP tools but never add them, with a conformance case; MCP `propose` assigns `page_id` (D20); the non-UTF-8 fix lives in `_read_text_or_empty`, not in the selector. bet_status unchanged. |
| 2026-10-27 | shaped (revised) | PR #50 review, second pass. Finding 4 lists the four callers of `_read_text_or_empty` and what each does after the change; a non-UTF-8 page becomes a structural-lint violation so it is reported once instead of reading as empty everywhere (S1). bet_status unchanged. |
| 2026-10-27 | shaped (revised) | PR #50 review, third pass. `promote` lints the whole staged wiki, so an existing non-UTF-8 page refuses every promote: S1 says so, carries the 0.8.0 upgrade note with the remedy, and adds the blocked-then-fixed promote test. bet_status unchanged. |
| 2026-10-27 | bet | Bet for cycle 03. |
| 2026-10-27 | building | Cycle 03 started; hill chart initialized. |
| 2026-10-30 | shipped | Cycle 03 closed. Shipped in 0.8.0 (2026-10-29): build PR #56, evidence PR #59 (held-out measurement, fts5 default, Claude Code host run), the pin-check fix PR #57 the evidence run needed, release fixes PR #58, #60, #61; Release C closed with the tag. All five scopes done; the hill was not updated during the cycle (auto-build driver), set to done at close. |
