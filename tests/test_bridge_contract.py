# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The memkernel bridge path, replayed without memkernel (0.7.0 US1, FR-001 and FR-002).

memkernel's ``propose_and_promote`` (gosha70/memkernel ``src/memkernel/wiki/studio.py``
lines 151-193 at main 641a508, verified 2026-10-26) builds one ``create`` per
exported page, one ``append-index`` holding every index line and one
``append-log`` holding every log line, then calls ``api.propose(edits, paths,
name=..., source="memkernel wiki_export", backend="memkernel")`` and
``api.promote(proposal, paths)`` with ``paths = WikiPaths.for_root(project_root,
wiki_dir=..., proposals_dir=<root>/.memkernel/wiki-proposals)``. The helpers
below replay that call sequence, and the page shape ``WikiExporter._page_for``
renders (``sync.py`` lines 254-278: ``status: draft``, the extra keys
``memkernel_ref`` and ``memory_type``, a ``memkernel://<project>/<ref>``
source). Nothing in this module imports memkernel; the real packages meet in
``tests/integration/``.
"""

from __future__ import annotations

import datetime
import json
import tempfile
import threading
import time
import unittest
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

from tests.conftest import run_cli
from tests.test_cli_contract import _proposals_dir
from tests.test_promote_concurrency import _spawn, _wait_for
from tests.test_promote_recovery import _Fail, _receipt, _tree
from wiki_studio import api, promoter
from wiki_studio.api import PageEdit
from wiki_studio.audit import payload_digest
from wiki_studio.errors import ContractViolationError, OutputWriteError, PromoteValidationError
from wiki_studio.lint import list_pages
from wiki_studio.paths import WikiPaths
from wiki_studio.wikilock import lock_path_for

if TYPE_CHECKING:
    import subprocess
    from collections.abc import Callable

# memkernel.wiki.sync.DEFAULT_PROPOSALS_SUBDIR and the constants of memkernel.wiki.studio.
BRIDGE_PROPOSALS_SUBDIR = Path(".memkernel") / "wiki-proposals"
BRIDGE_SOURCE = "memkernel wiki_export"
BRIDGE_BACKEND = "memkernel"
BRIDGE_RATIONALE = "memkernel export"
# memkernel.wiki.sync.PLACEHOLDER and PAGE_SECTIONS["concept"].
PLACEHOLDER = "_Not recorded in memory — curate before marking this page stable._"
CONCEPT_SECTIONS = ("Summary", "Key ideas", "Where this shows up", "Related")
TODAY = "2026-10-26"
PROJECT = "wiki-studio"
RECEIPT = "receipt.json"


class GateError(RuntimeError):
    """memkernel.wiki.studio.GateError: the gate rejected or failed to apply an export."""


@dataclass(frozen=True)
class GatedPage:
    """memkernel.wiki.studio.GatedPage: one page of an export plus its index and log lines."""

    path: str
    content: str
    index_line: str | None
    log_line: str | None


def memkernel_page(slug: str, title: str, ref: str, *, memory_type: str = "fact", body: str = "Body.") -> GatedPage:
    """A concept page as ``WikiExporter._page_for`` + ``render_page`` write it, with its index and log lines."""
    sections: list[str] = []
    for i, heading in enumerate(CONCEPT_SECTIONS):
        sections.append(f"## {heading}\n\n{body if i == 0 else PLACEHOLDER}\n")
    content = (
        "---\n"
        f"page_type: concept\nslug: {slug}\ntitle: {title}\nstatus: draft\nlast_reviewed: {TODAY}\n"
        f"memkernel_ref: {ref}\nmemory_type: {memory_type}\n"
        f'sources:\n  - url: "memkernel://{PROJECT}/{ref}"\n    retrieved: {TODAY}\n'
        "---\n\n"
        f"# {title}\n\n" + "\n".join(sections)
    )
    rel = f"concepts/{slug}.md"
    return GatedPage(
        path=rel,
        content=content,
        index_line=f"- [{title}]({rel}) — draft compiled from memkernel ({memory_type}).",
        log_line=f"- {TODAY} — created `{slug}` (concept): compiled from memkernel {ref}",
    )


def export_name() -> str:
    """``memkernel-export-<ts>-<hex>`` as ``WikiExporter._export_gated`` names a submission (sync.py:218)."""
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"memkernel-export-{stamp}-{uuid.uuid4().hex[:8]}"


def bridge_paths(root: Path) -> WikiPaths:
    """The layout memkernel passes: the project root, its wiki, and the proposals directory under ``.memkernel/``."""
    return WikiPaths.for_root(root, wiki_dir=root / "knowledge" / "wiki", proposals_dir=root / BRIDGE_PROPOSALS_SUBDIR)


def bridge_edits(pages: list[GatedPage]) -> list[PageEdit]:
    """``propose_and_promote`` lines 164-187: one create per page, then one append-index and one append-log."""
    index_lines = [page.index_line for page in pages if page.index_line is not None]
    log_lines = [page.log_line for page in pages if page.log_line is not None]
    edits = [
        PageEdit(path=page.path, action="create", new_content=page.content, rationale=BRIDGE_RATIONALE)
        for page in pages
    ]
    if index_lines:
        edits.append(
            PageEdit(
                path="index.md", action="append-index", new_content="\n".join(index_lines), rationale=BRIDGE_RATIONALE
            )
        )
    if log_lines:
        edits.append(
            PageEdit(path="log.md", action="append-log", new_content="\n".join(log_lines), rationale=BRIDGE_RATIONALE)
        )
    return edits


def propose_and_promote(
    pages: list[GatedPage],
    paths: WikiPaths,
    name: str,
    *,
    before_promote: Callable[[Path], None] | None = None,
) -> Path:
    """``propose_and_promote`` lines 166-193: propose, promote, and wrap any failure as ``GateError``.

    ``before_promote`` runs between the two calls with the proposal directory
    (the window in which another writer may land); it is the test's hook, not
    memkernel's. Returns the proposal directory the bridge handed to ``promote``.
    """
    try:
        proposal = api.propose(bridge_edits(pages), paths, name=name, source=BRIDGE_SOURCE, backend=BRIDGE_BACKEND)
        if before_promote is not None:
            before_promote(proposal)
        api.promote(proposal, paths)
    except Exception as exc:
        raise GateError(f"wiki-studio gate rejected the export: {exc}") from exc
    return proposal


def submission(proposal: Path) -> dict[str, bytes]:
    """``plan.json`` and every ``preview/`` file of a proposal, by relative path, as bytes."""
    return {
        p.relative_to(proposal).as_posix(): p.read_bytes()
        for p in proposal.rglob("*")
        if p.is_file() and (p.name == "plan.json" or p.relative_to(proposal).parts[0] == "preview")
    }


def archive_writes(name: str, pages: list[GatedPage]) -> list[str]:
    """The wiki-relative paths a bridge export of ``pages`` writes, receipt order aside."""
    return sorted(
        [page.path for page in pages]
        + ["index.md", "log.md", f".audit/proposals/{name}/plan.json", f".audit/proposals/{name}/proposal.md"]
    )


class _BridgeCase(unittest.TestCase):
    """A project root with a wiki scaffolded by ``api.init`` and no proposals directory yet (memkernel's start)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-bridge-")
        self.root = Path(self._tmp.name).resolve()
        self.paths = bridge_paths(self.root)
        self.wiki = self.paths.wiki_dir
        api.init(self.paths)
        self.pages = [
            memkernel_page(
                "retry-budget", "Retry budget", "mem-0001", memory_type="fact", body="Three retries, then stop."
            ),
            memkernel_page("prefer-small-commits", "Prefer small commits", "mem-0002", memory_type="convention"),
        ]

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _cli_writer_lands(self, _proposal: Path) -> None:
        """A cooperating wiki-studio writer (the default layout) promotes a page while the export is proposed."""
        api.promote(_proposals_dir(self.root), WikiPaths.for_root(self.root))

    def assert_pages_landed(self, pages: list[GatedPage]) -> None:
        for page in pages:
            self.assertEqual((self.wiki / page.path).read_bytes(), page.content.encode("utf-8"), page.path)
        index = (self.wiki / "index.md").read_text(encoding="utf-8")
        log = (self.wiki / "log.md").read_text(encoding="utf-8")
        for page in pages:
            assert page.index_line is not None and page.log_line is not None
            self.assertEqual(index.count(page.index_line), 1, page.path)
            self.assertEqual(log.count(page.log_line), 1, page.path)


class TestBridgeExport(_BridgeCase):
    """FR-001: the call sequence of ``propose_and_promote`` against the live API."""

    def test_pages_index_and_log_land_on_current_content_with_a_committed_receipt_and_archive(self) -> None:
        name = export_name()
        captured: dict[str, bytes] = {}
        digests: list[str] = []

        def between(proposal: Path) -> None:
            captured.update(submission(proposal))
            digests.append(payload_digest(proposal))
            self._cli_writer_lands(proposal)

        proposal = propose_and_promote(self.pages, self.paths, name, before_promote=between)
        # (a) The pages land byte for byte; the one index and the one log append
        # land on the content the other writer left, not on the content seen at propose.
        self.assert_pages_landed(self.pages)
        index = (self.wiki / "index.md").read_text(encoding="utf-8")
        log = (self.wiki / "log.md").read_text(encoding="utf-8")
        cli_index = "- [CLI Fixture](incidents/cli-fixture.md) — fixture."
        self.assertIn(cli_index, index)
        self.assertIn("promote cli-fixture (incident).", log)
        assert self.pages[0].index_line is not None and self.pages[1].index_line is not None
        self.assertLess(index.index(cli_index), index.index(self.pages[0].index_line))
        self.assertLess(index.index(self.pages[0].index_line), index.index(self.pages[1].index_line))
        self.assertTrue((self.wiki / "incidents" / "cli-fixture.md").is_file(), "the other writer's page stays")
        # (b) The receipt is committed, carries the submission digest, and the
        # archived plan.json and preview/ are the submitted bytes.
        self.assertFalse(proposal.exists(), "the source directory was archived")
        archive = self.paths.applied_dir / name
        self.assertEqual(archive, self.root / BRIDGE_PROPOSALS_SUBDIR / ".applied" / name)
        receipt = _receipt(archive)
        self.assertEqual(receipt["state"], "committed")
        self.assertEqual(receipt["proposal"], name)
        self.assertEqual(receipt["submission_digest"], digests[0])
        self.assertEqual(receipt["submission_digest"], payload_digest(archive))
        self.assertEqual(receipt["promoter"]["entry_point"], "api")
        self.assertEqual(sorted(receipt["written_paths"]), archive_writes(name, self.pages))
        self.assertEqual(submission(archive), captured)
        plan = json.loads((archive / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual((plan["version"], plan["source_path"], plan["backend"]), (1, BRIDGE_SOURCE, BRIDGE_BACKEND))
        self.assertEqual(
            [(e["path"], e["action"]) for e in plan["edits"]],
            [(p.path, "create") for p in self.pages] + [("index.md", "append-index"), ("log.md", "append-log")],
        )
        self.assertEqual((self.wiki / ".audit" / "proposals" / name / "plan.json").read_bytes(), captured["plan.json"])

    def test_the_lock_file_sits_beside_the_wiki_and_the_wiki_lints_clean(self) -> None:
        propose_and_promote(self.pages, self.paths, export_name())
        lock = lock_path_for(self.wiki)
        self.assertTrue(lock.is_file())
        self.assertEqual(lock.parent, self.wiki.resolve().parent)
        self.assertFalse(lock.resolve().is_relative_to(self.wiki.resolve()))
        self.assertEqual(lock.name, ".wiki.wiki-studio.lock")
        self.assertNotIn(lock, list_pages(self.wiki))
        result = api.lint(self.paths)
        self.assertEqual(result.violations, ())
        self.assertEqual(result.audit_errors, ())
        self.assertEqual(result.pages_checked, 2 + len(self.pages))

    def test_a_second_export_proposed_after_the_first_landed_is_refused_by_propose(self) -> None:
        propose_and_promote(self.pages, self.paths, export_name())
        wiki_before = _tree(self.wiki)
        proposals_before = sorted(p.name for p in self.paths.proposals_dir.iterdir())
        again = [memkernel_page("retry-budget", "Retry budget", "mem-0001", body="Exported again.")]
        with self.assertRaises(ContractViolationError) as ctx:
            api.propose(
                bridge_edits(again), self.paths, name=export_name(), source=BRIDGE_SOURCE, backend=BRIDGE_BACKEND
            )
        self.assertEqual(ctx.exception.exit_code, 4)
        self.assertIn("concepts/retry-budget.md: create target already exists", str(ctx.exception))
        self.assertEqual(sorted(p.name for p in self.paths.proposals_dir.iterdir()), proposals_before)
        self.assertEqual(_tree(self.wiki), wiki_before)
        # The bridge wraps it as its GateError, the same way as any other refusal.
        with self.assertRaises(GateError):
            propose_and_promote(again, self.paths, export_name())
        self.assertEqual(_tree(self.wiki), wiki_before)

    def test_a_second_export_proposed_before_the_first_landed_is_refused_at_promote(self) -> None:
        first_name, second_name = export_name(), export_name()
        first = api.propose(
            bridge_edits(self.pages), self.paths, name=first_name, source=BRIDGE_SOURCE, backend=BRIDGE_BACKEND
        )
        again = [memkernel_page("retry-budget", "Retry budget", "mem-0001", body="Exported again.")]
        second = api.propose(
            bridge_edits(again), self.paths, name=second_name, source=BRIDGE_SOURCE, backend=BRIDGE_BACKEND
        )
        api.promote(first, self.paths)
        self.assert_pages_landed(self.pages)
        wiki_before, second_before = _tree(self.wiki), _tree(second)
        common = [
            "--root",
            str(self.root),
            "--wiki-dir",
            str(self.wiki),
            "--proposals-dir",
            str(self.paths.proposals_dir),
        ]
        result = run_cli("promote", str(second), *common, cwd=self.root)
        self.assertEqual(result.returncode, PromoteValidationError.exit_code, result.stderr)
        self.assertEqual(result.returncode, 9)
        self.assertIn("concepts/retry-budget.md: create target already exists", result.stderr)
        with self.assertRaises(PromoteValidationError) as ctx:
            api.promote(second, self.paths)
        self.assertEqual(ctx.exception.exit_code, 9)
        self.assertEqual(_tree(self.wiki), wiki_before, "nothing written to the wiki")
        self.assertEqual(_tree(second), second_before, "the refused proposal is untouched, no receipt")
        self.assertFalse((self.paths.applied_dir / second_name).exists())
        self.assertTrue((self.paths.applied_dir / first_name / RECEIPT).is_file())

    def test_a_promote_interrupted_after_its_commit_resolves_from_the_receipt_and_reapplies_nothing(self) -> None:
        interruptions = {
            "committed, archive never written": (
                "wiki_studio.promoter._write_archive_file",
                lambda: OSError("disk full"),
                None,
            ),
            "committing, rewrite as committed failed": (
                "wiki_studio.promoter._write_receipt",
                lambda: _Fail(promoter._write_receipt, 2, OSError("disk full during the committed rewrite")),
                OutputWriteError,
            ),
        }
        for label, (target, side_effect, raises) in interruptions.items():
            with self.subTest(interruption=label):
                suffix = "a" if raises is None else "b"
                pages = [memkernel_page(f"page-{suffix}", f"Page {suffix.upper()}", f"mem-{suffix}")]
                name = export_name()
                proposal = api.propose(
                    bridge_edits(pages), self.paths, name=name, source=BRIDGE_SOURCE, backend=BRIDGE_BACKEND
                )
                with patch(target, side_effect=side_effect()):
                    if raises is None:
                        self.assertIsNone(api.promote(proposal, self.paths).archived_dir)
                    else:
                        with self.assertRaises(raises):
                            api.promote(proposal, self.paths)
                # The commit happened: the receipt is in the proposal directory, the archive is not published.
                self.assertTrue((proposal / RECEIPT).is_file())
                self.assertFalse((self.paths.applied_dir / name).exists())
                self.assert_pages_landed(pages)
                after_commit = _tree(self.wiki)
                retry = api.promote(proposal, self.paths)
                self.assertEqual(retry.archived_dir, self.paths.applied_dir / name)
                self.assertEqual(sorted(retry.applied_paths), archive_writes(name, pages))
                self.assertEqual(_tree(self.wiki), after_commit, "the retry re-applied nothing")
                self.assert_pages_landed(pages)
                self.assertFalse(proposal.exists())
                self.assertEqual(_receipt(self.paths.applied_dir / name)["state"], "committed")


class TestBridgeAndCliWriters(_BridgeCase):
    """FR-002: a CLI ``promote`` (a subprocess, via the bootstrap) contends with a bridge export in ``api.promote``."""

    def _assert_both_landed(self, name: str, cli_prop: Path, *, bridge_first: bool) -> None:
        self.assert_pages_landed(self.pages)
        self.assertTrue((self.wiki / "incidents" / "cli-fixture.md").is_file())
        index = (self.wiki / "index.md").read_text(encoding="utf-8")
        log = (self.wiki / "log.md").read_text(encoding="utf-8")
        cli_index, cli_log = "- [CLI Fixture](incidents/cli-fixture.md) — fixture.", "promote cli-fixture (incident)."
        self.assertEqual(index.count(cli_index), 1)
        self.assertEqual(log.count(cli_log), 1)
        assert self.pages[0].index_line is not None and self.pages[0].log_line is not None
        if bridge_first:
            self.assertLess(index.index(self.pages[0].index_line), index.index(cli_index))
            self.assertLess(log.index(self.pages[0].log_line), log.index(cli_log))
        else:
            self.assertLess(index.index(cli_index), index.index(self.pages[0].index_line))
            self.assertLess(log.index(cli_log), log.index(self.pages[0].log_line))
        bridge_archive = self.paths.applied_dir / name
        cli_archive = WikiPaths.for_root(self.root).applied_dir / cli_prop.name
        self.assertFalse(cli_prop.exists())
        for archive, entry_point in ((bridge_archive, "api"), (cli_archive, "cli")):
            receipt = _receipt(archive)
            self.assertEqual(receipt["state"], "committed", archive)
            self.assertEqual(receipt["promoter"]["entry_point"], entry_point)
            self.assertGreaterEqual(receipt["lock_wait_seconds"], 0.0)
        self.assertEqual(sorted(_receipt(bridge_archive)["written_paths"]), archive_writes(name, self.pages))
        for archived in (name, cli_prop.name):
            self.assertTrue((self.wiki / ".audit" / "proposals" / archived / "plan.json").is_file(), archived)
        result = api.lint(self.paths)
        self.assertEqual((result.violations, result.audit_errors), ((), ()))

    def test_a_cli_promote_started_during_a_bridge_export_waits_for_the_lock_and_both_land(self) -> None:
        name = export_name()
        proposal = api.propose(
            bridge_edits(self.pages), self.paths, name=name, source=BRIDGE_SOURCE, backend=BRIDGE_BACKEND
        )
        cli_prop = _proposals_dir(self.root)
        sync = self.root / "sync"
        sync.mkdir()
        real_apply = promoter._apply_planned
        children: list[subprocess.Popen[str]] = []

        def spawn_then_apply(planned: list[promoter._PlannedWrite], paths: WikiPaths) -> list[str]:
            # Inside api.promote, lock held, before the commit: the CLI promote starts and must wait.
            child = _spawn(sync, self.root, "promote", str(cli_prop), "--root", str(self.root))
            children.append(child)
            time.sleep(0.5)
            self.assertIsNone(child.poll(), "the CLI promote finished while the bridge export held the lock")
            self.assertFalse((sync / "staged").exists(), "the CLI promote staged while the bridge export held the lock")
            return real_apply(planned, paths)

        try:
            with patch("wiki_studio.promoter._apply_planned", side_effect=spawn_then_apply):
                result = api.promote(proposal, self.paths)
            self.assertEqual(result.archived_dir, self.paths.applied_dir / name)
            child = children[0]
            self.assertTrue(_wait_for(sync / "staged"), "the CLI promote never staged after the bridge export released")
            (sync / "go").write_text("go\n", encoding="utf-8")
            _, err = child.communicate(timeout=60)
            self.assertEqual(child.returncode, 0, err)
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
        self._assert_both_landed(name, cli_prop, bridge_first=True)

    def test_a_bridge_export_started_during_a_held_cli_promote_waits_for_the_lock_and_both_land(self) -> None:
        name = export_name()
        proposal = api.propose(
            bridge_edits(self.pages), self.paths, name=name, source=BRIDGE_SOURCE, backend=BRIDGE_BACKEND
        )
        cli_prop = _proposals_dir(self.root)
        sync = self.root / "sync"
        sync.mkdir()
        child = _spawn(sync, self.root, "promote", str(cli_prop), "--root", str(self.root))
        outcomes: list[api.PromoteResult | BaseException] = []

        def bridge_promote() -> None:
            try:
                outcomes.append(api.promote(proposal, self.paths))
            except BaseException as exc:  # reported by the assertions below
                outcomes.append(exc)

        try:
            self.assertTrue(_wait_for(sync / "staged"), "the CLI promote never reached the post-stage hold")
            thread = threading.Thread(target=bridge_promote)
            thread.start()
            time.sleep(0.5)
            self.assertTrue(thread.is_alive(), "the bridge export finished while the CLI promote held the lock")
            self.assertFalse((proposal / RECEIPT).exists(), "the bridge export wrote a receipt under another's lock")
            (sync / "go").write_text("go\n", encoding="utf-8")
            _, err = child.communicate(timeout=60)
            self.assertEqual(child.returncode, 0, err)
            thread.join(60)
            self.assertFalse(thread.is_alive())
        finally:
            if child.poll() is None:
                child.kill()
        self.assertEqual(len(outcomes), 1)
        outcome = outcomes[0]
        if isinstance(outcome, BaseException):
            raise outcome
        self.assertEqual(outcome.archived_dir, self.paths.applied_dir / name)
        self._assert_both_landed(name, cli_prop, bridge_first=False)


if __name__ == "__main__":
    unittest.main()
