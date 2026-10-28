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
from unittest.mock import patch

from conformance.mcp import run
from wiki_studio import errors
from wiki_studio.mcp_adapter.config import LaunchError, parse_launch
from wiki_studio.mcp_adapter.tools import WikiTools, error_payload
from wiki_studio.mcp_adapter.trace import TRACE_KEYS, WireObserver, open_trace

HAS_MCP = importlib.util.find_spec("mcp") is not None
RUNNER = Path(run.__file__)
SERVER_BOOT = "import sys; from wiki_studio.mcp_adapter import main; sys.exit(main(sys.argv[1:]))"
HOST_PROTOCOL = "2025-11-25"
HOST_ACTOR = "claude-code-host-run"
TRAVERSAL_PATH = "../outside.md"
SCENARIO_QUESTION = "How do we retry outbound calls?"
SCENARIO_PROPOSAL = "host-run-update"
STALE_PROPOSAL = "host-run-stale"
BAD_PROMOTE_NAME = "../x"


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
    """What the SDK's ``ClientSession`` gives the cases, served in process by the adapter's tools.

    An unregistered tool raises, as the SDK's refusal reads; with
    ``unknown_tool_as_payload`` it is instead a wiki-studio error result, as
    a server that ran the name through its own error path would answer.
    """

    def __init__(
        self, tools: WikiTools, extra_tool: str | None = None, *, unknown_tool_as_payload: bool = False
    ) -> None:
        self.tools = tools
        self.extra_tool = extra_tool
        self.unknown_tool_as_payload = unknown_tool_as_payload

    async def list_tools(self) -> _Listed:
        names = list(self.tools.registry())
        if self.extra_tool:
            names.append(self.extra_tool)
        return _Listed([_Dumped({"name": name, "inputSchema": {"type": "object", "properties": {}}}) for name in names])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> _Dumped:
        method = self.tools.registry().get(name)
        if method is None and self.unknown_tool_as_payload:
            payload = error_payload(ValueError(f"unknown tool {name}"))
            return _Dumped({"content": [{"type": "text", "text": json.dumps(payload)}], "isError": True})
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

    def serve(
        self, launch: run.Launch, *flags: str, extra_tool: str | None = None, unknown_tool_as_payload: bool = False
    ) -> InProcessSession:
        config = parse_launch(["--root", str(launch.root), "--by", run.LAUNCH_ACTOR, *flags], env={})
        return InProcessSession(WikiTools(config), extra_tool, unknown_tool_as_payload=unknown_tool_as_payload)

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

    def test_only_the_sdks_unknown_tool_error_passes_the_propose_only_check(self) -> None:
        """A disabled promote must be refused by the SDK (no payload); a wiki-studio error result means it ran."""
        vr = self.version_run
        vr.record(2, run.PASS, "surface")
        only = vr.launch("propose-only", run.VARIANT_DEFAULT, *run.DISABLE_PROMOTE)
        session = self.serve(only, *run.DISABLE_PROMOTE, unknown_tool_as_payload=True)
        asyncio.run(vr._propose_only_cases(only)(session))
        self.assertEqual(vr.results[2].status, run.FAIL)
        self.assertIn("expected the SDK's unknown-tool error", vr.results[2].detail)
        sdk = run.ToolCall(is_error=True, payload=None, text="Unknown tool: promote")
        self.assertTrue(sdk.is_unknown_tool_error())
        self.assertTrue(
            run.ToolCall(is_error=True, payload=None, raised="McpError: Unknown tool").is_unknown_tool_error()
        )
        ran = run.ToolCall(is_error=True, payload=error_payload(ValueError("unknown tool promote")), text="{}")
        self.assertFalse(ran.is_unknown_tool_error())
        self.assertFalse(
            run.ToolCall(is_error=True, payload=None, text="Error executing tool promote").is_unknown_tool_error()
        )
        self.assertFalse(
            run.ToolCall(is_error=False, payload=None, text="Unknown tool: promote").is_unknown_tool_error()
        )

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


