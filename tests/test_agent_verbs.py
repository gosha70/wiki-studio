# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.4.0: ``init``, ``propose --from`` and ``find`` let an agent use the wiki from a shell with no model (issue #10)."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tests.conftest import chdir, run_cli
from wiki_studio import api
from wiki_studio.errors import ContractViolationError, SourceMissingError
from wiki_studio.lint import lint_wiki
from wiki_studio.paths import WikiPaths

# The fixture memkernel's lc-wiki tasks start from: an index, no log.
LC_WIKI_INDEX = (
    "---\npage_type: index\nslug: index\ntitle: Wiki Index\nstatus: draft\nlast_reviewed: 2026-10-16\n---\n\n"
    "# Wiki Index\n"
)

DECISION = (
    "---\npage_type: decision\nslug: retry-backoff\ntitle: Retry backoff\nstatus: draft\nlast_reviewed: 2026-10-16\n"
    "sources:\n  - path: notes.md\n---\n\n# Retry backoff\n\n"
    "## Decision\n\nStart at 250 ms, double each attempt, cap at 8 s.\n\n"
    "## Context\n\nAgreed with the platform team.\n\n## Alternatives considered\n\nFixed 1 s delay.\n\n"
    "## Consequences\n\nLong outages wait at most 8 s between tries.\n"
)


