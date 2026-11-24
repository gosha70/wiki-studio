---
page_type: decision
slug: mk-memkernel-0-7-wiring-spool-spec-01
title: 'The wiring check runs both paths'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-wiring-spool/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

A new `--wiki-path` option:
**`governed`:** after `wiki_export` in the source namespace, the check curates the exported page as a curator
would, with wiki-studio, through the server's interpreter:
promote an `update` patch-set setting `status: draft` to `status: stable`, with the page's base sha256.
`approve` refuses a draft (wiki-studio's `promoter.py`, its approve checks).
approve the page (`<python> -m wiki_studio --root … --wiki-dir … approve <page> --by wiring-check`).

The transfer then carries the wiki, including its manifest and approval records. In the destination,
`wiki_import` must report the page as imported, governed.
**`ungoverned`:** the server runs with wiki-studio hidden: a stub `wiki_studio` package, first on the server's
`PYTHONPATH`, raises `ModuleNotFoundError(name="wiki_studio")`, the only error memkernel treats as absence. This
needs no product setting. Release B part 2c's governed and ungoverned modes are a separate spec. The import must
report `"governed": false` and the page imported.
**`both`:** runs the two legs in fresh namespaces, one after the other. Each step's name is prefixed with its
leg, and the check passes only when both pass.
**`auto` (the default):** `governed` when the server's interpreter has wiki-studio 0.7.0 or later, else
`ungoverned`. So the image's run keeps today's meaning, and a dev-venv run takes the governed path.
The report names the path(s) it ran.