class TestNegotiation(unittest.TestCase):
    """Case 1 across the tested versions: a server that negotiates none of them fails, and the suite exits 1."""

    def run_suite_with(self, session: Any) -> tuple[int, str]:
        """The suite's command line with the SDK session replaced by ``session`` (the server always answers)."""
        with (
            patch.object(run, "_require_sdk", lambda: None),
            patch.object(run, "_session", session),
            patch.object(run, "_answered", lambda record: True),
        ):
            return run_main("--server-cmd", "a-server")

    @staticmethod
    def case_lines(output: str, number: int) -> dict[str, str]:
        """Each version's status line for case ``number``, by version."""
        lines = {}
        for line in output.splitlines():
            if f"] {number:02d} {run.CASES[number]}" in line:
                lines[line.split("[", 1)[1].split("]", 1)[0]] = line
        return lines

    def test_a_server_refusing_every_version_fails_case_1_and_the_suite_exits_1(self) -> None:
        async def refuse(launch: run.Launch, version: str, body: Any) -> run.Negotiation:
            return run.Negotiation(refused="the server offered 1999-01-01")

        code, output = self.run_suite_with(refuse)
        self.assertEqual(code, run.EXIT_FAIL, output)
        first = self.case_lines(output, 1)
        self.assertEqual(set(first), set(run.TESTED_VERSIONS), output)
        for version, line in first.items():
            with self.subTest(version=version):
                self.assertTrue(line.startswith(run.FAIL), line)
                self.assertIn("negotiated none of", line)
                self.assertIn("refused cleanly", line)

    def test_a_clean_refusal_passes_case_1_when_another_version_was_negotiated(self) -> None:
        agreed = run.HANDSHAKE_VERSIONS[0]

        async def one_version(launch: run.Launch, version: str, body: Any) -> run.Negotiation:
            if version == agreed:
                return run.Negotiation(negotiated=version)
            return run.Negotiation(refused=f"the server offered {agreed}")

        code, output = self.run_suite_with(one_version)
        self.assertEqual(code, run.EXIT_FAIL, output)  # the cases after case 1 were not reached for the agreed version
        first = self.case_lines(output, 1)
        self.assertEqual(set(first), set(run.TESTED_VERSIONS), output)
        for version, line in first.items():
            with self.subTest(version=version):
                self.assertTrue(line.startswith(run.PASS), line)
        self.assertIn("negotiated", first[agreed])
        self.assertNotIn("negotiated none of", output)
        for version in run.TESTED_VERSIONS:
            if version != agreed:
                self.assertTrue(self.case_lines(output, 2)[version].startswith(run.SKIP), output)


# ── check-host-run ───────────────────────────────────────────


