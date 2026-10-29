# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.8.0 (US4): the MCP adapter, ``wiki-studio-mcp`` (FR-031, FR-034..FR-041).

Two layers. The tool implementations, the launch configuration, the error
mapping and the trace observer are standard library and are tested in
process whether or not the ``mcp`` extra is installed. The server itself is
driven through a subprocess over stdio with the SDK's client, and its stdout
is read raw to check that every byte belongs to a protocol frame; those tests
are skipped when ``mcp`` is not importable (CI's dev group and the ``mcp-min``
and ``mcp-latest`` jobs install it).
"""

from __future__ import annotations

import asyncio
import contextlib
import importlib
import importlib.util
import inspect
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from tests.conftest import FIXTURES_DIR
from wiki_studio import api, errors
from wiki_studio.mcp_adapter import EXIT_LAUNCH_ERROR, INSTALL_INSTRUCTION, main
from wiki_studio.mcp_adapter.config import TOOL_NAMES, LaunchError, describe_launch, parse_launch
from wiki_studio.mcp_adapter.tools import INTERNAL_ERROR, WikiTools, error_payload
from wiki_studio.mcp_adapter.trace import (
    ERROR_RESULT_KEYS,
    KNOWN_ERRORS,
    KNOWN_METHODS,
    TOOL_ARG_KEYS,
    TOOL_RESULT_KEYS,
    TRACE_KEYS,
    UNKNOWN,
    WireObserver,
    open_trace,
)
from wiki_studio.paths import ENV_ACTOR, ENV_PROPOSALS_DIR, WikiPaths

HAS_MCP = importlib.util.find_spec("mcp") is not None
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
FIXTURE_ROOT = FIXTURES_DIR / "mcp"
PAGE_ID_RE = re.compile(r"^page_id: pg-[0-9a-f]{32}$", re.MULTILINE)
DEFAULT_NAME_RE = re.compile(r"^mcp-\d{8}T\d{6}Z-[0-9a-f]{8}$")
RETRY_PAGE = "decisions/retry-policy.md"
# FR-036: no tool argument may name a location, a backend, an actor or an escape hatch.
FORBIDDEN_PROPERTIES = frozenset(
    {
        "root",
        "wiki_dir",
        "proposals_dir",
        "backend",
        "by",
        "actor",
        "allow_out_of_repo",
        "allow_unguarded_updates",
        "entry_point",
        "lock_timeout",
        "ranker_config",
    }
)
NEW_PAGE = (
    "---\npage_type: decision\nslug: {slug}\ntitle: {title}\nstatus: stable\nlast_reviewed: 2026-10-27\n"
    'sources:\n  - url: "https://example.com/{slug}"\n    retrieved: 2026-10-27\n---\n\n# {title}\n\n'
    "## Decision\n\n{body}\n\n## Context\n\nAgreed in review.\n\n## Alternatives considered\n\nNone.\n\n"
    "## Consequences\n\nCallers wait less.\n"
)
SERVER_BOOT = "import sys; from wiki_studio.mcp_adapter import main; sys.exit(main(sys.argv[1:]))"


def new_page(slug: str, body: str = "Time out outbound calls after 5 s.") -> str:
    return NEW_PAGE.format(slug=slug, title=slug.replace("-", " ").title(), body=body)


def create_edits(slug: str) -> list[dict[str, Any]]:
    """A create of ``decisions/<slug>.md`` plus its index line, as the propose tool takes them."""
    rel = f"decisions/{slug}.md"
    return [
        {"path": rel, "action": "create", "content": new_page(slug)},
        {"path": "index.md", "action": "append-index", "content": f"- [{slug}]({rel})"},
    ]


def without_actor_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k != ENV_ACTOR}


class FixtureCase(unittest.TestCase):
    """A copy of ``tests/fixtures/mcp`` (root, wiki, two decision pages) with a manifest from ``init``."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-mcp-")
        self.base = Path(self._tmp.name).resolve()
        self.root = self.base / "project"
        shutil.copytree(FIXTURE_ROOT, self.root)
        self.paths = WikiPaths.for_root(self.root)
        self.wiki = self.paths.wiki_dir
        api.init(self.paths)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def set_auto_approve(self) -> None:
        manifest = self.wiki / ".wiki-studio.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["policy"]["auto_approve_on_promote"] = True
        manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def launch(self, *flags: str, env: dict[str, str] | None = None) -> WikiTools:
        config = parse_launch(["--root", str(self.root), *flags], env={} if env is None else env, cwd=self.root)
        return WikiTools(config, protocol_version=lambda: "2025-06-18")

    def tree(self) -> dict[str, bytes]:
        return {p.relative_to(self.wiki).as_posix(): p.read_bytes() for p in self.wiki.rglob("*") if p.is_file()}

    def approval_records(self) -> list[dict[str, Any]]:
        root = self.wiki / ".audit" / "approvals"
        files = sorted(p for p in root.rglob("*") if p.is_file()) if root.is_dir() else []
        return [json.loads(p.read_text(encoding="utf-8")) for p in files]


