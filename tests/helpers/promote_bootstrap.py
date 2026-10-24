# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Bootstrap for a child ``wiki-studio`` process whose promotion is held after staging.

Usage (from a test)::

    python -m tests.helpers.promote_bootstrap <sync-dir> <cli argv...>

The child patches ``wiki_studio.promoter._validate_staged_tree`` (the last
step before the commit) so that, after validation, it writes ``<sync-dir>/staged``
and then waits for ``<sync-dir>/go`` before returning; then it calls
``wiki_studio.cli.main(argv)`` and exits with its code. The lock is held
throughout, so a second promote contends for it before staging.

Shipped code has no pause hook: the interleaving is forced here, in the
test process, before ``cli.main`` runs.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wiki_studio.paths import WikiPaths
    from wiki_studio.proposal import WikiPatchSet

HOLD_TIMEOUT_SECONDS = 60.0
STAGED_MARKER = "staged"
GO_MARKER = "go"


def main(argv: list[str]) -> int:
    sync_dir = Path(argv[0])
    cli_argv = argv[1:]

    from wiki_studio import cli, promoter

    original = promoter._validate_staged_tree

    def held_validate(stage_dir: Path, paths: WikiPaths, patch: WikiPatchSet) -> None:
        original(stage_dir, paths, patch)
        (sync_dir / STAGED_MARKER).write_text("staged\n", encoding="utf-8")
        deadline = time.monotonic() + HOLD_TIMEOUT_SECONDS
        while not (sync_dir / GO_MARKER).exists():
            if time.monotonic() > deadline:
                raise RuntimeError("promote_bootstrap: no go marker within the hold timeout")
            time.sleep(0.01)

    promoter._validate_staged_tree = held_validate
    return cli.main(cli_argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
