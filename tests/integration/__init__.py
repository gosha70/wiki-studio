# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The clean-install harness: the real memkernel bridge against the installed wiki-studio (0.7.0 FR-004).

Every test here is skipped unless ``memkernel`` is importable. CI runs the
package in the ``memkernel-compat`` job of ``.github/workflows/ci.yml``: the
wheel and a pinned memkernel in a fresh virtual environment, nothing from
``src/``. memkernel is never a dependency of the package or of the default
dev group, and memkernel's ``MemoryService`` is never mocked.
"""