# ── Packaging without the extra (FR-031) ─────────────────────


class TestWithoutTheExtra(unittest.TestCase):
    def test_main_prints_the_install_instruction_and_exits_2(self) -> None:
        blocked = {"mcp": None, "mcp.server": None, "mcp.types": None}
        err = io.StringIO()
        with patch.dict(sys.modules, blocked):
            sys.modules.pop("wiki_studio.mcp_adapter.server", None)
            with contextlib.redirect_stderr(err):
                code = main([])
        self.assertEqual(code, EXIT_LAUNCH_ERROR)
        self.assertEqual(err.getvalue().strip(), INSTALL_INSTRUCTION)

    def test_the_server_module_raises_import_error_with_the_instruction(self) -> None:
        with patch.dict(sys.modules, {"mcp": None, "mcp.server": None, "mcp.types": None}):
            sys.modules.pop("wiki_studio.mcp_adapter.server", None)
            with self.assertRaises(ImportError) as caught:
                importlib.import_module("wiki_studio.mcp_adapter.server")
        self.assertEqual(str(caught.exception), INSTALL_INSTRUCTION)

    def test_the_package_and_its_stdlib_modules_import_without_mcp(self) -> None:
        code = (
            "import sys; sys.modules['mcp'] = None\n"
            "import wiki_studio.mcp_adapter, wiki_studio.mcp_adapter.config, wiki_studio.mcp_adapter.tools, "
            "wiki_studio.mcp_adapter.trace\n"
            "print('ok')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(SRC_DIR)},
            check=False,
        )
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "ok"), result.stderr)

    def test_the_core_package_never_imports_the_adapter(self) -> None:
        package = SRC_DIR / "wiki_studio"
        offenders = [
            py.relative_to(package).as_posix()
            for py in package.rglob("*.py")
            if "mcp_adapter" not in py.relative_to(package).parts
            and re.search(r"^\s*(from|import)\s+[.\w]*mcp_adapter", py.read_text(encoding="utf-8"), re.MULTILINE)
        ]
        self.assertEqual(offenders, [])


# ── Launch configuration (FR-034, FR-037) ────────────────────


class TestLaunch(FixtureCase):
    def test_the_layout_actor_and_ranker_are_resolved_once(self) -> None:
        config = self.launch("--by", "alice", "--ranker", "fts5").config
        self.assertEqual(config.paths.wiki_dir, self.wiki)
        self.assertEqual((config.launch_by, config.actor.name, config.actor.source), ("alice", "alice", "flag"))
        self.assertEqual((config.ranker, config.ranker_source), ("fts5", "flag"))
        self.assertEqual(config.tools, TOOL_NAMES)

    def test_the_environment_supplies_the_actor_and_the_ranker(self) -> None:
        config = self.launch(env={ENV_ACTOR: "bob", "WIKI_STUDIO_RANKER": "index-first"}).config
        self.assertIsNone(config.launch_by)
        self.assertEqual((config.actor.name, config.actor.source), ("bob", "env"))
        self.assertEqual(config.ranker_source, "env")

    def test_disable_tool_removes_only(self) -> None:
        config = self.launch("--disable-tool", "promote", "--disable-tool", "promote").config
        self.assertEqual(config.tools, tuple(n for n in TOOL_NAMES if n != "promote"))
        self.assertEqual(config.disabled_tools, ("promote",))
        self.assertEqual(list(WikiTools(config).registry()), list(config.tools))

    def test_an_unknown_tool_name_is_a_launch_error(self) -> None:
        with self.assertRaisesRegex(LaunchError, "unknown tool nope"):
            self.launch("--disable-tool", "nope")

    def test_bad_values_are_launch_errors(self) -> None:
        for flags in (("--lock-timeout", "-1"), ("--ranker", "bm42")):
            with self.subTest(flags=flags), self.assertRaises(LaunchError):
                self.launch(*flags)
        inside = self.wiki / "cache.sqlite"
        with self.assertRaises(LaunchError):
            self.launch("--search-cache", str(inside))

    def test_a_proposals_dir_outside_the_root_is_a_launch_error(self) -> None:
        outside = self.base / "elsewhere" / "proposals"
        with self.assertRaisesRegex(LaunchError, "outside the root"):
            self.launch("--proposals-dir", str(outside))
        with self.assertRaisesRegex(LaunchError, "outside the root"):
            self.launch(env={ENV_PROPOSALS_DIR: str(outside)})
        self.assertFalse(outside.exists())

    def test_a_proposals_dir_inside_the_root_gives_a_root_relative_proposal_dir(self) -> None:
        tools = self.launch("--proposals-dir", str(self.root / ".memkernel" / "wiki-proposals"))
        result = tools.propose(create_edits("timeout-policy"))
        self.assertEqual(result["proposal_dir"], f".memkernel/wiki-proposals/{result['name']}")
        promoted = tools.promote(result["name"])
        self.assertIn("decisions/timeout-policy.md", promoted["applied_paths"])

    def test_the_start_up_line_names_wiki_actor_ranker_tools_and_policy(self) -> None:
        self.set_auto_approve()
        line = describe_launch(self.launch("--by", "alice", "--disable-tool", "promote").config)
        self.assertIn(str(self.wiki), line)
        self.assertIn("actor alice (flag)", line)
        self.assertIn("ranker fts5 (default)", line)
        self.assertIn("propose-only mode", line)
        self.assertNotIn("promote,", line)
        self.assertIn("auto_approve_on_promote=true", line)


