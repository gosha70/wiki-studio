# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""A copy of memkernel's whole-wiki snapshot, for the hazard reproduction only (0.7.0 US1, FR-003).

Copied from gosha70/memkernel ``src/memkernel/wiki/sync.py`` at main 641a508
(641a508a2289b2d20775e6d149a0bb47678d1621, "Merge pull request #51 from
gosha70/release/0.5.0rc1", 2026-10-26), class ``_WikiSnapshot`` lines
299-363, verbatim (citation verified 2026-10-26, see the spec FR-003), as
0.5.0 copied memkernel's quoting rules into ``tests/test_avoid_roundtrip.py``.

memkernel's bridge takes it before a gated export and calls ``restore`` on
failure, outside the wiki lock; ``tests/test_snapshot_hazard.py`` shows what
that does to another writer's committed work. Test fixture only: nothing here
ships, and nothing here is a test of memkernel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class _WikiSnapshot:
    """Every file a gated export can write, taken before it starts, so a failure restores exactly that.

    wiki-studio's promote before 0.4.1 (gosha70/wiki-studio#21) rolls back only
    the writes that completed, and only on ``OSError``: a page or ``index.md`` whose
    write failed part-way stays as it was left. Its commit step writes every ``*.md`` of the staged wiki that
    differs from the live one, plus ``.audit/**/plan.json``, so the snapshot holds
    all of those as bytes (not only the files memkernel's edits change), and any
    such file that appears during the export is removed again. The cost is one
    read of every page per gated export, which is negligible at the size of a
    project wiki (tens to hundreds of pages).
    """

    wiki_dir: Path
    files: dict[Path, bytes]
    dirs: set[Path]  # directories that existed, the wiki directory included when it did

    @classmethod
    def take(cls, wiki_dir: Path) -> _WikiSnapshot:
        files = {path: path.read_bytes() for path in cls._tracked(wiki_dir)}
        dirs = {path for path in wiki_dir.rglob("*") if path.is_dir()} if wiki_dir.is_dir() else set()
        if wiki_dir.is_dir():
            dirs.add(wiki_dir)
        return cls(wiki_dir, files, dirs)

    @staticmethod
    def _tracked(wiki_dir: Path) -> list[Path]:
        if not wiki_dir.is_dir():
            return []
        return [
            path
            for path in wiki_dir.rglob("*")
            if path.is_file() and (path.suffix == ".md" or (path.name == "plan.json" and ".audit" in path.parts))
        ]

    def restore(self) -> list[str]:
        """Put every tracked file back; returns what could not be restored (empty = the wiki is as it was)."""
        problems: list[str] = []
        for path in self._tracked(self.wiki_dir):
            if path not in self.files:
                try:
                    path.unlink()
                except OSError as exc:
                    problems.append(self._problem(path, exc))
        for path, original in self.files.items():
            try:
                if not path.is_file() or path.read_bytes() != original:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(original)
            except OSError as exc:
                problems.append(self._problem(path, exc))
        created = [path for path in self.wiki_dir.rglob("*") if path.is_dir() and path not in self.dirs]
        if self.wiki_dir.is_dir() and self.wiki_dir not in self.dirs:
            created.append(self.wiki_dir)
        for directory in sorted(created, key=lambda d: len(d.parts), reverse=True):
            try:
                if not any(directory.iterdir()):
                    directory.rmdir()
            except OSError as exc:
                problems.append(self._problem(directory, exc))
        return problems

    def _problem(self, path: Path, exc: OSError) -> str:
        return f"{path.relative_to(self.wiki_dir.parent).as_posix()}: {exc}"
