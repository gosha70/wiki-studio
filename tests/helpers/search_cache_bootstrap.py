# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Bootstrap for a child ``wiki-studio`` process whose search-cache refresh is interrupted or held.

Usage (from a test)::

    python -m tests.helpers.search_cache_bootstrap <mode> <sync-dir> <cli argv...>

The child patches ``wiki_studio.search_index._apply_diff`` (the refresh step
inside the ``BEGIN IMMEDIATE`` transaction) so that, after the diff has been
written but before the commit:

- ``kill``: it writes ``<sync-dir>/staged`` and sends itself ``SIGKILL``;
- ``hold``: it writes ``<sync-dir>/staged`` and waits for ``<sync-dir>/go``;
- ``plain``: nothing is patched.

Then it calls ``wiki_studio.cli.main(argv)`` and exits with its code. Shipped
code has no pause hook: the interleaving is forced here, in the test process,
before ``cli.main`` runs.
"""

from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Sequence

    from wiki_studio.search_index import IndexedPage

HOLD_TIMEOUT_SECONDS = 60.0
STAGED_MARKER = "staged"
GO_MARKER = "go"
MODE_KILL = "kill"
MODE_HOLD = "hold"
MODE_PLAIN = "plain"


def main(argv: list[str]) -> int:
    mode, sync_dir, cli_argv = argv[0], Path(argv[1]), argv[2:]

    from wiki_studio import cli, search_index

    original = search_index._apply_diff

    def interrupted(connection: sqlite3.Connection, pages: Sequence[IndexedPage]) -> None:
        original(connection, pages)
        (sync_dir / STAGED_MARKER).write_text("staged\n", encoding="utf-8")
        if mode == MODE_KILL:
            os.kill(os.getpid(), signal.SIGKILL)
        deadline = time.monotonic() + HOLD_TIMEOUT_SECONDS
        while not (sync_dir / GO_MARKER).exists():
            if time.monotonic() > deadline:
                raise RuntimeError("search_cache_bootstrap: no go marker within the hold timeout")
            time.sleep(0.01)

    if mode in (MODE_KILL, MODE_HOLD):
        search_index._apply_diff = interrupted
    return cli.main(cli_argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
