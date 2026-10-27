# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.8.0 (US5): the MCP conformance suite, ``conformance/mcp/run.py`` (FR-043, FR-045).

``TestSuiteAgainstWikiStudioMcp`` runs the whole suite against
``wiki-studio-mcp`` through the SDK's client for every tested protocol
version; it is skipped when ``mcp`` is not importable (the dev group and the
``mcp-min`` and ``mcp-latest`` jobs install it). The other classes need no
SDK: they drive the runner's case logic through an in-process session over
the adapter's tools, and check ``check-host-run`` on recorded runs built here.
"""

from __future__ import annotations

import ast
import asyncio
import contextlib
import importlib.util
import io
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from conformance.mcp import run
from wiki_studio import errors
from wiki_studio.mcp_adapter.config import parse_launch
from wiki_studio.mcp_adapter.tools import WikiTools, error_payload

HAS_MCP = importlib.util.find_spec("mcp") is not None
RUNNER = Path(run.__file__)
SERVER_BOOT = "import sys; from wiki_studio.mcp_adapter import main; sys.exit(main(sys.argv[1:]))"
HOST_PROTOCOL = "2025-11-25"
HOST_ACTOR = "claude-code-host-run"


def server_command() -> str:
    """The installed ``wiki-studio-mcp`` beside this interpreter, else the same entry point through ``-c``."""
    script = Path(sys.executable).with_name("wiki-studio-mcp")
    if script.exists():
        return shlex.join([str(script), "--root", run.ROOT_PLACEHOLDER])
    return shlex.join([sys.executable, "-c", SERVER_BOOT, "--root", run.ROOT_PLACEHOLDER])


def run_main(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = run.main(list(argv))
    return code, out.getvalue()


class TestRunnerIsAdapterAgnostic(unittest.TestCase):
    def test_the_runner_imports_nothing_from_wiki_studio(self) -> None:
        for path in sorted(RUNNER.parent.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    with self.subTest(file=path.name, module=name):
                        self.assertNotEqual(name.split(".")[0], "wiki_studio")

    def test_the_tool_contract_matches_the_adapters(self) -> None:
        from wiki_studio.mcp_adapter.config import TOOL_NAMES

        self.assertEqual(run.TOOL_NAMES, TOOL_NAMES)

    def test_the_known_sha256_is_the_fixture_pages(self) -> None:
        page = run.FIXTURE_PROJECT / run.WIKI_REL / run.KNOWN_PAGE
        self.assertEqual(run.sha256_bytes(page.read_bytes()), run.KNOWN_SHA256)

    def test_without_the_sdk_the_suite_cannot_run(self) -> None:
        if HAS_MCP:
            self.skipTest("the mcp SDK is installed")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code, _ = run_main("--server-cmd", "wiki-studio-mcp")
        self.assertEqual(code, run.EXIT_CANNOT_RUN)
        self.assertIn("needs the MCP SDK", err.getvalue())


class TestRelay(unittest.TestCase):
    def test_the_relay_copies_stdin_through_and_records_stdout_unchanged(self) -> None:
        echo = "import sys; data = sys.stdin.read(); sys.stdout.write(data.upper()); sys.exit(3)"
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "server.stdout"
            result = subprocess.run(
                [sys.executable, str(run.RELAY), str(record), "--", sys.executable, "-c", echo],
                input=b'{"jsonrpc":"2.0"}\n',
                capture_output=True,
                check=False,
            )
            self.assertEqual((result.returncode, result.stdout), (3, b'{"JSONRPC":"2.0"}\n'))
            self.assertEqual(record.read_bytes(), result.stdout)


@unittest.skipUnless(HAS_MCP, "the mcp extra is not installed")
class TestSuiteAgainstWikiStudioMcp(unittest.TestCase):
    """FR-043: the twelve cases pass for each tested protocol version against ``wiki-studio-mcp``."""

    def test_all_twelve_cases_pass_for_every_tested_version(self) -> None:
        code, output = run_main("--server-cmd", server_command())
        self.assertEqual(code, run.EXIT_PASS, output)
        lines = [line for line in output.splitlines() if line.startswith((run.PASS, run.FAIL, run.SKIP))]
        self.assertEqual(len(lines), len(run.TESTED_VERSIONS) * len(run.CASES), output)
        self.assertTrue(all(line.startswith(run.PASS) for line in lines), output)

    def test_the_trace_flag_reaches_every_launch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            trace = Path(tmp) / "trace.jsonl"
            code, output = run_main(
                "--server-cmd", server_command(), "--protocol-version", "2025-06-18", "--trace", str(trace)
            )
            self.assertEqual(code, run.EXIT_PASS, output)
            records = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(sum(r["method"] == "initialize" for r in records), 3)
        self.assertEqual({r["protocol_version"] for r in records}, {"2025-06-18"})


# ── The case logic, without the SDK ──────────────────────────


class _Dumped:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def model_dump(self, **_kwargs: Any) -> dict[str, Any]:
        return self._data


class _Listed:
    def __init__(self, tools: list[_Dumped]) -> None:
        self.tools = tools


class InProcessSession:
    """What the SDK's ``ClientSession`` gives the cases, served in process by the adapter's tools."""

    def __init__(self, tools: WikiTools, extra_tool: str | None = None) -> None:
        self.tools = tools
        self.extra_tool = extra_tool

    async def list_tools(self) -> _Listed:
        names = list(self.tools.registry())
        if self.extra_tool:
            names.append(self.extra_tool)
        return _Listed([_Dumped({"name": name, "inputSchema": {"type": "object", "properties": {}}}) for name in names])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> _Dumped:
        method = self.tools.registry().get(name)
        if method is None:
            raise LookupError(f"unknown tool {name}")
        try:
            payload, is_error = method(**arguments), False
        except (errors.IngestError, ValueError) as exc:
            payload, is_error = error_payload(exc), True
        return _Dumped({"content": [{"type": "text", "text": json.dumps(payload)}], "isError": is_error})


class TestCaseLogic(unittest.TestCase):
    """The runner's cases 2-12 over the fixture, served in process (the SDK transport is CI's part)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-conformance-")
        self.addCleanup(self._tmp.cleanup)
        self.version_run = run.VersionRun("2025-06-18", ["unused"], Path(self._tmp.name).resolve(), None)

    def serve(self, launch: run.Launch, *flags: str, extra_tool: str | None = None) -> InProcessSession:
        config = parse_launch(["--root", str(launch.root), "--by", run.LAUNCH_ACTOR, *flags], env={})
        return InProcessSession(WikiTools(config), extra_tool)

    def statuses(self) -> dict[int, str]:
        return {number: result.status for number, result in self.version_run.results.items()}

    def test_every_case_passes_against_the_adapters_tools(self) -> None:
        vr = self.version_run
        main = vr.launch("main", run.VARIANT_DEFAULT)
        asyncio.run(vr._main_cases(main)(self.serve(main)))
        only = vr.launch("propose-only", run.VARIANT_DEFAULT, *run.DISABLE_PROMOTE)
        asyncio.run(vr._propose_only_cases(only)(self.serve(only, *run.DISABLE_PROMOTE)))
        auto = vr.launch("auto-approve", run.VARIANT_AUTO_APPROVE)
        asyncio.run(vr._auto_approve_cases(auto)(self.serve(auto)))
        details = {n: r.line() for n, r in vr.results.items()}
        self.assertEqual(self.statuses(), dict.fromkeys(range(2, 12), run.PASS), details)
        self.assertIn("propose-only mode", vr.results[2].detail)

    def test_an_extra_tool_fails_the_surface_case(self) -> None:
        vr = self.version_run
        main = vr.launch("main", run.VARIANT_DEFAULT)
        asyncio.run(vr._main_cases(main)(self.serve(main, extra_tool="approve")))
        self.assertEqual(vr.results[2].status, run.FAIL)
        self.assertIn("approve", vr.results[2].detail)

    def test_a_promoting_propose_only_server_fails_the_surface_case(self) -> None:
        vr = self.version_run
        vr.record(2, run.PASS, "surface")
        only = vr.launch("propose-only", run.VARIANT_DEFAULT, *run.DISABLE_PROMOTE)
        asyncio.run(vr._propose_only_cases(only)(self.serve(only)))
        self.assertEqual(vr.results[2].status, run.FAIL)

    def test_a_backend_invocation_fails_case_11(self) -> None:
        vr = self.version_run
        vr.stub_log.write_text("invoked\n", encoding="utf-8")
        main = vr.launch("main", run.VARIANT_DEFAULT)
        asyncio.run(vr._main_cases(main)(self.serve(main)))
        self.assertEqual(vr.results[11].status, run.FAIL)

    def test_stdout_records_must_hold_frames_only(self) -> None:
        vr = self.version_run
        good = vr.base / "good.stdout"
        good.write_bytes(b'{"jsonrpc":"2.0","id":1,"result":{}}\n')
        vr.records = [good]
        asyncio.run(vr.run_case(12, vr.case_clean_stdout))
        self.assertEqual(vr.results[12].status, run.PASS)
        self.assertTrue(run._answered(good))
        bad = vr.base / "bad.stdout"
        bad.write_bytes(b'{"jsonrpc":"2.0","id":1,"result":{}}\nstarting server\n')
        vr.records = [good, bad]
        asyncio.run(vr.run_case(12, vr.case_clean_stdout))
        self.assertEqual(vr.results[12].status, run.FAIL)
        self.assertFalse(run._answered(vr.base / "missing.stdout"))