class HostSession:
    """The scenario's steps served in process by the adapter's tools, traced by the wire observer as a host's are."""

    def __init__(self, tools: WikiTools, trace: io.StringIO) -> None:
        self.tools = tools
        self.observer = WireObserver(trace)
        self.next_id = 0

    def exchange(self, method: str, params: dict[str, Any], result: dict[str, Any]) -> None:
        self.next_id += 1
        request = {"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params}
        response = {"jsonrpc": "2.0", "id": self.next_id, "result": result}
        self.observer.inbound(json.dumps(request).encode())
        self.observer.outbound(json.dumps(response).encode())

    def initialize(self) -> None:
        params = {"protocolVersion": HOST_PROTOCOL, "clientInfo": {"name": "claude-code", "version": "9.9.9"}}
        self.exchange("initialize", params, {"protocolVersion": HOST_PROTOCOL, "capabilities": {}})

    def list_tools(self) -> None:
        self.exchange("tools/list", {}, {"tools": [{"name": name} for name in self.tools.registry()]})

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            payload, is_error = self.tools.registry()[name](**arguments), False
        except (errors.IngestError, ValueError) as exc:
            payload, is_error = error_payload(exc), True
        result = {"content": [{"type": "text", "text": json.dumps(payload)}], "isError": is_error}
        self.exchange("tools/call", {"name": name, "arguments": arguments}, result)
        return payload


class TestCheckHostRun(unittest.TestCase):
    """FR-045: cases 2-9 on a run's trace and end state, here a scenario run through the adapter's tools."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-host-run-")
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name).resolve()

    def record_run(self, variant: str = run.VARIANT_DEFAULT, *, traversal: bool = True, refusals: bool = True) -> Path:
        """Do the scenario's ten steps in process (``refusals`` False stops after step 7) and record the run."""
        root = run.copy_fixture(self.base / "work", variant)
        trace = io.StringIO()
        session = HostSession(WikiTools(parse_launch(["--root", str(root), "--by", HOST_ACTOR], env={})), trace)
        session.initialize()
        session.list_tools()
        session.call(run.TOOL_FIND, {"question": SCENARIO_QUESTION})
        base = session.call(run.TOOL_READ_PAGE, {"path": run.KNOWN_PAGE})["sha256"]
        if traversal:
            session.call(run.TOOL_READ_PAGE, {"path": TRAVERSAL_PATH})
        content = run.page_text("retry-policy", "Retry at most five times.")
        edit = {"path": run.KNOWN_PAGE, "action": "update", "content": content, "base_sha256": base}
        session.call(run.TOOL_PROPOSE, {"edits": [edit], "name": SCENARIO_PROPOSAL, "rationale": "Cap the retries."})
        session.call(run.TOOL_PROMOTE, {"name": SCENARIO_PROPOSAL})
        session.call(run.TOOL_REVIEW_STATE, {"pages": [run.KNOWN_PAGE]})
        if refusals:
            # Steps 8-10: the same update with the now stale hash, its refused promote, and a promote of ../x.
            session.call(run.TOOL_PROPOSE, {"edits": [edit], "name": STALE_PROPOSAL, "rationale": "Stale."})
            stale = session.call(run.TOOL_PROMOTE, {"name": STALE_PROPOSAL})
            self.assertEqual(stale.get("exit_code"), run.EXIT_PROMOTE_VALIDATION, stale)
            bad = session.call(run.TOOL_PROMOTE, {"name": BAD_PROMOTE_NAME})
            self.assertEqual((bad.get("error"), bad.get("exit_code")), (run.ERROR_VALUE_ERROR, run.EXIT_VALUE_ERROR))
        run_dir = self.base / "run"
        run_dir.mkdir()
        (run_dir / run.RUN_TRACE).write_text(trace.getvalue(), encoding="utf-8")
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

    def rewrite_trace(self, run_dir: Path, edit: Any) -> None:
        """Apply ``edit`` to each trace record (it returns the record to keep, or None to drop it)."""
        trace = run_dir / run.RUN_TRACE
        records = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines() if line]
        kept = [r for r in map(edit, records) if r is not None]
        trace.write_text("".join(json.dumps(r) + "\n" for r in kept), encoding="utf-8")

    def test_a_scenario_run_proves_cases_2_to_9_and_the_verdict_names_them(self) -> None:
        run_dir = self.record_run()
        results = run.check_host_run(run_dir)
        statuses = {r.number: r.status for r in results}
        proofs = {r.number: r.proof for r in results}
        self.assertEqual(statuses, dict.fromkeys(run.HOST_RUN_CASES, run.PASS), results)
        self.assertEqual(
            proofs,
            {
                2: run.PROOF_TRACE,
                3: run.PROOF_TRACE,
                4: run.PROOF_TRACE,
                5: run.PROOF_END_STATE,
                6: run.PROOF_END_STATE,
                7: run.PROOF_END_STATE,
                8: run.PROOF_TRACE,
                9: run.PROOF_END_STATE,
            },
        )
        details = {r.number: r.detail for r in results}
        self.assertIn("exit 9", details[7])
        self.assertIn("name rule", details[8])
        code, output = run_main("check-host-run", "--run", str(run_dir), "--record")
        self.assertEqual(code, run.EXIT_PASS, output)
        self.assertIn("the host run proves case(s) 2, 3, 4, 5, 6, 7, 8, 9", output)
        self.assertNotIn("not provable from a host run", output)
        self.assertIn("; passed", output)
        self.assertNotIn(f"[{run.PROOF_NONE}]", output)
        verdict = json.loads((run_dir / run.RUN_MANIFEST).read_text(encoding="utf-8"))["verdict"]
        self.assertTrue(verdict["passed"])
        self.assertEqual(
            (verdict["proved"], verdict["not_provable"], verdict["failed"]), ([2, 3, 4, 5, 6, 7, 8, 9], [], [])
        )
        self.assertEqual(set(verdict["cases"]), {str(n) for n in run.HOST_RUN_CASES})
        self.assertEqual(verdict["proof"]["8"], run.PROOF_TRACE)

    def test_a_run_without_the_refusal_steps_cannot_prove_cases_7_and_8(self) -> None:
        run_dir = self.record_run(refusals=False)
        results = {r.number: r for r in run.check_host_run(run_dir)}
        self.assertEqual({n: r.status for n, r in results.items() if n in (7, 8)}, {7: run.SKIP, 8: run.SKIP})
        self.assertEqual((results[7].proof, results[8].proof), (run.PROOF_NONE, run.PROOF_NONE))
        self.assertIn("exit 9", results[7].detail)
        self.assertIn("name rule", results[8].detail)
        code, output = run_main("check-host-run", "--run", str(run_dir), "--record")
        self.assertEqual(code, run.EXIT_FAIL, output)
        self.assertIn("the host run proves case(s) 2, 3, 4, 5, 6, 9", output)
        self.assertIn("not provable from a host run, the protocol suite's: 7, 8", output)
        self.assertIn("not passed: case(s) 7, 8 unproved", output)
        self.assertIn(f"[{run.PROOF_NONE}]", output)
        verdict = json.loads((run_dir / run.RUN_MANIFEST).read_text(encoding="utf-8"))["verdict"]
        self.assertEqual(
            (verdict["proved"], verdict["not_provable"], verdict["failed"]), ([2, 3, 4, 5, 6, 9], [7, 8], [])
        )

    def test_case_7_needs_the_guarded_propose_and_case_8_the_name_rule_error(self) -> None:
        run_dir = self.record_run()
        trace = run_dir / run.RUN_TRACE
        records = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines() if line]
        [r for r in records if r["tool"] == run.TOOL_PROPOSE][-1]["summary"]["with_base_sha256"] = 0
        for record in records:
            if record["tool"] == run.TOOL_PROMOTE and record["outcome"] == run.EXIT_VALUE_ERROR:
                record["summary"]["error"] = None  # an exit-1 promote that is not the name rule's ValueError
        trace.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        results = {r.number: r for r in run.check_host_run(run_dir)}
        self.assertEqual(results[7].status, run.FAIL)
        self.assertIn("no base_sha256", results[7].detail)
        self.assertEqual(results[7].proof, run.PROOF_FAILED)
        self.assertEqual((results[8].status, results[8].proof), (run.SKIP, run.PROOF_NONE))

    def test_the_recorded_trace_carries_the_evidence_keys_and_no_content(self) -> None:
        run_dir = self.record_run()
        text = (run_dir / run.RUN_TRACE).read_text(encoding="utf-8")
        self.assertNotIn("retry outbound", text)
        self.assertNotIn(run.KNOWN_PAGE, text)
        self.assertNotIn(TRAVERSAL_PATH, text)
        self.assertNotIn(BAD_PROMOTE_NAME, text)
        self.assertNotIn(STALE_PROPOSAL, text)
        records = [json.loads(line) for line in text.splitlines()]
        self.assertTrue(all(tuple(r) == TRACE_KEYS == run.TRACE_KEYS for r in records), records)
        for key in ("unknown_tool_names", "unknown_arg_keys", "unknown_result_keys"):
            self.assertEqual({r[key] for r in records}, {None, 0}, key)
        by_tool = {(r["tool"], r["outcome"]): r for r in records}
        self.assertEqual(by_tool[(None, 0)]["tool_names"], sorted(run.TOOL_NAMES))
        self.assertEqual(by_tool[("find", 0)]["arg_keys"], ["question"])
        self.assertEqual(by_tool[("find", 0)]["summary"]["has_sha256"], True)
        self.assertEqual(by_tool[("read_page", 0)]["summary"], {"has_sha256": True})
        self.assertEqual(by_tool[("read_page", 7)]["summary"], {"exit_code": 7, "error": "PathOutsideRootError"})
        self.assertEqual(
            by_tool[("propose", 0)]["summary"],
            {"creates": 0, "updates": 1, "with_base_sha256": 1, "page_id_supplied": 0},
        )
        promoted = by_tool[("promote", 0)]["summary"]
        self.assertGreaterEqual(promoted.pop("applied"), 1)  # the page, and the index and log lines the promote adds
        self.assertEqual(promoted, {"dry_run": False, "approved": 0})
        self.assertEqual(by_tool[("promote", 9)]["summary"], {"exit_code": 9, "error": "PromoteValidationError"})
        self.assertEqual(by_tool[("promote", 1)]["summary"], {"exit_code": 1, "error": "ValueError"})
        self.assertEqual(by_tool[("promote", 1)]["result_keys"], ["error", "exit_code", "message"])
        self.assertEqual(by_tool[("review_state", 0)]["summary"], {"states": 1, "approved": 0})
        self.assertEqual(by_tool[("promote", 0)]["result_keys"], sorted(by_tool[("promote", 0)]["result_keys"]))

    def test_an_auto_approving_wiki_fails_case_9(self) -> None:
        statuses = self.statuses(self.record_run(run.VARIANT_AUTO_APPROVE))
        self.assertEqual(statuses[9], run.FAIL)

    def test_a_seven_page_find_fails_case_3(self) -> None:
        run_dir = self.record_run()

        def seven_pages(record: dict[str, Any]) -> dict[str, Any]:
            if record["tool"] == run.TOOL_FIND:
                record["summary"]["pages"] = 7
            return record

        self.rewrite_trace(run_dir, seven_pages)
        results = {r.number: r for r in run.check_host_run(run_dir)}
        self.assertEqual(results[3].status, run.FAIL)
        self.assertIn("7 pages", results[3].detail)
        self.assertEqual(results[3].proof, run.PROOF_FAILED)

    def test_a_trace_without_the_traversal_refusal_cannot_prove_containment(self) -> None:
        results = {r.number: r for r in run.check_host_run(self.record_run(traversal=False))}
        self.assertEqual(results[4].status, run.FAIL)
        self.assertIn("containment is not provable from this run", results[4].detail)
        self.assertIn("exit 7", results[4].detail)

    def test_a_tools_list_without_the_eight_names_fails_case_2(self) -> None:
        run_dir = self.record_run()

        def drop_promote(record: dict[str, Any]) -> dict[str, Any]:
            if record["method"] == run.METHOD_LIST:
                record["tool_names"] = [n for n in record["tool_names"] if n != run.TOOL_PROMOTE]
            return record

        self.rewrite_trace(run_dir, drop_promote)
        self.assertEqual(self.statuses(run_dir)[2], run.FAIL)

    def test_a_tampered_end_state_or_scenario_fails_case_2(self) -> None:
        run_dir = self.record_run()
        (run_dir / run.RUN_END_STATE / "extra.txt").write_text("x", encoding="utf-8")
        self.assertEqual(self.statuses(run_dir)[2], run.FAIL)
        self.write_manifest(run_dir, scenario_sha256="0" * 64)
        self.assertEqual(self.statuses(run_dir)[2], run.FAIL)

    def test_a_trace_without_promote_fails_cases_6_and_9(self) -> None:
        run_dir = self.record_run()
        self.rewrite_trace(run_dir, lambda r: None if r["tool"] == run.TOOL_PROMOTE else r)
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


