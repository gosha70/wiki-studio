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
import posixpath
import re
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from .schema import PAGE_TYPE_DIRS, ROOT_DIR

# The directories a page may live in, one level below the wiki root.
_PAGE_DIRS: frozenset[str] = frozenset(d for d in PAGE_TYPE_DIRS.values() if d != ROOT_DIR)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

# Environment variables (the CLI flags of the same name take precedence).
ENV_ROOT = "WIKI_STUDIO_ROOT"
ENV_WIKI_DIR = "WIKI_STUDIO_WIKI_DIR"
ENV_PROPOSALS_DIR = "WIKI_STUDIO_PROPOSALS_DIR"
ENV_LOCK_TIMEOUT = "WIKI_STUDIO_LOCK_TIMEOUT"
# ``os.pathsep``-separated directories outside the root that page links may reference (``--source-root``).
ENV_SOURCE_ROOTS = "WIKI_STUDIO_SOURCE_ROOTS"
# Who proposes, promotes or approves when no ``--by`` is given (attribution, never authentication).
ENV_ACTOR = "WIKI_STUDIO_ACTOR"
# Where the ``fts5`` ranker keeps its rebuildable search cache (``--search-cache``; 0.8.0, FR-012).
ENV_SEARCH_CACHE = "WIKI_STUDIO_SEARCH_CACHE"

# Where an actor's name came from (``Actor.source``). The OS user name is never one of them.
ACTOR_SOURCE_FLAG = "flag"
ACTOR_SOURCE_ENV = "env"
ACTOR_SOURCE_NONE = "none"
ACTOR_SOURCES: frozenset[str] = frozenset({ACTOR_SOURCE_FLAG, ACTOR_SOURCE_ENV, ACTOR_SOURCE_NONE})

# Why ``contain`` refused a candidate (``ContainmentError.reason``).
CONTAIN_ABSOLUTE = "absolute"
CONTAIN_SYMLINK = "symlink"
CONTAIN_OUTSIDE = "outside"

# A Windows drive or UNC prefix: absolute on any platform for the purpose of a link target.
_WINDOWS_ABSOLUTE_RE = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\)")

# Seconds a writer waits for the wiki lock (``--lock-timeout`` / ``WIKI_STUDIO_LOCK_TIMEOUT``).
DEFAULT_LOCK_TIMEOUT = 30.0

# Defaults, relative to the root. These names are the documented layout and
# must not be spelled anywhere else in the package.
DEFAULT_WIKI_DIR = "knowledge/wiki"
DEFAULT_PROPOSALS_DIR = "doc_internal/proposals"
DEFAULT_QUERY_LOG = "doc_internal/wiki-query-log.jsonl"

# The search cache beside the wiki, named as the lock file is (``<parent>/.<wiki-dir-name><suffix>``).
SEARCH_CACHE_SUFFIX = ".wiki-studio.search.sqlite"

# Fixed names inside the wiki directory.
AUDIT_DIR_NAME = ".audit"
AUDIT_LOG_NAME = "ingest-log.md"
SCHEMA_DIR_NAME = "schema"
APPLIED_DIR_NAME = ".applied"
# The root manifest: the wiki's identity, schema contract and policy (written only by ``init``).
MANIFEST_NAME = ".wiki-studio.json"


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


def is_absolute_path(text: str) -> bool:
    """True for a path that is absolute on this platform, as POSIX, or as a Windows drive or UNC path."""
    return Path(text).is_absolute() or posixpath.isabs(text) or bool(_WINDOWS_ABSOLUTE_RE.match(text))


def sidecar_path_for(wiki_dir: Path, suffix: str) -> Path:
    """``<resolved-wiki-parent>/.<wiki-dir-name><suffix>``: a file beside the wiki, keyed to its resolved path."""
    resolved = Path(wiki_dir).resolve()
    return resolved.parent / f".{resolved.name}{suffix}"


def search_cache_path_for(wiki_dir: Path) -> Path:
    """The derived search cache for ``wiki_dir``, beside its lock file (FR-012)."""
    return sidecar_path_for(wiki_dir, SEARCH_CACHE_SUFFIX)


def path_inside_dir(path: Path, directory: Path) -> bool:
    """True when ``path`` (its parent resolved, its last component not followed) lies in or at ``directory``."""
    absolute = Path(path).absolute()
    location = absolute.parent.resolve() / absolute.name
    real_dir = Path(directory).resolve()
    return location == real_dir or location.is_relative_to(real_dir)


def _refuse_cache_inside_wiki(search_cache: Path, wiki_dir: Path) -> None:
    if path_inside_dir(search_cache, wiki_dir):
        raise ValueError(f"search cache {search_cache} is inside the wiki directory {wiki_dir}; it must lie outside it")