# ── check-host-run ───────────────────────────────────────────


class TestCheckHostRun(unittest.TestCase):
    """FR-045: cases 2-9 on a run's trace and end state, here a scenario run through the adapter's tools."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-host-run-")
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name).resolve()

    def record_run(self, variant: str = run.VARIANT_DEFAULT) -> Path:
        """Do the scenario's six steps in process and record the run directory as the README describes."""
        root = run.copy_fixture(self.base / "work", variant)
        tools = WikiTools(parse_launch(["--root", str(root), "--by", HOST_ACTOR], env={}))
        steps = [
            ("tools/list", None),
            ("tools/call", run.TOOL_FIND),
            ("tools/call", run.TOOL_READ_PAGE),
            ("tools/call", run.TOOL_PROPOSE),
            ("tools/call", run.TOOL_PROMOTE),
            ("tools/call", run.TOOL_REVIEW_STATE),
        ]
        tools.find("How do we retry outbound calls?")
        base = tools.read_page(run.KNOWN_PAGE)["sha256"]
        content = run.page_text("retry-policy", "Retry at most five times.")
        edit = {"path": run.KNOWN_PAGE, "action": "update", "content": content, "base_sha256": base}
        tools.propose([edit], name="host-run-update", rationale="Cap the retries.")
        tools.promote("host-run-update")
        tools.review_state([run.KNOWN_PAGE])
        run_dir = self.base / "run"
        run_dir.mkdir()
        trace = [
            {
                "ts": "2026-10-27T12:00:00.000Z",
                "method": method,
                "tool": tool,
                "protocol_version": HOST_PROTOCOL,
                "client_name": "claude-code",
                "client_version": "9.9.9",
                "outcome": 0,
                "duration_ms": 3,
            }
            for method, tool in [("initialize", None), *steps]
        ]
        (run_dir / run.RUN_TRACE).write_text("".join(json.dumps(r) + "\n" for r in trace), encoding="utf-8")
        shutil.copytree(root, run_dir / run.RUN_END_STATE)
        for derived in (run_dir / run.RUN_END_STATE / "knowledge").glob(run.DERIVED_PREFIX + "*"):
            derived.unlink()
        self.write_manifest(run_dir)
        return run_dir

    def write_manifest(self, run_dir: Path, **overrides: Any) -> None:
        manifest = {
            "claude_code_version": "9.9.9",
            "model": "claude-opus-5-5",
            "wiki_studio_commit": "0" * 40,
            "wiki_studio_version": "0.8.0",
            "mcp_version": "2.3.0",
            "protocol_version": HOST_PROTOCOL,
            "scenario_sha256": run.sha256_bytes(run.SCENARIO.read_bytes()),
            "end_state_sha256": run.tree_sha256(run_dir / run.RUN_END_STATE),
            **overrides,
        }
        (run_dir / run.RUN_MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    def statuses(self, run_dir: Path) -> dict[int, str]:
        return {r.number: r.status for r in run.check_host_run(run_dir)}

    def test_a_scenario_run_passes_cases_2_to_9_and_the_verdict_is_recorded(self) -> None:
        run_dir = self.record_run()
        results = run.check_host_run(run_dir)
        self.assertEqual({r.number: r.status for r in results}, dict.fromkeys(run.HOST_RUN_CASES, run.PASS), results)
        code, output = run_main("check-host-run", "--run", str(run_dir), "--record")
        self.assertEqual(code, run.EXIT_PASS, output)
        verdict = json.loads((run_dir / run.RUN_MANIFEST).read_text(encoding="utf-8"))["verdict"]
        self.assertTrue(verdict["passed"])
        self.assertEqual(set(verdict["cases"]), {str(n) for n in run.HOST_RUN_CASES})

    def test_an_auto_approving_wiki_fails_case_9(self) -> None:
        statuses = self.statuses(self.record_run(run.VARIANT_AUTO_APPROVE))
        self.assertEqual(statuses[9], run.FAIL)

    def test_a_tampered_end_state_or_scenario_fails_case_2(self) -> None:
        run_dir = self.record_run()
        (run_dir / run.RUN_END_STATE / "extra.txt").write_text("x", encoding="utf-8")
        statuses = self.statuses(run_dir)
        self.assertEqual(statuses[2], run.FAIL)
        self.assertEqual(statuses[8], run.FAIL)
        self.write_manifest(run_dir, scenario_sha256="0" * 64)
        self.assertEqual(self.statuses(run_dir)[2], run.FAIL)

    def test_a_trace_without_promote_fails_cases_6_and_9(self) -> None:
        run_dir = self.record_run()
        trace = run_dir / run.RUN_TRACE
        lines = [line for line in trace.read_text(encoding="utf-8").splitlines() if '"promote"' not in line]
        trace.write_text("\n".join(lines) + "\n", encoding="utf-8")
        statuses = self.statuses(run_dir)
        self.assertEqual((statuses[6], statuses[9]), (run.FAIL, run.FAIL))

    def test_a_missing_run_entry_cannot_be_checked(self) -> None:
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code, _ = run_main("check-host-run", "--run", str(self.base / "nothing"))
        self.assertEqual(code, run.EXIT_CANNOT_RUN)

    def test_tree_hash_prints_the_end_state_hash(self) -> None:
        run_dir = self.record_run()
        code, output = run_main("tree-hash", str(run_dir / run.RUN_END_STATE))
        self.assertEqual((code, output.strip()), (run.EXIT_PASS, run.tree_sha256(run_dir / run.RUN_END_STATE)))


if __name__ == "__main__":
    unittest.main()
