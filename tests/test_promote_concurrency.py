# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Two writers, no lost update (0.6.0 US1, FR-001..FR-003).

The 22 October reproduction: two promotes that start together used to revert
each other's pages, because the commit wrote back every staged page that
differed from the live one. Now the commit is scoped to the patch-set's own
paths, and the wiki lock serialises cooperating writers before staging.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.conftest import make_repo_layout
from tests.test_audit_flush import _init_repo
from tests.test_cli_contract import _proposals_dir
from wiki_studio import api, audit_flush, promoter
from wiki_studio.audit import append_ingest_log, payload_digest, payload_digest_from_files, proposal_hash
from wiki_studio.audit_flush import detect_pending
from wiki_studio.audit_lint import validate_audit_tree
from wiki_studio.errors import ContractViolationError, OutputWriteError, PromoteApplyError
from wiki_studio.paths import WikiPaths
from wiki_studio.proposal import IngestLogRecord
from wiki_studio.wikilock import WikiLock

REPO_ROOT = Path(__file__).resolve().parents[1]
_HEX = "a" * 64

PAGE = (
    "---\npage_type: concept\nslug: {slug}\ntitle: {title}\nstatus: draft\nlast_reviewed: 2026-05-06\n"
    "sources:\n  - path: src.md\n    sha: abc\n---\n\n# {title}\n\n{body}\n"
)


def _concept(slug: str, body: str) -> str:
    return PAGE.format(slug=slug, title=slug.title(), body=body)


def _wiki_page(wiki: Path, slug: str, body: str) -> Path:
    """A concept page linked from the index (so the staged tree lints clean)."""
    page = wiki / "concepts" / f"{slug}.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(_concept(slug, body), encoding="utf-8")
    index = wiki / "index.md"
    index.write_text(
        index.read_text(encoding="utf-8") + f"- [{slug.title()}](concepts/{slug}.md) — page.\n", encoding="utf-8"
    )
    return page


