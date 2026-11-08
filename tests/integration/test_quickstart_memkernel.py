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
import os
import re
import sys
import unittest
from pathlib import Path

from tests.helpers.quickstart_blocks import child_environment, parse_run_blocks, pip_install_commands, run_quickstart

REPO_ROOT = Path(__file__).resolve().parents[2]
QUICKSTART = REPO_ROOT / "docs" / "quickstart-memkernel.md"
HAS_MEMKERNEL = importlib.util.find_spec("memkernel") is not None
SKIP_REASON = (
    "memkernel is not installed; the quickstart-memkernel CI job runs this page against the wheel and memkernel==0.6.0"
)
BLOCK_TIMEOUT_SECONDS = 300.0
ALLOWED_IMPORT_ROOTS = set(sys.stdlib_module_names) | {"memkernel", "wiki_studio"}
# The page's run markers, in page order: index, language, expected exit, stdout token.
# A block that gains, loses or changes its marker without this list changing fails here.
EXPECTED_RUN_BLOCKS = [
    (1, "bash", 0, None),
    (2, "bash", 0, None),
    (3, "python", 0, "wrong-rule-current"),
    (4, "python", 0, "export-gated"),
    (5, "bash", 0, None),
    (6, "python", 0, "correction-drafted"),
    (7, "bash", 0, None),
    (8, "bash", 0, None),
    (9, "bash", 0, None),
    (10, "python", 0, "right-rule-current"),
    (11, "bash", 0, None),
    (12, "python", 0, "handoff-ok"),
]
# The page's install lines: memkernel with base wiki-studio, then the MCP extra in its own
# environment (memkernel 0.6.0 requires mcp<2, the extra mcp>=2.3). CI resolves each one.
EXPECTED_INSTALL_COMMANDS = [
    ["memkernel[wiki]==0.6.0", "wiki-studio==0.9.0"],
    ["wiki-studio[mcp]==0.9.0"],
]


class QuickstartMemkernelPageTest(unittest.TestCase):
    """FR-006, FR-008: the page's shape, checked without running memkernel."""

    def test_the_page_marks_exactly_the_blocks_this_test_expects(self) -> None:
        """The executed set is the page's own, and this list makes a marker change visible."""
        blocks = parse_run_blocks(QUICKSTART.read_text(encoding="utf-8"))
        self.assertEqual(
            [(block.index, block.language, block.expected_exit, block.contains) for block in blocks],
            EXPECTED_RUN_BLOCKS,
        )

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

    def test_the_page_installs_the_mcp_extra_apart_from_memkernel(self) -> None:
        commands = pip_install_commands(QUICKSTART.read_text(encoding="utf-8"))
        self.assertEqual(commands, EXPECTED_INSTALL_COMMANDS)
        for args in commands:
            with self.subTest(command=args):
                together = any(arg.startswith("memkernel") for arg in args) and any(
                    arg.startswith("wiki-studio[mcp]") for arg in args
                )
                self.assertFalse(together, "memkernel 0.6.0 and wiki-studio[mcp] cannot resolve in one environment")

    def test_the_setup_block_writes_the_stated_gitignore(self) -> None:
        blocks = parse_run_blocks(QUICKSTART.read_text(encoding="utf-8"))
        setup = next(block for block in blocks if ".gitignore" in block.text)
        match = re.search(r"cat > \.gitignore <<'EOF'\n(.*?)\nEOF\n", setup.text, re.DOTALL)
        self.assertIsNotNone(match, "the setup block does not write .gitignore")
        assert match is not None
        self.assertEqual(match.group(1).splitlines(), [".wiki.wiki-studio.*", ".memkernel/", ".env"])

    def test_the_block_environment_forwards_the_pinned_model_and_the_cache(self) -> None:
        """The CI job exports the model pin and the offline flag; every block's process must see them."""
        env = child_environment()
        for key in ("MEMKERNEL_EMBEDDING_MODEL", "HF_HUB_OFFLINE", "HOME", "HF_HOME"):
            if key in os.environ:
                self.assertEqual(env.get(key), os.environ[key], f"{key} reaches the block")

    def test_the_page_names_memkernel_tools_beside_the_executed_blocks(self) -> None:
        markdown = QUICKSTART.read_text(encoding="utf-8")
        for tool in ("retain", "recall", "wiki_export", "wiki_import"):
            with self.subTest(tool=tool):
                self.assertIn(f"`{tool}`", markdown)


@unittest.skipUnless(HAS_MEMKERNEL, SKIP_REASON)
class QuickstartMemkernelRunTest(unittest.TestCase):
    """FR-006, FR-007, FR-009: the page's blocks, in order, against the real packages."""

    def test_every_run_block_passes_in_page_order(self) -> None:
        self.assertIn(
            "MEMKERNEL_EMBEDDING_MODEL",
            os.environ,
            "the quickstart-memkernel job pins memkernel's embedding model; without it the page downloads one",
        )
        results = run_quickstart(QUICKSTART, timeout=BLOCK_TIMEOUT_SECONDS)
        executed = [
            (result.block.index, result.block.language, result.block.expected_exit, result.block.contains)
            for result in results
        ]
        self.assertEqual(executed, EXPECTED_RUN_BLOCKS, "the executed blocks are the page's run-marked blocks")


if __name__ == "__main__":
    unittest.main()
