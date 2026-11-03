# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The memkernel composition quickstart page, executed (0.8.1 US2, FR-006..FR-010).

``docs/quickstart-memkernel.md`` is the only source of its commands (D8): the
run blocks are extracted from the markdown and executed in page order in a
fresh temporary project directory by ``tests/helpers/quickstart_blocks.py``.
The page itself checks the wrong rule before the correction, the gated export,
the governed import and the handoff clone, and exits non-zero naming the check
that failed, so a failure reports the memkernel call that went wrong.

memkernel is optional here (never in the package or the dev group), so the
execution test is skipped, with the reason, when it is not installed; the
``quickstart-memkernel`` clean-install job installs the wheel and
``memkernel==0.6.0`` and runs the page against the real packages. The page's
structure tests run everywhere.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import sys
import unittest
from pathlib import Path

from tests.helpers.quickstart_blocks import parse_run_blocks, run_quickstart

REPO_ROOT = Path(__file__).resolve().parents[2]
QUICKSTART = REPO_ROOT / "docs" / "quickstart-memkernel.md"
HAS_MEMKERNEL = importlib.util.find_spec("memkernel") is not None
SKIP_REASON = (
    "memkernel is not installed; the quickstart-memkernel CI job runs this page against the wheel and memkernel==0.6.0"
)
BLOCK_TIMEOUT_SECONDS = 300.0
ALLOWED_IMPORT_ROOTS = set(sys.stdlib_module_names) | {"memkernel", "wiki_studio"}


class QuickstartMemkernelPageTest(unittest.TestCase):
    """FR-006, FR-008: the page's shape, checked without running memkernel."""

    def test_the_python_blocks_import_only_memkernel_wiki_studio_and_the_standard_library(self) -> None:
        blocks = parse_run_blocks(QUICKSTART.read_text(encoding="utf-8"))
        for block in blocks:
            if block.language != "python":
                continue
            with self.subTest(block=block.index):
                roots: set[str] = set()
                for node in ast.walk(ast.parse(block.text)):
                    if isinstance(node, ast.Import):
                        roots.update(alias.name.split(".")[0] for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        roots.add(node.module.split(".")[0])
                self.assertLessEqual(roots, ALLOWED_IMPORT_ROOTS, f"block {block.index} imports {sorted(roots)}")

    def test_the_setup_block_writes_the_stated_gitignore(self) -> None:
        blocks = parse_run_blocks(QUICKSTART.read_text(encoding="utf-8"))
        setup = next(block for block in blocks if ".gitignore" in block.text)
        match = re.search(r"cat > \.gitignore <<'EOF'\n(.*?)\nEOF\n", setup.text, re.DOTALL)
        self.assertIsNotNone(match, "the setup block does not write .gitignore")
        assert match is not None
        self.assertEqual(match.group(1).splitlines(), [".wiki.wiki-studio.*", ".memkernel/", ".env"])

    def test_the_page_names_memkernel_tools_beside_the_executed_blocks(self) -> None:
        markdown = QUICKSTART.read_text(encoding="utf-8")
        for tool in ("retain", "recall", "wiki_export", "wiki_import"):
            with self.subTest(tool=tool):
                self.assertIn(f"`{tool}`", markdown)


@unittest.skipUnless(HAS_MEMKERNEL, SKIP_REASON)
class QuickstartMemkernelRunTest(unittest.TestCase):
    """FR-006, FR-007, FR-009: the page's blocks, in order, against the real packages."""

    def test_every_run_block_passes_in_page_order(self) -> None:
        results = run_quickstart(QUICKSTART, timeout=BLOCK_TIMEOUT_SECONDS)
        expected = parse_run_blocks(QUICKSTART.read_text(encoding="utf-8"))
        self.assertEqual([result.block.index for result in results], [block.index for block in expected])
        self.assertEqual([result.block.language for result in results].count("python"), 6)
        self.assertGreaterEqual(len(results), 12)


if __name__ == "__main__":
    unittest.main()
