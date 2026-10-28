# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The launch configuration of ``wiki-studio-mcp`` (FR-034, FR-037): parsed once, held for the process.

Standard library only, so a launch error is testable without the ``mcp`` extra.
Every location, the actor and the ranker are resolved here by the rules the
CLI uses (flag, then ``WIKI_STUDIO_*`` variable, then default); no tool can
change them afterwards, and client-advertised MCP roots are never read.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ..contract import POLICY_AUTO_APPROVE_ON_PROMOTE, read_manifest
from ..discovery import RANKERS, resolve_ranker
from ..errors import ContractViolationError
from ..paths import WikiPaths, path_inside_dir, resolve_actor

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from ..paths import Actor

PROG = "wiki-studio-mcp"

# The tool surface, in registration order (FR-035). Nothing else is ever registered (FR-036).
TOOL_FIND = "find"
TOOL_READ_PAGE = "read_page"
TOOL_PROPOSE = "propose"
TOOL_PROMOTE = "promote"
TOOL_LINT = "lint"
TOOL_INFO = "info"
TOOL_FINDINGS = "findings"
TOOL_REVIEW_STATE = "review_state"
TOOL_NAMES: tuple[str, ...] = (
    TOOL_FIND,
    TOOL_READ_PAGE,
    TOOL_PROPOSE,
    TOOL_PROMOTE,
    TOOL_LINT,
    TOOL_INFO,
    TOOL_FINDINGS,
    TOOL_REVIEW_STATE,
)


class LaunchError(Exception):
    """The server cannot start with this configuration; ``wiki-studio-mcp`` exits 2 with the message."""


@dataclass(frozen=True)
class LaunchConfig:
    """What the server was launched with, resolved once.

    ``launch_by`` is the ``--by`` value itself (None without the flag): the
    tools pass it to ``api.propose`` and ``api.promote``, where None means read
    ``WIKI_STUDIO_ACTOR`` (FR-037). ``actor`` is the resolved actor the start-up
    line and ``info`` report. ``tools`` is the live surface after
    ``--disable-tool``.
    """

    paths: WikiPaths
    launch_by: str | None
    actor: Actor
    ranker: str
    ranker_source: str
    tools: tuple[str, ...]
    disabled_tools: tuple[str, ...]
    trace: Path | None


def describe_launch(config: LaunchConfig) -> str:
    """The start-up stderr line: the wiki, the actor and the ranker with their sources, the tools, the policy."""
    try:
        manifest = read_manifest(config.paths)
    except ContractViolationError as exc:
        policy = f"unreadable ({exc})"
    else:
        if manifest is None:
            policy = "none (legacy wiki, no manifest)"
        else:
            policy = ", ".join(f"{key}={str(value).lower()}" for key, value in manifest.policy.items()) or "default"
            if manifest.policy.get(POLICY_AUTO_APPROVE_ON_PROMOTE):
                policy += f" ({POLICY_AUTO_APPROVE_ON_PROMOTE}: promote approves the pages it writes)"
    actor = config.actor
    mode = " (propose-only mode)" if TOOL_PROMOTE in config.disabled_tools else ""
    return (
        f"{PROG}: wiki {config.paths.wiki_dir}; actor {actor.name or '(none)'} ({actor.source}); "
        f"ranker {config.ranker} ({config.ranker_source}); tools {', '.join(config.tools)}{mode}; policy {policy}"
    )


