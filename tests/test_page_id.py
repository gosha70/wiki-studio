# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.7.0 (US3): ``page_id`` assignment, lint and the page key (FR-014..FR-016, FR-019)."""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.conftest import make_repo_layout, run_cli
from tests.test_manifest import DECISION, ManifestCase, decision_edit
from wiki_studio import api
from wiki_studio.errors import PromoteValidationError
from wiki_studio.lint import lint_wiki
from wiki_studio.paths import WikiPaths
from wiki_studio.proposal import PageEdit, is_page_id, with_page_id
from wiki_studio.review import canonical_path, frontmatter_page_id, page_key
from wiki_studio.schema import SCHEMA_VERSION

PAGE_ID_LINE_RE = re.compile(r"^page_id: (pg-[0-9a-f]{32})$", re.MULTILINE)
CALLER_ID = "pg-0123456789abcdef0123456789abcdef"
PAGE = "decisions/retry-backoff.md"

# A page shaped like memkernel's bridge export (``status: draft``, its extra keys, a memkernel:// source).
BRIDGE_PAGE = (
    "---\npage_type: decision\nslug: bridge-export\ntitle: Bridge export\nstatus: draft\nlast_reviewed: 2026-10-25\n"
    "memkernel_ref: mem-42\nmemory_type: decision\nsources:\n  - url: memkernel://demo/mem-42\n"
    "    retrieved: 2026-10-25\n---\n\n# Bridge export\n\n## Decision\n\nKeep it.\n\n## Context\n\nExported.\n\n"
    "## Alternatives considered\n\nNone.\n\n## Consequences\n\nNone.\n"
)


def frontmatter_lines(text: str) -> list[str]:
    lines = text.split("\n")
    return lines[1 : lines.index("---", 1)]


def with_id(content: str, page_id: str) -> str:
    """``content`` with ``page_id`` written by the caller as the first frontmatter key."""
    return content.replace("---\n", f"---\npage_id: {page_id}\n", 1)


class TestAssignment(unittest.TestCase):
    def test_the_id_is_the_last_frontmatter_line(self) -> None:
        out = with_page_id(DECISION.format(slug="x"))
        fm = frontmatter_lines(out)
        match = PAGE_ID_LINE_RE.fullmatch(fm[-1])
        assert match is not None, fm
        self.assertTrue(is_page_id(match.group(1)))
        self.assertEqual(out.replace(f"{fm[-1]}\n", "", 1), DECISION.format(slug="x"), "only the line is added")

    def test_every_assignment_is_fresh(self) -> None:
        ids = {PAGE_ID_LINE_RE.findall(with_page_id(DECISION.format(slug="x")))[0] for _ in range(20)}
        self.assertEqual(len(ids), 20)

    def test_a_caller_id_is_never_rewritten(self) -> None:
        for value in (CALLER_ID, "not-an-id", ""):
            with self.subTest(value=value):
                content = with_id(DECISION.format(slug="x"), value)
                self.assertEqual(with_page_id(content), content)

    def test_without_complete_frontmatter_nothing_changes(self) -> None:
        for content in ("# no frontmatter\n", "---\nslug: x\n", ""):
            with self.subTest(content=content):
                self.assertEqual(with_page_id(content), content)

    def test_crlf_frontmatter_keeps_its_line_ending(self) -> None:
        content = DECISION.format(slug="x").replace("\n", "\r\n")
        out = with_page_id(content)
        self.assertRegex(out, r"\r\npage_id: pg-[0-9a-f]{32}\r\n---\r\n")


