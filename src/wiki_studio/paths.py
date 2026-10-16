# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""WikiPaths — the single place where the wiki's locations are resolved.

Every verb and every library function takes a :class:`WikiPaths` instead of
spelling directory names itself. The defaults reproduce the original
code-copilot-team layout (``knowledge/wiki`` and ``doc_internal`` under the
repository root), so an unflagged run is byte-identical to the old wrapper;
each location can be overridden by a CLI flag or an ``WIKI_STUDIO_*`` variable.

Precedence, highest first: CLI flag, environment variable, default.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from .schema import PAGE_TYPE_DIRS, ROOT_DIR

# The directories a page may live in, one level below the wiki root.
_PAGE_DIRS: frozenset[str] = frozenset(d for d in PAGE_TYPE_DIRS.values() if d != ROOT_DIR)

if TYPE_CHECKING:
    from collections.abc import Mapping

# Environment variables (the CLI flags of the same name take precedence).
ENV_ROOT = "WIKI_STUDIO_ROOT"
ENV_WIKI_DIR = "WIKI_STUDIO_WIKI_DIR"
ENV_PROPOSALS_DIR = "WIKI_STUDIO_PROPOSALS_DIR"

# Defaults, relative to the root. These names are the documented layout and
# must not be spelled anywhere else in the package.
DEFAULT_WIKI_DIR = "knowledge/wiki"
DEFAULT_PROPOSALS_DIR = "doc_internal/proposals"
DEFAULT_QUERY_LOG = "doc_internal/wiki-query-log.jsonl"

# Fixed names inside the wiki directory.
AUDIT_DIR_NAME = ".audit"
AUDIT_LOG_NAME = "ingest-log.md"
SCHEMA_DIR_NAME = "schema"
APPLIED_DIR_NAME = ".applied"


def looks_wiki_relative(path: str) -> bool:
    """True when ``path`` has the shape of a wiki page path: ``<page-dir>/<name>.md`` or a root ``<name>.md``.

    Only the shape is judged (the page directories of the schema, one level deep,
    or a root-level markdown file); content and placement are the validators' job.
    """
    parts = path.split("/")
    if len(parts) == 1:
        return parts[0].endswith(".md")
    return len(parts) == 2 and parts[0] in _PAGE_DIRS and parts[1].endswith(".md")


def git_toplevel(cwd: Path | None = None) -> Path | None:
    """Return the git work-tree root containing ``cwd``, or None when there is none."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(cwd) if cwd is not None else None,
        )
    except OSError:
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip())


def default_root(cwd: Path | None = None) -> Path:
    """The default root: the git toplevel of ``cwd`` (default: the working directory), else ``cwd`` itself."""
    base = Path.cwd() if cwd is None else Path(cwd)
    return git_toplevel(base) or base.resolve()


def _absolute(value: str | os.PathLike[str], cwd: Path) -> Path:
    """Make an explicit (flag or environment) value absolute against ``cwd`` without resolving symlinks."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else cwd / path


