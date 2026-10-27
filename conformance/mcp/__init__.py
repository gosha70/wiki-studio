# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The MCP conformance suite (0.8.0, FR-043, FR-045): ``python -m conformance.mcp.run``.

Adapter-agnostic: the runner imports nothing from ``wiki_studio``. It drives
any ``--server-cmd`` over stdio through the MCP SDK's client against a copy of
``fixture/`` and reads the fixture's end state from disk.
"""