def _update_proposal(root: Path, name: str, slug: str, body: str, *, base_sha256: str | None = None) -> Path:
    """A proposal with one ``update`` of ``concepts/<slug>.md``; ``base_sha256`` is written when given."""
    prop = root / "doc_internal" / "proposals" / name
    (prop / "preview" / "concepts").mkdir(parents=True)
    (prop / "preview" / "concepts" / f"{slug}.md").write_text(_concept(slug, body), encoding="utf-8")
    edit: dict[str, str] = {
        "path": f"concepts/{slug}.md",
        "action": "update",
        "rationale": "r",
        "preview": f"preview/concepts/{slug}.md",
    }
    if base_sha256 is not None:
        edit["base_sha256"] = base_sha256
    plan = {"version": 1, "source_path": "src.md", "backend": "test", "rationale": "update", "edits": [edit]}
    (prop / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return prop


def _live_sha(page: Path) -> str:
    return hashlib.sha256(page.read_bytes()).hexdigest()


def _record(n: int) -> IngestLogRecord:
    return IngestLogRecord(
        v=1,
        ts="2026-05-17T14:03:22Z",
        source_path=f"notes/{n}.md",
        source_repo_relative=True,
        source_sha=_HEX,
        backend="test",
        disposition="reject",
        reason=f"record {n}",
        proposal_dir=None,
        target_paths=[],
        page_types=[],
        proposal_hash=None,
    )


class _LayoutCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-concurrency-")
        self.root = make_repo_layout(Path(self._tmp.name), with_schema=True, with_sample=True)
        self.paths = WikiPaths.for_root(self.root)
        self.wiki = self.paths.wiki_dir
        self.sample = self.root / "sample-incident.md"

    def tearDown(self) -> None:
        self._tmp.cleanup()


class TestCommitScope(_LayoutCase):
    """The focused reproduction: stage both from one pre-state, commit sequentially."""

    def test_a_stale_stage_never_writes_back_another_writers_page(self) -> None:
        # Drives _stage_wiki / _plan_commit / _apply_planned directly, without the
        # lock or the receipt protocol: the property under test is the commit
        # scope alone. TestInterleavedProcesses covers the full promote path.
        page = _wiki_page(self.wiki, "x", "Original.")
        a = _update_proposal(self.root, "a", "x", "Updated by A.", base_sha256=_live_sha(page))
        b = _proposals_dir(self.root, slug="b")
        handle = promoter._open_wiki(self.wiki)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                stages = {}
                for prop in (a, b):
                    capture = promoter._capture_submission(prop)
                    patch_set, _ = promoter._parse_patch(capture, prop)
                    stage = Path(tmp) / prop.name / "wiki"
                    promoter._stage_wiki(handle, self.wiki, stage)  # both from the same pre-state
                    for edit in patch_set.edits:
                        promoter._apply_edit(stage, edit)
                    archive_rel = promoter._stage_audit_archive(stage, prop.name, capture, patch_set)
                    stages[prop.name] = (stage, patch_set, archive_rel)
                stage_a, patch_a, rel_a = stages["a"]
                written_a = promoter._apply_planned(
                    promoter._plan_commit(stage_a, self.paths, patch_a, rel_a), self.paths
                )
                stage_b, patch_b, rel_b = stages["2026-05-06-b"]
                # B's stage still holds the old concepts/x.md; it is not B's path, so it is not written.
                self.assertIn("Original.", (stage_b / "concepts" / "x.md").read_text(encoding="utf-8"))
                written_b = promoter._apply_planned(
                    promoter._plan_commit(stage_b, self.paths, patch_b, rel_b), self.paths
                )
        finally:
            handle.close()
        self.assertEqual(written_a, ["concepts/x.md", ".audit/proposals/a/plan.json", ".audit/proposals/a/proposal.md"])
        self.assertEqual(
            written_b,
            [
                "incidents/b.md",
                "log.md",
                "index.md",
                ".audit/proposals/2026-05-06-b/plan.json",
                ".audit/proposals/2026-05-06-b/proposal.md",
            ],
        )
        self.assertIn("Updated by A.", (self.wiki / "concepts" / "x.md").read_text(encoding="utf-8"))
        self.assertTrue((self.wiki / "incidents" / "b.md").is_file())
        self.assertIn("[CLI Fixture](incidents/b.md)", (self.wiki / "index.md").read_text(encoding="utf-8"))

    def test_planned_writes_exclude_no_ops_and_include_the_archive(self) -> None:
        page = _wiki_page(self.wiki, "x", "Same.")
        prop = _update_proposal(self.root, "same", "x", "Same.", base_sha256=_live_sha(page))
        result = api.promote(prop, self.paths)
        self.assertEqual(result.applied_paths, [".audit/proposals/same/plan.json", ".audit/proposals/same/proposal.md"])
        receipt = json.loads((self.paths.applied_dir / "same" / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual([w["path"] for w in receipt["planned_writes"]], result.applied_paths)
        self.assertTrue(all(w["pre_sha256"] is None for w in receipt["planned_writes"]))


def _spawn(sync_dir: Path, root: Path, *argv: str) -> subprocess.Popen[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(REPO_ROOT / "src"), str(REPO_ROOT), env.get("PYTHONPATH")) if p)
    return subprocess.Popen(
        [sys.executable, "-m", "tests.helpers.promote_bootstrap", str(sync_dir), *argv],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _wait_for(path: Path, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while not path.exists():
        if time.monotonic() > deadline:
            return False
        time.sleep(0.01)
    return True


class TestInterleavedProcesses(_LayoutCase):
    """Two ``wiki-studio promote`` processes: the first is held after staging, the second waits on the lock."""

    def _run_interleaved(self, second_wiki_dir: Path | None = None) -> tuple[Path, Path]:
        first = _proposals_dir(self.root, slug="first")
        second = _proposals_dir(self.root, slug="second")
        sync1, sync2 = self.root / "sync1", self.root / "sync2"
        sync1.mkdir()
        sync2.mkdir()
        common = ["--root", str(self.root)]
        p1 = _spawn(sync1, self.root, "promote", str(first), *common)
        try:
            self.assertTrue(_wait_for(sync1 / "staged"), "first promote never reached the post-stage hold")
            argv2 = ["promote", str(second), *common]
            if second_wiki_dir is not None:
                argv2 += ["--wiki-dir", str(second_wiki_dir)]
            p2 = _spawn(sync2, self.root, *argv2)
            try:
                time.sleep(0.5)
                self.assertIsNone(p2.poll(), "second promote finished while the first held the lock")
                self.assertFalse((sync2 / "staged").exists(), "second promote staged while the first held the lock")
                (sync1 / "go").write_text("go\n", encoding="utf-8")
                out1, err1 = p1.communicate(timeout=60)
                self.assertEqual(p1.returncode, 0, err1)
                self.assertTrue(_wait_for(sync2 / "staged"), "second promote never staged after the release")
                (sync2 / "go").write_text("go\n", encoding="utf-8")
                out2, err2 = p2.communicate(timeout=60)
                self.assertEqual(p2.returncode, 0, err2)
            finally:
                if p2.poll() is None:
                    p2.kill()
        finally:
            if p1.poll() is None:
                p1.kill()
        return first, second

    def _assert_both_landed(self, first: Path, second: Path) -> None:
        self.assertTrue((self.wiki / "incidents" / "first.md").is_file())
        self.assertTrue((self.wiki / "incidents" / "second.md").is_file())
        index = (self.wiki / "index.md").read_text(encoding="utf-8")
        log = (self.wiki / "log.md").read_text(encoding="utf-8")
        for slug in ("first", "second"):
            self.assertIn(f"(incidents/{slug}.md)", index)
            self.assertIn(f"promote {slug} (incident).", log)
        self.assertFalse(first.exists())
        self.assertFalse(second.exists())
        receipts = {}
        for prop in (first, second):
            archive = self.paths.applied_dir / prop.name
            self.assertTrue((archive / "receipt.json").is_file(), f"{prop.name} has no receipt")
            receipts[prop.name] = json.loads((archive / "receipt.json").read_text(encoding="utf-8"))
        # Serialisation is proven above (the second process stayed blocked with no
        # receipt staged); the measured wait depends on scheduling, so only its
        # presence and sign are asserted, never a wall-clock floor.
        self.assertGreaterEqual(receipts[second.name]["lock_wait_seconds"], 0.0)
        self.assertEqual(receipts[second.name]["promoter"]["entry_point"], "cli")
        self.assertEqual(
            sorted(receipts[first.name]["written_paths"]),
            sorted(
                [
                    "incidents/first.md",
                    "log.md",
                    "index.md",
                    f".audit/proposals/{first.name}/plan.json",
                    f".audit/proposals/{first.name}/proposal.md",
                ]
            ),
        )

    def test_the_second_promote_waits_before_staging_and_both_pages_land(self) -> None:
        first, second = self._run_interleaved()
        self._assert_both_landed(first, second)

    def test_two_spellings_of_the_wiki_directory_share_the_lock(self) -> None:
        alias = self.root / "wiki-alias"
        alias.symlink_to(self.wiki, target_is_directory=True)
        first, second = self._run_interleaved(second_wiki_dir=alias)
        self._assert_both_landed(first, second)


class TestLockLifetime(_LayoutCase):
    def test_a_failure_during_the_commit_releases_the_lock(self) -> None:
        prop = _proposals_dir(self.root)
        with (
            patch("wiki_studio.promoter._apply_planned", side_effect=PromoteApplyError("boom")),
            self.assertRaises(PromoteApplyError),
        ):
            api.promote(prop, self.paths)
        with WikiLock(self.wiki, timeout=0.2) as lock:
            self.assertLess(lock.wait_seconds, 0.2)

    def test_promote_holds_the_lock_from_before_staging_to_after_the_archive_move(self) -> None:
        prop = _proposals_dir(self.root)
        seen: list[tuple[str, bool]] = []

        def probe(stage: str) -> None:
            try:
                WikiLock(self.wiki, timeout=0.05).acquire().release()
                seen.append((stage, False))
            except PromoteApplyError:
                seen.append((stage, True))

        real_stage, real_remove = promoter._stage_wiki, promoter._remove_source_dir

        def stage_probe(*args: object, **kwargs: object) -> None:
            probe("before staging")
            real_stage(*args, **kwargs)  # type: ignore[arg-type]

        def remove_probe(*args: object, **kwargs: object) -> None:
            real_remove(*args, **kwargs)  # type: ignore[arg-type]
            probe("after archive move")

        with (
            patch("wiki_studio.promoter._stage_wiki", side_effect=stage_probe),
            patch("wiki_studio.promoter._remove_source_dir", side_effect=remove_probe),
        ):
            api.promote(prop, self.paths)
        self.assertEqual(seen, [("before staging", True), ("after archive move", True)])


class TestIngestLogAppends(unittest.TestCase):
    def test_concurrent_appends_all_land_as_whole_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo_layout(Path(tmp), with_schema=False, with_sample=False)
            paths = WikiPaths.for_root(root)
            errors: list[BaseException] = []

            def worker(base: int) -> None:
                try:
                    for n in range(10):
                        append_ingest_log(paths, _record(base * 100 + n))
                except BaseException as exc:  # surfaced by the assertion below
                    errors.append(exc)

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(30)
            self.assertEqual(errors, [])
            lines = [ln for ln in paths.audit_log.read_text(encoding="utf-8").splitlines()[2:] if ln]
            self.assertEqual(len(lines), 40)
            self.assertEqual(
                sorted(json.loads(ln)["reason"] for ln in lines),
                sorted(f"record {i * 100 + n}" for i in range(4) for n in range(10)),
            )
            self.assertEqual(validate_audit_tree(paths), [])

    def test_an_append_that_overlaps_audit_flush_lands_after_the_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _init_repo(Path(tmp))
            (repo / "knowledge" / "wiki").mkdir(parents=True)
            paths = WikiPaths.for_root(repo)
            append_ingest_log(paths, _record(1))
            before = paths.audit_log.read_bytes()
            in_commit = threading.Event()
            real_run = audit_flush._run

            def slow_commit(argv: list[str], **kw: object) -> subprocess.CompletedProcess[bytes]:
                if "commit" in argv:
                    in_commit.set()
                    time.sleep(0.5)
                return real_run(argv, **kw)

            flushed: list[object] = []
            with patch("wiki_studio.audit_flush._run", side_effect=slow_commit):
                flusher = threading.Thread(target=lambda: flushed.append(audit_flush.flush_state(paths, False)))
                flusher.start()
                self.assertTrue(in_commit.wait(10))
                started = time.monotonic()
                append_ingest_log(paths, _record(2))  # waits for the flush to release the lock
                waited = time.monotonic() - started
                flusher.join(30)
            self.assertGreater(waited, 0.3)
            self.assertTrue(getattr(flushed[0], "committed", False))
            committed = subprocess.run(
                ["git", "-C", str(repo), "show", "HEAD:./knowledge/wiki/.audit/ingest-log.md"], capture_output=True
            ).stdout
            self.assertEqual(committed, before, "the flush committed the pre-append bytes, not a torn tail")
            state = detect_pending(paths)
            self.assertEqual((state.pending, state.diverged, state.malformed), (1, False, False))


class TestSubmissionIdentity(_LayoutCase):
    def test_a_second_ingest_of_the_same_source_lands_in_a_new_directory(self) -> None:
        first = api.ingest(self.sample, self.paths, backend="test").written
        second = api.ingest(self.sample, self.paths, backend="test").written
        assert first is not None and second is not None
        self.assertNotEqual(first, second)
        self.assertEqual(second.name, f"{first.name}-2")
        self.assertTrue((first / "plan.json").is_file())
        self.assertTrue((second / "plan.json").is_file())

    def test_a_caller_selected_name_that_exists_is_an_error(self) -> None:
        prop = _proposals_dir(self.root, slug="taken")
        edits = api.edits_from_dir(self._draft(), self.paths)
        with self.assertRaises(OutputWriteError) as ctx:
            api.propose(edits, self.paths, name=prop.name)
        self.assertIn("already exists", str(ctx.exception))
        self.assertTrue((prop / "plan.json").is_file(), "the existing proposal is untouched")

    def _draft(self) -> Path:
        draft = self.root / "draft"
        (draft / "concepts").mkdir(parents=True)
        (draft / "concepts" / "drafted.md").write_text(_concept("drafted", "Body."), encoding="utf-8")
        (draft / "index.md").write_text("- [Drafted](concepts/drafted.md)\n", encoding="utf-8")
        return draft

    def test_same_name_same_plan_different_previews_get_different_identities_and_both_archive(self) -> None:
        # Two legacy proposals (no base revision), so the plan bytes can be identical: both
        # need the compatibility option, which is what records them as unguarded.
        _wiki_page(self.wiki, "x", "v0")
        prop = _update_proposal(self.root, "same", "x", "v1")
        plan_bytes = (prop / "plan.json").read_bytes()
        api.promote(prop, self.paths, allow_unguarded_updates=True)
        again = _update_proposal(self.root, "same", "x", "v2")
        self.assertEqual((again / "plan.json").read_bytes(), plan_bytes)
        api.promote(again, self.paths, allow_unguarded_updates=True)
        first = json.loads((self.paths.applied_dir / "same" / "receipt.json").read_text(encoding="utf-8"))
        second = json.loads((self.paths.applied_dir / "same-2" / "receipt.json").read_text(encoding="utf-8"))
        self.assertNotEqual(first["submission_digest"], second["submission_digest"])
        self.assertEqual(first["plan_sha256"], second["plan_sha256"])
        self.assertIn("v2", (self.wiki / "concepts" / "x.md").read_text(encoding="utf-8"))

    def test_hidden_and_unreferenced_preview_files_change_the_digest(self) -> None:
        prop = _proposals_dir(self.root)
        base_digest, base_hash = payload_digest(prop), proposal_hash(prop)
        (prop / "preview" / ".line.md").write_text("hidden\n", encoding="utf-8")
        hidden_digest = payload_digest(prop)
        self.assertNotEqual(hidden_digest, base_digest)
        self.assertEqual(proposal_hash(prop), base_hash, "recipe 1 still skips dot components")
        (prop / "preview" / "unreferenced.md").write_text("extra\n", encoding="utf-8")
        unreferenced_digest = payload_digest(prop)
        self.assertNotEqual(unreferenced_digest, hidden_digest)
        # A file outside preview/ is provenance, archived with the proposal but outside the identity.
        (prop / "review-notes.md").write_text("outside preview\n", encoding="utf-8")
        self.assertEqual(payload_digest(prop), unreferenced_digest)
        files = {p.relative_to(prop).as_posix(): p.read_bytes() for p in prop.rglob("*") if p.is_file()}
        self.assertEqual(payload_digest_from_files(files), payload_digest(prop))

    def test_a_preview_pointer_outside_preview_is_refused_with_exit_4(self) -> None:
        for i, pointer in enumerate(
            ("line.md", "../escape.md", "/tmp/abs.md", "preview/../line.md", "preview/incidents")
        ):
            with self.subTest(pointer=pointer):
                prop = _proposals_dir(self.root, slug=f"ptr-{i}")
                (prop / "line.md").write_text("- outside\n", encoding="utf-8")
                plan = json.loads((prop / "plan.json").read_text(encoding="utf-8"))
                plan["edits"][1]["preview"] = pointer
                (prop / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
                log_before = (self.wiki / "log.md").read_bytes()
                with self.assertRaises(ContractViolationError) as ctx:
                    api.promote(prop, self.paths)
                self.assertEqual(ctx.exception.exit_code, 4)
                self.assertIn(pointer, str(ctx.exception))
                self.assertEqual((self.wiki / "log.md").read_bytes(), log_before)
                self.assertFalse((prop / "receipt.json").exists())

    def test_receipt_digest_equals_the_ingest_log_hash_for_an_unchanged_proposal(self) -> None:
        ingested = api.ingest(self.sample, self.paths, backend="test")
        assert ingested.written is not None and ingested.record is not None
        self.assertEqual(ingested.record.hash_recipe, 2)
        result = api.promote(ingested.written, self.paths)
        assert result.archived_dir is not None
        receipt = json.loads((result.archived_dir / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["submission_digest"], ingested.record.proposal_hash)
        self.assertEqual(receipt["digest_recipe"], 2)
        line = json.loads(self.paths.audit_log.read_text(encoding="utf-8").splitlines()[2])
        self.assertEqual(line["hash_recipe"], 2)
        self.assertEqual(line["proposal_hash"], receipt["submission_digest"])

    def test_a_curator_edit_leaves_the_log_entry_and_changes_receipt_and_archive(self) -> None:
        ingested = api.ingest(self.sample, self.paths, backend="test")
        assert ingested.written is not None and ingested.record is not None
        log_before = self.paths.audit_log.read_bytes()
        preview = next(p for p in (ingested.written / "preview").rglob("*.md") if p.parent.name != "preview")
        edited = preview.read_bytes() + b"\nCurated sentence.\n"
        preview.write_bytes(edited)
        rel = preview.relative_to(ingested.written).as_posix()
        result = api.promote(ingested.written, self.paths)
        assert result.archived_dir is not None
        self.assertEqual(self.paths.audit_log.read_bytes(), log_before)
        receipt = json.loads((result.archived_dir / "receipt.json").read_text(encoding="utf-8"))
        self.assertNotEqual(receipt["submission_digest"], ingested.record.proposal_hash)
        self.assertEqual((result.archived_dir / rel).read_bytes(), edited)
        manifest = {e["path"]: e["sha256"] for e in receipt["submission_manifest"]}
        self.assertEqual(manifest[rel], promoter._sha256(edited))
        delta = (self.wiki / ".audit" / "proposals" / ingested.written.name / "curator-delta.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("+Curated sentence.", delta)
        self.assertIn((self.wiki / rel[len("preview/") :]).read_bytes(), [edited])

    def test_an_ingest_during_a_held_promote_lands_in_a_new_unpromoted_directory(self) -> None:
        first = api.ingest(self.sample, self.paths, backend="test").written
        assert first is not None
        captured = {p.relative_to(first).as_posix(): p.read_bytes() for p in first.rglob("*") if p.is_file()}
        captured_digest = payload_digest_from_files(captured)
        results: list[api.IngestResult] = []
        real_apply = promoter._apply_planned

        def hold_then_apply(planned: list[promoter._PlannedWrite], paths: WikiPaths) -> list[str]:
            # Between capture and archive: a second ingest of the same source starts and waits on the lock.
            thread = threading.Thread(target=lambda: results.append(api.ingest(self.sample, paths, backend="test")))
            thread.start()
            time.sleep(0.3)
            self.assertEqual(results, [], "the ingest wrote its directory while the promote held the lock")
            hold_then_apply.thread = thread  # type: ignore[attr-defined]
            return real_apply(planned, paths)

        with patch("wiki_studio.promoter._apply_planned", side_effect=hold_then_apply):
            promoted = api.promote(first, self.paths)
        hold_then_apply.thread.join(30)  # type: ignore[attr-defined]
        assert promoted.archived_dir is not None
        receipt = json.loads((promoted.archived_dir / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["submission_digest"], captured_digest)
        for rel, data in captured.items():
            self.assertEqual((promoted.archived_dir / rel).read_bytes(), data)
        for rel, data in captured.items():
            if rel.startswith("preview/") and rel.count("/") == 2:
                self.assertEqual((self.wiki / rel[len("preview/") :]).read_bytes(), data)
        second = results[0].written
        assert second is not None
        self.assertNotEqual(second.resolve(), promoted.archived_dir.resolve())
        self.assertTrue((second / "plan.json").is_file())
        self.assertFalse((second / "receipt.json").exists(), "the new proposal stays unpromoted")
        self.assertFalse(".applied" in second.parts)


if __name__ == "__main__":
    unittest.main()
