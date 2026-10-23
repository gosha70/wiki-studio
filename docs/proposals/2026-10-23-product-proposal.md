<!-- Owner's product proposal of 23 October 2026, converted from Wiki_Studio_Product_Proposal.docx. The research record behind docs/roadmap.md and specs/wiki-studio-0-6-0/. Kept verbatim; later decisions live in the roadmap. -->

# Wiki Studio product proposal (23 October 2026)

23 October 2026 · Proposed roadmap · Code baselines Wiki Studio 41cfe54 and MemKernel 2d41062

# Product decision

Build Wiki Studio as an independent, embeddable curation engine for project knowledge used by AI agents. MemKernel is the flagship composition. The Python API, CLI, Markdown format, and evaluation suite must remain useful without MemKernel.

The product should help teams control which agent-generated decisions, conventions, and procedures become durable knowledge, explain why each revision was accepted, and ensure that corrections reach future sessions. Its competitive claim should be demonstrated through that complete workflow.

Start with engineers maintaining coding-agent harnesses and small teams sharing project knowledge. Their immediate problem is an agent reusing an obsolete decision or unreviewed draft. They need a reviewable change, an enforceable acceptance policy, and reliable withdrawal of the old version.

## The adoption experience

A developer connects an agent, proposes a change, reviews its diff and validation results, accepts it under the configured policy, and verifies retrieval in a later session. An example repository must also demonstrate rejection of a stale edit and withdrawal of a superseded decision.

## Product boundaries

| **Component** | **Primary responsibility**                                                             | **Independent adoption path**                  |
|---------------|----------------------------------------------------------------------------------------|------------------------------------------------|
| Wiki Studio   | Page schema, proposals, validation, promotion, revision evidence, standalone discovery | Python API and CLI; optional MCP adapter later |
| MemKernel     | Runtime retention, code-aware recall, lifecycle, harness integration                   | Existing memory server and in-process API      |
| Bridge        | Identity mapping, approval metadata, synchronization and withdrawal                    | Small adapter with published conformance tests |
| Harness       | Agent execution, tool permissions, review authority and user interaction               | Claude Code, Kiro, CCT or another runtime      |