class ContainmentError(ValueError):
    """:func:`contain` refused ``candidate``.

    ``reason`` is ``"absolute"`` (the candidate is not relative), ``"symlink"``
    (a component on the way is a symlink) or ``"outside"`` (the real path
    lies outside the boundary); the message names the offending path.
    """

    def __init__(self, candidate: str, boundary: Path, reason: str, message: str) -> None:
        super().__init__(message)
        self.candidate = candidate
        self.boundary = boundary
        self.reason = reason


def contain(candidate: str | os.PathLike[str], boundary: Path, *, base: Path | None = None) -> Path:
    """The one containment check (FR-012): the real path of ``candidate`` when it stays inside ``boundary``.

    ``candidate`` is a relative path taken from ``base`` (default: the boundary
    itself); an absolute candidate is refused outright. Both sides are
    resolved: ``base`` and ``boundary`` with ``Path.resolve``, the candidate by
    walking it component by component from the resolved base without ever
    following a symlink. A component that is a symlink, file or directory,
    is refused even when a later ``..`` would step back out of it; ``..``
    steps to the real parent. Because no symlink was followed, the path
    reached is the one the kernel would resolve, and it must lie inside the
    resolved boundary. Nothing is read, and existence is the caller's
    question: a target that does not exist yet (a page about to be created)
    passes when its path does.

    Raises :class:`ContainmentError` with ``reason`` ``"absolute"``,
    ``"symlink"`` or ``"outside"``.
    """
    text = os.fspath(candidate)
    if is_absolute_path(text):
        raise ContainmentError(
            text, boundary, CONTAIN_ABSOLUTE, f"{text}: absolute path (must be relative to {boundary})"
        )
    start = (boundary if base is None else base).resolve()
    boundary_real = boundary.resolve()
    current = start
    for part in Path(text).parts:
        if part == ".":
            continue
        if part == "..":
            current = current.parent
            continue
        current = current / part
        if current.is_symlink():
            raise ContainmentError(text, boundary, CONTAIN_SYMLINK, f"{text}: {current} is a symlink")
    if current != boundary_real and not current.is_relative_to(boundary_real):
        raise ContainmentError(text, boundary, CONTAIN_OUTSIDE, f"{text}: resolves to {current}, outside {boundary}")
    return current


@dataclass(frozen=True)
class Actor:
    """Who proposed, promoted or approved: a ``name`` (None when unknown) and where it came from (FR-017).

    Attribution, not authentication: the name is whatever the caller passed
    or the environment held; the host supplies authority.
    """

    name: str | None
    source: str

    def as_dict(self) -> dict[str, str | None]:
        """``{"name", "source"}`` as ``plan.json`` and the receipt record it."""
        return {"name": self.name, "source": self.source}