class TestApiPropose(ManifestCase):
    def setUp(self) -> None:
        super().setUp()
        api.init(self.paths)

    def preview(self, proposal: Path, rel: str = PAGE) -> str:
        return (proposal / "preview" / rel).read_text(encoding="utf-8")

    def test_the_default_leaves_bridge_shaped_bytes_unchanged(self) -> None:
        edits = [
            PageEdit("decisions/bridge-export.md", "create", BRIDGE_PAGE, "export"),
            PageEdit("index.md", "append-index", "- [Bridge export](decisions/bridge-export.md)", "export"),
        ]
        proposal = api.propose(edits, self.paths, name="memkernel-export-1", backend="memkernel")
        self.assertEqual(self.preview(proposal, "decisions/bridge-export.md"), BRIDGE_PAGE)
        api.promote(proposal, self.paths)
        self.assertEqual((self.wiki / "decisions" / "bridge-export.md").read_text(encoding="utf-8"), BRIDGE_PAGE)

    def test_opting_in_assigns_one_id_that_the_commit_carries(self) -> None:
        proposal = api.propose(decision_edit(), self.paths, name="p", assign_page_ids=True)
        preview = self.preview(proposal)
        ids = PAGE_ID_LINE_RE.findall(preview)
        self.assertEqual(len(ids), 1)
        # The index line is an append: never touched.
        self.assertEqual(self.preview(proposal, "index.md"), decision_edit()[1].new_content)
        api.promote(proposal, self.paths)
        self.assertEqual((self.wiki / PAGE).read_bytes(), preview.encode("utf-8"), "preview and commit: same bytes")
        self.assertEqual(lint_wiki(self.wiki), [])

    def test_a_caller_id_is_kept(self) -> None:
        edits = decision_edit()
        edits[0] = PageEdit(PAGE, "create", with_id(edits[0].new_content, CALLER_ID), "why")
        proposal = api.propose(edits, self.paths, name="p", assign_page_ids=True)
        self.assertEqual(self.preview(proposal), edits[0].new_content)

    def test_updates_are_never_assigned_an_id(self) -> None:
        api.promote(api.propose(decision_edit(), self.paths, name="first"), self.paths)
        page = api.read_page(PAGE, self.paths)
        revised = page.text.replace("status: draft", "status: stable")
        update = [PageEdit(PAGE, "update", revised, "stable", base_sha256=page.sha256)]
        proposal = api.propose(update, self.paths, name="second", assign_page_ids=True)
        self.assertEqual(self.preview(proposal), revised)


class TestProposeFromDir(ManifestCase):
    def setUp(self) -> None:
        super().setUp()
        api.init(self.paths)
        self.draft = self.root / "draft"
        (self.draft / "decisions").mkdir(parents=True)

    def test_a_create_carries_a_fresh_id_in_the_preview_and_the_commit(self) -> None:
        (self.draft / PAGE).write_text(DECISION.format(slug="retry-backoff"), encoding="utf-8")
        (self.draft / "index.md").write_text("- [Retry backoff](decisions/retry-backoff.md)\n", encoding="utf-8")
        result = self.cli("propose", "--from", str(self.draft), "--name", "cli", "--promote")
        self.assertEqual(result.returncode, 0, result.stderr)
        archived = self.paths.applied_dir / "cli" / "preview" / PAGE
        committed = (self.wiki / PAGE).read_bytes()
        self.assertEqual(committed, archived.read_bytes())
        ids = PAGE_ID_LINE_RE.findall(committed.decode("utf-8"))
        self.assertEqual(len(ids), 1)
        self.assertEqual(frontmatter_lines(committed.decode("utf-8"))[-1], f"page_id: {ids[0]}")
        self.assertEqual(lint_wiki(self.wiki), [])

    def test_a_caller_id_is_kept(self) -> None:
        content = with_id(DECISION.format(slug="retry-backoff"), CALLER_ID)
        (self.draft / PAGE).write_text(content, encoding="utf-8")
        (self.draft / "index.md").write_text("- [Retry backoff](decisions/retry-backoff.md)\n", encoding="utf-8")
        result = self.cli("propose", "--from", str(self.draft), "--name", "cli", "--promote")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.wiki / PAGE).read_text(encoding="utf-8"), content)


