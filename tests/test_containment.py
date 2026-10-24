# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Containment (0.6.0 US3, FR-012 and FR-013): the wiki, proposal and source boundaries on every surface.

Each surface (page write, staging, ``read_page`` / ``read``, ``find``,
``query``, ``plan.json``, preview pointer, snapshot file, receipt) is tried
with an absolute path, a ``../`` escape and a symlink target; each is refused
before any read or write. Lint classifies every local link target and
``find`` never lists a file outside the wiki.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.conftest import make_repo_layout, run_cli
from tests.test_cli_contract import _proposals_dir
from tests.test_promote_concurrency import _concept, _update_proposal, _wiki_page
from wiki_studio import api, promoter
from wiki_studio.audit import payload_digest, proposal_hash
from wiki_studio.errors import ContractViolationError, PathOutsideRootError, PromoteValidationError
from wiki_studio.paths import ENV_SOURCE_ROOTS, WikiPaths
from wiki_studio.wiki_state import load_wiki_state

_OUTSIDE_TEXT = "The outside launch notes are kept here.\n"


def _snapshot(directory: Path) -> dict[str, bytes | str]:
    """Every entry under ``directory``: file bytes, or the symlink target for a symlink."""
    found: dict[str, bytes | str] = {}
    for dirpath, dirnames, filenames in os.walk(directory, followlinks=False):
        base = Path(dirpath)
        for name in (*dirnames, *filenames):
            path = base / name
            rel = path.relative_to(directory).as_posix()
            if path.is_symlink():
                found[rel] = os.readlink(path)
            elif path.is_file():
                found[rel] = path.read_bytes()
    return found


