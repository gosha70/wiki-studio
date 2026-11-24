---
page_type: decision
slug: mk-memkernel-0-13-one-store-across-tools-spec-05
title: 'Codex''s cap: `--max-chars 6000`'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-13-one-store-across-tools/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

**The cap:** about 2,500 tokens by default per model-visible hook message.
**The arithmetic:** at about 4 characters per token that is about 10,000 characters, but code-heavy text runs
nearer 3, about 7,500. The block holds code and paths, so 8,000 could pass the cap.
**Over the cap,** Codex saves the output to a file and shows a head-and-tail preview (its hooks docs), so it
cuts the output, not drops it. Even so, a cut that removes the middle of the block loses the context section.
**6,000,** a 20% margin under the code-heavy estimate. It changes nothing in Codex's own settings.
