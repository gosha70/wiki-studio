# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""A stale replacement is refused (0.6.0 US2, FR-005..FR-011).

The 22 October reproduction: a replacement carried no record of the page it
was drafted from, so a stale draft overwrote a newer page. Now ``read`` gives
content and hash from one read, the hash travels with the edit as
``base_sha256``, and promote checks it against the live page under the lock,
immediately before the commit. Creates need absence, appends land on the
current content, and an update without a hash is refused unless the caller
opts into compatibility mode, which is recorded.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from tests.conftest import make_repo_layout, run_cli
from tests.test_cli_contract import _proposals_dir
from tests.test_promote_concurrency import _concept, _live_sha, _spawn, _update_proposal, _wait_for, _wiki_page
from wiki_studio import api, ingestor_multi, promoter
from wiki_studio.api import PageEdit
from wiki_studio.errors import ContractViolationError, PromoteApplyError, PromoteValidationError
from wiki_studio.ingestor_multi import DefaultMultiIngestor
from wiki_studio.paths import WikiPaths
from wiki_studio.proposal import IngestRequest, WikiPatchSet
from wiki_studio.wiki_state import WikiState
from wiki_studio.wikilock import WikiLock

SLUG = "retry"
REL = f"concepts/{SLUG}.md"


def _tree(root: Path) -> dict[str, bytes | None]:
    """Every entry under ``root``: files by bytes, directories as None (absent root: empty)."""
    if not root.exists():
        return {}
    return {p.relative_to(root).as_posix(): (None if p.is_dir() else p.read_bytes()) for p in root.rglob("*")}


