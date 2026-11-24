---
page_type: decision
slug: mk-memkernel-0-8-untrusted-memory-spec-02
title: 'The delimiter: named tags'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-8-untrusted-memory/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

Each piece of stored text sits inside a `<stored-memory>` element, written as a
literal tag in the markdown block:

```
<stored-memory kind="checkpoint" ref_id="…">
…the checkpoint's text…
</stored-memory>
```

A list item becomes `- [decision] <stored-memory ref_id="…">…preview…</stored-memory>`, on one line.
**Only the tag itself is escaped** (the owner's amendments). Any opening or closing tag inside the stored text is
neutralised before wrapping:
matched in any case: `<Stored-Memory`, `</STORED-MEMORY`;
with whitespace after `<` or after `/`: `< stored-memory`, `</ stored-memory>`, `< / stored-memory`.

The match is the pattern `<\s*/?\s*stored-memory`, case-insensitive. The match's `<` becomes `&lt;`. Every other `<` in stored text is left exactly as it is. So stored text can never close or open
a block, and that replacement is the only change made to stored text.
The block is read as raw text, never entity-decoded, so `&lt;` stays inert. Stored text that already contains
`&lt;stored-memory` is left as it is: it opens nothing.
The attributes come only from memkernel:
`kind` is one of a fixed set: `checkpoint`, `context`, `candidate`, `review`, `debt`;
`ref_id` is memkernel's own record key.

No attribute value is taken from stored text.
The tag name, the kinds, the escape and the notice are constants in `lifecycle.py`, imported by the tests.
**Rejected:** markdown code fences. A fence that is longer than any backtick run inside the content is also
escape-proof, but it hides the `ref_id` inside, or loses it to a separate line, and it renders the checkpoint as
code. Anthropic's prompting guidance recommends XML-style tags for separating data from instructions.