# ── The tools (FR-035, FR-036, FR-038, FR-039) ───────────────


class TestTools(FixtureCase):
    def test_find_returns_the_find_json_object(self) -> None:
        result = self.launch().find("retry backoff")
        self.assertEqual(result["pages"][0]["path"], RETRY_PAGE)
        from tests.conftest import run_cli

        cli = json.loads(run_cli("find", "retry backoff", "--json", "--root", str(self.root), cwd=self.root).stdout)
        self.assertEqual(result, cli)

    def test_find_max_pages_outside_1_to_5_is_a_value_error(self) -> None:
        tools = self.launch()
        for bad in (0, 6, True):
            with self.subTest(max_pages=bad), self.assertRaises(ValueError):
                tools.find("retry", max_pages=bad)

    def test_find_takes_a_per_call_ranker_and_refuses_an_unknown_one(self) -> None:
        tools = self.launch()
        self.assertEqual(tools.find("retry", ranker="index-first")["ranker"], "index-first")
        with self.assertRaises(ValueError):
            tools.find("retry", ranker="bm42")

    def test_read_page_returns_the_hash_of_the_bytes(self) -> None:
        result = self.launch().read_page(RETRY_PAGE)
        self.assertEqual(result["path"], RETRY_PAGE)
        self.assertEqual(result["content"], (self.wiki / RETRY_PAGE).read_text(encoding="utf-8"))
        self.assertEqual(set(result), {"path", "sha256", "content"})
        with self.assertRaises(errors.PathOutsideRootError):
            self.launch().read_page("../notes.md")

    def test_propose_writes_a_proposal_with_page_ids_and_leaves_the_wiki(self) -> None:
        before = self.tree()
        result = self.launch().propose(create_edits("timeout-policy"), rationale="why")
        self.assertRegex(result["name"], DEFAULT_NAME_RE)
        self.assertEqual(result["proposal_dir"], f"doc_internal/proposals/{result['name']}")
        self.assertEqual(result["warnings"], [])
        preview = self.root / result["proposal_dir"] / "preview" / "decisions" / "timeout-policy.md"
        self.assertRegex(preview.read_text(encoding="utf-8"), PAGE_ID_RE)
        plan = json.loads((self.root / result["proposal_dir"] / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual((plan["source_path"], plan["backend"]), ("mcp", "mcp"))
        self.assertEqual(self.tree(), before)

    def test_propose_refuses_malformed_edits(self) -> None:
        tools = self.launch()
        for edits in (["x"], [{"path": "a.md", "action": "create"}], [{**create_edits("a")[0], "by": "eve"}]):
            with self.subTest(edits=edits), self.assertRaises(ValueError):
                tools.propose(edits)  # type: ignore[arg-type]

    def test_promote_lands_the_proposal_with_entry_point_mcp(self) -> None:
        tools = self.launch()
        name = tools.propose(create_edits("timeout-policy"), name="p1")["name"]
        result = tools.promote(name)
        self.assertIn("decisions/timeout-policy.md", result["applied_paths"])
        self.assertEqual(result["approved_paths"], [])
        receipt = json.loads((self.root / result["archived_dir"] / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["promoter"]["entry_point"], "mcp")
        self.assertEqual(receipt["state"], "committed")
        (state,) = tools.review_state(["decisions/timeout-policy.md"])["states"]
        self.assertNotEqual(state["state"], "approved")

    def test_promote_refuses_a_name_that_is_not_one_component_and_reads_nothing(self) -> None:
        tools = self.launch()
        for name in ("../x", str(self.root / "elsewhere"), "a/b", ".hidden", ""):
            with self.subTest(name=name), patch.object(api, "promote") as promote:
                with self.assertRaises(ValueError):
                    tools.promote(name)
                promote.assert_not_called()

    def test_a_stale_update_is_refused_with_the_wiki_unchanged(self) -> None:
        tools = self.launch()
        base = tools.read_page(RETRY_PAGE)["sha256"]
        update = [{"path": RETRY_PAGE, "action": "update", "content": new_page("retry-policy"), "base_sha256": base}]
        tools.propose(update, name="u1")
        (self.wiki / RETRY_PAGE).write_text(new_page("retry-policy", "Changed by hand."), encoding="utf-8")
        before = self.tree()
        with self.assertRaises(errors.PromoteValidationError):
            tools.promote("u1")
        self.assertEqual(self.tree(), before)

    def test_lint_with_health_never_resolves_a_backend(self) -> None:
        with patch.object(api, "prepare_backend", side_effect=AssertionError("a backend was resolved")):
            result = self.launch().lint(health=True, prose=True)
        self.assertTrue(result["passed"], result)
        self.assertEqual(set(result), {"violations", "pages_checked", "audit_errors", "health", "prose", "passed"})
        self.assertEqual(set(result["health"]), {"pages_checked", "findings"})
        self.assertEqual(set(result["prose"]), {"pages_checked", "findings"})
        self.assertIsNone(self.launch().lint()["health"])

    def test_info_adds_the_adapter_and_the_launch_ranker(self) -> None:
        data = self.launch("--ranker", "fts5", "--by", "alice", "--disable-tool", "promote").info()
        self.assertEqual(
            set(data["adapter"]),
            {"adapter_version", "sdk_version", "protocol_version", "tools", "actor", "ranker", "disabled_tools"},
        )
        self.assertEqual(data["adapter"]["actor"], {"name": "alice", "source": "flag"})
        self.assertEqual(data["adapter"]["ranker"], {"name": "fts5", "source": "flag"})
        self.assertEqual(data["adapter"]["protocol_version"], "2025-06-18")
        self.assertNotIn("promote", data["adapter"]["tools"])
        self.assertEqual(data["adapter"]["disabled_tools"], ["promote"])
        self.assertEqual(
            (data["discovery"]["default_ranker"], data["discovery"]["default_ranker_source"]), ("fts5", "flag")
        )
        self.assertEqual(self.launch().info()["discovery"]["default_ranker_source"], "default")

    def test_findings_and_review_state_shapes(self) -> None:
        tools = self.launch()
        self.assertIn("findings", tools.findings())
        states = tools.review_state()["states"]
        self.assertEqual({s["path"] for s in states}, {RETRY_PAGE, "decisions/cache-policy.md"})
        self.assertEqual(
            set(states[0]),
            {"path", "page_key", "state", "reason", "live_sha256", "approved_sha256", "record_path", "warnings"},
        )


class TestActor(FixtureCase):
    """FR-037: the launch actor is the proposer, the promoter and the approver; tools take no ``by``."""

    def promote_one(self, tools: WikiTools) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        name = tools.propose(create_edits("timeout-policy"), name="a1")["name"]
        plan = json.loads((self.paths.proposals_dir / name / "plan.json").read_text(encoding="utf-8"))
        result = tools.promote(name)
        receipt = json.loads((self.root / result["archived_dir"] / "receipt.json").read_text(encoding="utf-8"))
        return plan, receipt, result

    def test_a_flag_actor_is_recorded_everywhere(self) -> None:
        self.set_auto_approve()
        with patch.dict(os.environ, without_actor_env(), clear=True):
            plan, receipt, result = self.promote_one(self.launch("--by", "alice"))
        alice = {"name": "alice", "source": "flag"}
        self.assertEqual(plan["proposer"], alice)
        self.assertEqual(receipt["actor"], alice)
        (record,) = self.approval_records()
        self.assertEqual(record["approver"], alice)
        self.assertEqual(result["approved_paths"], ["decisions/timeout-policy.md"])

    def test_an_environment_actor_is_recorded_with_source_env(self) -> None:
        self.set_auto_approve()
        env = {**without_actor_env(), ENV_ACTOR: "bob"}
        with patch.dict(os.environ, env, clear=True):
            plan, receipt, _result = self.promote_one(self.launch(env=env))
        bob = {"name": "bob", "source": "env"}
        self.assertEqual(plan["proposer"], bob)
        self.assertEqual(receipt["actor"], bob)
        (record,) = self.approval_records()
        self.assertEqual(record["approver"], bob)

    def test_auto_approval_succeeds_with_the_policy_warning(self) -> None:
        self.set_auto_approve()
        with patch.dict(os.environ, without_actor_env(), clear=True):
            _plan, _receipt, result = self.promote_one(self.launch("--by", "alice"))
        (warning,) = result["warnings"]
        self.assertIn("auto_approve_on_promote", warning)
        self.assertIn("approved by policy", warning)
        self.assertIn("alice (source flag)", warning)
        self.assertEqual(self.launch().review_state([result["approved_paths"][0]])["states"][0]["state"], "approved")


# ── Errors (FR-040) ──────────────────────────────────────────


class TestErrorPayload(unittest.TestCase):
    def test_every_ingest_error_class_maps_to_its_exit_code(self) -> None:
        classes = [
            errors.BackendNotFoundError,
            errors.BackendInvocationError,
            errors.ContractViolationError,
            errors.SourceMissingError,
            errors.PathOutsideRootError,
            errors.OutputWriteError,
            errors.PromoteValidationError,
            errors.AuditFlushError,
        ]
        for cls in classes:
            with self.subTest(cls=cls.__name__):
                payload = error_payload(cls("boom"))
                self.assertEqual(payload, {"error": cls.__name__, "exit_code": cls.exit_code, "message": "boom"})
        apply = error_payload(errors.PromoteApplyError("stuck", reason="lock_timeout"))
        self.assertEqual((apply["error"], apply["exit_code"]), ("PromoteApplyError", 10))

    def test_value_error_is_exit_1_and_anything_else_is_internal_with_the_class_name_only(self) -> None:
        self.assertEqual(error_payload(ValueError("bad")), {"error": "ValueError", "exit_code": 1, "message": "bad"})
        payload = error_payload(RuntimeError("/secret/path traceback"))
        self.assertEqual(payload, {"error": INTERNAL_ERROR, "exit_code": 1, "message": "RuntimeError"})


# ── The trace (FR-041) ───────────────────────────────────────


class TestTrace(FixtureCase):
    def test_the_known_methods_cover_what_a_real_host_sends(self) -> None:
        """Every MCP 2025-06-18 client request method is recorded by name; a valid host run never reads as unknown."""
        required = {"initialize", "tools/list", "tools/call", "ping"}
        self.assertTrue(required <= KNOWN_METHODS, required - KNOWN_METHODS)
        self.assertEqual(
            KNOWN_METHODS,
            required
            | {
                "resources/list",
                "resources/templates/list",
                "resources/read",
                "resources/subscribe",
                "resources/unsubscribe",
                "prompts/list",
                "prompts/get",
                "completion/complete",
                "logging/setLevel",
            },
        )

    def test_a_trace_inside_the_wiki_or_unwritable_is_a_launch_error(self) -> None:
        with self.assertRaisesRegex(LaunchError, "inside the wiki"):
            open_trace(self.wiki / "trace.jsonl", self.paths)
        with self.assertRaisesRegex(LaunchError, "cannot be opened"):
            open_trace(self.base / "missing-dir" / "trace.jsonl", self.paths)

    def test_one_line_per_request_with_no_content(self) -> None:
        path = self.base / "trace.jsonl"
        ticks = iter([1.0, 1.25, 2.0, 2.5, 3.0, 3.01])
        observer = WireObserver(open_trace(path, self.paths), clock=lambda: next(ticks))
        frames_in = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "clientInfo": {"name": "probe", "version": "9.1"},
                    "capabilities": {},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "find", "arguments": {"question": "SECRET QUESTION"}},
            },
            {"jsonrpc": "2.0", "id": "three", "method": "tools/list"},
        ]
        error_text = json.dumps({"error": "ValueError", "exit_code": 1, "message": "SECRET"})
        frames_out = [
            {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-06-18", "capabilities": {}}},
            {"jsonrpc": "2.0", "id": 2, "result": {"isError": True, "content": [{"type": "text", "text": error_text}]}},
            {"jsonrpc": "2.0", "id": "three", "result": {"tools": []}},
        ]
        for frame in frames_in[:3]:
            observer.inbound(json.dumps(frame).encode())
        observer.outbound(json.dumps(frames_out[0]).encode())
        observer.outbound(json.dumps(frames_out[1]).encode())
        observer.inbound(json.dumps(frames_in[3]).encode())
        observer.outbound(json.dumps(frames_out[2]).encode())
        observer.inbound(b"not json")
        observer.close()
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("SECRET", text)
        lines = [json.loads(line) for line in text.splitlines()]
        self.assertEqual([tuple(line) for line in lines], [TRACE_KEYS] * 3)
        self.assertEqual(
            [(r["method"], r["tool"], r["outcome"]) for r in lines],
            [("initialize", None, 0), ("tools/call", "find", 1), ("tools/list", None, 0)],
        )
        self.assertEqual({r["protocol_version"] for r in lines}, {"2025-06-18"})
        self.assertEqual({(r["client_name"], r["client_version"]) for r in lines}, {("probe", "9.1")})
        self.assertEqual([r["duration_ms"] for r in lines], [1000, 1250, 10])
        self.assertEqual(observer.protocol_version, "2025-06-18")

    def test_client_chosen_names_are_never_recorded(self) -> None:
        """FR-041: a tool name, argument key, method or listed name outside the schema is counted, never copied."""
        path = self.base / "trace.jsonl"
        observer = WireObserver(open_trace(path, self.paths))
        bad_tool, bad_key, bad_method, bad_name = "../../etc/passwd", "/tmp/x", "/etc/shadow", "../evil"
        find_result = json.dumps({"pages": [], "ranker": "index-first", bad_key: 1})
        exchanges: list[tuple[dict[str, Any], dict[str, Any]]] = [
            (
                {"id": 1, "method": "tools/call", "params": {"name": bad_tool, "arguments": {bad_key: 1}}},
                {
                    "id": 1,
                    "result": {"isError": True, "content": [{"type": "text", "text": f"Unknown tool: {bad_tool}"}]},
                },
            ),
            (
                {
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "find", "arguments": {"question": "q", bad_key: 1}},
                },
                {"id": 2, "result": {"content": [{"type": "text", "text": find_result}]}},
            ),
            ({"id": 3, "method": "tools/list"}, {"id": 3, "result": {"tools": [{"name": "find"}, {"name": bad_name}]}}),
            ({"id": 4, "method": bad_method, "params": {}}, {"id": 4, "result": {}}),
        ]
        for request, response in exchanges:
            observer.inbound(json.dumps({"jsonrpc": "2.0", **request}).encode())
            observer.outbound(json.dumps({"jsonrpc": "2.0", **response}).encode())
        observer.close()
        text = path.read_text(encoding="utf-8")
        for secret in (bad_tool, bad_key, bad_method, bad_name, "passwd", "shadow", "evil", "tmp"):
            self.assertNotIn(secret, text)
        lines = [json.loads(line) for line in text.splitlines()]
        self.assertEqual([tuple(line) for line in lines], [TRACE_KEYS] * 4)
        unknown, find, listed, other = lines
        self.assertEqual((unknown["method"], unknown["tool"], unknown["outcome"]), ("tools/call", UNKNOWN, 1))
        self.assertEqual((unknown["arg_keys"], unknown["unknown_arg_keys"]), ([], 1))
        self.assertEqual((unknown["result_keys"], unknown["unknown_result_keys"]), (None, None))
        self.assertEqual(unknown["summary"], {"exit_code": 1, "error": None})
        self.assertEqual((find["tool"], find["arg_keys"], find["unknown_arg_keys"]), ("find", ["question"], 1))
        self.assertEqual((find["result_keys"], find["unknown_result_keys"]), (["pages", "ranker"], 1))
        self.assertEqual((listed["tool_names"], listed["unknown_tool_names"]), (["find"], 1))
        self.assertEqual(
            (other["method"], other["tool"], other["arg_keys"], other["tool_names"]), (UNKNOWN, None, None, None)
        )

    def test_the_known_argument_and_result_keys_are_each_tools_own(self) -> None:
        """The key sets the trace keeps are exactly the tools' signatures and the keys their results carry."""
        tools = self.launch("--by", "alice")
        for name, method in tools.registry().items():
            with self.subTest(tool=name):
                self.assertEqual(TOOL_ARG_KEYS[name], frozenset(inspect.signature(method).parameters))
        results = {
            "find": tools.find("retry"),
            "read_page": tools.read_page(RETRY_PAGE),
            "propose": tools.propose(create_edits("known-keys"), name="k1"),
            "promote": tools.promote("k1"),
            "lint": tools.lint(health=True),
            "info": tools.info(),
            "findings": tools.findings(),
            "review_state": tools.review_state(),
        }
        self.assertEqual(set(results), set(TOOL_NAMES))
        for name, result in results.items():
            with self.subTest(tool=name):
                self.assertEqual(set(result), set(TOOL_RESULT_KEYS[name]))
        self.assertEqual(set(error_payload(ValueError("x"))), set(ERROR_RESULT_KEYS))
        self.assertLessEqual(
            {"ValueError", INTERNAL_ERROR, "PathOutsideRootError", "PromoteValidationError", "OutputWriteError"},
            KNOWN_ERRORS,
        )