@dataclass(frozen=True)
class WikiPaths:
    """Resolved locations of everything the maintainer reads or writes.

    Attributes
    ----------
    root : Path
        The project root. Source and proposal paths are confined to it by
        default, and repo-relative citations are resolved against it.
    wiki_dir : Path
        The wiki itself (``index.md``, ``log.md``, typed page directories).
    proposals_dir : Path
        Where ``ingest`` writes patch-sets and ``promote`` archives them.
    query_log : Path
        The JSONL log of ``query`` runs.
    audit_log : Path
        The append-only ingest log, ``<wiki_dir>/.audit/ingest-log.md``.
    schema_dir : Path
        A project-local copy of the schema documents; used only when it exists.
    """

    root: Path
    wiki_dir: Path
    proposals_dir: Path
    query_log: Path
    audit_log: Path
    schema_dir: Path

    @classmethod
    def for_root(
        cls,
        root: Path | str,
        *,
        wiki_dir: Path | str | None = None,
        proposals_dir: Path | str | None = None,
    ) -> WikiPaths:
        """Build the layout under ``root`` with the defaults, optionally overriding the two directories.

        Relative inputs are made absolute against the current working directory (symlinks are
        not resolved), so a layout never depends on a later working directory.
        """
        root_path = Path(root).absolute()
        wiki = Path(wiki_dir).absolute() if wiki_dir is not None else root_path / DEFAULT_WIKI_DIR
        proposals = Path(proposals_dir).absolute() if proposals_dir is not None else root_path / DEFAULT_PROPOSALS_DIR
        return cls(
            root=root_path,
            wiki_dir=wiki,
            proposals_dir=proposals,
            query_log=root_path / DEFAULT_QUERY_LOG,
            audit_log=wiki / AUDIT_DIR_NAME / AUDIT_LOG_NAME,
            schema_dir=wiki / SCHEMA_DIR_NAME,
        )

    @classmethod
    def resolve(
        cls,
        *,
        root: str | os.PathLike[str] | None = None,
        wiki_dir: str | os.PathLike[str] | None = None,
        proposals_dir: str | os.PathLike[str] | None = None,
        env: Mapping[str, str] | None = None,
        cwd: Path | None = None,
    ) -> WikiPaths:
        """Resolve the layout from flags, then ``WIKI_STUDIO_*`` variables, then defaults.

        Explicit values (flag or variable) that are relative are taken relative
        to ``cwd``; defaults are relative to the resolved root.
        """
        environ: Mapping[str, str] = os.environ if env is None else env
        base = Path.cwd() if cwd is None else Path(cwd)

        root_value = root or environ.get(ENV_ROOT)
        root_path = _absolute(root_value, base) if root_value else default_root(base)

        wiki_value = wiki_dir or environ.get(ENV_WIKI_DIR)
        wiki_path = _absolute(wiki_value, base) if wiki_value else None

        proposals_value = proposals_dir or environ.get(ENV_PROPOSALS_DIR)
        proposals_path = _absolute(proposals_value, base) if proposals_value else None

        return cls.for_root(root_path, wiki_dir=wiki_path, proposals_dir=proposals_path)

    def with_wiki_dir(self, wiki_dir: Path) -> WikiPaths:
        """The same layout with the wiki (and its audit log and schema dir) at ``wiki_dir``.

        Used by ``promote`` to validate a staged copy of the wiki with the
        real root and proposals directory.
        """
        return replace(
            self,
            wiki_dir=wiki_dir,
            audit_log=wiki_dir / AUDIT_DIR_NAME / AUDIT_LOG_NAME,
            schema_dir=wiki_dir / SCHEMA_DIR_NAME,
        )

    @property
    def applied_dir(self) -> Path:
        """Where promoted proposal directories are archived."""
        return self.proposals_dir / APPLIED_DIR_NAME

    @property
    def wiki_label(self) -> str:
        """The wiki directory as shown to humans and models.

        Root-relative (POSIX) when the wiki is under the root; otherwise only its
        directory name, so no absolute filesystem path reaches a backend prompt.
        """
        try:
            return self.wiki_dir.resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return self.wiki_dir.name

    def strip_wiki_label(self, path: str, *, must_exist: bool = False) -> str:
        """Remove one leading ``<wiki_label>/`` from a path a backend returned, and nothing else.

        Prompts show wiki files as ``<label>/<path>``; a model that copies the label
        into an edit path is corrected here for that exact prefix only, before the
        usual validation. A path that already has a valid wiki-relative shape is
        never touched: with the wiki directory itself named ``concepts``, the page
        ``concepts/x.md`` keeps its one ``concepts/`` while ``concepts/concepts/x.md``
        loses the copied one. ``wiki/wiki/x.md`` with label ``wiki`` becomes
        ``wiki/x.md`` and then fails validation as it should.

        ``must_exist`` is for edits whose target already exists (``update``,
        ``append-log``, ``append-index``): in the collision case, when the path
        as given does not exist under the wiki but the stripped one does, the
        prefix was copied and is removed (label ``decisions``: a copied
        ``decisions/index.md`` becomes ``index.md`` when only the root index exists).
        """
        prefix = self.wiki_label + "/"
        if not path.startswith(prefix):
            return path
        stripped = path[len(prefix) :]
        if looks_wiki_relative(path):
            if must_exist and not (self.wiki_dir / path).exists() and (self.wiki_dir / stripped).exists():
                return stripped
            return path
        return stripped

    def relative_to_root(self, path: Path) -> str:
        """``path`` relative to the root as POSIX when it is under the root, else as given."""
        try:
            return path.resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()

    def within_root(self, path: Path) -> bool:
        """True when ``path`` resolves to a location inside the root."""
        try:
            path.resolve().relative_to(self.root.resolve())
        except ValueError:
            return False
        return True
