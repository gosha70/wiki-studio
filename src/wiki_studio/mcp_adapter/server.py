# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The ``wiki-studio-mcp`` server: the SDK's ``MCPServer`` over stdio only (FR-034, FR-040).

The only module that imports ``mcp``; without the extra, importing it raises
``ImportError`` with the install instruction. Each tool of :mod:`.tools` is
registered under its name with the signature the SDK turns into its input
schema; its result becomes a tool result whose text is the JSON object, and an
``IngestError`` or ``ValueError`` becomes an error result
``{error, exit_code, message}`` (anything else ``InternalError`` with the class
name only). stdout carries protocol frames only: logging and warnings go to
stderr, and the wire observer of :mod:`.trace` relays the frames unchanged.
"""

from __future__ import annotations

import inspect
import json
import logging
import sys
import typing
from typing import TYPE_CHECKING, Any

from .. import __version__
from ..errors import IngestError
from . import EXIT_LAUNCH_ERROR, INSTALL_INSTRUCTION
from .config import PROG, LaunchError, describe_launch, parse_launch
from .tools import WikiTools, error_payload
from .trace import WireObserver, observed_stdio, open_trace

if TYPE_CHECKING:
    from collections.abc import Callable

try:
    from mcp.server import MCPServer
    from mcp.types import CallToolResult
except ImportError as exc:  # the mcp extra is not installed
    raise ImportError(INSTALL_INSTRUCTION) from exc

SERVER_NAME = "wiki-studio"
TRANSPORT_STDIO = "stdio"
LOG_FORMAT = f"{PROG}: %(levelname)s %(name)s: %(message)s"

logger = logging.getLogger(__name__)


def tool_result(payload: dict[str, Any], *, is_error: bool) -> CallToolResult:
    """A tool result whose one text block is ``payload`` as JSON, also given as structured content."""
    return CallToolResult.model_validate(
        {
            "content": [{"type": "text", "text": json.dumps(payload)}],
            "structuredContent": payload,
            "isError": is_error,
        }
    )


def as_tool(name: str, method: Callable[..., dict[str, Any]]) -> Callable[..., CallToolResult]:
    """Wrap one tool method for the SDK: its own signature and description, results and errors as tool results.

    The wrapper publishes the method's signature with its annotations
    evaluated, so the SDK builds the input schema from the method's arguments
    alone and calls the wrapper with them.
    """

    def call(**kwargs: Any) -> CallToolResult:
        try:
            payload = method(**kwargs)
        except (IngestError, ValueError) as exc:
            return tool_result(error_payload(exc), is_error=True)
        except Exception as exc:
            logger.exception("tool %s failed", name)
            return tool_result(error_payload(exc), is_error=True)
        return tool_result(payload, is_error=False)

    hints = typing.get_type_hints(method)
    signature = inspect.signature(method, eval_str=True)
    call.__name__ = name
    call.__qualname__ = name
    call.__doc__ = method.__doc__
    call.__signature__ = signature.replace(return_annotation=inspect.Signature.empty)  # type: ignore[attr-defined]
    call.__annotations__ = {key: value for key, value in hints.items() if key != "return"}
    return call


def build_server(tools: WikiTools) -> MCPServer:
    """An ``MCPServer`` with exactly the live tools registered: no resources, prompts or other tools."""
    server: MCPServer = MCPServer(name=SERVER_NAME, version=__version__)
    for name, method in tools.registry().items():
        description = inspect.cleandoc(method.__doc__ or name)
        server.add_tool(as_tool(name, method), name=name, description=description, structured_output=False)
    return server


def serve(argv: list[str]) -> int:
    """Parse the launch flags once, open the trace, log the start-up line to stderr and serve stdio until EOF."""
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING, format=LOG_FORMAT)
    logging.captureWarnings(True)
    try:
        config = parse_launch(argv)
        trace_file = None if config.trace is None else open_trace(config.trace, config.paths)
    except LaunchError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return EXIT_LAUNCH_ERROR
    observer = WireObserver(trace_file)
    tools = WikiTools(config, protocol_version=lambda: observer.protocol_version)
    server = build_server(tools)
    print(describe_launch(config), file=sys.stderr, flush=True)
    with observed_stdio(observer):
        server.run(TRANSPORT_STDIO)
    return 0
