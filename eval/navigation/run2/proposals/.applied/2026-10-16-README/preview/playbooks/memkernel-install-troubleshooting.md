---
page_type: playbook
slug: memkernel-install-troubleshooting
title: MemKernel install troubleshooting
status: draft
last_reviewed: 2026-10-16
sources:
  - path: eval/navigation/corpus/README.md
    sha: 8b7f14d
---

# MemKernel install troubleshooting

## Symptom

One of the following happens:

- `pipx install memkernel` reports "No matching distribution found", or pip reports "from versions: none".
- The shell prints `No such file or directory` for an old `memkernel` path after a reinstall.
- `memkernel --help` hangs.
- The first MCP connection is slow or times out.
- Another tool, such as `langchain-chroma`, breaks after a global pip install.

## Recovery steps

1. **No matching distribution**: the installing interpreter is outside 3.11–3.13. Pass a supported one explicitly, for example `pipx install --python /opt/homebrew/opt/python@3.11/bin/python3.11 memkernel`.
2. **Stale path after a reinstall**: the shell has cached the old location. Run `hash -r` (bash) or `rehash` (zsh), then `which memkernel`.
3. **`--help` hangs**: versions before 0.4.0 had no flags and started the server instead. Press Ctrl-C and upgrade; from 0.4.0 on, `--help` and `--version` print and exit.
4. **Slow first connection**: the server is downloading the embedding model at startup. Wait for it to finish once, or pre-warm the cache in the same environment with `python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"`.
5. **A global pip install broke another tool**: uninstall memkernel from that interpreter, reinstall the versions the other tool needs (for example `chromadb < 0.6`), then install memkernel with pipx.

## Verification

`which memkernel` resolves to the pipx-managed binary, `memkernel --version` prints and exits, the MCP client connects without timing out, and the previously broken tool imports cleanly again.

## Prevention

- Always install MemKernel with pipx or into a project virtual environment, never into Homebrew's or the system's `python3`.
- Put the absolute command path in the MCP config, because Claude Code may not see PATH changes made in your shell profile.
- Pre-warm the embedding model on new machines before the first connection.

## Related

- [Register MemKernel with Claude Code](../workflows/memkernel-claude-code-setup.md)