class _Workspace(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-agent-")
        self.root = Path(self._tmp.name).resolve()
        (self.root / "notes.md").write_text("# notes\n", encoding="utf-8")
        self.paths = WikiPaths.for_root(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def cli(self, *argv: str):  # noqa: ANN201 - test helper
        return run_cli(*argv, cwd=self.root)

    def write_draft(self, files: dict[str, str], name: str = "draft") -> Path:
        draft = self.root / name
        for rel, text in files.items():
            (draft / rel).parent.mkdir(parents=True, exist_ok=True)
            (draft / rel).write_text(text, encoding="utf-8")
        return draft


class TestInit(_Workspace):
    def test_creates_index_and_log_that_lint_clean(self) -> None:
        result = self.cli("init", "--title", "Team wiki")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("created index.md, log.md", result.stdout)
        self.assertIn("title: Team wiki", (self.paths.wiki_dir / "index.md").read_text(encoding="utf-8"))
        self.assertEqual(lint_wiki(self.paths.wiki_dir), [])

    def test_never_overwrites_and_is_idempotent(self) -> None:
        self.paths.wiki_dir.mkdir(parents=True)
        (self.paths.wiki_dir / "index.md").write_text(LC_WIKI_INDEX, encoding="utf-8")
        first = api.init(self.paths)
        self.assertEqual(first.created, ["log.md"])
        self.assertEqual((self.paths.wiki_dir / "index.md").read_text(encoding="utf-8"), LC_WIKI_INDEX)
        second = self.cli("init")
        self.assertEqual(second.returncode, 0)
        self.assertIn("already initialised", second.stdout)


class TestProposeFromDir(_Workspace):
    def setUp(self) -> None:
        super().setUp()
        api.init(self.paths)

    def test_page_index_and_log_land_through_the_gate(self) -> None:
        draft = self.write_draft(
            {
                "decisions/retry-backoff.md": DECISION,
                "index.md": "- [Retry backoff](decisions/retry-backoff.md) — 250 ms doubling, 8 s cap.\n",
                "log.md": "- 2026-10-16 — created retry-backoff (decision)\n",
            }
        )
        result = self.cli("propose", "--from", str(draft), "--name", "backoff", "--promote")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("create decisions/retry-backoff.md", result.stdout)
        self.assertIn("append-index index.md", result.stdout)
        self.assertIn("applied", result.stdout)
        self.assertEqual((self.paths.wiki_dir / "decisions" / "retry-backoff.md").read_text(encoding="utf-8"), DECISION)
        self.assertIn("decisions/retry-backoff.md", (self.paths.wiki_dir / "index.md").read_text(encoding="utf-8"))
        self.assertEqual(lint_wiki(self.paths.wiki_dir), [])

    def test_promote_into_external_proposals_dir_needs_allow_out_of_repo(self) -> None:
        """Issue #24: --promote with a --proposals-dir outside the root is refused (exit 7) unless
        --allow-out-of-repo is given, which propose now accepts and forwards to promote."""
        outside = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="wiki_studio-outside-"))).resolve()
        files = {
            "decisions/retry-backoff.md": DECISION,
            "index.md": "- [Retry backoff](decisions/retry-backoff.md)\n",
        }
        argv = ("propose", "--from", str(self.write_draft(files)), "--proposals-dir", str(outside), "--promote")

        refused = self.cli(*argv, "--name", "refused")
        self.assertEqual(refused.returncode, 7, refused.stderr)
        self.assertIn("--allow-out-of-repo", refused.stderr)
        self.assertFalse((self.paths.wiki_dir / "decisions" / "retry-backoff.md").exists())
        self.assertTrue((outside / "refused" / "plan.json").is_file(), "the written proposal is kept")

        allowed = self.cli(*argv, "--name", "allowed", "--allow-out-of-repo")
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertEqual((self.paths.wiki_dir / "decisions" / "retry-backoff.md").read_text(encoding="utf-8"), DECISION)
        self.assertTrue((outside / ".applied" / "allowed").is_dir())
        self.assertEqual(lint_wiki(self.paths.wiki_dir), [])

    def test_existing_page_becomes_an_update(self) -> None:
        self.cli(
            "propose",
            "--from",
            str(
                self.write_draft(
                    {"decisions/retry-backoff.md": DECISION, "index.md": "- [R](decisions/retry-backoff.md)\n"}
                )
            ),
            "--name",
            "first",
            "--promote",
        )
        edits = api.edits_from_dir(
            self.write_draft({"decisions/retry-backoff.md": DECISION.replace("8 s.", "10 s.")}, name="second"),
            self.paths,
        )
        self.assertEqual([(e.action, e.path) for e in edits], [("update", "decisions/retry-backoff.md")])

    def test_content_index_page_is_a_page_not_an_append(self) -> None:
        glossary = (
            "---\npage_type: glossary\nslug: glossary\ntitle: Glossary\nstatus: draft\nlast_reviewed: 2026-10-16\n"
            "sources:\n  - path: notes.md\n---\n\n# Glossary\n\n### Backoff\n\nWaiting longer after each failure.\n"
        )
        edits = api.edits_from_dir(self.write_draft({"glossary/index.md": glossary}), self.paths)
        self.assertEqual([(e.action, e.path) for e in edits], [("create", "glossary/index.md")])

    def test_index_file_with_frontmatter_is_refused(self) -> None:
        draft = self.write_draft({"index.md": LC_WIKI_INDEX})
        with self.assertRaises(ContractViolationError):
            api.edits_from_dir(draft, self.paths)
        result = self.cli("propose", "--from", str(draft))
        self.assertEqual(result.returncode, 4)
        self.assertEqual(list(self.paths.proposals_dir.glob("*")), [])

    def test_invalid_page_is_rejected_before_anything_is_written(self) -> None:
        bad = DECISION.replace("page_type: decision", "page_type: concept")
        result = self.cli("propose", "--from", str(self.write_draft({"decisions/retry-backoff.md": bad})))
        self.assertEqual(result.returncode, 4)
        self.assertIn("should live under concepts/", result.stderr)
        self.assertFalse((self.paths.wiki_dir / "decisions").exists())

    def test_missing_or_empty_directory(self) -> None:
        with self.assertRaises(SourceMissingError):
            api.edits_from_dir(self.root / "nope", self.paths)
        (self.root / "empty").mkdir()
        self.assertEqual(self.cli("propose", "--from", str(self.root / "empty")).returncode, 4)

    def test_draft_inside_the_wiki_is_refused_and_hidden_dirs_are_skipped(self) -> None:
        with self.assertRaises(ContractViolationError):
            api.edits_from_dir(self.paths.wiki_dir, self.paths)
        draft = self.write_draft(
            {"decisions/retry-backoff.md": DECISION, ".audit/proposals/x/proposal.md": "# leftover\n"}, name="hidden"
        )
        self.assertEqual([e.path for e in api.edits_from_dir(draft, self.paths)], ["decisions/retry-backoff.md"])

    def test_default_name_sanitises_the_directory_name(self) -> None:
        from wiki_studio.cli import _default_proposal_name

        name = _default_proposal_name(self.root / "my draft (v2)!")
        self.assertRegex(name, r"^\d{4}-\d{2}-\d{2}-\d{6}-my-draft-v2$")
        self.assertRegex(_default_proposal_name(self.root / "..."), r"^\d{4}-\d{2}-\d{2}-\d{6}-agent$")

    def test_default_name_never_reuses_an_existing_or_archived_proposal(self) -> None:
        from wiki_studio.cli import _default_proposal_name

        base = _default_proposal_name(self.root / "draft")
        (self.paths.proposals_dir / base).mkdir(parents=True)
        (self.paths.proposals_dir / ".applied" / f"{base}-2").mkdir(parents=True)
        name = _default_proposal_name(self.root / "draft", self.paths.proposals_dir)
        self.assertIn(name, (f"{base}-3", _default_proposal_name(self.root / "draft")))  # clock may tick


