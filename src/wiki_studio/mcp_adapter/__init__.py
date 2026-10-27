# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wiki_studio.mcp_adapter — ``wiki-studio-mcp``, the optional MCP server over stdio (0.8.0, FR-031..FR-041).

The adapter is the one place the package may import the ``mcp`` SDK, and only
behind the ``mcp`` extra (``pip install 'wiki-studio[mcp]'``). Importing this
package needs nothing outside the standard library; :func:`main` imports the
server module, which imports ``mcp``, and without the extra prints the install
instruction and exits 2. The core package never imports this one.
"""

from __future__ import annotations

import sys

INSTALL_INSTRUCTION = "wiki-studio-mcp needs the mcp extra: pip install 'wiki-studio[mcp]'"
# A launch that cannot start (no extra, a bad flag, an unknown --disable-tool, an unusable --trace).
EXIT_LAUNCH_ERROR = 2


def main(argv: list[str] | None = None) -> int:
    """Console entry point of ``wiki-studio-mcp``: start the stdio server, or exit 2 when it cannot start."""
    try:
        from .server import serve
    except ImportError as exc:
        if str(exc) != INSTALL_INSTRUCTION:
            raise
        print(INSTALL_INSTRUCTION, file=sys.stderr)
        return EXIT_LAUNCH_ERROR
    return serve(sys.argv[1:] if argv is None else list(argv))
