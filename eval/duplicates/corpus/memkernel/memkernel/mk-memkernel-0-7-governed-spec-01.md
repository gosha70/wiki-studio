---
page_type: decision
slug: mk-memkernel-0-7-governed-spec-01
title: 'One setting picks the wiki mode: `MEMKERNEL_WIKI_MODE` = `auto` (default) | `governed` | `ungated`'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-governed/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

**`auto`** is today's behavior, unchanged: the gate and the governed import when wiki-studio >= 0.7.0 is
installed, the direct writer and the file-reading import when it is absent, a refusal when it is installed but
broken or too old.
**`governed`** requires, before any write or read of pages, for both `wiki_export` and `wiki_import`:
wiki-studio >= 0.7.0 installed and working (`gate_available()` returns the API);
`api.info`'s `capabilities` include every capability the bridge uses, a named constant
(`GOVERNED_CAPABILITIES`): `wiki-lock`, `receipts`, `root-manifest`, `page-id` (G5), `approval-record`,
`superseded-by`, `findings`. A missing one refuses, naming it; the constant changes only with the wiki-studio
floor;
the wiki's manifest `mode` is `governed` (policy `approval_required: true`). A `managed` wiki (a manifest,
default policy) and a `legacy` one (no manifest) are refused, with the remedy (`wiki-studio init`, then set
`approval_required: true` in the manifest's policy);
no schema drift (`api.info`'s `warnings` empty), which wiki-studio would refuse later anyway.

These checks are the **governed preflight**, one function both directions and the curation debt (G2) call.
Any failure: the export reports `gate_error` and commits no drafted page (the preflight runs before
`api.init`, so a preflight refusal writes nothing at all); the import reports `import_error` and writes nothing
to the memory store or the sync ledger.
**What a gate failure after the preflight leaves.** The gated export runs `api.init` before `propose` when
`index.md` or `log.md` is missing (memkernel-0-6 FR-002), and memkernel keeps no outer rollback (memkernel-0-6
FR-001). So a rejection after that point commits no drafted page but may leave the scaffold `index.md` and
`log.md` that `init` created. The README says so. The direct writer is never used, so `update_index=False` is refused too.
**`ungated`** never loads wiki-studio: no `load_studio`, gate, lint, review state or findings call, whatever
is installed. The direct export today calls `lint_wiki` after writing, which loads wiki-studio; in `ungated`
mode it is skipped, and `lint` is reported as `null` with `lint_hint` naming the mode.
Every `wiki_export` and `wiki_import` response gains `"mode"`, the path that ran (`gated` through
wiki-studio's gate and review state, `ungated` around it), and `"configured_mode"`, the setting
(`auto`, `governed`, `ungated`). `gated` is not wiki-studio's `governed` wiki mode: in `auto`, a `managed` wiki
goes through the gate as today, and the strict preflight applies only when `configured_mode` is `governed`.
**Rejected:** a per-call argument. The mode is a property of the deployment, set where the MCP server or the
library is configured; an agent that calls the tools could otherwise pass `ungated` around the gate. An agent
that can change the server's environment is outside this boundary, as for every other setting.