class TestRepeatedRecordings(_Workspace):
    """PR #19 review: three recordings in one day from the same draft path all land and archive."""

    def setUp(self) -> None:
        super().setUp()
        api.init(self.paths)

    def test_three_recordings_from_one_draft_path(self) -> None:
        draft = self.root / "wiki-draft"
        for n in (1, 2, 3):
            slug = f"decision-{n}"
            page = DECISION.replace("slug: retry-backoff", f"slug: {slug}").replace(
                "title: Retry backoff", f"title: D{n}"
            )
            for old in draft.rglob("*"):
                if old.is_file():
                    old.unlink()
            (draft / "decisions").mkdir(parents=True, exist_ok=True)
            (draft / "decisions" / f"{slug}.md").write_text(page, encoding="utf-8")
            (draft / "index.md").write_text(f"- [D{n}](decisions/{slug}.md)\n", encoding="utf-8")
            result = self.cli("propose", "--from", str(draft), "--promote")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("archived to", result.stdout)
        self.assertEqual(
            sorted(p.name for p in (self.paths.wiki_dir / "decisions").iterdir()),
            ["decision-1.md", "decision-2.md", "decision-3.md"],
        )
        self.assertEqual([p for p in self.paths.proposals_dir.iterdir() if p.name != ".applied"], [])
        self.assertEqual(len(list((self.paths.proposals_dir / ".applied").iterdir())), 3)

    def test_archive_clash_is_archived_next_to_it(self) -> None:
        # Two proposals with the same explicit name on different days of the archive.
        for n in (1, 2):
            slug = f"clash-{n}"
            page = DECISION.replace("slug: retry-backoff", f"slug: {slug}")
            draft = self.write_draft(
                {f"decisions/{slug}.md": page, "index.md": f"- [C](decisions/{slug}.md)\n"}, name=f"d{n}"
            )
            written = api.propose(api.edits_from_dir(draft, self.paths), self.paths, name=f"same-{n}")
            target = self.paths.proposals_dir / "same"
            written.rename(target)
            result = api.promote(target, self.paths)
            expected = "same" if n == 1 else "same-2"
            self.assertEqual(result.archived_dir, self.paths.applied_dir / expected)
            self.assertFalse(target.exists())

    def test_default_name_is_dated_and_safe(self) -> None:
        draft = self.write_draft(
            {"decisions/retry-backoff.md": DECISION, "index.md": "- [R](decisions/retry-backoff.md)\n"}
        )
        result = self.cli("propose", "--from", str(draft))
        self.assertEqual(result.returncode, 0, result.stderr)
        written = Path(result.stdout.splitlines()[0])
        self.assertTrue(written.name.endswith("-draft"))
        self.assertEqual(json.loads((written / "plan.json").read_text(encoding="utf-8"))["backend"], "cli")