class _Case(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki-studio-containment-")
        base = Path(self._tmp.name).resolve()
        self.root = make_repo_layout(base / "proj", with_schema=False, with_sample=False)
        self.outside = base / "outside"
        self.outside.mkdir()
        (self.outside / "outside.md").write_text(_concept("outside", _OUTSIDE_TEXT), encoding="utf-8")
        (self.outside / "diagram.png").write_bytes(b"png")
        self.paths = WikiPaths.for_root(self.root)
        self.wiki = self.paths.wiki_dir
        _wiki_page(self.wiki, "alpha", "Alpha explains the launch procedure.\n")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def assertNothingWritten(self, before: dict[str, bytes | str], prop: Path | None = None) -> None:  # noqa: N802
        self.assertEqual(_snapshot(self.wiki), before)
        self.assertEqual((self.outside / "outside.md").read_text(encoding="utf-8"), _concept("outside", _OUTSIDE_TEXT))
        if prop is not None:
            self.assertFalse((prop / "receipt.json").exists())
            self.assertFalse((prop.parent / ".applied").exists())


# ── read_page / read ──────────────────────────────────────────


class TestReadBoundary(_Case):
    def test_absolute_and_escaping_paths_exit_7_before_any_read(self) -> None:
        for bad in (
            str(self.outside / "outside.md"),
            "/etc/hosts",
            "../../../outside/outside.md",
            "concepts/../../x.md",
        ):
            with self.subTest(path=bad):
                with self.assertRaises(PathOutsideRootError):
                    api.read_page(bad, self.paths)
                result = run_cli("read", bad, cwd=self.root)
                self.assertEqual(result.returncode, 7, result.stderr)
                self.assertNotIn("launch codes", result.stdout)

    def test_symlinked_page_and_symlinked_directory_exit_7(self) -> None:
        (self.wiki / "concepts" / "sym.md").symlink_to(self.outside / "outside.md")
        (self.wiki / "decisions").symlink_to(self.outside, target_is_directory=True)
        for bad in ("concepts/sym.md", "decisions/secret.md"):
            with self.subTest(path=bad):
                with self.assertRaises(PathOutsideRootError) as ctx:
                    api.read_page(bad, self.paths)
                self.assertIn("symlink", str(ctx.exception))
                result = run_cli("read", bad, "--json", cwd=self.root)
                self.assertEqual(result.returncode, 7, result.stderr)
                self.assertNotIn("launch codes", result.stdout)
        self.assertEqual(api.read_page("concepts/alpha.md", self.paths).path, "concepts/alpha.md")


# ── find / query: the index-entry rule as a defence ───────────


class TestNavigationBoundary(_Case):
    def setUp(self) -> None:
        super().setUp()
        (self.root / "knowledge" / "outside.md").write_text(_concept("outside", _OUTSIDE_TEXT), encoding="utf-8")
        (self.wiki / "concepts" / "sym.md").symlink_to(self.outside / "outside.md")
        index = self.wiki / "index.md"
        index.write_text(
            index.read_text(encoding="utf-8")
            + "- [Escape](../secret.md) — secret launch codes.\n"
            + "- [Absolute](/etc/launch.md) — secret launch codes.\n"
            + "- [Far](../../../outside/secret.md) — secret launch codes.\n"
            + "- [Symlink](concepts/sym.md) — secret launch codes.\n",
            encoding="utf-8",
        )

    def test_lint_fails_first_and_find_lists_nothing_outside_the_wiki(self) -> None:
        lint = api.lint(self.paths)
        self.assertFalse(lint.passed)
        for expected in (
            "index.md: index entry outside the wiki → ../secret.md",
            "index.md: absolute link target → /etc/launch.md",
            "index.md: index entry outside the wiki → ../../../outside/secret.md",
            "index.md: link target passes through a symlink → concepts/sym.md",
            "concepts/sym.md: symlink inside the wiki",
        ):
            self.assertTrue(any(expected in v for v in lint.violations), f"{expected!r} not in {lint.violations}")
        self.assertEqual(run_cli("lint", cwd=self.root).returncode, 1)

        found = api.find("secret launch codes", self.paths)
        self.assertEqual([p.path for p in found.pages], ["concepts/alpha.md"])
        wiki_real = self.wiki.resolve()
        for page in found.pages:
            self.assertTrue(page.file.resolve().is_relative_to(wiki_real))
        result = run_cli("find", "secret launch codes", "--json", cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("outside.md", result.stdout)
        self.assertNotIn("sym.md", result.stdout)

    def test_query_shares_the_selection(self) -> None:
        answer = api.query("secret launch codes", self.paths, backend="test").answer
        self.assertEqual(answer.pages_loaded, ["concepts/alpha.md"])
        self.assertTrue(all(c.page in ("index.md", "concepts/alpha.md") for c in answer.citations))


# ── the source boundary: --source-root / WIKI_STUDIO_SOURCE_ROOTS ──


class TestSourceRoots(_Case):
    def setUp(self) -> None:
        super().setUp()
        # concepts/ → wiki → knowledge → proj → base, then into outside/.
        self.target = "../../../../outside/diagram.png"
        _wiki_page(self.wiki, "beta", f"![diagram]({self.target})\n")

    def test_lint_admits_the_reference_only_with_a_source_root(self) -> None:
        self.assertIn(
            f"concepts/beta.md: link target escapes the project root → {self.target}", api.lint(self.paths).violations
        )
        self.assertEqual(run_cli("lint", cwd=self.root).returncode, 1)
        self.assertEqual(run_cli("lint", "--source-root", str(self.outside), cwd=self.root).returncode, 0)
        self.assertEqual(run_cli("--source-root", str(self.outside), "lint", cwd=self.root).returncode, 0)
        with patch.dict(os.environ, {ENV_SOURCE_ROOTS: str(self.outside)}):
            self.assertEqual(run_cli("lint", cwd=self.root).returncode, 0)
        admitted = WikiPaths.for_root(self.root, source_roots=[self.outside])
        self.assertTrue(api.lint(admitted).passed)

    def test_info_reports_the_source_roots(self) -> None:
        info = json.loads(run_cli("info", "--json", "--source-root", str(self.outside), cwd=self.root).stdout)
        self.assertEqual(info["source_roots"], [str(self.outside)])
        self.assertEqual(json.loads(run_cli("info", "--json", cwd=self.root).stdout)["source_roots"], [])
        self.assertIn("source-roots: (none", run_cli("info", cwd=self.root).stdout)

    def test_promote_applies_the_same_rule_to_the_staged_tree(self) -> None:
        prop = _proposals_dir(self.root)
        page = prop / "preview" / "incidents" / "cli-fixture.md"
        page.write_text(page.read_text(encoding="utf-8") + f"\n![d]({self.target})\n", encoding="utf-8")
        before = _snapshot(self.wiki)
        result = run_cli("promote", str(prop), cwd=self.root)
        self.assertEqual(result.returncode, 9, result.stderr)
        self.assertIn("escapes the project root", result.stderr)
        self.assertNothingWritten(before, prop)
        result = run_cli("promote", str(prop), "--source-root", str(self.outside), cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.wiki / "incidents" / "cli-fixture.md").is_file())


# ── staging and the write targets: the wiki boundary ─────────


class TestStagingBoundary(_Case):
    def test_a_symlinked_page_stops_promote_before_any_write(self) -> None:
        (self.wiki / "concepts" / "sym.md").symlink_to(self.outside / "outside.md")
        prop = _proposals_dir(self.root)
        before = _snapshot(self.wiki)
        with self.assertRaises(PromoteValidationError) as ctx:
            api.promote(prop, self.paths)
        self.assertIn("concepts/sym.md", str(ctx.exception))
        self.assertIn("symlink", str(ctx.exception))
        self.assertNothingWritten(before, prop)
        result = run_cli("promote", str(prop), cwd=self.root)
        self.assertEqual(result.returncode, 9, result.stderr)
        self.assertNothingWritten(before, prop)

    def test_a_symlinked_directory_stops_promote_before_any_write(self) -> None:
        (self.wiki / "decisions").symlink_to(self.outside, target_is_directory=True)
        prop = _proposals_dir(self.root)
        before = _snapshot(self.wiki)
        with self.assertRaises(PromoteValidationError) as ctx:
            api.promote(prop, self.paths)
        self.assertIn("decisions", str(ctx.exception))
        self.assertNothingWritten(before, prop)
        self.assertEqual(sorted(p.name for p in self.outside.iterdir()), ["diagram.png", "outside.md"])

    def test_the_path_based_staging_copy_refuses_symlinks_too(self) -> None:
        (self.wiki / "concepts" / "sym.md").symlink_to(self.outside / "outside.md")
        prop = _proposals_dir(self.root)
        before = _snapshot(self.wiki)
        with patch.object(promoter, "_FD_STAGING", False), self.assertRaises(PromoteValidationError) as ctx:
            api.promote(prop, self.paths)
        self.assertIn("concepts/sym.md", str(ctx.exception))
        self.assertNothingWritten(before, prop)

    def test_replacing_a_page_that_is_a_symlink_never_writes_through_it(self) -> None:
        live = self.wiki / "concepts" / "alpha.md"
        live.unlink()
        live.symlink_to(self.outside / "outside.md")
        prop = _update_proposal(self.root, "2026-05-06-upd", "alpha", "Rewritten.\n")
        before = _snapshot(self.wiki)
        with self.assertRaises(PromoteValidationError):
            api.promote(prop, self.paths, allow_unguarded_updates=True)
        self.assertNothingWritten(before, prop)

    def test_edit_paths_that_escape_the_wiki_are_refused_before_staging(self) -> None:
        for n, path in enumerate(("../escape.md", "/tmp/escape.md", "concepts/../../escape.md")):
            prop = _update_proposal(self.root, f"2026-05-06-esc-{n}", "alpha", "x\n")
            plan = json.loads((prop / "plan.json").read_text(encoding="utf-8"))
            plan["edits"][0]["path"] = path
            plan["edits"][0]["action"] = "create"
            (prop / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
            before = _snapshot(self.wiki)
            with self.subTest(path=path), patch.object(promoter, "_stage_wiki") as staged:
                with self.assertRaises(PromoteValidationError):
                    api.promote(prop, self.paths)
                staged.assert_not_called()
            self.assertNothingWritten(before, prop)
            self.assertFalse((self.root / "knowledge" / "escape.md").exists())
            self.assertFalse(Path("/tmp/escape.md").exists())

    def test_apply_edit_refuses_a_target_that_leaves_the_staged_tree(self) -> None:
        with tempfile.TemporaryDirectory() as stage:
            edit = api.PageEdit("../escape.md", "create", "x\n", "r")
            with self.assertRaises(PromoteValidationError) as ctx:
                promoter._apply_edit(Path(stage) / "wiki", edit)
            self.assertIn("escapes the wiki directory", str(ctx.exception))
            self.assertFalse((Path(stage) / "escape.md").exists())

    def _hijack_incidents_dir(self) -> None:
        """Make the directory the commit would create a symlink to the outside, as a racing writer could."""
        (self.wiki / "incidents").symlink_to(self.outside, target_is_directory=True)

    def test_a_symlink_appearing_after_staging_is_caught_when_the_commit_is_planned(self) -> None:
        prop = _proposals_dir(self.root)
        original = promoter._check_preconditions

        def hijack_then_check(*args: object, **kwargs: object) -> list[str]:
            result = original(*args, **kwargs)  # type: ignore[arg-type]
            self._hijack_incidents_dir()
            return result

        with (
            patch.object(promoter, "_check_preconditions", hijack_then_check),
            patch.object(promoter, "_apply_planned", wraps=promoter._apply_planned) as applied,
            self.assertRaises(PromoteValidationError) as ctx,
        ):
            api.promote(prop, self.paths)
        self.assertIn("symlink", str(ctx.exception))
        applied.assert_not_called()
        self.assertFalse((self.outside / "cli-fixture.md").exists())
        self.assertFalse((prop / "receipt.json").exists())

    def test_a_symlink_appearing_after_planning_is_caught_by_the_lstat_recheck(self) -> None:
        prop = _proposals_dir(self.root)
        original = promoter._plan_commit

        def plan_then_hijack(*args: object, **kwargs: object) -> list[promoter._PlannedWrite]:
            result = original(*args, **kwargs)  # type: ignore[arg-type]
            self._hijack_incidents_dir()
            return result

        with (
            patch.object(promoter, "_plan_commit", plan_then_hijack),
            patch.object(promoter, "_apply_planned", wraps=promoter._apply_planned) as applied,
            self.assertRaises(PromoteValidationError) as ctx,
        ):
            api.promote(prop, self.paths)
        self.assertIn("incidents", str(ctx.exception))
        self.assertIn("symlink", str(ctx.exception))
        applied.assert_not_called()
        self.assertFalse((self.outside / "cli-fixture.md").exists())
        self.assertFalse((prop / "receipt.json").exists())


# ── the proposal boundary ─────────────────────────────────────


class TestProposalBoundary(_Case):
    def test_a_symlinked_plan_json_is_refused_unread(self) -> None:
        prop = _proposals_dir(self.root)
        real = self.outside / "plan.json"
        shutil.move(str(prop / "plan.json"), str(real))
        (prop / "plan.json").symlink_to(real)
        before = _snapshot(self.wiki)
        with self.assertRaises(PromoteValidationError) as ctx:
            api.promote(prop, self.paths)
        self.assertIn("plan.json", str(ctx.exception))
        self.assertIn("symlink", str(ctx.exception))
        self.assertNothingWritten(before, prop)

    def test_absolute_and_escaping_preview_pointers_exit_4(self) -> None:
        pointers = (str(self.outside / "outside.md"), "../../../outside/outside.md", "preview/../../x.md", "/etc/hosts")
        for n, pointer in enumerate(pointers):
            prop = _proposals_dir(self.root, slug=f"ptr-{n}")
            plan = json.loads((prop / "plan.json").read_text(encoding="utf-8"))
            plan["edits"][0]["preview"] = pointer
            (prop / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
            before = _snapshot(self.wiki)
            with self.subTest(pointer=pointer):
                with self.assertRaises(ContractViolationError) as ctx:
                    api.promote(prop, self.paths)
                self.assertIn(pointer, str(ctx.exception))
                self.assertEqual(run_cli("promote", str(prop), cwd=self.root).returncode, 4)
            self.assertNothingWritten(before, prop)

    def test_a_symlinked_preview_target_is_refused_by_the_enumeration(self) -> None:
        prop = _proposals_dir(self.root)
        preview = prop / "preview" / "incidents" / "cli-fixture.md"
        preview.unlink()
        preview.symlink_to(self.outside / "outside.md")
        before = _snapshot(self.wiki)
        with self.assertRaises(PromoteValidationError) as ctx:
            api.promote(prop, self.paths)
        self.assertIn("preview/incidents/cli-fixture.md", str(ctx.exception))
        self.assertNothingWritten(before, prop)

    def test_an_unreferenced_symlink_under_preview_is_refused_by_hashing_and_by_promote(self) -> None:
        prop = _proposals_dir(self.root)
        (prop / "preview" / ".stray.md").symlink_to(self.outside / "outside.md")
        with self.assertRaises(PromoteValidationError):
            payload_digest(prop)
        with self.assertRaises(PromoteValidationError):
            proposal_hash(prop)
        before = _snapshot(self.wiki)
        with self.assertRaises(PromoteValidationError) as ctx:
            api.promote(prop, self.paths)
        self.assertIn("preview/.stray.md", str(ctx.exception))
        self.assertNothingWritten(before, prop)

    def test_an_unreferenced_symlink_under_the_snapshot_is_refused_before_the_curator_delta(self) -> None:
        prop = _proposals_dir(self.root)
        snapshot = prop / ".ingest-snapshot"
        shutil.copytree(prop / "preview", snapshot / "preview")
        shutil.copy(prop / "plan.json", snapshot / "plan.json")
        (snapshot / "preview" / "stray.md").symlink_to(self.outside / "outside.md")
        before = _snapshot(self.wiki)
        with self.assertRaises(PromoteValidationError) as ctx:
            api.promote(prop, self.paths)
        self.assertIn(".ingest-snapshot/preview/stray.md", str(ctx.exception))
        self.assertNothingWritten(before, prop)
        self.assertFalse((self.wiki / ".audit" / "proposals").exists())

    def test_a_symlinked_snapshot_directory_is_refused(self) -> None:
        prop = _proposals_dir(self.root)
        (prop / ".ingest-snapshot").symlink_to(self.outside, target_is_directory=True)
        before = _snapshot(self.wiki)
        with self.assertRaises(PromoteValidationError) as ctx:
            api.promote(prop, self.paths)
        self.assertIn(".ingest-snapshot", str(ctx.exception))
        self.assertNothingWritten(before, prop)

    def test_a_symlinked_receipt_is_refused_before_it_is_read(self) -> None:
        prop = _proposals_dir(self.root)
        forged = self.outside / "receipt.json"
        forged.write_text(json.dumps({"state": "committed"}), encoding="utf-8")
        (prop / "receipt.json").symlink_to(forged)
        before = _snapshot(self.wiki)
        with self.assertRaises(PromoteValidationError) as ctx:
            api.promote(prop, self.paths)
        self.assertIn("receipt.json", str(ctx.exception))
        self.assertEqual(_snapshot(self.wiki), before)
        self.assertFalse((prop.parent / ".applied").exists())


class TestArchiveRootBoundary(_Case):
    """PR #41 review: a symlinked ``.applied/`` never receives an archive, and the source proposal stays."""

    def test_a_symlinked_applied_root_is_refused_before_any_write(self) -> None:
        prop = _proposals_dir(self.root)
        elsewhere = self.outside / "applied-elsewhere"
        elsewhere.mkdir()
        (prop.parent / ".applied").symlink_to(elsewhere)
        before = _snapshot(self.wiki)
        with self.assertRaises(PromoteValidationError) as ctx:
            api.promote(prop, self.paths)
        self.assertIn(".applied", str(ctx.exception))
        self.assertEqual(_snapshot(self.wiki), before)
        self.assertEqual(list(elsewhere.iterdir()), [], "nothing archived outside the proposal root")
        self.assertTrue((prop / "plan.json").is_file(), "the source proposal is untouched")
        self.assertFalse((prop / "receipt.json").exists())

    def test_a_file_named_applied_is_refused(self) -> None:
        prop = _proposals_dir(self.root)
        (prop.parent / ".applied").write_text("not a directory", encoding="utf-8")
        with self.assertRaises(PromoteValidationError):
            api.promote(prop, self.paths)
        self.assertTrue((prop / "plan.json").is_file())


class TestWikiStateBoundary(_Case):
    """PR #41 review: ingest's wiki-state reads stay inside the wiki (FR-012)."""

    def _state(self) -> object:
        return load_wiki_state(
            self.paths, source_path=self.root / "src.md", source_content="outside launch notes alpha"
        )

    def test_a_symlinked_page_never_reaches_the_snapshot(self) -> None:
        (self.wiki / "concepts").mkdir(exist_ok=True)
        (self.wiki / "concepts" / "outside.md").symlink_to(self.outside / "outside.md")
        state = self._state()
        self.assertNotIn("concepts/secret.md", state.candidates)  # type: ignore[attr-defined]
        for content in state.candidates.values():  # type: ignore[attr-defined]
            self.assertNotIn(_OUTSIDE_TEXT.strip(), content.text)
        self.assertIn("concepts/alpha.md", state.candidates)  # type: ignore[attr-defined]

    def test_a_symlinked_directory_never_reaches_the_snapshot(self) -> None:
        (self.wiki / "mirror").symlink_to(self.outside)
        state = self._state()
        self.assertFalse(any(rel.startswith("mirror/") for rel in state.candidates))  # type: ignore[attr-defined]

    def test_a_symlinked_index_or_log_is_refused(self) -> None:
        for name in ("index.md", "log.md"):
            with self.subTest(file=name):
                target = self.wiki / name
                backup = target.read_bytes() if target.exists() else None
                if target.exists():
                    target.unlink()
                target.symlink_to(self.outside / "outside.md")
                try:
                    with self.assertRaises(ContractViolationError) as ctx:
                        self._state()
                    self.assertIn(name, str(ctx.exception))
                finally:
                    target.unlink()
                    if backup is not None:
                        target.write_bytes(backup)


if __name__ == "__main__":
    unittest.main()