# ── The trace file (FR-041) ──────────────────────────────────


class TestTraceFile(unittest.TestCase):
    """``open_trace`` never follows a symlink (these belong with the adapter's trace tests; kept here for US5)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-trace-")
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name).resolve()
        self.root = run.copy_fixture(self.base, run.VARIANT_DEFAULT)
        self.paths = parse_launch(["--root", str(self.root)], env={}).paths
        self.index = self.root / run.WIKI_REL / "index.md"

    def test_a_symlink_into_the_wiki_is_refused_and_the_page_is_untouched(self) -> None:
        before = self.index.read_bytes()
        link = self.base / "trace.jsonl"
        link.symlink_to(self.index)
        with self.assertRaisesRegex(LaunchError, "symlink"):
            open_trace(link, self.paths)
        self.assertEqual(self.index.read_bytes(), before)

    def test_a_symlink_to_an_outside_file_is_refused(self) -> None:
        target = self.base / "elsewhere.log"
        target.write_text("kept\n", encoding="utf-8")
        link = self.base / "trace.jsonl"
        link.symlink_to(target)
        with self.assertRaisesRegex(LaunchError, "symlink"):
            open_trace(link, self.paths)
        self.assertEqual(target.read_text(encoding="utf-8"), "kept\n")

    def test_a_directory_is_not_a_regular_file(self) -> None:
        with self.assertRaisesRegex(LaunchError, "cannot be opened|not a regular file"):
            open_trace(self.base / "project", self.paths)

    def test_a_plain_file_is_appended_to(self) -> None:
        path = self.base / "trace.jsonl"
        path.write_text("first\n", encoding="utf-8")
        with open_trace(path, self.paths) as trace:
            trace.write("second\n")
        self.assertEqual(path.read_text(encoding="utf-8"), "first\nsecond\n")
        with open_trace(self.base / "new.jsonl", self.paths) as trace:
            trace.write("x\n")
        self.assertEqual((self.base / "new.jsonl").read_text(encoding="utf-8"), "x\n")


if __name__ == "__main__":
    unittest.main()