# ── Through the SDK's client over stdio ──────────────────────


@unittest.skipUnless(HAS_MCP, "the mcp extra is not installed")
class TestServerOverStdio(FixtureCase):
    """The server in a subprocess, driven by the SDK's client (FR-040)."""

    def server_env(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        return {"PYTHONPATH": str(SRC_DIR), **(extra or {})}

    def run_session(self, flags: list[str], body: Any, *, env: dict[str, str] | None = None) -> Any:
        from mcp import ClientSession, StdioServerParameters, stdio_client

        params = StdioServerParameters(
            command=sys.executable,
            args=["-c", SERVER_BOOT, "--root", str(self.root), *flags],
            env=self.server_env(env),
            cwd=str(self.root),
        )

        async def go() -> Any:
            with open(self.base / "server-stderr.log", "a", encoding="utf-8") as errlog:
                async with stdio_client(params, errlog=errlog) as (read, write), ClientSession(read, write) as session:
                    await session.initialize()
                    return await body(session)

        return asyncio.run(go())

    @staticmethod
    def dump(result: Any) -> dict[str, Any]:
        return result.model_dump(by_alias=True, exclude_none=True)

    @classmethod
    def payload(cls, result: Any) -> tuple[bool, dict[str, Any]]:
        data = cls.dump(result)
        return bool(data.get("isError")), json.loads(data["content"][0]["text"])

    def test_tools_list_is_exactly_the_eight_with_no_forbidden_argument(self) -> None:
        async def body(session: Any) -> Any:
            return (await session.list_tools()).tools

        tools = [self.dump(t) for t in self.run_session([], body)]
        self.assertEqual(sorted(t["name"] for t in tools), sorted(TOOL_NAMES))
        for tool in tools:
            properties = set(tool["inputSchema"].get("properties", {}))
            self.assertEqual(properties & FORBIDDEN_PROPERTIES, set(), tool["name"])

    def test_every_tool_and_each_reachable_error_class(self) -> None:
        self.set_auto_approve()

        async def body(session: Any) -> dict[str, Any]:
            out: dict[str, Any] = {}
            call = session.call_tool
            out["find"] = await call("find", {"question": "retry backoff"})
            out["read"] = await call("read_page", {"path": RETRY_PAGE})
            out["propose"] = await call("propose", {"edits": create_edits("timeout-policy"), "name": "s1"})
            # The same name while s1 still waits in the proposals directory (after promote it is archived and free).
            out["e_exists"] = await call("propose", {"edits": create_edits("other-policy"), "name": "s1"})
            out["promote"] = await call("promote", {"name": "s1"})
            out["lint"] = await call("lint", {"health": True})
            out["info"] = await call("info", {})
            out["findings"] = await call("findings", {})
            out["review_state"] = await call("review_state", {"pages": ["decisions/timeout-policy.md"]})
            out["e_value"] = await call("find", {"question": "x", "max_pages": 6})
            out["e_name"] = await call("promote", {"name": "../x"})
            out["e_outside"] = await call("read_page", {"path": "../notes.md"})
            out["e_missing"] = await call("read_page", {"path": "decisions/none.md"})
            out["e_contract"] = await call("propose", {"edits": [], "name": "s2"})
            return out

        out = self.run_session(["--by", "alice"], body)
        for key in ("find", "read", "propose", "promote", "lint", "info", "findings", "review_state"):
            with self.subTest(tool=key):
                self.assertFalse(self.payload(out[key])[0], self.dump(out[key]))
        self.assertEqual(self.payload(out["promote"])[1]["approved_paths"], ["decisions/timeout-policy.md"])
        self.assertEqual(self.payload(out["info"])[1]["adapter"]["actor"], {"name": "alice", "source": "flag"})
        self.assertIsNotNone(self.payload(out["info"])[1]["adapter"]["protocol_version"])
        expected = {
            "e_value": ("ValueError", 1),
            "e_name": ("ValueError", 1),
            "e_outside": ("PathOutsideRootError", 7),
            "e_missing": ("SourceMissingError", 5),
            "e_contract": ("ContractViolationError", 4),
            "e_exists": ("OutputWriteError", 6),
        }
        for key, (name, code) in expected.items():
            with self.subTest(error=key):
                is_error, data = self.payload(out[key])
                self.assertTrue(is_error)
                self.assertEqual((data["error"], data["exit_code"]), (name, code))
                self.assertEqual(set(data), {"error", "exit_code", "message"})

    def test_a_stale_update_is_an_exit_9_error_result(self) -> None:
        async def body(session: Any) -> Any:
            read = self.payload(await session.call_tool("read_page", {"path": RETRY_PAGE}))[1]
            edit = {
                "path": RETRY_PAGE,
                "action": "update",
                "content": new_page("retry-policy"),
                "base_sha256": read["sha256"],
            }
            await session.call_tool("propose", {"edits": [edit], "name": "u1"})
            (self.wiki / RETRY_PAGE).write_text(new_page("retry-policy", "By hand."), encoding="utf-8")
            return await session.call_tool("promote", {"name": "u1"})

        is_error, data = self.payload(self.run_session([], body))
        self.assertTrue(is_error)
        self.assertEqual(data["exit_code"], 9)

    def test_disable_tool_promote_is_propose_only_mode(self) -> None:
        async def body(session: Any) -> Any:
            names = [t.name for t in (await session.list_tools()).tools]
            try:
                refused = self.dump(await session.call_tool("promote", {"name": "x"})).get("isError", False)
            except Exception:  # the SDK may raise for an unknown tool instead of returning an error result
                refused = True
            others = [
                await session.call_tool("find", {"question": "retry"}),
                await session.call_tool("read_page", {"path": RETRY_PAGE}),
                await session.call_tool("propose", {"edits": create_edits("p-only"), "name": "p1"}),
                await session.call_tool("lint", {}),
                await session.call_tool("info", {}),
                await session.call_tool("findings", {}),
                await session.call_tool("review_state", {}),
            ]
            return names, refused, others

        names, refused, others = self.run_session(["--disable-tool", "promote"], body)
        self.assertEqual(sorted(names), sorted(n for n in TOOL_NAMES if n != "promote"))
        self.assertTrue(refused)
        self.assertTrue(all(not self.payload(r)[0] for r in others))

    def test_the_trace_records_each_request(self) -> None:
        trace = self.base / "trace.jsonl"

        async def body(session: Any) -> None:
            await session.list_tools()
            await session.call_tool("find", {"question": "retry SECRET"})
            await session.call_tool("find", {"question": "x", "max_pages": 6})

        self.run_session(["--trace", str(trace)], body)
        text = trace.read_text(encoding="utf-8")
        self.assertNotIn("SECRET", text)
        records = [json.loads(line) for line in text.splitlines()]
        self.assertTrue(all(tuple(r) == TRACE_KEYS for r in records), records)
        methods = [(r["method"], r["tool"], r["outcome"]) for r in records]
        self.assertEqual(methods[0], ("initialize", None, 0))
        self.assertIn(("tools/list", None, 0), methods)
        self.assertIn(("tools/call", "find", 0), methods)
        self.assertIn(("tools/call", "find", 1), methods)

    def launch_raw(self, *flags: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-c", SERVER_BOOT, "--root", str(self.root), *flags],
            input="",
            capture_output=True,
            text=True,
            env={**os.environ, **self.server_env()},
            cwd=self.root,
            timeout=60,
            check=False,
        )

    def test_launch_errors_exit_2_before_serving(self) -> None:
        cases = {
            "unknown tool": ["--disable-tool", "nope"],
            "trace inside the wiki": ["--trace", str(self.wiki / "trace.jsonl")],
            "unwritable trace": ["--trace", str(self.base / "missing" / "trace.jsonl")],
            "proposals dir outside the root": ["--proposals-dir", str(self.base / "elsewhere")],
        }
        for label, flags in cases.items():
            with self.subTest(label):
                result = self.launch_raw(*flags)
                self.assertEqual(result.returncode, EXIT_LAUNCH_ERROR, result.stderr)
                self.assertEqual(result.stdout, "")
        self.assertFalse((self.wiki / "trace.jsonl").exists())

    def test_stdout_carries_protocol_frames_only(self) -> None:
        requests: list[dict[str, Any]] = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "raw", "version": "1"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "find", "arguments": {"question": "retry"}},
            },
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "lint", "arguments": {"health": True}},
            },
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"name": "read_page", "arguments": {"path": "../x"}},
            },
        ]
        proc = subprocess.Popen(
            [sys.executable, "-c", SERVER_BOOT, "--root", str(self.root)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, **self.server_env()},
            cwd=self.root,
        )
        assert proc.stdin is not None and proc.stdout is not None
        ids_seen: set[int] = set()
        for request in requests:
            proc.stdin.write(json.dumps(request).encode() + b"\n")
            proc.stdin.flush()
            if "id" in request:
                while request["id"] not in ids_seen:
                    line = proc.stdout.readline()
                    self.assertTrue(line, "server closed stdout early")
                    message = json.loads(line)
                    self.assertEqual(message.get("jsonrpc"), "2.0", line)
                    if "id" in message and "method" not in message:
                        ids_seen.add(message["id"])
        proc.stdin.close()
        rest = proc.stdout.read()
        proc.wait(timeout=60)
        stderr = proc.stderr.read().decode() if proc.stderr else ""
        for line in rest.splitlines():
            self.assertEqual(json.loads(line).get("jsonrpc"), "2.0", line)
        self.assertEqual(proc.returncode, 0, stderr)
        self.assertIn("wiki-studio-mcp: wiki", stderr)