class _Case(unittest.TestCase):
    """A layout with one concept page, ``concepts/retry.md``, linked from the index."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-preconditions-")
        self.root = make_repo_layout(Path(self._tmp.name), with_schema=True, with_sample=False)
        self.paths = WikiPaths.for_root(self.root)
        self.wiki = self.paths.wiki_dir
        self.page = _wiki_page(self.wiki, SLUG, "v1")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def cli(self, *argv: str):  # noqa: ANN201 - test helper
        return run_cli(*argv, cwd=self.root)

    def replacement(self, name: str, body: str, base: str | None) -> Path:
        """``api.propose`` of one ``update`` of the page, drafted from the revision ``base`` names."""
        return api.propose(
            [PageEdit(REL, "update", _concept(SLUG, body), "r", base_sha256=base)], self.paths, name=name
        )

    def land(self, name: str, body: str) -> None:
        """Another writer: read the live page, replace it, promote."""
        api.promote(self.replacement(name, body, api.read_page(REL, self.paths).sha256), self.paths)

    def assert_nothing_written(self, proposal: Path, wiki_before: dict[str, bytes | None]) -> None:
        self.assertEqual(_tree(self.wiki), wiki_before, "the wiki changed")
        self.assertTrue((proposal / "plan.json").is_file(), "the proposal was moved or removed")
        self.assertFalse((proposal / "receipt.json").exists(), "a refused promotion persisted a receipt")
        self.assertFalse((self.paths.applied_dir / proposal.name).exists(), "a refused promotion was archived")


class TestStaleReplacement(_Case):
    def test_early_interval_read_then_other_writer_then_stale_replacement_exits_9(self) -> None:
        # Agent reads A; another writer commits A'; the agent's replacement, drafted from A, is refused.
        read = api.read_page(REL, self.paths)
        self.assertEqual(read.sha256, _live_sha(self.page))
        self.land("other", "v2")
        stale = self.replacement("stale", "drafted from v1", read.sha256)
        before = _tree(self.wiki)

        result = self.cli("promote", str(stale))
        self.assertEqual(result.returncode, PromoteValidationError.exit_code, result.stderr)
        self.assertIn(REL, result.stderr)
        self.assertIn("nothing was written", result.stderr)
        self.assert_nothing_written(stale, before)

        with self.assertRaises(PromoteValidationError) as ctx:
            api.promote(stale, self.paths)
        self.assertEqual(ctx.exception.exit_code, 9)
        self.assertIn(REL, str(ctx.exception))
        self.assert_nothing_written(stale, before)
        self.assertIn("v2", self.page.read_text(encoding="utf-8"))

    def test_late_interval_change_between_propose_and_promote_exits_9(self) -> None:
        mine = self.replacement("mine", "drafted from v1", api.read_page(REL, self.paths).sha256)
        self.land("other", "v2")  # between propose and promote
        before = _tree(self.wiki)
        with self.assertRaises(PromoteValidationError) as ctx:
            api.promote(mine, self.paths)
        self.assertIn("not the revision this update was drafted from", str(ctx.exception))
        self.assert_nothing_written(mine, before)

    def test_conflicting_edits_to_one_page_the_second_exits_9(self) -> None:
        base = api.read_page(REL, self.paths).sha256
        first = self.replacement("first", "first draft", base)
        second = self.replacement("second", "second draft", base)
        landed = api.promote(first, self.paths)
        self.assertIn(REL, landed.applied_paths)
        self.assertEqual(landed.unguarded_paths, [])
        receipt = json.loads((self.paths.applied_dir / "first" / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["unguarded_paths"], [])
        before = _tree(self.wiki)
        with self.assertRaises(PromoteValidationError):
            api.promote(second, self.paths)
        self.assert_nothing_written(second, before)
        self.assertIn("first draft", self.page.read_text(encoding="utf-8"))

    def test_a_matching_hash_lands_through_both_entry_points(self) -> None:
        api.promote(self.replacement("api", "v2", api.read_page(REL, self.paths).sha256), self.paths)
        self.assertIn("v2", self.page.read_text(encoding="utf-8"))
        proposal = self.replacement("cli", "v3", api.read_page(REL, self.paths).sha256)
        result = self.cli("promote", str(proposal))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("warning:", result.stderr)
        self.assertIn("v3", self.page.read_text(encoding="utf-8"))

    def test_a_malformed_base_hash_is_refused_before_anything_is_written(self) -> None:
        with self.assertRaises(ContractViolationError):
            self.replacement("bad", "v2", "not-a-hash")
        with self.assertRaises(ContractViolationError):
            api.propose(
                [PageEdit("concepts/new.md", "create", _concept("new", "x"), "r", "a" * 64)], self.paths, name="c"
            )
        raw = _update_proposal(self.root, "raw", SLUG, "v2", base_sha256="XYZ")
        before = _tree(self.wiki)
        with self.assertRaises(PromoteValidationError):
            api.promote(raw, self.paths)
        self.assert_nothing_written(raw, before)


class TestCreateRequiresAbsence(_Case):
    def test_the_check_itself_refuses_a_create_whose_target_now_exists(self) -> None:
        (self.wiki / "incidents").mkdir()
        (self.wiki / "incidents" / "dup.md").write_text("# taken\n", encoding="utf-8")
        patch_set = WikiPatchSet(
            edits=[
                PageEdit("incidents/dup.md", "create", "# new\n", "r"),
                PageEdit("incidents/free.md", "create", "# new\n", "r"),
                PageEdit("log.md", "append-log", "- line", "r"),
            ],
            source_path="s",
            backend="t",
            rationale="r",
        )
        with self.assertRaises(PromoteValidationError) as ctx:
            promoter._check_preconditions(patch_set, self.paths, allow_unguarded_updates=False)
        message = str(ctx.exception)
        self.assertIn("incidents/dup.md: create requires absence", message)
        self.assertNotIn("incidents/free.md", message)
        self.assertNotIn("log.md", message)
        self.assertEqual(ctx.exception.exit_code, 9)

    def test_concurrent_create_of_one_path_the_waiting_writer_exits_9(self) -> None:
        first = _proposals_dir(self.root, slug="dup")
        second = first.with_name("other-dup")
        shutil.copytree(first, second)
        sync1, sync2 = self.root / "sync1", self.root / "sync2"
        sync1.mkdir()
        sync2.mkdir()
        common = ["--root", str(self.root)]
        p1 = _spawn(sync1, self.root, "promote", str(first), *common)
        try:
            self.assertTrue(_wait_for(sync1 / "staged"), "first promote never reached the post-stage hold")
            p2 = _spawn(sync2, self.root, "promote", str(second), *common)
            try:
                time.sleep(0.3)
                self.assertIsNone(p2.poll(), "second promote finished while the first held the lock")
                (sync1 / "go").write_text("go\n", encoding="utf-8")
                _out1, err1 = p1.communicate(timeout=60)
                self.assertEqual(p1.returncode, 0, err1)
                _out2, err2 = p2.communicate(timeout=60)
            finally:
                if p2.poll() is None:
                    p2.kill()
        finally:
            if p1.poll() is None:
                p1.kill()
        self.assertEqual(p2.returncode, PromoteValidationError.exit_code, err2)
        self.assertIn("incidents/dup.md", err2)
        self.assertEqual((self.wiki / "incidents" / "dup.md").read_text(encoding="utf-8").count("# CLI Fixture"), 1)
        self.assertTrue((second / "plan.json").is_file())
        self.assertFalse((second / "receipt.json").exists())
        index = (self.wiki / "index.md").read_text(encoding="utf-8")
        self.assertEqual(index.count("(incidents/dup.md)"), 1, "the refused promote appended nothing")


class TestLegacyProposals(_Case):
    """Per-operation policy for proposals written before 0.6.0 (no base revision)."""

    def test_creates_and_appends_from_two_legacy_proposals_both_land(self) -> None:
        one = _proposals_dir(self.root, slug="one")
        two = _proposals_dir(self.root, slug="two")
        for prop in (one, two):
            result = self.cli("promote", str(prop))
            self.assertEqual(result.returncode, 0, result.stderr)
        index = (self.wiki / "index.md").read_text(encoding="utf-8")
        log = (self.wiki / "log.md").read_text(encoding="utf-8")
        for slug in ("one", "two"):
            self.assertTrue((self.wiki / "incidents" / f"{slug}.md").is_file())
            self.assertIn(f"(incidents/{slug}.md)", index)
            self.assertIn(f"promote {slug} (incident).", log)

    def test_legacy_update_exits_9_with_both_remedies_then_lands_under_the_option_and_is_recorded(self) -> None:
        legacy = _update_proposal(self.root, "legacy", SLUG, "v2")
        before = _tree(self.wiki)
        refused = self.cli("promote", str(legacy))
        self.assertEqual(refused.returncode, PromoteValidationError.exit_code, refused.stderr)
        self.assertIn(f"{REL}: update carries no base_sha256", refused.stderr)
        self.assertIn(f"wiki-studio read {REL}", refused.stderr)
        self.assertIn("--allow-unguarded-updates", refused.stderr)
        self.assertIn("compatibility mode with incomplete conflict protection", refused.stderr)
        self.assert_nothing_written(legacy, before)

        allowed = self.cli("promote", str(legacy), "--allow-unguarded-updates")
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertIn(f"warning: {REL}: replaced without a base revision", allowed.stderr)
        self.assertIn("compatibility mode with incomplete conflict protection", allowed.stderr)
        self.assertIn("v2", self.page.read_text(encoding="utf-8"))
        receipt = json.loads((self.paths.applied_dir / "legacy" / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["unguarded_paths"], [REL])
        self.assertEqual(receipt["state"], "committed")

    def test_api_promote_records_unguarded_paths_and_warnings(self) -> None:
        legacy = _update_proposal(self.root, "legacy", SLUG, "v2")
        with self.assertRaises(PromoteValidationError) as ctx:
            api.promote(legacy, self.paths)
        self.assertIn("allow_unguarded_updates=True", str(ctx.exception))
        result = api.promote(legacy, self.paths, allow_unguarded_updates=True)
        self.assertEqual(result.unguarded_paths, [REL])
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("compatibility mode with incomplete conflict protection", result.warnings[0])
        self.assertIn(REL, result.applied_paths)

    def test_the_option_does_not_bypass_a_recorded_hash(self) -> None:
        stale = self.replacement("stale", "from v1", api.read_page(REL, self.paths).sha256)
        self.land("other", "v2")
        with self.assertRaises(PromoteValidationError):
            api.promote(stale, self.paths, allow_unguarded_updates=True)

    def test_help_calls_it_compatibility_mode(self) -> None:
        for verb in ("promote", "propose"):
            result = self.cli(verb, "--help")
            self.assertEqual(result.returncode, 0)
            self.assertIn("--allow-unguarded-updates", result.stdout)
            self.assertIn("incomplete conflict protection", " ".join(result.stdout.split()))
            self.assertNotIn("prevents stale", result.stdout)


class TestBaseManifest(_Case):
    """``propose --from`` takes the hash from ``<draft>/.base.json`` and never from the live page."""

    def draft(self, body: str, manifest: dict[str, str] | None, name: str = "draft") -> Path:
        draft = self.root / name
        (draft / "concepts").mkdir(parents=True)
        (draft / REL).write_text(_concept(SLUG, body), encoding="utf-8")
        if manifest is not None:
            (draft / ".base.json").write_text(json.dumps(manifest), encoding="utf-8")
        return draft

    def test_a_current_manifest_lands(self) -> None:
        draft = self.draft("v2", {REL: api.read_page(REL, self.paths).sha256})
        result = self.cli("propose", "--from", str(draft), "--name", "fresh", "--promote")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("v2", self.page.read_text(encoding="utf-8"))
        plan = json.loads((self.paths.applied_dir / "fresh" / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["edits"][0]["base_sha256"], hashlib.sha256(_concept(SLUG, "v1").encode()).hexdigest())

    def test_a_stale_manifest_exits_9_and_the_proposal_is_kept(self) -> None:
        draft = self.draft("from v1", {REL: api.read_page(REL, self.paths).sha256})
        self.land("other", "v2")
        before = _tree(self.wiki)
        result = self.cli("propose", "--from", str(draft), "--name", "stale", "--promote")
        self.assertEqual(result.returncode, PromoteValidationError.exit_code, result.stderr)
        self.assertIn(REL, result.stderr)
        self.assert_nothing_written(self.paths.proposals_dir / "stale", before)

    def test_a_missing_manifest_is_unguarded(self) -> None:
        edits = api.edits_from_dir(self.draft("v2", None), self.paths)
        self.assertEqual([(e.action, e.base_sha256) for e in edits], [("update", None)])
        refused = self.cli("propose", "--from", str(self.root / "draft"), "--name", "u", "--promote")
        self.assertEqual(refused.returncode, PromoteValidationError.exit_code, refused.stderr)
        self.assertIn("no base_sha256", refused.stderr)
        self.assertIn("v1", self.page.read_text(encoding="utf-8"))
        allowed = self.cli(
            "propose", "--from", str(self.root / "draft"), "--name", "u2", "--promote", "--allow-unguarded-updates"
        )
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertIn("warning:", allowed.stderr)
        receipt = json.loads((self.paths.applied_dir / "u2" / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["unguarded_paths"], [REL])

    def test_a_manifest_entry_without_a_live_page_is_not_attached_to_the_create(self) -> None:
        draft = self.root / "draft"
        (draft / "concepts").mkdir(parents=True)
        (draft / "concepts" / "new.md").write_text(_concept("new", "x"), encoding="utf-8")
        (draft / ".base.json").write_text(json.dumps({"concepts/new.md": "a" * 64}), encoding="utf-8")
        edits = api.edits_from_dir(draft, self.paths)
        self.assertEqual([(e.action, e.base_sha256) for e in edits], [("create", None)])

    def test_a_malformed_manifest_exits_4(self) -> None:
        for bad in ("not json", json.dumps(["list"]), json.dumps({REL: "short"}), json.dumps({REL: 1})):
            with self.subTest(bad=bad):
                draft = self.root / "draft"
                shutil.rmtree(draft, ignore_errors=True)
                (draft / "concepts").mkdir(parents=True)
                (draft / REL).write_text(_concept(SLUG, "v2"), encoding="utf-8")
                (draft / ".base.json").write_text(bad, encoding="utf-8")
                with self.assertRaises(ContractViolationError) as ctx:
                    api.edits_from_dir(draft, self.paths)
                self.assertEqual(ctx.exception.exit_code, 4)


class _HashingBackend:
    """Replies with an ``update`` of the pages named, each carrying a forged ``base_sha256``."""

    def __init__(self, targets: list[str]) -> None:
        self.targets = targets
        self.prompt: dict[str, Any] | None = None

    def call(self, prompt: dict[str, Any]) -> dict[str, Any]:
        self.prompt = prompt
        return {
            "version": 1,
            "rationale": "forged hashes",
            "edits": [
                {
                    "path": rel,
                    "action": "update",
                    "new_content": _concept(Path(rel).stem, "rewritten"),
                    "rationale": "r",
                    "base_sha256": "f" * 64,
                }
                for rel in self.targets
            ],
        }


class TestBackendCannotSetHashes(_Case):
    def test_the_hash_is_the_prompt_bytes_not_the_backend_value(self) -> None:
        other = _wiki_page(self.wiki, "zzz-unrelated", "nothing in common")
        source = self.root / "retry-notes.md"
        source.write_text("# Retry\n\nretry retry retry\n", encoding="utf-8")
        backend = _HashingBackend([REL, "concepts/zzz-unrelated.md"])
        real_load = ingestor_multi.load_wiki_state

        def only_retry(**kwargs: Any) -> WikiState:
            # The selector ranks by shared tokens (the temporary path shares many); pin the
            # prompt to one page so the "not shown to the model" case is exact.
            state = real_load(**kwargs)
            return WikiState(state.index_md, state.log_md, {REL: state.candidates[REL]})

        with patch.object(ingestor_multi, "load_wiki_state", side_effect=only_retry):
            patch_set = DefaultMultiIngestor(backend=backend, paths=self.paths).ingest_multi(
                IngestRequest(source_path=source, source_kind="file", backend_name="stub")
            )
        assert backend.prompt is not None
        candidates = backend.prompt["wiki_state"]["candidate_pages"]
        self.assertEqual(list(candidates), [REL])
        by_path = {e.path: e.base_sha256 for e in patch_set.edits}
        # The page the prompt showed: hashed from exactly the bytes whose text the prompt holds.
        self.assertEqual(by_path[REL], hashlib.sha256(candidates[REL].encode("utf-8")).hexdigest())
        self.assertEqual(by_path[REL], _live_sha(self.page))
        self.assertNotEqual(by_path[REL], "f" * 64)
        # A page the prompt did not show: the model never read it, so the update is unguarded.
        self.assertIsNone(by_path["concepts/zzz-unrelated.md"])
        self.assertTrue(other.is_file())

    def test_ingest_writes_the_captured_hash_into_plan_json(self) -> None:
        source = self.root / "retry-notes.md"
        source.write_text("# Retry\n\nretry\n", encoding="utf-8")
        written = api.ingest(source, self.paths, backend=_HashingBackend([REL])).written
        assert written is not None
        plan = json.loads((written / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["edits"][0]["base_sha256"], _live_sha(self.page))
        result = api.promote(written, self.paths)
        self.assertEqual(result.unguarded_paths, [])
        self.assertIn("rewritten", self.page.read_text(encoding="utf-8"))


class TestDryRun(_Case):
    def test_dry_run_holds_the_lock_only_for_the_check_and_writes_nothing(self) -> None:
        legacy = _update_proposal(self.root, "legacy", SLUG, "v2")
        wiki_before, proposals_before = _tree(self.wiki), _tree(self.paths.proposals_dir)
        seen: list[tuple[str, bool]] = []

        def held() -> bool:
            try:
                WikiLock(self.wiki, timeout=0.05).acquire().release()
            except PromoteApplyError:
                return True
            return False

        real_check, real_validate = promoter._check_preconditions, promoter._validate_staged_tree

        def check_probe(*args: object, **kwargs: object) -> list[str]:
            seen.append(("preconditions", held()))
            return real_check(*args, **kwargs)  # type: ignore[arg-type]

        def validate_probe(*args: object, **kwargs: object) -> None:
            seen.append(("validation", held()))
            real_validate(*args, **kwargs)  # type: ignore[arg-type]

        with (
            patch("wiki_studio.promoter._check_preconditions", side_effect=check_probe),
            patch("wiki_studio.promoter._validate_staged_tree", side_effect=validate_probe),
        ):
            result = api.promote(legacy, self.paths, dry_run=True, allow_unguarded_updates=True)
        self.assertTrue(result.dry_run)
        self.assertEqual(result.applied_paths, [REL])
        self.assertEqual(result.unguarded_paths, [REL])
        self.assertEqual(seen, [("preconditions", True), ("validation", False)])
        self.assertEqual(_tree(self.wiki), wiki_before)
        self.assertEqual(_tree(self.paths.proposals_dir), proposals_before)

    def test_dry_run_refuses_a_stale_replacement_and_an_unguarded_update(self) -> None:
        stale = self.replacement("stale", "from v1", api.read_page(REL, self.paths).sha256)
        self.land("other", "v2")
        before = _tree(self.wiki)
        result = self.cli("promote", str(stale), "--dry-run")
        self.assertEqual(result.returncode, PromoteValidationError.exit_code, result.stderr)
        self.assert_nothing_written(stale, before)
        legacy = _update_proposal(self.root, "legacy", SLUG, "v3")
        self.assertEqual(self.cli("promote", str(legacy), "--dry-run").returncode, PromoteValidationError.exit_code)
        ok = self.cli("promote", str(legacy), "--dry-run", "--allow-unguarded-updates")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIn("point-in-time", ok.stdout)
        self.assertIn("warning:", ok.stderr)
        self.assert_nothing_written(legacy, before)

    def test_help_says_point_in_time(self) -> None:
        result = self.cli("promote", "--help")
        self.assertIn("point-in-time", " ".join(result.stdout.split()))


class TestReadVerb(_Case):
    def test_read_json_prints_content_and_sha256_from_one_read(self) -> None:
        reads: list[Path] = []
        real = Path.read_bytes

        def counting(path: Path) -> bytes:
            reads.append(path)
            return real(path)

        with patch.object(Path, "read_bytes", counting):
            result = self.cli("read", "index.md", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        index_bytes = (self.wiki / "index.md").read_bytes()
        self.assertEqual(set(payload), {"path", "sha256", "content"})
        self.assertEqual(payload["path"], "index.md")
        self.assertEqual(payload["content"], index_bytes.decode("utf-8"))
        self.assertEqual(payload["sha256"], hashlib.sha256(index_bytes).hexdigest())
        self.assertEqual([p for p in reads if p.name == "index.md"], [self.wiki / "index.md"])

    def test_read_prints_the_text_verbatim(self) -> None:
        self.page.write_text("---\npage_type: concept\n---\n\nno trailing newline", encoding="utf-8")
        result = self.cli("read", REL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "---\npage_type: concept\n---\n\nno trailing newline")
        self.assertEqual(self.cli("read", f"./{REL}", "--json").returncode, 0)

    def test_read_refuses_paths_outside_the_wiki_before_reading(self) -> None:
        (self.root / "secret.md").write_text("top secret\n", encoding="utf-8")
        link = self.wiki / "concepts" / "link.md"
        link.symlink_to(self.root / "secret.md")
        for bad in ("../../secret.md", str(self.root / "secret.md"), "concepts/link.md", "..", "."):
            with self.subTest(path=bad):
                result = self.cli("read", bad)
                self.assertEqual(result.returncode, 7, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("top secret", result.stderr)

    def test_read_missing_exits_5_and_non_utf8_exits_4_with_no_content(self) -> None:
        self.assertEqual(self.cli("read", "concepts/nope.md").returncode, 5)
        self.page.write_bytes(b"---\npage_type: concept\n---\n\xff\xfe\n")
        result = self.cli("read", REL, "--json")
        self.assertEqual(result.returncode, ContractViolationError.exit_code, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("not valid UTF-8", result.stderr)

    def test_find_reports_the_sha256_of_the_bytes_it_read(self) -> None:
        # 0.6.0 pinned that find did not hash; 0.8.0 (FR-008, FR-009) hashes the one read of each page.
        result = self.cli("find", "retry", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.page.read_bytes()
        (page,) = json.loads(result.stdout)["pages"]
        self.assertEqual(page["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(page["bytes"], len(data))


if __name__ == "__main__":
    unittest.main()