class TestIngest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-pageid-")
        self.root = make_repo_layout(Path(self._tmp.name))
        self.paths = WikiPaths.for_root(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_ingest_creates_carry_a_page_id_that_lands_unchanged(self) -> None:
        result = api.ingest(self.root / "sample-incident.md", self.paths, backend="test")
        assert result.written is not None and result.patch is not None
        creates = [e for e in result.patch.edits if e.action == "create"]
        self.assertEqual(len(creates), 1)
        preview = (result.written / "preview" / creates[0].path).read_bytes()
        self.assertEqual(len(PAGE_ID_LINE_RE.findall(preview.decode("utf-8"))), 1)
        for edit in result.patch.edits:
            if edit.action != "create":
                self.assertNotIn("page_id:", edit.new_content)
        api.promote(result.written, self.paths)
        self.assertEqual((self.paths.wiki_dir / creates[0].path).read_bytes(), preview)

    def test_cli_ingest_assigns_too(self) -> None:
        result = run_cli("ingest", "sample-incident.md", "--backend", "test", cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        written = Path(result.stdout.strip().splitlines()[0])
        plan = json.loads((written / "plan.json").read_text(encoding="utf-8"))
        create = next(e for e in plan["edits"] if e["action"] == "create")
        self.assertEqual(len(PAGE_ID_LINE_RE.findall((written / create["preview"]).read_text(encoding="utf-8"))), 1)


class TestLint(ManifestCase):
    def setUp(self) -> None:
        super().setUp()
        api.init(self.paths)

    def land(self, slug: str, page_id: str | None = None, name: str = "p") -> None:
        edits = decision_edit(slug)
        if page_id is not None:
            edits[0] = PageEdit(edits[0].path, "create", with_id(edits[0].new_content, page_id), "why")
        api.promote(api.propose(edits, self.paths, name=name), self.paths)

    def test_a_malformed_id_is_a_violation(self) -> None:
        self.land("retry-backoff")
        page = self.wiki / PAGE
        for bad in ("pg-ABCDEF", "pg-0123456789ABCDEF0123456789ABCDEF", "0123456789abcdef0123456789abcdef", ""):
            with self.subTest(bad=bad):
                page.write_text(with_id(DECISION.format(slug="retry-backoff"), bad), encoding="utf-8")
                violations = lint_wiki(self.wiki)
                self.assertEqual(len(violations), 1, violations)
                self.assertIn(f"{PAGE}: malformed page_id", violations[0])

    def test_a_shared_id_is_reported_on_every_page(self) -> None:
        self.land("retry-backoff", CALLER_ID, "one")
        other = self.wiki / "decisions" / "jitter.md"
        other.write_text(with_id(DECISION.format(slug="jitter"), CALLER_ID), encoding="utf-8")
        (self.wiki / "index.md").write_text(
            (self.wiki / "index.md").read_text(encoding="utf-8") + "- [Jitter](decisions/jitter.md)\n",
            encoding="utf-8",
        )
        violations = lint_wiki(self.wiki)
        self.assertEqual(
            sorted(violations),
            [
                f"decisions/jitter.md: duplicate page_id '{CALLER_ID}' (also in {PAGE})",
                f"{PAGE}: duplicate page_id '{CALLER_ID}' (also in decisions/jitter.md)",
            ],
        )

    def test_a_create_that_copies_an_id_is_refused_at_promote(self) -> None:
        self.land("retry-backoff", CALLER_ID, "one")
        edits = decision_edit("jitter")
        edits[0] = PageEdit(edits[0].path, "create", with_id(edits[0].new_content, CALLER_ID), "why")
        before = self.tree()
        with self.assertRaises(PromoteValidationError):
            api.promote(api.propose(edits, self.paths, name="copy-api"), self.paths)
        cli = self.cli("promote", str(api.propose(edits, self.paths, name="copy-cli")))
        self.assertEqual(cli.returncode, 9, cli.stderr)
        self.assertIn("duplicate page_id", cli.stderr)
        self.assertEqual(self.tree(), before, "nothing written")


class TestPageKey(unittest.TestCase):
    def test_canonical_path(self) -> None:
        for given in ("concepts/x.md", "./concepts/x.md", "/concepts/x.md", "concepts//x.md", "concepts/./x.md"):
            with self.subTest(given=given):
                self.assertEqual(canonical_path(given), "concepts/x.md")
        for bad in ("", ".", "..", "../x.md", "concepts/../../x.md"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                canonical_path(bad)

    def test_the_key_is_a_well_formed_id_else_the_canonical_path(self) -> None:
        page = DECISION.format(slug="x")
        self.assertEqual(page_key("./decisions/x.md", with_id(page, CALLER_ID)), CALLER_ID)
        self.assertEqual(page_key("./decisions/x.md", with_id(page, f'"{CALLER_ID}"')), CALLER_ID)
        self.assertEqual(page_key("./decisions/x.md", page), "decisions/x.md")
        self.assertEqual(page_key("decisions/x.md", with_id(page, "pg-bad")), "decisions/x.md")
        self.assertIsNone(frontmatter_page_id("# no frontmatter\n"))
        # A page_id below the frontmatter is body text, not a key.
        self.assertIsNone(frontmatter_page_id(page + f"\npage_id: {CALLER_ID}\n"))


class TestSchemaVersion(ManifestCase):
    def test_a_new_manifest_declares_schema_version_2(self) -> None:
        self.assertEqual(SCHEMA_VERSION, 2)
        api.init(self.paths)
        self.assertEqual(json.loads(self.manifest.read_text(encoding="utf-8"))["schema"]["version"], 2)

    def test_a_version_1_manifest_is_still_accepted(self) -> None:
        api.init(self.paths)
        self.edit_manifest(schema={"id": "wiki-studio/page-schema", "version": 1})
        api.promote(api.propose(decision_edit(), self.paths, name="p"), self.paths)
        self.assertEqual(api.info(self.paths).schema_contract.version, 1)

    def test_the_constant_cites_adr_0002(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "src" / "wiki_studio" / "schema" / "__init__.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("docs/adr/0002-page-identity-and-review-keys.md", source)
        adr = Path(__file__).resolve().parents[1] / "docs" / "adr" / "0002-page-identity-and-review-keys.md"
        self.assertTrue(adr.is_file())


if __name__ == "__main__":
    unittest.main()