@unittest.skipUnless(HAS_MCP, "the mcp extra is not installed")
class TestToolWrapper(unittest.TestCase):
    """The SDK wrapper: the method's own signature, and an unexpected exception as InternalError."""

    def test_an_unexpected_exception_is_internal_error_with_the_class_name_only(self) -> None:
        from wiki_studio.mcp_adapter.server import as_tool

        def broken(question: str) -> dict[str, Any]:
            raise RuntimeError(f"/private/path {question}")

        with self.assertLogs("wiki_studio.mcp_adapter.server"):
            result = as_tool("find", broken)(question="q").model_dump(by_alias=True)
        self.assertTrue(result["isError"])
        self.assertEqual(
            json.loads(result["content"][0]["text"]),
            {"error": "InternalError", "exit_code": 1, "message": "RuntimeError"},
        )

    def test_the_wrapper_publishes_the_methods_signature(self) -> None:
        import inspect

        from wiki_studio.mcp_adapter.server import as_tool

        config = parse_launch(["--root", str(FIXTURE_ROOT)], env={})
        wrapped = as_tool("find", WikiTools(config).find)
        self.assertEqual(list(inspect.signature(wrapped).parameters), ["question", "max_pages", "max_bytes", "ranker"])


if __name__ == "__main__":
    unittest.main()