def resolve_actor(by: str | None = None, *, env: Mapping[str, str] | None = None) -> Actor:
    """The one actor rule: a non-empty ``by`` (``--by``) is ``flag``, else a non-empty ``WIKI_STUDIO_ACTOR`` is ``env``.

    Otherwise ``{name: None, source: "none"}``. The OS user name is never
    captured.
    """
    if by is not None and by.strip():
        return Actor(by, ACTOR_SOURCE_FLAG)
    environ: Mapping[str, str] = os.environ if env is None else env
    value = environ.get(ENV_ACTOR, "")
    if value.strip():
        return Actor(value, ACTOR_SOURCE_ENV)
    return Actor(None, ACTOR_SOURCE_NONE)


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
    lock_timeout : float
        Seconds a writer waits for the wiki lock (``wikilock.WikiLock``) before
        exit 10 ``lock_timeout``.
    source_roots : tuple[Path, ...]
        Directories outside the root whose files a page may reference with a
        local link (``--source-root``, ``WIKI_STUDIO_SOURCE_ROOTS``); empty by
        default. A local link target must resolve inside the root or one of
        these (the source boundary of FR-012).
    search_cache : Path | None
        An explicit location for the ``fts5`` search cache (``--search-cache``,
        ``WIKI_STUDIO_SEARCH_CACHE``); None derives it beside the lock file
        (:meth:`search_cache_file`). Never inside the wiki.
    """

    root: Path
    wiki_dir: Path
    proposals_dir: Path
    query_log: Path
    audit_log: Path
    schema_dir: Path
    lock_timeout: float = DEFAULT_LOCK_TIMEOUT
    source_roots: tuple[Path, ...] = ()
    search_cache: Path | None = None

    @classmethod
    def for_root(
        cls,
        root: Path | str,
        *,
        wiki_dir: Path | str | None = None,
        proposals_dir: Path | str | None = None,
        lock_timeout: float | None = None,
        source_roots: Sequence[Path | str] | None = None,
        search_cache: Path | str | None = None,
    ) -> WikiPaths:
        """Build the layout under ``root`` with the defaults, optionally overriding the two directories.

        Relative inputs are made absolute against the current working directory (symlinks are
        not resolved), so a layout never depends on a later working directory. A
        ``search_cache`` inside the wiki directory raises ``ValueError``.
        """
        root_path = Path(root).absolute()
        wiki = Path(wiki_dir).absolute() if wiki_dir is not None else root_path / DEFAULT_WIKI_DIR
        proposals = Path(proposals_dir).absolute() if proposals_dir is not None else root_path / DEFAULT_PROPOSALS_DIR
        cache = Path(search_cache).absolute() if search_cache is not None else None
        if cache is not None:
            _refuse_cache_inside_wiki(cache, wiki)
        return cls(
            root=root_path,
            wiki_dir=wiki,
            proposals_dir=proposals,
            query_log=root_path / DEFAULT_QUERY_LOG,
            audit_log=wiki / AUDIT_DIR_NAME / AUDIT_LOG_NAME,
            schema_dir=wiki / SCHEMA_DIR_NAME,
            lock_timeout=DEFAULT_LOCK_TIMEOUT if lock_timeout is None else float(lock_timeout),
            source_roots=tuple(Path(p).absolute() for p in (source_roots or ())),
            search_cache=cache,
        )

    @classmethod
    def resolve(
        cls,
        *,
        root: str | os.PathLike[str] | None = None,
        wiki_dir: str | os.PathLike[str] | None = None,
        proposals_dir: str | os.PathLike[str] | None = None,
        lock_timeout: float | None = None,
        source_roots: Sequence[str | os.PathLike[str]] | None = None,
        search_cache: str | os.PathLike[str] | None = None,
        env: Mapping[str, str] | None = None,
        cwd: Path | None = None,
    ) -> WikiPaths:
        """Resolve the layout from flags, then ``WIKI_STUDIO_*`` variables, then defaults.

        Explicit values (flag or variable) that are relative are taken relative
        to ``cwd``; defaults are relative to the resolved root. A lock timeout
        that is not a non-negative number raises ``ValueError``. ``source_roots``
        (the repeatable ``--source-root``) replaces the ``os.pathsep``-separated
        list in ``WIKI_STUDIO_SOURCE_ROOTS``; both default to none. A search
        cache (``--search-cache``, ``WIKI_STUDIO_SEARCH_CACHE``) inside the wiki
        directory raises ``ValueError``.
        """
        environ: Mapping[str, str] = os.environ if env is None else env
        base = Path.cwd() if cwd is None else Path(cwd)

        root_value = root or environ.get(ENV_ROOT)
        root_path = _absolute(root_value, base) if root_value else default_root(base)

        wiki_value = wiki_dir or environ.get(ENV_WIKI_DIR)
        wiki_path = _absolute(wiki_value, base) if wiki_value else None

        proposals_value = proposals_dir or environ.get(ENV_PROPOSALS_DIR)
        proposals_path = _absolute(proposals_value, base) if proposals_value else None

        roots_value: Sequence[str | os.PathLike[str]] = (
            list(source_roots) if source_roots else environ.get(ENV_SOURCE_ROOTS, "").split(os.pathsep)
        )
        roots = tuple(_absolute(value, base) for value in roots_value if value)

        cache_value = search_cache or environ.get(ENV_SEARCH_CACHE)
        cache_path = _absolute(cache_value, base) if cache_value else None

        timeout = lock_timeout
        if timeout is None:
            timeout_value = environ.get(ENV_LOCK_TIMEOUT)
            if timeout_value:
                try:
                    timeout = float(timeout_value)
                except ValueError as exc:
                    raise ValueError(f"{ENV_LOCK_TIMEOUT} must be a number of seconds, got {timeout_value!r}") from exc
        if timeout is not None and not timeout >= 0:  # also rejects NaN
            raise ValueError(f"lock timeout must be a non-negative number of seconds, got {timeout!r}")

        return cls.for_root(
            root_path,
            wiki_dir=wiki_path,
            proposals_dir=proposals_path,
            lock_timeout=timeout,
            source_roots=roots,
            search_cache=cache_path,
        )

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

    def search_cache_file(self) -> Path:
        """The search cache: the explicit ``search_cache``, else the derived file beside the lock (FR-012)."""
        return self.search_cache if self.search_cache is not None else search_cache_path_for(self.wiki_dir)

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
