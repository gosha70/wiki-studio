---
page_type: decision
slug: mk-memkernel-0-7-wiki-scope-spec-02
title: 'A wiki''s identity: two tags'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-wiki-scope/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

**The tags.** Every memory the import retains, or finds already current, carries:
`wiki-path:<hash>`: the sha256 of the wiki directory's path relative to the project root, which the ledger
already uses as its fallback key. It is the wiki's **current** path: a move replaces it (S6);
`wiki-id:<uuid>`: the manifest's `wiki_id`, when the wiki has a manifest.
**Membership.** A memory belongs to this wiki when:
it carries a `wiki-id:` and that id is this wiki's id; or
it is path-only, this wiki has no manifest, and the path is this wiki's.

Nothing else belongs, in particular no legacy memory (S4) and no path-only memory once the wiki has a
manifest (S6, manifest added).
**Both paths derive the id the same way.** The governed import reads it through `api.info`. The ungoverned
import reads `<wiki>/.wiki-studio.json` itself and validates the **identity fields** as wiki-studio's
`parse_manifest` does:
opened without following symlinks, and a regular file;
a UTF-8 JSON object;
`manifest_version` a positive integer no newer than 1;
`wiki_id` a UUID string.

A manifest that fails any of these stops either import with `import_error`.
**Contract fields** (schema, fingerprint, policy, `created_by`) are enforced only on the governed path, where
wiki-studio is installed. They don't affect identity, so the two paths cannot derive different identities for a
valid manifest.
**Rejected:** B (project-relative `source`) changes an existing field's meaning and needs a path migration. C
(scope by the ledger only) never matches legacy memories, and the ungoverned import has no ledger.