The existing consumer guide and MemKernel integration already establish much of this separation. The bridge is implemented; the guarantees around it need strengthening. [\[S1\]](https://github.com/gosha70/wiki-studio/blob/41cfe5433a1e2097d615eb62ffbe4b8ace18ee24/docs/consumers.md) [\[S2\]](https://github.com/gosha70/memkernel/blob/2d410624e482f97a2439fc5d4eee0db97e41048d/docs/adr/ADR-010-wiki-studio-as-wiki-maintainer.md)

## Investment rule

Prioritize correctness, integration effort and measured user value. Keep the core free of third-party runtime dependencies; let the host agent draft and synthesize. Ship the safety patch before new contracts and broad integrations. Hosted collaboration, a new runtime, a vector store and mandatory semantic judges are outside the initial scope.

# Competitive position

Markdown storage, MCP, provenance, and memory lifecycle are already established capabilities. Wiki Studio should compete on a portable workflow for accepting and correcting durable project knowledge. That is a product hypothesis to validate, not a claim that competitors lack governance.

| **Approach**     | **Documented strength**                                                                                      | **Where Wiki Studio should compete or compose**                                                                                                                                                                                                   |
|------------------|--------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Basic Memory     | Markdown as the source of truth, a derived index, MCP and file synchronization; semantic search is available | Offer explicit proposal review, revision preconditions and policy-controlled promotion for engineering knowledge. A future adapter must preserve its format and synchronization rules. [\[S7\]](https://github.com/basicmachines-co/basic-memory) |
| Mem0             | Memory extraction and retrieval, updates, history and expiration; hosted and self-managed options            | Supply reviewed project decisions and procedures as approved inputs. Compare the governed workflow separately from general conversational memory. [\[S8\]](https://docs.mem0.ai/platform/platform-vs-oss)                                         |
| Graphiti and Zep | Graphiti provides temporal facts and source lineage; Zep adds managed enterprise context and governance      | Integrate approved artifacts with temporal retrieval. Do not claim novelty for supersession, provenance or governance itself. [\[S9\]](https://github.com/getzep/graphiti)                                                                        |
| Letta            | Agent memory in a Git-backed filesystem with ordinary file operations                                        | Provide an optional acceptance workflow for shared project knowledge. Git history alone is not Wiki Studio's differentiation. [\[S10\]](https://docs.letta.com/concepts/memfs)                                                                    |
| LangMem          | Extraction, consolidation and memory management primitives with storage integrations                         | Validate and curate generated durable artifacts while the host owns memory processing and storage. [\[S11\]](https://langchain-ai.github.io/langmem/)                                                                                             |

This comparison uses current primary documentation. It is not a comparative performance benchmark, and it does not assert that any proposed adapter already exists.

## The advantage to earn

Make the following workflow easy to adopt and easy to inspect: an agent proposes a change; policy determines whether it may land; concurrent changes are preserved; the accepted revision carries evidence; replacing it prevents the obsolete version from returning as current knowledge.

The durable advantage would be the combination of a stable contract, useful policy checks, reproducible failure tests, reliable adapters, and low integration cost. A collection of features can be copied. A small component that repeatedly passes another team's integration and recovery tests is harder to replace casually.

## Positioning

**Wiki Studio:** Reviewable project knowledge for AI agents, with validated proposals, controlled promotion and revision history.

**Flagship composition:** MemKernel retains and retrieves memory. Wiki Studio curates the durable project knowledge it uses.

Use “trustworthy” as the intended outcome of the workflow. Public technical claims should name demonstrated guarantees. Avoid “best in class,” “rejects all bad pages,” “atomic” without qualification, and assertions that the rest of the market has not addressed governance.

# Replaceable components and contracts

The diagram shows the proposed workflow. Approval enforcement and withdrawal propagation still require implementation.

<img src="docs/proposals/2026-10-23-product-proposal/media/image1.png" style="width:6.7in;height:3.29417in" alt="Proposed curation loop. The agent uses runtime memory and a replaceable adapter. Wiki Studio validates proposals and publishes approved Markdown, which the adapter imports or withdraws from runtime memory." />

Standalone agents use Wiki Studio's CLI or API. MemKernel users retrieve through MemKernel. Other runtimes implement the same adapter contract.

## A versioned knowledge contract

Expose schema identity and version, proposal and audit format versions, and capabilities through the information API and CLI. Initialization persists the selected schema in a root manifest. Include a fingerprint for project-local schemas; the package version cannot identify customized rules.

Adapters check supported capabilities and versions. Incompatible formats fail with migration guidance. Document tested package pairs and how to re-create legacy proposals without revision preconditions. Publish this contract before adding supersession fields.

## Identity and evidence

Accepted revisions identify the wiki, stable page ID, content hash, source revisions, proposal, policy, decision, proposer, promoter and timestamp. Record the approver separately when required. Renames preserve knowledge identity.

An actor flag such as --by supplies attribution, not authentication. Record the identity source; the host supplies authority. Local audit files provide traceability, not tamper-proof evidence.

## Retention and review are separate

Keep review state independent of memory tier. Governed adapters expose approved project knowledge by default and label requested drafts or historical material. Operational memories and code snapshots retain their own policies.

Bind approval to the revision and policy; manual edits require revalidation. Enforcement applies to participating APIs, imports and host permissions. Direct filesystem access remains possible; the core is not an operating-system sandbox.

# Release A Safe changes

**Owner:** Wiki Studio, with coordinated MemKernel changes where its outer writer participates. **Release condition:** the reproduced failures become regression tests and pass through both entry points. Release this patch before schema expansion or promotion campaigns.

## Correctness work

1\. Commit only paths named by the patch-set and the required audit artifacts. Serialize cooperating writers using a lock keyed to the canonical wiki location. Include shared index and log appends; do not key the lock to a configurable proposals directory.

2\. Require the revision used to draft each replacement. Capture that hash when the page is read and carry it through proposal creation. Compare it under the lock immediately before committing. Creation requires absence; stale replacements return a conflict without mutation.

3\. Apply containment consistently to page writes, candidate reads and proposal preview reads, including symlinked parent paths. Wiki pages must remain inside the wiki. Legitimate source citations may resolve inside the configured project or an explicitly allowed source root; do not reject every source link outside the wiki directory.

4\. Verify that each cited fragment occurs in the permitted cited revision and that a substantive generated answer includes evidence or a structured abstention. Document that quotation checks do not establish logical support. Describe the fact-change checker as a heuristic, including its negation limitation.

5\. Coordinate audit-log writes and MemKernel's scaffolding and rollback. The current outer whole-wiki snapshot can undo another writer's successful changes. Remove that compatibility workaround when the dependency floor permits, or hold the same wiki lock across its complete lifecycle. [\[S3\]](https://github.com/gosha70/memkernel/blob/2d410624e482f97a2439fc5d4eee0db97e41048d/src/memkernel/wiki/sync.py) [\[S4\]](https://github.com/gosha70/wiki-studio/blob/41cfe5433a1e2097d615eb62ffbe4b8ace18ee24/src/wiki_studio/promoter.py) [\[S15\]](https://github.com/gosha70/wiki-studio/blob/41cfe5433a1e2097d615eb62ffbe4b8ace18ee24/src/wiki_studio/audit.py)

## Acceptance cases

The regression suite must cover disjoint concurrent edits, conflicting edits to one page, concurrent creation of one path, shared index and log appends, simultaneous audit records, stale drafting before proposal creation, symlink escapes, forged citations, and failure during commit. Exercise separate proposal directories against one wiki, plus direct Wiki Studio and MemKernel callers.

Document the supported filesystem and process model. A local file lock is not a claim of distributed coordination across machines or network filesystems. External editors that bypass the protocol require revision validation before their content is accepted.

## Honest guarantees

Describe the initial implementation as validation, conflict detection, serialized managed writes and exception rollback. It does not provide crash-safe multi-file transactions or consistent snapshots to uncoordinated readers. Recovery failures must be visible. A later durability design should be justified by deployment needs and verified with fault injection.

Existing checks and tests provide a useful base, but their passing does not invalidate the reproduced defects. Preserve the current navigation results as historical evidence; correctness claims require separate failure tests. [\[S3\]](https://github.com/gosha70/memkernel/blob/2d410624e482f97a2439fc5d4eee0db97e41048d/src/memkernel/wiki/sync.py) [\[S5\]](https://github.com/gosha70/wiki-studio/blob/41cfe5433a1e2097d615eb62ffbe4b8ace18ee24/README.md)

# Release B Governed curation

**Owner:** Wiki Studio contract and MemKernel adapter. **Dependency:** Release A. **Release condition:** one complete correction loop passes on clean installs with compatible versions and survives retries.

## Require the governed path explicitly

MemKernel already uses the gate when a compatible Wiki Studio installation is available. The additional work is a governed configuration that requires it, refuses unchecked fallback, and prevents bypass through alternate writer options. Keep a clearly identified ungated mode for independent MemKernel deployments. [\[S2\]](https://github.com/gosha70/memkernel/blob/2d410624e482f97a2439fc5d4eee0db97e41048d/docs/adr/ADR-010-wiki-studio-as-wiki-maintainer.md) [\[S3\]](https://github.com/gosha70/memkernel/blob/2d410624e482f97a2439fc5d4eee0db97e41048d/src/memkernel/wiki/sync.py)

Separate creating a valid draft from accepting it as current project knowledge. The policy may permit automatic acceptance for specified changes; it need not demand a human for every operation. Permission must come from the host configuration and policy, not from the model declaring its own approval.

## Close the round trip

The current importer accepts drafts and skips deprecated pages without withdrawing their previously imported memories. Deleting a page also leaves its prior imported memory untouched. The bridge must reconcile these states. [\[S3\]](https://github.com/gosha70/memkernel/blob/2d410624e482f97a2439fc5d4eee0db97e41048d/src/memkernel/wiki/sync.py)

Use stable page identity and revision hashes to import accepted content idempotently. Supersession, deprecation and explicit deletion must withdraw or mark the earlier projection so it cannot appear as current approved knowledge. Distinguish an intentional deletion from a temporarily unavailable directory; never infer mass withdrawal from a failed scan.

Record durable synchronization work after promotion and report pending, applied or failed synchronization. Replaying a receipt must not duplicate memories. A successful wiki update followed by a failed store update needs a visible pending state and a retry path. Do not advertise a transaction spanning Markdown and the memory database.

When an approved page corrects an originating raw memory, retain its provenance but prevent that obsolete source from competing as the current authoritative answer. Multi-source pages require an explicit mapping rather than blindly superseding every source memory.

## Make curation affordable

MemKernel should report curation debt at session start: useful candidates without pages, stale approved sources, conflicts and pending synchronization. Batch a bounded number of candidates so curation does not interrupt every interaction. Wiki Studio should expose findings without a model call; the host decides when synthesis or review is useful.

Track source content hashes for freshness; retain Git revision metadata when available. A recorded commit alone does not detect uncommitted source edits. Establish stable page keys and supersession semantics through a contract decision before adding advanced freshness tiers.

## Two tested quickstarts

Publish a standalone shell-agent example and a MemKernel composition, each with Claude Code and Kiro instructions where applicable. Both should demonstrate proposal, validation, review, promotion and reading. The composition adds retain, export, governed import, correction and next-session recall. Run lint before acceptance; post-import lint is not a substitute for the acceptance gate.

# Release C Standalone usefulness and broader adoption

**Owner:** Wiki Studio. **Dependency:** stable shared API. **Release condition:** standalone quality improves on declared fixtures, and the adapter can be replaced without changing the core.

## Improve discovery with SQLite FTS5

Keep Markdown authoritative and index only eligible pages from the validated navigation structure. Use FTS5 ranking while preserving the index-first workflow and five-page cap; add a byte or token budget because five pages can still be large. Treat the index as a rebuildable cache.

Detect manual edits, Git checkouts, renames and deletions with a content manifest or equivalent mechanism. Test stale-index recovery. Probe FTS5 availability at runtime: Python's SQLite interface does not guarantee every linked SQLite build includes the extension. Provide a documented fallback or clear unsupported-runtime message. [\[S12\]](https://www.sqlite.org/fts5.html)

Retain the original evaluation output and save versioned new results. The published questions are now a development and regression set. Add a held-out corpus and freeze its protocol before final tuning. Report counts, unanswerable-query behavior, ingestion coverage, context size and latency alongside retrieval hit rates. The existing 3/21 hit-at-one result is a baseline, not a general market comparison. [\[S5\]](https://github.com/gosha70/wiki-studio/blob/41cfe5433a1e2097d615eb62ffbe4b8ace18ee24/README.md)

## Add an optional MCP adapter

Expose discovery, page reading with revision hashes, proposals, promotion, lint and information through the same validated API. Keep proposal and promotion distinct operations; auto-promotion is a configured policy. Bind the server to configured roots and keep model-spawning verbs off the default surface.

Prefer an optional package or extra using the official MCP SDK while preserving the standard-library core. A hand-written JSON-RPC loop is only part of MCP; maintaining protocol behavior and client compatibility is ongoing work. Test supported protocol versions and target hosts. A fully dependency-free adapter is reasonable only if its maintenance cost is explicitly accepted. [\[S13\]](https://modelcontextprotocol.io/docs/2026-07-28/sdk)

## Keep delivery small

| **Increment**          | **Accountable component**                     | **Exit evidence**                                                  |
|------------------------|-----------------------------------------------|--------------------------------------------------------------------|
| A Correctness patch    | Wiki Studio plus MemKernel writer integration | Reproductions and mixed-writer tests pass; guarantees corrected    |
| B Governed composition | Shared contract and bridge                    | Draft exclusion, revision binding, withdrawal and retry tests pass |
| C Standalone discovery | Wiki Studio                                   | Versioned retrieval results and cache recovery tests               |
| C Runtime portability  | Optional adapter                              | One non-MemKernel integration passes the same conformance suite    |

Use small changes grouped by failure mode. Extend existing APIs and fixtures before adding frameworks. Keep a tested minimum dependency version and a current-version job. Do not delay the safety patch for actor metadata, new schemas, search, branding or MCP. Calendar estimates should follow issue decomposition; these are release criteria, not delivery promises.

# Evidence and launch

Run correctness tests during every release. Start integration measurements with Release B; do not postpone evidence until after broad distribution.

## Measure the complete workflow

The primary comparison should hold agent, model, task set and MemKernel retrieval configuration constant while varying the curation workflow. Include MemKernel alone, MemKernel with governed Wiki Studio, and a files-plus-grep control. Use a separate standalone comparison for Wiki Studio discovery.

The existing frozen Wiki Studio arm tests a CLI treatment; it does not isolate the incremental value of governance inside MemKernel. Preserve its pinned 0.4.1 historical run. Create a separately versioned experiment for the hardened composition. [\[S6\]](https://github.com/gosha70/memkernel/blob/2d410624e482f97a2439fc5d4eee0db97e41048d/eval/lifecycle-suite/arms/wiki_studio/config.frozen.json)

| **Question**                          | **Measurement**                                                             |
|---------------------------------------|-----------------------------------------------------------------------------|
| Does governance improve task outcomes | Paired task success and failure categories across sessions                  |
| Do corrections reach the agent        | Obsolete-answer rate after replacement, deprecation and deletion            |
| Can changes be explained              | Fraction of accepted revisions with resolvable source and decision evidence |
| Does failure recovery work            | Lost updates, duplicates and unreconciled revisions under controlled faults |
| What does curation cost               | Model calls, input and output tokens, wall time, review time and queue age  |
| Can others adopt it                   | Time to first accepted revision and corrected recall on a clean install     |

Use executable task checkers where possible. For judgment-dependent outcomes, publish the rubric and blinded review procedure. Freeze evaluation sets, budgets and analysis before measured runs. Report uncertainty, negative controls, failures and full version identifiers. Safety regressions are release blockers; broad accuracy or cost superiority requires evidence rather than a small-fixture percentage.

## Launch sequence

After Release A, publish the patch and precise guarantees. Handle path-escape reports privately until fixes are available, following the repository's security policy, then publish credited advisories and regression evidence. Ordinary correctness defects can use public issues. [\[S14\]](https://github.com/gosha70/wiki-studio/blob/41cfe5433a1e2097d615eb62ffbe4b8ace18ee24/SECURITY.md)

After Release B, publish the two quickstarts, a compatibility matrix and a short demonstration: an obsolete decision is recalled, corrected through a reviewed proposal, imported, and absent from the next session's current knowledge. Show the revision and receipt alongside the answer.

Recruit a small pilot cohort spanning standalone use, MemKernel and one external runtime. A proposed initial target is three teams, each completing a correction loop on its own project and repeating it across sessions. Treat this as a validation target, not evidence of demand already obtained.

After Release C, publish conformance fixtures and measured results, then distribute the optional adapter through relevant registries. Build further adapters in response to repeat use. Expansion should follow observed setup failures, curation effort and correction reliability rather than a feature-count race.

# Evidence register

Repository baselines were checked on 23 October 2026. Wiki Studio remained at 41cfe5433a1e2097d615eb62ffbe4b8ace18ee24; MemKernel remained at 2d410624e482f97a2439fc5d4eee0db97e41048d. Recommendations describe proposed behavior unless explicitly identified as current.

The preceding review reproduced Wiki Studio failure cases. MemKernel importer and rollback findings were checked with isolated probes of the source using a fake memory service. Those probes are not a full storage, concurrency, security or production audit. Competitor descriptions below come from primary documentation; no cross-product benchmark was run for this proposal.

- [\[S1\]](https://github.com/gosha70/wiki-studio/blob/41cfe5433a1e2097d615eb62ffbe4b8ace18ee24/docs/consumers.md) Wiki Studio consumer guide — existing integration and independent consumers.

- [\[S2\]](https://github.com/gosha70/memkernel/blob/2d410624e482f97a2439fc5d4eee0db97e41048d/docs/adr/ADR-010-wiki-studio-as-wiki-maintainer.md) MemKernel ADR 010 — optional integration, ownership boundaries and compatibility history.

- [\[S3\]](https://github.com/gosha70/memkernel/blob/2d410624e482f97a2439fc5d4eee0db97e41048d/src/memkernel/wiki/sync.py) MemKernel wiki bridge — export paths, outer rollback and import behavior.

- [\[S4\]](https://github.com/gosha70/wiki-studio/blob/41cfe5433a1e2097d615eb62ffbe4b8ace18ee24/src/wiki_studio/promoter.py) Wiki Studio promotion implementation — staging, write scope and rollback.

- [\[S5\]](https://github.com/gosha70/wiki-studio/blob/41cfe5433a1e2097d615eb62ffbe4b8ace18ee24/README.md) Wiki Studio README — published navigation evaluation and its limitations.

- [\[S6\]](https://github.com/gosha70/memkernel/blob/2d410624e482f97a2439fc5d4eee0db97e41048d/eval/lifecycle-suite/arms/wiki_studio/config.frozen.json) MemKernel frozen Wiki Studio arm — treatment, persistence and package pin.

- [\[S7\]](https://github.com/basicmachines-co/basic-memory) Basic Memory technical documentation and repository — Markdown, indexing, MCP and semantic search.

- [\[S8\]](https://docs.mem0.ai/platform/platform-vs-oss) Mem0 platform and open-source comparison — memory operations, history and expiration.

- [\[S9\]](https://github.com/getzep/graphiti) Graphiti repository — temporal graph capabilities and distinction from managed Zep.

- [\[S10\]](https://docs.letta.com/concepts/memfs) Letta MemFS documentation — Git-backed agent memory.

- [\[S11\]](https://langchain-ai.github.io/langmem/) LangMem introduction — memory processing and storage integration.

- [\[S12\]](https://www.sqlite.org/fts5.html) SQLite FTS5 documentation — indexing, rebuild behavior and build availability.

- [\[S13\]](https://modelcontextprotocol.io/docs/2026-07-28/sdk) Official MCP SDK documentation — supported server and client implementation paths.

- [\[S14\]](https://github.com/gosha70/wiki-studio/blob/41cfe5433a1e2097d615eb62ffbe4b8ace18ee24/SECURITY.md) Wiki Studio security policy — vulnerability reporting and supported releases.

- [\[S15\]](https://github.com/gosha70/wiki-studio/blob/41cfe5433a1e2097d615eb62ffbe4b8ace18ee24/src/wiki_studio/audit.py) Wiki Studio ingest audit writer — log update implementation.
