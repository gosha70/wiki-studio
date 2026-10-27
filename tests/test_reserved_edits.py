# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.7.0 (US4): reserved edit paths and self-declared approval keys are refused on every wiki (FR-028, FR-029)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from tests.test_approve import ApprovalCase, page_text
from wiki_studio import api
from wiki_studio.errors import ContractViolationError, PromoteValidationError
from wiki_studio.proposal import PageEdit, reserved_edit_problems
from wiki_studio.schema import RESERVED_APPROVAL_KEYS

if TYPE_CHECKING:
    from pathlib import Path

RESERVED_PATHS = (
    ".wiki-studio.json",
    f".audit/approvals/path/{'0' * 64}/{'1' * 64}/{'2' * 64}/approved.json",
    "schema/page-types.md",
    "./.audit/ingest-log.md",
    ".hidden/notes.md",
)


class TestReservedEditsInPropose(ApprovalCase):
    def test_each_reserved_path_is_refused_with_exit_4_naming_it(self) -> None:
        for path in RESERVED_PATHS:
            with self.subTest(path), self.assertRaises(ContractViolationError) as ctx:
                api.propose([PageEdit(path, "create", page_text("x"), "why")], self.paths, name="reserved")
            self.assertIn(f"{path}: reserved path", str(ctx.exception))
        self.assertFalse((self.paths.proposals_dir / "reserved").exists())

    def test_the_cli_propose_refuses_a_reserved_path(self) -> None:
        drafts = self.root / "drafts"
        (drafts / "schema").mkdir(parents=True)
        (drafts / "schema" / "page-types.md").write_text(page_text("page-types"), encoding="utf-8")
        result = self.cli("propose", "--from", str(drafts), "--name", "p")
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertIn("schema/page-types.md: reserved path", result.stderr)

    def test_each_reserved_frontmatter_key_is_refused_on_create_and_update(self) -> None:
        rel = self.create("existing")
        base = api.read_page(rel, self.paths).sha256
        for key in RESERVED_APPROVAL_KEYS:
            with self.subTest(key):
                claim = f"{key}: true\n"
                create = PageEdit("decisions/new.md", "create", page_text("new", extra=claim), "why")
                update = PageEdit(rel, "update", page_text("existing", extra=claim), "why", base_sha256=base)
                for edit in (create, update):
                    with self.assertRaises(ContractViolationError) as ctx:
                        api.propose([edit], self.paths, name=f"claim-{key}")
                    self.assertIn(f"{edit.path}: frontmatter key '{key}' is reserved", str(ctx.exception))

    def test_status_stable_is_allowed_and_a_raw_dot_slash_index_append_passes(self) -> None:
        edits = [
            PageEdit("decisions/fine.md", "create", page_text("fine", status="stable"), "why"),
            PageEdit("./index.md", "append-index", "- [fine](decisions/fine.md)", "why"),
        ]
        result = api.promote(api.propose(edits, self.paths, name="fine"), self.paths)
        self.assertIn("index.md", result.applied_paths)

    def test_an_indented_or_body_key_is_not_a_frontmatter_claim(self) -> None:
        text = page_text("fine", extra="sources_note:\n  approved: nested\n") + "\napproved: in the body\n"
        self.assertEqual(reserved_edit_problems([PageEdit("decisions/fine.md", "create", text, "why")]), [])

    def test_a_legacy_wiki_refuses_them_too(self) -> None:
        self.manifest.unlink()
        with self.assertRaises(ContractViolationError):
            api.propose([PageEdit(".wiki-studio.json", "create", "{}", "why")], self.paths, name="legacy")

    def test_an_escape_keeps_its_own_exit_code(self) -> None:
        with self.assertRaises(ContractViolationError) as ctx:
            api.propose([PageEdit("../outside.md", "create", page_text("outside"), "why")], self.paths, name="esc")
        self.assertIn("must be relative", str(ctx.exception))


class TestReservedEditsInPromote(ApprovalCase):
    """A proposal written by hand (not through ``propose``) is refused by ``promote`` before staging."""

    def _hand_proposal(self, name: str, edits: list[tuple[str, str, str]]) -> Path:
        directory = self.paths.proposals_dir / name
        (directory / "preview").mkdir(parents=True)
        plan_edits = []
        for index, (path, action, content) in enumerate(edits):
            preview = f"preview/{index}.md"
            (directory / preview).write_text(content, encoding="utf-8")
            plan_edits.append({"path": path, "action": action, "preview": preview, "rationale": "why"})
        plan = {"version": 1, "source_path": "", "backend": "hand", "rationale": "", "edits": plan_edits}
        (directory / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        return directory

    def test_reserved_paths_and_keys_are_exit_4_with_the_wiki_untouched(self) -> None:
        before = self.tree()
        cases = {
            "manifest": [(".wiki-studio.json", "create", "{}")],
            "record": [(RESERVED_PATHS[1], "create", "{}")],
            "override": [("schema/page-types.md", "create", "# rules\n")],
            "claim": [("decisions/claim.md", "create", page_text("claim", extra="approved: true\n"))],
        }
        for name, edits in cases.items():
            with self.subTest(name):
                directory = self._hand_proposal(name, edits)
                result = self.cli("promote", str(directory))
                self.assertEqual(result.returncode, 4, result.stderr)
                self.assertIn("reserved", result.stderr)
                with self.assertRaises(ContractViolationError):
                    api.promote(directory, self.paths, dry_run=True)
                self.assertEqual(self.tree(), before)

    def test_an_escape_in_a_hand_proposal_keeps_exit_9(self) -> None:
        directory = self._hand_proposal("escape", [("../outside.md", "create", page_text("outside"))])
        self.assertEqual(self.cli("promote", str(directory)).returncode, 9)
        with self.assertRaises(PromoteValidationError):
            api.promote(directory, self.paths)