class TestProposeFactWarnings(_Workspace):
    """0.5.0 (FR-016): ``propose --from`` prints what an update drops, before ``--promote`` applies it."""

    # The update drops the notes.md citation and both "8 s" mentions; the number is one item.
    REWRITE = DECISION.replace("sources:\n  - path: notes.md\n", "sources:\n  - url: https://example.com\n").replace(
        "8 s", "a few seconds"
    )

    def setUp(self) -> None:
        super().setUp()
        api.init(self.paths)
        live = self.paths.wiki_dir / "decisions" / "retry-backoff.md"
        live.parent.mkdir(parents=True)
        live.write_text(DECISION, encoding="utf-8")
        with (self.paths.wiki_dir / "index.md").open("a", encoding="utf-8") as index:
            index.write("\n- [Retry backoff](decisions/retry-backoff.md)\n")
        # The agent read the live page and recorded its hash, so --promote can apply the replacement.
        base = api.read_page("decisions/retry-backoff.md", self.paths).sha256
        self.draft = self.write_draft(
            {"decisions/retry-backoff.md": self.REWRITE, ".base.json": json.dumps({"decisions/retry-backoff.md": base})}
        )

    def cli_merged(self, *argv: str) -> tuple[int, str]:
        """Run the CLI with stdout and stderr in one buffer, so line order across the two is kept."""
        from wiki_studio.cli import main

        buffer = io.StringIO()
        with chdir(self.root), contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            code = main(list(argv))
        return code, buffer.getvalue()

    def test_without_promote_warns_and_applies_nothing(self) -> None:
        result = self.cli("propose", "--from", str(self.draft), "--name", "rewrite")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("fact-check: decisions/retry-backoff.md: 2 item(s) removed", result.stderr)
        self.assertIn("  - notes.md", result.stderr)
        self.assertIn("  - 8 s", result.stderr)
        self.assertNotIn("fact-check", result.stdout)
        self.assertEqual((self.paths.wiki_dir / "decisions" / "retry-backoff.md").read_text(encoding="utf-8"), DECISION)
        plan = json.loads((self.paths.proposals_dir / "rewrite" / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["edits"][0]["fact_warnings"], ["notes.md", "8 s"])

    def test_undecodable_live_page_does_not_block_the_proposal(self) -> None:
        live = self.paths.wiki_dir / "decisions" / "retry-backoff.md"
        live.write_bytes(DECISION.encode("utf-8") + b"\xff\n")
        result = self.cli("propose", "--from", str(self.draft), "--name", "rewrite")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("fact-check: decisions/retry-backoff.md: not compared (live page not readable", result.stderr)
        self.assertNotIn("item(s) removed", result.stderr)
        plan = json.loads((self.paths.proposals_dir / "rewrite" / "plan.json").read_text(encoding="utf-8"))
        self.assertNotIn("fact_warnings", plan["edits"][0])
        self.assertIn("live page not readable", plan["edits"][0]["fact_check_error"])

    def test_with_promote_warns_before_the_apply_line_and_applies(self) -> None:
        code, output = self.cli_merged("propose", "--from", str(self.draft), "--name", "rewrite", "--promote")
        self.assertEqual(code, 0, output)
        warning, applied = "fact-check: decisions/retry-backoff.md: 2 item(s) removed", "\napplied "
        self.assertIn(applied, output)
        self.assertLess(output.index(warning), output.index(applied))
        live = (self.paths.wiki_dir / "decisions" / "retry-backoff.md").read_text(encoding="utf-8")
        self.assertEqual(live, self.REWRITE)
        archived = json.loads((self.paths.applied_dir / "rewrite" / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(archived["edits"][0]["fact_warnings"], ["notes.md", "8 s"])


class TestFind(_Workspace):
    def setUp(self) -> None:
        super().setUp()
        api.init(self.paths)
        draft = self.write_draft(
            {
                "decisions/retry-backoff.md": DECISION,
                "index.md": "- [Retry backoff](decisions/retry-backoff.md) — retries.\n",
            }
        )
        api.promote(api.propose(api.edits_from_dir(draft, self.paths), self.paths, name="seed"), self.paths)

    def test_returns_the_pages_query_would_load_without_a_model(self) -> None:
        result = api.find("what retry backoff cap did we agree", self.paths)
        self.assertEqual([p.path for p in result.pages], ["decisions/retry-backoff.md"])
        self.assertEqual(result.pages[0].title, "Retry backoff")
        self.assertFalse(self.paths.query_log.exists(), "find must not write the query log")

    def test_cli_text_and_json(self) -> None:
        text = self.cli("find", "retry backoff")
        self.assertEqual(text.returncode, 0, text.stderr)
        self.assertIn("knowledge/wiki/index.md  (always read first)", text.stdout)
        self.assertIn("knowledge/wiki/decisions/retry-backoff.md  Retry backoff", text.stdout)
        payload = json.loads(self.cli("find", "retry backoff", "--json").stdout)
        self.assertEqual(payload["pages"][0]["path"], "decisions/retry-backoff.md")

    def test_missing_index_is_an_error_pointing_at_init(self) -> None:
        (self.paths.wiki_dir / "index.md").unlink()
        result = self.cli("find", "retry backoff")
        self.assertEqual(result.returncode, 5)
        self.assertIn("wiki-studio init", result.stderr)

    def test_no_match_says_so(self) -> None:
        result = self.cli("find", "kubernetes ingress annotations")
        self.assertEqual(result.returncode, 0)
        self.assertIn("no index-linked page shares a word", result.stdout)
        self.assertEqual(api.find("kubernetes ingress annotations", self.paths).pages, ())


class TestLcWikiShape(_Workspace):
    """memkernel's lc-wiki tasks: session 0 records a decision, session 1 sees only the wiki."""

    def test_session_zero_records_and_session_one_finds(self) -> None:
        self.paths.wiki_dir.mkdir(parents=True)
        (self.paths.wiki_dir / "index.md").write_text(LC_WIKI_INDEX, encoding="utf-8")
        # Session 0, from a shell: scaffold, write the page, propose and promote in one command.
        self.assertEqual(self.cli("init").returncode, 0)
        draft = self.write_draft(
            {
                "decisions/retry-backoff.md": DECISION,
                "index.md": "- [Retry backoff](decisions/retry-backoff.md) — 250 ms doubling, 8 s cap.\n",
                "log.md": "- 2026-10-16 — created retry-backoff (decision)\n",
            }
        )
        self.assertEqual(self.cli("propose", "--from", str(draft), "--promote").returncode, 0)
        # Session 1: only the wiki carried over.
        found = self.cli("find", "how long should the delay be between retry attempts")
        self.assertIn("decisions/retry-backoff.md", found.stdout)
        self.assertEqual(self.cli("lint").returncode, 0)


if __name__ == "__main__":
    unittest.main()