def build_parser() -> argparse.ArgumentParser:
    """The launch flags; every one has a ``WIKI_STUDIO_*`` variable except ``--disable-tool`` and ``--trace``."""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="wiki-studio's MCP server over stdio: eight tools over one wiki, fixed at launch.",
    )
    parser.add_argument("--root", type=Path, default=None, help="Project root (WIKI_STUDIO_ROOT).")
    parser.add_argument("--wiki-dir", type=Path, default=None, help="Wiki directory (WIKI_STUDIO_WIKI_DIR).")
    parser.add_argument(
        "--proposals-dir", type=Path, default=None, help="Proposals directory (WIKI_STUDIO_PROPOSALS_DIR)."
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        action="append",
        default=None,
        metavar="PATH",
        help="A directory outside the root pages may link into; repeatable (WIKI_STUDIO_SOURCE_ROOTS).",
    )
    parser.add_argument(
        "--lock-timeout", type=float, default=None, metavar="SECONDS", help="Wiki lock wait (WIKI_STUDIO_LOCK_TIMEOUT)."
    )
    parser.add_argument(
        "--search-cache",
        type=Path,
        default=None,
        metavar="PATH",
        help="The fts5 search cache, outside the wiki (WIKI_STUDIO_SEARCH_CACHE).",
    )
    parser.add_argument(
        "--ranker",
        default=None,
        metavar="{" + ",".join(RANKERS) + "}",
        help="The default ranker of the find tool (WIKI_STUDIO_RANKER); a call may override it.",
    )
    parser.add_argument(
        "--by",
        default=None,
        metavar="NAME",
        help="The actor every propose and promote is attributed to (WIKI_STUDIO_ACTOR). Attribution, "
        "not authentication.",
    )
    parser.add_argument(
        "--disable-tool",
        action="append",
        default=[],
        metavar="NAME",
        help="Remove a tool from the surface; repeatable. `--disable-tool promote` is propose-only mode. "
        f"Tools: {', '.join(TOOL_NAMES)}.",
    )
    parser.add_argument(
        "--trace",
        type=Path,
        default=None,
        metavar="PATH",
        help="Append one JSON line per request (no content, question, edit or path) to PATH, outside the wiki.",
    )
    return parser


def parse_launch(argv: Sequence[str], *, env: Mapping[str, str] | None = None, cwd: Path | None = None) -> LaunchConfig:
    """Parse the launch flags and resolve the layout, the actor and the ranker once.

    Raises :class:`LaunchError` for an unknown ``--disable-tool`` name, a bad
    location, lock timeout or ranker, and for a proposals directory outside
    the root: the adapter's proposal boundary is inside the root, so
    ``propose`` always reports a root-relative ``proposal_dir`` (FR-035) and
    ``promote`` never needs ``allow_out_of_repo`` (FR-039). ``argparse``
    itself exits 2 on a malformed command line.
    """
    args = build_parser().parse_args(list(argv))
    unknown = [name for name in args.disable_tool if name not in TOOL_NAMES]
    if unknown:
        raise LaunchError(f"--disable-tool: unknown tool {', '.join(unknown)}; tools are {', '.join(TOOL_NAMES)}")
    try:
        paths = WikiPaths.resolve(
            root=args.root,
            wiki_dir=args.wiki_dir,
            proposals_dir=args.proposals_dir,
            lock_timeout=args.lock_timeout,
            source_roots=args.source_root,
            search_cache=args.search_cache,
            env=env,
            cwd=cwd,
        )
        ranker, ranker_source = resolve_ranker(args.ranker, env=env)
    except ValueError as exc:
        raise LaunchError(str(exc)) from exc
    if not path_inside_dir(paths.proposals_dir, paths.root):
        raise LaunchError(
            f"proposals directory {paths.proposals_dir} is outside the root {paths.root}; the adapter's proposal "
            "boundary is inside the root (propose reports a root-relative proposal_dir and promote never passes "
            "allow_out_of_repo)"
        )
    trace: Path | None = None
    if args.trace is not None:
        # Checked against the wiki and opened by trace.open_trace before the server starts.
        trace = args.trace if args.trace.is_absolute() else (Path.cwd() if cwd is None else cwd) / args.trace
    launch_by = args.by if args.by is not None and args.by.strip() else None
    disabled = tuple(dict.fromkeys(args.disable_tool))
    return LaunchConfig(
        paths=paths,
        launch_by=launch_by,
        actor=resolve_actor(launch_by, env=env),
        ranker=ranker,
        ranker_source=ranker_source,
        tools=tuple(name for name in TOOL_NAMES if name not in disabled),
        disabled_tools=disabled,
        trace=trace,
    )
