---
page_type: decision
slug: mk-memkernel-0-9-mcp2-spec-01
title: 'Range'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-9-mcp2/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

hard move to `mcp>=2.3,<3`. It is the only range that co-installs with `wiki-studio[mcp]`
(`>=2.3`), and hosts are unaffected because the wire protocol versions are the same. Not a range spanning both
majors.
