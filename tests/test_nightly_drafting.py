# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.10.0 (US3, US4): drafting with an explicit backend and no duplicate on rerun (FR-013 - FR-023, FR-025 - FR-027).

The test backend supplies the valid deterministic draft; stub backends (an
object with ``call(prompt)`` passed to ``api.nightly``, or the test backend
patched behind ``--backend test`` for the CLI cases) supply the refused
shapes. Every run is wrapped by FR-007's snapshot of every file under the
wiki.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from tests.conftest import make_repo_layout, packaged_schema_dir, run_cli
from wiki_studio import api, nightly
from wiki_studio.backends.test import TestBackend
from wiki_studio.errors import (
    BackendInvocationError,
    OutputWriteError,
    PromoteApplyError,
    SourceMissingError,
)
from wiki_studio.findings import Finding
from wiki_studio.nightly import (
    INLINE_LINK_RE,
    NightlyResult,
    code_regions,
    count_links_to,
    proposal_name,
    resolve_link_target,
    strip_links_to,
)
from wiki_studio.paths import WikiPaths
from wiki_studio.prompt import CURATE_TASK, compose_curate_prompt
from wiki_studio.proposal import PageAction, PageEdit

_INDEX = (
    "---\npage_type: index\nslug: index\ntitle: Test Wiki\nstatus: stable\nlast_reviewed: 2026-11-17\n---\n"
    "\n# Test Wiki\n\n{links}\n"
)

_DECISION = (
    "---\n"
    "page_type: decision\n"
    "slug: {slug}\n"
    "title: {title}\n"
    "status: stable\n"
    "last_reviewed: 2026-11-17\n"
    "sources:\n"
    "  - path: notes.md\n"
    "---\n"
    "\n"
    "# {title}\n"
    "\n"
    "## Decision\n"
    "\n"
    "{body}\n"
    "\n"
    "## Context\n"
    "\n"
    "Agreed with the platform team.\n"
    "\n"
    "## Alternatives considered\n"
    "\n"
    "A fixed delay was rejected.\n"
    "\n"
    "## Consequences\n"
    "\n"
    "Retries are bounded.\n"
)

_GLOSSARY = (
    "---\n"
    "page_type: glossary\n"
    "slug: {slug}\n"
    "title: {title}\n"
    "status: stable\n"
    "last_reviewed: 2026-11-17\n"
    "avoid: {avoid}\n"
    "sources:\n"
    "  - path: notes.md\n"
    "---\n"
    "\n"
    "# {title}\n"
    "\n"
    "## Definition\n"
    "\n"
    "{body}\n"
    "\n"
    "## Where it appears\n"
    "\n"
    "Everywhere.\n"
)


def _decision(slug: str, title: str, body: str) -> str:
    return _DECISION.format(slug=slug, title=title, body=body)


def _glossary(slug: str, title: str, body: str, avoid: str) -> str:
    return _GLOSSARY.format(slug=slug, title=title, body=body, avoid=avoid)


class CountingBackend:
    """A stub backend that delegates to the test backend and records every call."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def call(self, prompt: dict) -> dict:
        self.calls.append(prompt)
        return TestBackend().call(prompt)


@contextlib.contextmanager
def _patched_test_backend(mutator):
    """Patch the test backend behind ``--backend test`` with ``mutator(prompt, draft)``."""
    original = TestBackend.call

    def call(self, prompt):  # noqa: ANN001 - a stub replacing the bound method
        return mutator(prompt, original(self, prompt))

    with patch.object(TestBackend, "call", call):
        yield


def _first_update(draft: dict) -> dict:
    return next(edit for edit in draft["edits"] if edit["action"] == "update")


def _append_index(draft: dict) -> dict:
    return next(edit for edit in draft["edits"] if edit["action"] == "append-index")


def _append_log(draft: dict) -> dict:
    return next(edit for edit in draft["edits"] if edit["action"] == "append-log")


def _reword(prompt: dict, draft: dict) -> dict:
    """FR-023(c): the link is added and one word of the sentence changes."""
    edit = _first_update(draft)
    edit["new_content"] = edit["new_content"].replace("drains nightly", "drains each night")
    return draft


def _see_also(prompt: dict, draft: dict) -> dict:
    """FR-023(c): a new ``See also`` line."""
    edit = _first_update(draft)
    edit["new_content"] = edit["new_content"] + "\nSee also: [Queue Policy](queue-policy.md)\n"
    return draft


def _changed_frontmatter(prompt: dict, draft: dict) -> dict:
    """FR-023(c): the link is added and ``last_reviewed:`` changes."""
    edit = _first_update(draft)
    edit["new_content"] = edit["new_content"].replace("last_reviewed: 2026-11-17", "last_reviewed: 2026-11-16")
    return draft


def _second_index_link(prompt: dict, draft: dict) -> dict:
    """FR-023(c): the index line links the orphan and one more page."""
    edit = _append_index(draft)
    edit["new_content"] = edit["new_content"] + " See [the first page](decisions/alpha.md)."
    return draft


def _always_refused(prompt: dict, draft: dict) -> dict:
    """A draft FR-019 always refuses: the first edit gains one more link."""
    draft["edits"][0]["new_content"] = draft["edits"][0]["new_content"] + " [x](y.md)"
    return draft


def _canonical_link_sub(transform):
    """Rewrite the added link to the canonical page in the first update with ``transform(match)``."""

    def mutator(prompt: dict, draft: dict) -> dict:
        edit = _first_update(draft)
        edit["new_content"] = INLINE_LINK_RE.sub(
            lambda match: transform(match) if match.group(2).endswith("queue-policy.md") else match.group(0),
            edit["new_content"],
        )
        return draft

    return mutator


class DraftingCase(unittest.TestCase):
    """A managed wiki in a temporary project layout, built with ``api.init``."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-nightly-drafting-")
        self.root = make_repo_layout(Path(self._tmp.name))
        (self.root / "notes.md").write_text("# notes\n", encoding="utf-8")
        self.paths = WikiPaths.for_root(self.root)
        api.init(self.paths)
        self.wiki = self.paths.wiki_dir
        self.proposals = self.paths.proposals_dir

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # -- fixtures -------------------------------------------------

    def run_cli(self, *argv: str):
        return run_cli(*argv, cwd=self.root)

    def write_page(self, rel: str, text: str) -> None:
        target = self.wiki / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def write_index(self, *rels: str) -> None:
        links = "\n".join(f"- [{Path(rel).stem}]({rel})" for rel in rels)
        (self.wiki / "index.md").write_text(_INDEX.format(links=links), encoding="utf-8")

    def build_wiki(self) -> None:
        """One ``missing-cross-link`` (editable: beta, gamma) and one draftable weak orphan (hidden)."""
        self.write_index("decisions/alpha.md", "decisions/beta.md", "decisions/gamma.md", "decisions/queue-policy.md")
        self.write_page("decisions/queue-policy.md", _decision("queue-policy", "Queue Policy", "The rules live here."))
        self.write_page(
            "decisions/alpha.md",
            _decision(
                "alpha",
                "Alpha",
                "The queue policy drains nightly. See [the queue policy](queue-policy.md). Start from "
                "[the second page](beta.md), and the note sits in [the hidden page](hidden.md).",
            ),
        )
        self.write_page(
            "decisions/beta.md",
            _decision("beta", "Beta", "The queue policy drains nightly. Start from [the third page](gamma.md)."),
        )
        self.write_page(
            "decisions/gamma.md",
            _decision("gamma", "Gamma", "The queue policy drains nightly. Start from [the first page](alpha.md)."),
        )
        self.write_page(
            "decisions/hidden.md", _decision("hidden", "Hidden Decision", "This note is linked from a content page.")
        )

    def build_cross_link_wiki(self) -> None:
        """Only the ``missing-cross-link`` finding is draftable (editable: beta, gamma)."""
        self.write_index("decisions/alpha.md", "decisions/beta.md", "decisions/gamma.md", "decisions/queue-policy.md")
        self.write_page("decisions/queue-policy.md", _decision("queue-policy", "Queue Policy", "The rules live here."))
        self.write_page(
            "decisions/alpha.md",
            _decision(
                "alpha",
                "Alpha",
                "The queue policy drains nightly. See [the queue policy](queue-policy.md). Start from "
                "[the second page](beta.md).",
            ),
        )
        self.write_page(
            "decisions/beta.md",
            _decision("beta", "Beta", "The queue policy drains nightly. Start from [the third page](gamma.md)."),
        )
        self.write_page(
            "decisions/gamma.md",
            _decision("gamma", "Gamma", "The queue policy drains nightly. Start from [the first page](alpha.md)."),
        )

    def build_orphan_wiki(self) -> None:
        """Only the weak orphan ``decisions/hidden.md`` is draftable."""
        self.write_index("decisions/alpha.md", "decisions/beta.md", "decisions/gamma.md")
        self.write_page(
            "decisions/alpha.md",
            _decision("alpha", "Alpha", "A first page. See [the hidden page](hidden.md)."),
        )
        self.write_page("decisions/beta.md", _decision("beta", "Beta", "A second page. See [the third](gamma.md)."))
        self.write_page("decisions/gamma.md", _decision("gamma", "Gamma", "A third page. See [the first](alpha.md)."))
        self.write_page(
            "decisions/hidden.md", _decision("hidden", "Hidden Decision", "This note is linked from a content page.")
        )

    def build_orphans(self, count: int) -> None:
        """``count`` draftable weak orphans, ``decisions/hidden-1`` .. ``hidden-N``, each linked once from alpha."""
        links = " ".join(f"[the hidden page {i}](hidden-{i}.md)" for i in range(1, count + 1))
        self.write_index("decisions/alpha.md")
        self.write_page("decisions/alpha.md", _decision("alpha", "Alpha", f"A first page. See {links}."))
        for i in range(1, count + 1):
            self.write_page(
                f"decisions/hidden-{i}.md",
                _decision(f"hidden-{i}", f"Hidden {i}", "This note is linked from a content page."),
            )

    def build_seven_unlinked_wiki(self) -> None:
        """One cross-link finding with seven unlinked pages, every one editable."""
        unlinked = [f"decisions/unlinked-{i}.md" for i in range(1, 8)]
        self.write_index("decisions/budget-policy.md", "decisions/linker.md", *unlinked)
        self.write_page("decisions/budget-policy.md", _decision("budget-policy", "Budget Policy", "The rules here."))
        self.write_page(
            "decisions/linker.md",
            _decision("linker", "Linker", "See [the budget policy](budget-policy.md)."),
        )
        for i in range(1, 8):
            self.write_page(
                f"decisions/unlinked-{i}.md",
                _decision(f"unlinked-{i}", f"Unlinked {i}", "The budget policy applies here."),
            )

    def build_code_only_wiki(self) -> None:
        """A cross-link finding whose unlinked page beta mentions the entity only inside a fenced block."""
        self.write_index("decisions/alpha.md", "decisions/beta.md", "decisions/gamma.md", "decisions/queue-policy.md")
        self.write_page("decisions/queue-policy.md", _decision("queue-policy", "Queue Policy", "The rules live here."))
        self.write_page(
            "decisions/alpha.md",
            _decision("alpha", "Alpha", "See [the queue policy](queue-policy.md)."),
        )
        self.write_page(
            "decisions/beta.md",
            _decision("beta", "Beta", "Quoted only:\n\n```\nThe queue policy is quoted.\n```"),
        )
        self.write_page("decisions/gamma.md", _decision("gamma", "Gamma", "The queue policy applies here."))

    def build_alias_wiki(self) -> None:
        """A glossary canonical page whose avoid term ``backlog`` is what the unlinked pages mention."""
        self.write_index("glossary/queue.md", "decisions/alpha.md", "decisions/beta.md", "decisions/gamma.md")
        self.write_page("glossary/queue.md", _glossary("queue", "Queue", "The queue holds work.", "backlog"))
        self.write_page("decisions/alpha.md", _decision("alpha", "Alpha", "See [the queue](../glossary/queue.md)."))
        self.write_page("decisions/beta.md", _decision("beta", "Beta", "The backlog holds work."))
        self.write_page("decisions/gamma.md", _decision("gamma", "Gamma", "The backlog grows."))

    # -- proofs ---------------------------------------------------

    def wiki_snapshot(self) -> dict[str, str]:
        """Every file under the wiki: relative path -> sha256, ``.audit/`` included (FR-007)."""
        return {
            path.relative_to(self.wiki).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(self.wiki.rglob("*"))
            if path.is_file()
        }

    def proposal_dirs(self) -> list[str]:
        """The pending (non-hidden) proposal directories directly under the proposals directory (FR-006)."""
        return sorted(
            entry.name for entry in self.proposals.iterdir() if entry.is_dir() and not entry.name.startswith(".")
        )

    def assert_refused_through_cli(self, build: str, mutator) -> None:
        getattr(self, f"build_{build}_wiki")()
        before = self.wiki_snapshot()
        with _patched_test_backend(mutator):
            result = self.run_cli("nightly", "--backend", "test")
        self.assertEqual(self.wiki_snapshot(), before)
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertEqual(self.proposal_dirs(), [])
        self.assertIn("out of bounds", result.stdout)
        self.assertIn("### Failed", result.stdout)

    def assert_out_of_bounds(self, mutator, *, build: str = "cross_link", contains: str | None = None) -> str:
        getattr(self, f"build_{build}_wiki")()
        before = self.wiki_snapshot()
        result = api.nightly(self.paths, backend=_StubBackend(mutator))
        self.assertEqual(self.wiki_snapshot(), before)
        self.assertEqual(self.proposal_dirs(), [])
        self.assertEqual(result.exit_code, 4)
        self.assertTrue(result.failed, result.not_drafted)
        self.assertIn("out of bounds", result.failed[0].reason)
        if contains is not None:
            self.assertIn(contains, result.failed[0].reason)
        return result.failed[0].reason


class _StubBackend:
    """A stub backend: the test backend's draft, mutated before it is returned."""

    def __init__(self, mutator) -> None:
        self._mutator = mutator

    def call(self, prompt: dict) -> dict:
        return self._mutator(prompt, TestBackend().call(prompt))


class TestDrafting(DraftingCase):
    def test_one_proposal_per_draftable_finding_with_the_base_hashes(self) -> None:
        self.build_wiki()
        before = self.wiki_snapshot()
        result = api.nightly(self.paths, backend="test")
        self.assertEqual(self.wiki_snapshot(), before)
        self.assertEqual(result.drafting.state, "on")
        self.assertEqual(result.drafting.attempts, 2)
        self.assertEqual(result.drafting.created, 2)
        self.assertEqual(result.exit_code, 0, [entry.message for entry in result.failed])
        expected = sorted(
            (
                proposal_name("weak-orphan", ("decisions/hidden.md",)),
                proposal_name(
                    "missing-cross-link",
                    ("decisions/queue-policy.md", "decisions/beta.md", "decisions/gamma.md"),
                ),
            )
        )
        self.assertEqual(self.proposal_dirs(), expected)
        for created in result.created:
            plan = json.loads((Path(created.path) / "plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["backend"], "test")
            for entry in plan["edits"]:
                if entry["action"] == "update":
                    self.assertEqual(entry["base_sha256"], api.read_page(entry["path"], self.paths).sha256)

    def test_every_created_proposal_promotes_cleanly_and_clears_its_finding(self) -> None:
        self.build_wiki()
        result = api.nightly(self.paths, backend="test")
        self.assertEqual(len(result.created), 2)
        for created in result.created:
            api.promote(Path(created.path), self.paths)
        kinds = {finding.kind for finding in api.findings(self.paths).findings}
        self.assertNotIn("missing-cross-link", kinds)
        self.assertNotIn("weak-orphan", kinds)

    def test_a_structurally_broken_wiki_drafts_nothing(self) -> None:
        self.build_orphan_wiki()
        self.write_page("decisions/orphan.md", _decision("orphan", "Orphan", "Nobody links here."))
        backend = CountingBackend()
        before = self.wiki_snapshot()
        result = api.nightly(self.paths, backend=backend)
        self.assertEqual(self.wiki_snapshot(), before)
        self.assertEqual(backend.calls, [])
        self.assertEqual(result.drafting.state, "skipped")
        self.assertEqual(result.drafting.reason, "structural lint failed")
        self.assertEqual(result.not_drafted[0].reason, "drafting skipped: structural lint failed")
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(self.proposal_dirs(), [])

    def test_a_draftable_finding_is_not_drafted_without_a_backend(self) -> None:
        self.build_orphan_wiki()
        result = api.nightly(self.paths)
        self.assertEqual(result.not_drafted[0].reason, "drafting off: no --backend")
        self.assertIn("drafting off: no --backend", result.render_markdown())

    def test_the_by_flag_is_recorded_as_the_proposer(self) -> None:
        self.build_orphan_wiki()
        result = self.run_cli("nightly", "--backend", "test", "--by", "curator-ada")
        self.assertEqual(result.returncode, 0, result.stderr)
        (proposal,) = [entry for entry in self.proposals.iterdir() if entry.is_dir()]
        plan = json.loads((proposal / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["proposer"], {"name": "curator-ada", "source": "flag"})

    def test_an_unreadable_page_is_not_drafted_without_a_call(self) -> None:
        self.build_orphan_wiki()
        backend = CountingBackend()
        original = api.read_page

        def read(page: str, paths: WikiPaths):
            if page == "decisions/hidden.md":
                raise SourceMissingError("page not found")
            return original(page, paths)

        with patch("wiki_studio.api.read_page", side_effect=read):
            result = api.nightly(self.paths, backend=backend)
        self.assertEqual(backend.calls, [])
        self.assertEqual(result.not_drafted[0].reason, "page unreadable: page not found")
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(self.proposal_dirs(), [])

    def test_a_reply_base_sha256_is_ignored(self) -> None:
        self.build_cross_link_wiki()

        def mutate(prompt: dict, draft: dict) -> dict:
            for edit in draft["edits"]:
                edit["base_sha256"] = "0" * 64
            return draft

        result = api.nightly(self.paths, backend=_StubBackend(mutate))
        self.assertEqual(len(result.created), 1, [entry.message for entry in result.failed])
        plan = json.loads((Path(result.created[0].path) / "plan.json").read_text(encoding="utf-8"))
        updates = [entry for entry in plan["edits"] if entry["action"] == "update"]
        self.assertTrue(updates)
        for entry in updates:
            self.assertEqual(entry["base_sha256"], api.read_page(entry["path"], self.paths).sha256)


class TestNoDuplicateOnRerun(DraftingCase):
    """US4: a rerun duplicates nothing; an archived or deleted proposal does not block (FR-025 - FR-027)."""

    def test_an_unchanged_rerun_makes_no_call_and_lists_every_finding_as_already_proposed(self) -> None:
        self.build_wiki()
        first = api.nightly(self.paths, backend="test")
        self.assertEqual(len(first.created), 2)
        names = self.proposal_dirs()
        backend = CountingBackend()
        before = self.wiki_snapshot()
        second = api.nightly(self.paths, backend=backend)
        self.assertEqual(self.wiki_snapshot(), before)
        self.assertEqual(backend.calls, [])
        self.assertEqual(self.proposal_dirs(), names)
        self.assertEqual(second.created, ())
        self.assertEqual(second.failed, ())
        self.assertEqual(second.not_drafted, ())
        self.assertEqual(second.drafting.attempts, 0)
        self.assertEqual(second.drafting.created, 0)
        self.assertEqual(second.drafting.state, "on")
        self.assertEqual(second.exit_code, 0)
        self.assertEqual(
            [(entry.name, entry.kind, entry.pages) for entry in second.already_proposed],
            [(entry.name, entry.kind, entry.pages) for entry in first.created],
        )
        self.assertEqual(
            second.as_dict()["proposals"]["already_proposed"],
            [{"name": entry.name, "kind": entry.kind, "pages": list(entry.pages)} for entry in second.already_proposed],
        )
        report = second.render_markdown()
        self.assertNotIn("### Already proposed\n\nnone", report)
        for entry in first.created:
            self.assertIn(f"- [{entry.kind}] {', '.join(entry.pages)}: {entry.name}", report)
        settled = {(entry.kind, entry.pages) for entry in second.already_proposed}
        curator = {(finding.kind, finding.pages) for finding in second.needs_curator}
        self.assertFalse(settled & curator, "an already proposed finding needs no curator")

    def test_two_consecutive_cli_runs_leave_the_same_directories_and_the_second_exits_zero(self) -> None:
        self.build_wiki()
        before = self.wiki_snapshot()
        first = self.run_cli("nightly", "--backend", "test")
        self.assertEqual(first.returncode, 0, first.stderr)
        names = self.proposal_dirs()
        self.assertEqual(len(names), 2)
        second = self.run_cli("nightly", "--backend", "test")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(self.wiki_snapshot(), before)
        self.assertEqual(self.proposal_dirs(), names)
        self.assertNotIn("### Already proposed\n\nnone", second.stdout)
        for name in names:
            self.assertIn(name, second.stdout)

    def test_a_proposal_archived_to_applied_does_not_block_the_redraft(self) -> None:
        self.build_orphan_wiki()
        first = api.nightly(self.paths, backend="test")
        (created,) = first.created
        _move_to_applied(self.proposals, Path(created.path))
        self.assertEqual(self.proposal_dirs(), [])
        before = self.wiki_snapshot()
        second = api.nightly(self.paths, backend="test")
        self.assertEqual(self.wiki_snapshot(), before)
        self.assertEqual([entry.name for entry in second.created], [created.name])
        self.assertEqual(second.already_proposed, ())
        self.assertEqual(self.proposal_dirs(), [created.name])
        self.assertEqual(second.exit_code, 0)

    def test_a_deleted_proposal_is_drafted_again(self) -> None:
        self.build_orphan_wiki()
        first = api.nightly(self.paths, backend="test")
        (created,) = first.created
        shutil.rmtree(Path(created.path))
        self.assertEqual(self.proposal_dirs(), [])
        before = self.wiki_snapshot()
        second = api.nightly(self.paths, backend="test")
        self.assertEqual(self.wiki_snapshot(), before)
        self.assertEqual([entry.name for entry in second.created], [created.name])
        self.assertEqual(second.already_proposed, ())
        self.assertEqual(second.exit_code, 0)

    def test_a_proposal_another_run_creates_during_the_draft_is_already_proposed(self) -> None:
        self.build_orphans(2)
        paths = self.paths

        def publish(prompt: dict, draft: dict) -> None:
            """The other run's proposal, written through ``api.propose`` under the same name (FR-026)."""
            shown = prompt["wiki_state"]["candidate_pages"]
            edits = [
                PageEdit(
                    path=entry["path"],
                    action=cast("PageAction", entry["action"]),
                    new_content=entry["new_content"],
                    rationale=entry["rationale"],
                    base_sha256=(
                        hashlib.sha256(shown[entry["path"]].encode("utf-8")).hexdigest()
                        if entry["action"] == "update"
                        else None
                    ),
                )
                for entry in draft["edits"]
            ]
            api.propose(edits, paths, name=proposal_name(prompt["finding"]["kind"], prompt["finding"]["pages"]))

        class AnotherRunWinsTheRace:
            def __init__(self) -> None:
                self.calls = 0

            def call(self, prompt: dict) -> dict:
                self.calls += 1
                draft = TestBackend().call(prompt)
                if self.calls == 1:
                    publish(prompt, draft)
                return draft

        backend = AnotherRunWinsTheRace()
        before = self.wiki_snapshot()
        result = api.nightly(self.paths, backend=backend)
        self.assertEqual(self.wiki_snapshot(), before)
        self.assertEqual(backend.calls, 2, "the second finding is still drafted")
        first_name = proposal_name("weak-orphan", ("decisions/hidden-1.md",))
        second_name = proposal_name("weak-orphan", ("decisions/hidden-2.md",))
        self.assertEqual(self.proposal_dirs(), sorted([first_name, second_name]))
        self.assertEqual([entry.name for entry in result.already_proposed], [first_name])
        self.assertEqual([entry.name for entry in result.created], [second_name])
        self.assertEqual(result.failed, ())
        self.assertEqual(result.exit_code, 0)

    def test_a_proposals_path_that_is_a_regular_file_is_a_write_failure(self) -> None:
        self.build_orphans(2)
        shutil.rmtree(self.proposals)
        self.proposals.write_text("a regular file\n", encoding="utf-8")
        backend = CountingBackend()
        before = self.wiki_snapshot()
        result = api.nightly(self.paths, backend=backend)
        self.assertEqual(self.wiki_snapshot(), before)
        self.assertEqual(len(backend.calls), 1, "the next finding gets no backend call")
        self.assertEqual(result.already_proposed, ())
        self.assertEqual(result.created, ())
        self.assertEqual(result.failed[0].reason, "write failed")
        self.assertEqual(result.exit_code, 6)
        self.assertEqual(result.drafting.state, "stopped")
        self.assertEqual([entry.reason for entry in result.not_drafted], ["drafting stopped: write failed"])
        self.assertTrue(self.proposals.is_file())
        self.assertIn("Drafting: stopped (write failed)", result.render_markdown())


class TestRefusedDrafts(DraftingCase):
    """FR-023(c): the four named over-reaching drafts, each refused whole with exit 4 through ``cli.main``."""

    def test_a_reworded_sentence_is_refused(self) -> None:
        self.assert_refused_through_cli("cross_link", _reword)

    def test_a_see_also_line_is_refused(self) -> None:
        self.assert_refused_through_cli("cross_link", _see_also)

    def test_a_changed_frontmatter_line_is_refused(self) -> None:
        self.assert_refused_through_cli("cross_link", _changed_frontmatter)

    def test_a_second_index_link_is_refused(self) -> None:
        self.assert_refused_through_cli("orphan", _second_index_link)

    # -- the bounds cases ----------------------------------------

    def test_a_create_is_refused(self) -> None:
        def mutate(prompt: dict, draft: dict) -> dict:
            draft["edits"].append(
                {
                    "path": "decisions/new.md",
                    "action": "create",
                    "new_content": "---\npage_type: decision\n---\n",
                    "rationale": "create",
                }
            )
            return draft

        self.assert_out_of_bounds(mutate, contains="create is not allowed")

    def test_an_update_of_the_canonical_page_is_refused(self) -> None:
        def mutate(prompt: dict, draft: dict) -> dict:
            shown = prompt["wiki_state"]["candidate_pages"]["decisions/queue-policy.md"]
            draft["edits"].append(
                {"path": "decisions/queue-policy.md", "action": "update", "new_content": shown, "rationale": "r"}
            )
            return draft

        self.assert_out_of_bounds(mutate, contains="decisions/queue-policy.md: not an editable page")

    def test_an_update_of_a_page_not_shown_is_refused(self) -> None:
        def mutate(prompt: dict, draft: dict) -> dict:
            shown = api.read_page("decisions/alpha.md", self.paths).text
            draft["edits"].append(
                {"path": "decisions/alpha.md", "action": "update", "new_content": shown, "rationale": "r"}
            )
            return draft

        self.assert_out_of_bounds(mutate, contains="decisions/alpha.md: not an editable page")

    def test_an_update_that_adds_no_link_is_refused(self) -> None:
        def mutate(prompt: dict, draft: dict) -> dict:
            edit = _first_update(draft)
            edit["new_content"] = prompt["wiki_state"]["candidate_pages"][edit["path"]]
            return draft

        self.assert_out_of_bounds(mutate, contains="adds no link")

    def test_an_update_whose_new_link_targets_another_page_is_refused(self) -> None:
        self.assert_out_of_bounds(
            _canonical_link_sub(lambda match: f"[{match.group(1)}](alpha.md)"), contains="adds no link"
        )

    def test_an_update_with_an_empty_link_text_is_refused(self) -> None:
        self.assert_out_of_bounds(
            _canonical_link_sub(lambda match: f"[]({match.group(2)})"), contains="empty link text"
        )

    def test_a_link_inside_a_fenced_block_is_refused(self) -> None:
        self.assert_out_of_bounds(
            _canonical_link_sub(lambda match: f"\n```\n{match.group(0)}\n```\n"), contains="link inside code"
        )

    def test_a_link_inside_an_inline_span_is_refused(self) -> None:
        self.assert_out_of_bounds(_canonical_link_sub(lambda match: f"`{match.group(0)}`"), contains="link inside code")

    def test_a_link_carrying_a_fragment_is_accepted(self) -> None:
        self.build_cross_link_wiki()
        result = api.nightly(
            self.paths,
            backend=_StubBackend(_canonical_link_sub(lambda match: f"[{match.group(1)}]({match.group(2)}#policy)")),
        )
        self.assertEqual(len(result.created), 1, [entry.message for entry in result.failed])
        self.assertEqual(result.exit_code, 0)

    def test_a_log_line_holding_a_link_is_refused(self) -> None:
        def mutate(prompt: dict, draft: dict) -> dict:
            edit = _append_log(draft)
            edit["new_content"] = edit["new_content"] + " [x](y.md)"
            return draft

        self.assert_out_of_bounds(mutate, contains="log line not in the fixed form")

    def test_two_append_log_edits_are_refused(self) -> None:
        def mutate(prompt: dict, draft: dict) -> dict:
            draft["edits"].append(dict(_append_log(draft)))
            return draft

        self.assert_out_of_bounds(mutate, contains="more than one append-log")

    def test_a_missing_append_log_is_refused(self) -> None:
        def mutate(prompt: dict, draft: dict) -> dict:
            draft["edits"] = [edit for edit in draft["edits"] if edit["action"] != "append-log"]
            return draft

        self.assert_out_of_bounds(mutate, contains="log.md: lacks a required edit")

    def test_an_update_in_a_weak_orphan_draft_is_refused(self) -> None:
        def mutate(prompt: dict, draft: dict) -> dict:
            shown = prompt["wiki_state"]["candidate_pages"]["decisions/hidden.md"]
            draft["edits"].append(
                {"path": "decisions/hidden.md", "action": "update", "new_content": shown, "rationale": "r"}
            )
            return draft

        self.assert_out_of_bounds(mutate, build="orphan", contains="action 'update' is not allowed")

    # -- the index line and the log line forms -------------------

    def test_the_fixed_index_line_is_accepted(self) -> None:
        self.build_orphan_wiki()
        result = api.nightly(self.paths, backend="test")
        self.assertEqual(len(result.created), 1, [entry.message for entry in result.failed])
        plan = json.loads((Path(result.created[0].path) / "plan.json").read_text(encoding="utf-8"))
        index_edit = next(entry for entry in plan["edits"] if entry["action"] == "append-index")
        preview = (Path(result.created[0].path) / index_edit["preview"]).read_text(encoding="utf-8")
        self.assertEqual(preview, "- [Hidden Decision](decisions/hidden.md)")

    def test_an_index_line_with_extra_prose_is_refused(self) -> None:
        def mutate(prompt: dict, draft: dict) -> dict:
            edit = _append_index(draft)
            edit["new_content"] = "- [Hidden Decision](decisions/hidden.md) and more"
            return draft

        self.assert_out_of_bounds(mutate, build="orphan", contains="index line not in the fixed form")

    def test_an_index_line_with_a_different_title_is_refused(self) -> None:
        def mutate(prompt: dict, draft: dict) -> dict:
            edit = _append_index(draft)
            edit["new_content"] = "- [Another Title](decisions/hidden.md)"
            return draft

        self.assert_out_of_bounds(mutate, build="orphan", contains="index line not in the fixed form")

    def test_a_log_line_with_a_wrong_date_is_refused(self) -> None:
        def mutate(prompt: dict, draft: dict) -> dict:
            edit = _append_log(draft)
            edit["new_content"] = edit["new_content"].replace(prompt["finding"]["date"], "1999-01-01")
            return draft

        self.assert_out_of_bounds(mutate, contains="log line not in the fixed form")

    def test_a_log_line_naming_another_slug_is_refused(self) -> None:
        def mutate(prompt: dict, draft: dict) -> dict:
            edit = _append_log(draft)
            edit["new_content"] = re.sub(r"— link \S+ \(", "— link nobody (", edit["new_content"])
            return draft

        self.assert_out_of_bounds(mutate, contains="log line not in the fixed form")

    def test_a_log_line_that_is_more_than_one_line_is_refused(self) -> None:
        def mutate(prompt: dict, draft: dict) -> dict:
            edit = _append_log(draft)
            edit["new_content"] = edit["new_content"] + "\nsecond line"
            return draft

        self.assert_out_of_bounds(mutate, contains="append line is not one line")


class TestSevenUnlinkedPages(DraftingCase):
    def test_the_test_backend_updates_all_seven_with_their_own_base_hashes(self) -> None:
        self.build_seven_unlinked_wiki()
        backend = CountingBackend()
        before = self.wiki_snapshot()
        result = api.nightly(self.paths, backend=backend)
        self.assertEqual(self.wiki_snapshot(), before)
        self.assertEqual(len(result.created), 1, [entry.message for entry in result.failed])
        created = result.created[0]
        plan = json.loads((Path(created.path) / "plan.json").read_text(encoding="utf-8"))
        updates = [entry for entry in plan["edits"] if entry["action"] == "update"]
        self.assertEqual(len(updates), 7)
        for entry in updates:
            self.assertEqual(entry["base_sha256"], api.read_page(entry["path"], self.paths).sha256)
        shown = backend.calls[0]["wiki_state"]["candidate_pages"]
        expected = {"decisions/budget-policy.md"} | {f"decisions/unlinked-{i}.md" for i in range(1, 8)}
        self.assertEqual(set(shown), expected)
        api.promote(Path(created.path), self.paths)
        self.assertNotIn("missing-cross-link", {finding.kind for finding in api.findings(self.paths).findings})

    def test_one_reworded_update_among_seven_refuses_the_whole_draft(self) -> None:
        def mutate(prompt: dict, draft: dict) -> dict:
            edit = [entry for entry in draft["edits"] if entry["action"] == "update"][-1]
            edit["new_content"] = edit["new_content"].replace("applies here", "applies everywhere")
            return draft

        reason = self.assert_out_of_bounds(mutate, build="seven_unlinked", contains="out of bounds")
        self.assertIn("decisions/unlinked-7.md", reason)

    def test_one_of_the_seven_left_out_is_refused(self) -> None:
        def mutate(prompt: dict, draft: dict) -> dict:
            edits = draft["edits"]
            index = next(
                position
                for position, entry in enumerate(edits)
                if entry["action"] == "update" and entry["path"] == "decisions/unlinked-4.md"
            )
            del edits[index]
            return draft

        self.assert_out_of_bounds(mutate, build="seven_unlinked", contains="lacks a required edit")


class TestCodeOnlyMention(DraftingCase):
    def test_a_page_mentioning_the_entity_only_in_code_refuses_every_draft(self) -> None:
        self.build_code_only_wiki()
        first = api.nightly(self.paths, backend="test")
        self.assertEqual(self.proposal_dirs(), [])
        self.assertEqual(first.exit_code, 4)
        self.assertIn("adds no link", first.failed[0].reason)
        self.assertEqual(first.drafting.attempts, 1)
        second = api.nightly(self.paths, backend="test")
        self.assertEqual(self.proposal_dirs(), [])
        self.assertEqual(second.failed[0].reason, first.failed[0].reason)
        self.assertEqual(second.drafting.attempts, 1)


class TestAliases(DraftingCase):
    def test_a_linked_avoid_term_is_accepted_and_a_reworded_one_is_refused(self) -> None:
        self.build_alias_wiki()

        def link_as_it_stands(prompt: dict, draft: dict) -> dict:
            for edit in draft["edits"]:
                if edit["action"] == "update":
                    original = prompt["wiki_state"]["candidate_pages"][edit["path"]]
                    edit["new_content"] = original.replace("backlog", "[backlog](../glossary/queue.md)")
            return draft

        accepted = api.nightly(self.paths, backend=_StubBackend(link_as_it_stands))
        self.assertEqual(len(accepted.created), 1, [entry.message for entry in accepted.failed])
        self.assertEqual(accepted.exit_code, 0)

    def test_replacing_the_avoid_term_with_the_preferred_term_is_refused(self) -> None:
        self.build_alias_wiki()

        def reword(prompt: dict, draft: dict) -> dict:
            for edit in draft["edits"]:
                if edit["action"] == "update":
                    original = prompt["wiki_state"]["candidate_pages"][edit["path"]]
                    edit["new_content"] = original.replace("backlog", "[queue](../glossary/queue.md)")
            return draft

        result = api.nightly(self.paths, backend=_StubBackend(reword))
        self.assertEqual(result.exit_code, 4)
        self.assertIn("out of bounds", result.failed[0].reason)


class TestTheBounds(DraftingCase):
    def test_an_always_refused_first_finding_does_not_block_the_second(self) -> None:
        self.build_orphans(3)

        def failing(prompt: dict) -> bool:
            return prompt["finding"]["orphan"] == "decisions/hidden-1.md"

        class FirstFails:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def call(self, prompt: dict) -> dict:
                self.calls.append(prompt["finding"]["orphan"])
                draft = TestBackend().call(prompt)
                return _always_refused(prompt, draft) if failing(prompt) else draft

        stub = FirstFails()
        result = api.nightly(self.paths, backend=stub, max_proposals=1)
        self.assertEqual(len(stub.calls), 2)
        self.assertEqual(len(result.created), 1)
        self.assertEqual(result.created[0].pages, ("decisions/hidden-2.md",))
        self.assertEqual(result.failed[0].pages, ("decisions/hidden-1.md",))
        self.assertIn("out of bounds", result.failed[0].reason)
        reasons = {entry.pages: entry.reason for entry in result.not_drafted}
        self.assertEqual(reasons[("decisions/hidden-3.md",)], "cap: proposals")
        self.assertIn(
            ("weak-orphan", ("decisions/hidden-3.md",)),
            {(finding.kind, finding.pages) for finding in result.needs_curator},
        )

    def test_six_always_refused_findings_stop_at_two_n_attempts(self) -> None:
        self.build_orphans(6)

        class AlwaysRefused:
            def __init__(self) -> None:
                self.calls = 0

            def call(self, prompt: dict) -> dict:
                self.calls += 1
                return _always_refused(prompt, TestBackend().call(prompt))

        stub = AlwaysRefused()
        result = api.nightly(self.paths, backend=stub, max_proposals=2)
        self.assertEqual(stub.calls, 4)
        self.assertEqual(result.drafting.attempts, 4)
        self.assertEqual(result.drafting.created, 0)
        self.assertEqual(len(result.failed), 4)
        self.assertEqual(
            sorted(entry.pages for entry in result.not_drafted),
            [("decisions/hidden-5.md",), ("decisions/hidden-6.md",)],
        )
        self.assertTrue(all(entry.reason == "cap: attempts" for entry in result.not_drafted))
        self.assertIn("out of bounds", result.failed[0].reason)

    def test_max_proposals_zero_makes_no_call(self) -> None:
        self.build_orphans(2)
        backend = CountingBackend()
        result = api.nightly(self.paths, backend=backend, max_proposals=0)
        self.assertEqual(backend.calls, [])
        self.assertEqual(result.drafting.state, "off")
        self.assertEqual(result.drafting.reason, "--max-proposals 0")
        self.assertEqual(result.not_drafted[0].reason, "drafting off: --max-proposals 0")
        self.assertEqual(result.exit_code, 0)

    def test_a_second_run_repeats_the_first_with_no_state(self) -> None:
        self.build_orphans(3)

        def run_once() -> tuple[list[str], NightlyResult]:
            stub = _AlwaysRefusesFirst()
            result = api.nightly(self.paths, backend=stub, max_proposals=1)
            for created in result.created:
                _move_to_applied(self.proposals, Path(created.path))
            return stub.calls, result

        first_calls, first = run_once()
        second_calls, second = run_once()
        self.assertEqual(first_calls, second_calls)
        self.assertEqual(
            [(entry.kind, entry.pages) for entry in first.created],
            [(entry.kind, entry.pages) for entry in second.created],
        )
        self.assertEqual(
            [(entry.pages, entry.reason) for entry in first.not_drafted],
            [(entry.pages, entry.reason) for entry in second.not_drafted],
        )
        self.assertEqual(len(first.failed), len(second.failed))

    def test_two_findings_editing_one_page_overlap(self) -> None:
        self.write_index(
            "decisions/alpha-policy.md",
            "decisions/beta-policy.md",
            "decisions/linker-a.md",
            "decisions/linker-b.md",
            "decisions/shared-1.md",
            "decisions/shared-2.md",
            "decisions/shared-3.md",
        )
        self.write_page("decisions/alpha-policy.md", _decision("alpha-policy", "Alpha Policy", "The rules here."))
        self.write_page("decisions/beta-policy.md", _decision("beta-policy", "Beta Policy", "The rules here."))
        self.write_page(
            "decisions/linker-a.md",
            _decision("linker-a", "Linker A", "See [alpha policy](alpha-policy.md)."),
        )
        self.write_page(
            "decisions/linker-b.md",
            _decision("linker-b", "Linker B", "See [beta policy](beta-policy.md)."),
        )
        for i in range(1, 4):
            self.write_page(
                f"decisions/shared-{i}.md",
                _decision(f"shared-{i}", f"Shared {i}", "The alpha policy and the beta policy both apply here."),
            )
        result = api.nightly(self.paths, backend="test")
        self.assertEqual(len(result.created), 1, [entry.message for entry in result.failed])
        self.assertEqual(result.created[0].pages[0], "decisions/alpha-policy.md")
        self.assertIn("overlaps an earlier draft", {entry.reason for entry in result.not_drafted})


def _move_to_applied(proposals: Path, created: Path) -> None:
    """Archive one created proposal out of the pass's way (how ``promote`` archives it)."""
    applied = proposals / ".applied"
    applied.mkdir(parents=True, exist_ok=True)
    target = applied / created.name
    suffix = 2
    while target.exists():
        target = applied / f"{created.name}-{suffix}"
        suffix += 1
    created.rename(target)


class TestExplicitBackendOnly(DraftingCase):
    def test_the_env_var_and_auto_detect_are_never_consulted(self) -> None:
        self.build_orphan_wiki()
        before = self.wiki_snapshot()
        with (
            patch.dict(os.environ, {"WIKI_STUDIO_BACKEND": "test"}),
            patch("wiki_studio.backends.auto_detect", side_effect=AssertionError("auto-detect must not run")),
            patch("wiki_studio.backends.resolve_backend", side_effect=AssertionError("resolution must not run")),
            patch("wiki_studio.api.resolve_backend", side_effect=AssertionError("resolution must not run")),
        ):
            result = api.nightly(self.paths)
        self.assertEqual(self.wiki_snapshot(), before)
        self.assertEqual(result.drafting.state, "off")
        self.assertEqual(result.drafting.reason, "no --backend")
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(self.proposal_dirs(), [])

    def test_a_bogus_backend_exits_two_before_lint_and_writes_no_report(self) -> None:
        target = self.root / "reports" / "report.md"
        with patch("wiki_studio.api.lint", side_effect=AssertionError("lint must not run")) as lint_mock:
            result = self.run_cli("nightly", "--backend", "bogus", "--report", str(target))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(target.exists())
        lint_mock.assert_not_called()

    def test_a_negative_max_proposals_exits_one(self) -> None:
        result = self.run_cli("nightly", "--max-proposals", "-1")
        self.assertEqual(result.returncode, 1, result.stderr)

    def test_a_proposals_directory_inside_the_wiki_is_refused_before_any_call(self) -> None:
        self.build_orphan_wiki()
        inside = self.wiki / "proposals"
        before = self.wiki_snapshot()
        with patch.object(TestBackend, "call", side_effect=AssertionError("no backend call")):
            result = self.run_cli("nightly", "--backend", "test", "--proposals-dir", str(inside))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.wiki_snapshot(), before)
        self.assertFalse(inside.exists())

    def test_a_symlinked_proposals_directory_into_the_wiki_is_refused(self) -> None:
        self.build_orphan_wiki()
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "proposals").symlink_to(self.wiki, target_is_directory=True)
        with patch.object(TestBackend, "call", side_effect=AssertionError("no backend call")):
            result = self.run_cli("nightly", "--backend", "test", "--proposals-dir", str(outside / "proposals"))
        self.assertEqual(result.returncode, 1, result.stderr)


class TestSchemaContract(DraftingCase):
    def _drifted_wiki(self, *, governed: bool) -> None:
        self.build_orphan_wiki()
        schema_copy = self.wiki / "schema"
        schema_copy.mkdir()
        for source in packaged_schema_dir().glob("*.md"):
            (schema_copy / source.name).write_bytes(source.read_bytes())
        api.init(self.paths, update_schema=True)
        manifest = self.wiki / ".wiki-studio.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["policy"]["approval_required"] = governed
        manifest.write_text(json.dumps(data), encoding="utf-8")
        with (schema_copy / "ingest-rules.md").open("a", encoding="utf-8") as handle:
            handle.write("\nOne more rule.\n")

    def test_governed_drift_skips_drafting_with_exit_four(self) -> None:
        self._drifted_wiki(governed=True)
        backend = CountingBackend()
        before = self.wiki_snapshot()
        result = api.nightly(self.paths, backend=backend)
        self.assertEqual(self.wiki_snapshot(), before)
        self.assertEqual(backend.calls, [])
        self.assertEqual(result.drafting.state, "skipped")
        self.assertEqual(result.exit_code, 4)
        self.assertEqual(result.not_drafted[0].reason, "drafting skipped: schema contract")
        self.assertIn("Drafting: skipped (schema drift", result.render_markdown())
        self.assertEqual(self.proposal_dirs(), [])

    def test_managed_drift_is_a_warning_and_drafting_continues(self) -> None:
        self._drifted_wiki(governed=False)
        result = api.nightly(self.paths, backend="test")
        self.assertTrue(any("schema drift" in warning for warning in result.warnings), result.warnings)
        self.assertEqual(len(result.created), 1, [entry.message for entry in result.failed])
        self.assertEqual(result.exit_code, 0)


class TestPrecedence(DraftingCase):
    def test_a_lock_timeout_after_a_failed_draft_exits_ten(self) -> None:
        self.build_orphans(2)
        with patch("wiki_studio.api.propose", side_effect=PromoteApplyError("lock", reason="lock_timeout")):
            result = api.nightly(self.paths, backend=_FailsFirst())
        self.assertEqual(result.exit_code, 10)
        self.assertEqual(result.drafting.state, "stopped")

    def test_a_write_failure_after_a_failed_draft_exits_six(self) -> None:
        self.build_orphans(2)
        with patch("wiki_studio.api.propose", side_effect=OutputWriteError("disk full")):
            result = api.nightly(self.paths, backend=_FailsFirst())
        self.assertEqual(result.exit_code, 6)
        self.assertEqual(result.drafting.state, "stopped")

    def test_a_backend_failure_then_an_invalid_response_exits_three(self) -> None:
        self.build_orphans(2)
        result = api.nightly(self.paths, backend=_Mixed(("backend", "invalid")))
        self.assertEqual(result.exit_code, 3)

    def test_an_invalid_response_then_a_backend_failure_exits_four(self) -> None:
        self.build_orphans(2)
        result = api.nightly(self.paths, backend=_Mixed(("invalid", "backend")))
        self.assertEqual(result.exit_code, 4)

    def test_a_lock_timeout_with_an_unwritable_report_exits_six(self) -> None:
        self.build_orphan_wiki()
        blocker = self.root / "blocker"
        blocker.write_text("a regular file\n", encoding="utf-8")
        with patch("wiki_studio.api.propose", side_effect=PromoteApplyError("lock", reason="lock_timeout")):
            result = self.run_cli("nightly", "--backend", "test", "--report", str(blocker / "report.md"))
        self.assertEqual(result.returncode, 6, result.stderr)
        self.assertIn("could not write the report", result.stderr)


class _FailsFirst:
    """A stub backend that fails the first finding and drafts the second."""

    def __init__(self) -> None:
        self.calls = 0

    def call(self, prompt: dict) -> dict:
        self.calls += 1
        if self.calls == 1:
            raise BackendInvocationError("boom")
        return TestBackend().call(prompt)


class _Mixed:
    """A stub backend whose two replies are, in order, a backend failure and an invalid reply (or the reverse)."""

    def __init__(self, order: tuple[str, str]) -> None:
        self._order = order
        self.calls = 0

    def call(self, prompt: dict[str, Any]) -> Any:
        self.calls += 1
        if self._order[self.calls - 1] == "backend":
            raise BackendInvocationError("boom")
        return "not json"


class _AlwaysRefusesFirst:
    """A stub backend that refuses the first finding it is shown and drafts the rest."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def call(self, prompt: dict[str, Any]) -> Any:
        self.calls.append(str(prompt["finding"]["orphan"]))
        draft = TestBackend().call(prompt)
        return _always_refused(prompt, draft) if len(self.calls) == 1 else draft


class TestStopping(DraftingCase):
    def test_a_write_failure_stops_drafting_and_the_next_finding_gets_no_call(self) -> None:
        self.build_orphans(2)
        backend = CountingBackend()
        with patch("wiki_studio.api.propose", side_effect=OutputWriteError("disk full")):
            result = api.nightly(self.paths, backend=backend)
        self.assertEqual(len(backend.calls), 1)
        self.assertEqual(result.drafting.state, "stopped")
        self.assertEqual(result.drafting.reason, "write failed")
        self.assertEqual(result.not_drafted[0].reason, "drafting stopped: write failed")
        self.assertEqual(result.exit_code, 6)
        self.assertIn("Drafting: stopped (write failed)", result.render_markdown())

    def test_a_lock_timeout_stops_drafting_and_the_next_finding_gets_no_call(self) -> None:
        self.build_orphans(2)
        backend = CountingBackend()
        with patch("wiki_studio.api.propose", side_effect=PromoteApplyError("lock", reason="lock_timeout")):
            result = api.nightly(self.paths, backend=backend)
        self.assertEqual(len(backend.calls), 1)
        self.assertEqual(result.drafting.state, "stopped")
        self.assertEqual(result.drafting.reason, "lock timeout")
        self.assertEqual(result.not_drafted[0].reason, "drafting stopped: lock timeout")
        self.assertEqual(result.exit_code, 10)


class TestDraftFailures(DraftingCase):
    def test_a_backend_failure_on_one_finding_does_not_stop_the_next(self) -> None:
        self.build_wiki()

        class WeakOrphanFails:
            def __init__(self) -> None:
                self.calls = 0

            def call(self, prompt: dict) -> dict:
                self.calls += 1
                if prompt["finding"]["kind"] == "weak-orphan":
                    raise BackendInvocationError("boom")
                return TestBackend().call(prompt)

        backend = WeakOrphanFails()
        result = api.nightly(self.paths, backend=backend)
        self.assertEqual(backend.calls, 2)
        self.assertEqual(len(result.created), 1)
        self.assertEqual(result.created[0].kind, "missing-cross-link")
        self.assertEqual(result.failed[0].reason, "backend error")
        self.assertEqual(result.exit_code, 3)

    def test_an_unexpected_backend_exception_is_a_backend_error(self) -> None:
        self.build_orphan_wiki()

        class Raises:
            def call(self, prompt: dict) -> dict:
                raise RuntimeError("unexpected")

        result = api.nightly(self.paths, backend=Raises())
        self.assertEqual(result.failed[0].reason, "backend error")
        self.assertEqual(result.exit_code, 3)

    def test_an_invalid_reply_is_a_failed_draft_with_exit_four(self) -> None:
        self.build_orphan_wiki()

        class Invalid:
            def call(self, prompt: dict[str, Any]) -> Any:
                return "not json"

        result = api.nightly(self.paths, backend=Invalid())
        self.assertEqual(result.failed[0].reason, "invalid response")
        self.assertEqual(result.exit_code, 4)


class TestTheProposalReportAndJson(DraftingCase):
    def test_the_report_lists_the_drafting_state_and_the_four_subsections(self) -> None:
        self.build_wiki()
        result = api.nightly(self.paths, backend="test")
        report = result.render_markdown()
        self.assertEqual(
            [line for line in report.splitlines() if line.startswith("#")],
            [
                "# wiki-studio nightly report",
                "## Lint",
                "## Findings",
                "## Proposals",
                "### Created",
                "### Already proposed",
                "### Not drafted",
                "### Failed",
                "## Needs a curator",
                "### Findings",
                "### Pending proposals",
            ],
        )
        self.assertIn("Drafting: on (backend test; 2 of 5 proposals, 2 of 10 attempts)", report)
        self.assertIn("### Already proposed\n\nnone", report)
        self.assertIn("### Failed\n\nnone", report)
        self.assertIn("- Drafting: on (backend test; 2 of 5 proposals, 2 of 10 attempts)", report)
        for created in result.created:
            self.assertIn(created.name, report)
            self.assertIn("fact warnings: 0", report)

    def test_a_lint_failure_report_says_drafting_was_skipped(self) -> None:
        self.build_orphan_wiki()
        self.write_page("decisions/orphan.md", _decision("orphan", "Orphan", "Nobody links here."))
        result = api.nightly(self.paths, backend="test")
        self.assertIn("Drafting: skipped (structural lint failed)", result.render_markdown())

    def test_the_json_carries_the_drafting_and_proposal_keys(self) -> None:
        self.build_wiki()
        result = api.nightly(self.paths, backend="test")
        data = result.as_dict()
        self.assertEqual(
            set(data["drafting"]),
            {"state", "reason", "backend", "max_proposals", "max_attempts", "attempts", "created"},
        )
        self.assertEqual(data["drafting"]["state"], "on")
        self.assertEqual(data["drafting"]["max_proposals"], 5)
        self.assertEqual(data["drafting"]["max_attempts"], 10)
        self.assertEqual(data["drafting"]["attempts"], 2)
        self.assertEqual(data["drafting"]["created"], 2)
        self.assertEqual(set(data["proposals"]), {"created", "already_proposed", "not_drafted", "failed"})
        self.assertEqual(data["proposals"]["already_proposed"], [])
        self.assertEqual(len(data["proposals"]["created"]), 2)
        for entry in data["proposals"]["created"]:
            self.assertEqual(set(entry), {"name", "path", "kind", "pages", "edits", "fact_warnings"})
            for edit in entry["edits"]:
                self.assertEqual(set(edit), {"action", "path"})

    def test_the_failed_entry_carries_reason_code_and_message(self) -> None:
        self.build_cross_link_wiki()
        result = api.nightly(self.paths, backend=_StubBackend(_reword))
        entry = result.as_dict()["proposals"]["failed"][0]
        self.assertEqual(set(entry), {"name", "kind", "pages", "reason", "exit_code", "message"})
        self.assertIn("out of bounds", entry["reason"])
        self.assertEqual(entry["exit_code"], 4)
        self.assertTrue(entry["message"])


class TestLinkHelpers(unittest.TestCase):
    def test_links_match_and_an_image_is_not_a_link(self) -> None:
        matches = list(INLINE_LINK_RE.finditer("a [x](a.md) and ![alt](b.md) and [y](c.md#frag)"))
        self.assertEqual([match.group(1) for match in matches], ["x", "y"])
        self.assertEqual([match.group(2) for match in matches], ["a.md", "c.md#frag"])

    def test_targets_resolve_relative_to_the_page(self) -> None:
        self.assertEqual(resolve_link_target("decisions/a.md", "b.md"), "decisions/b.md")
        self.assertEqual(resolve_link_target("decisions/a.md", "../index.md"), "index.md")
        self.assertEqual(resolve_link_target("index.md", "decisions/a.md"), "decisions/a.md")
        self.assertEqual(resolve_link_target("decisions/a.md", "b.md#x"), "decisions/b.md")
        self.assertIsNone(resolve_link_target("decisions/a.md", "https://example.com/x"))
        self.assertIsNone(resolve_link_target("decisions/a.md", "mailto:x@example.com"))
        self.assertIsNone(resolve_link_target("decisions/a.md", "/abs.md"))
        self.assertIsNone(resolve_link_target("decisions/a.md", "#frag"))
        self.assertIsNone(resolve_link_target("decisions/a.md", ""))

    def test_stripping_replaces_only_links_to_the_target(self) -> None:
        text = "The [queue policy](queue-policy.md) and [other](other.md) and [again](../decisions/queue-policy.md#x)."
        self.assertEqual(
            strip_links_to(text, "decisions/beta.md", "decisions/queue-policy.md"),
            "The queue policy and [other](other.md) and again.",
        )

    def test_counting_counts_only_links_to_the_target(self) -> None:
        text = "[a](queue-policy.md) [b](queue-policy.md#x) [c](other.md) ![d](queue-policy.md)"
        self.assertEqual(count_links_to(text, "decisions/beta.md", "decisions/queue-policy.md"), 2)

    def test_the_proposal_name_is_deterministic_and_keyed_on_sorted_pages(self) -> None:
        name = proposal_name("weak-orphan", ("b.md", "a.md"))
        expected = "nightly-weak-orphan-" + hashlib.sha256(b"weak-orphan\na.md\nb.md").hexdigest()[:12]
        self.assertEqual(name, expected)
        self.assertEqual(proposal_name("weak-orphan", ("a.md", "b.md")), name)


class TestCodeRegionHelper(unittest.TestCase):
    @staticmethod
    def _inside(text: str, needle: str) -> bool:
        offset = text.index(needle)
        return any(start <= offset < end for start, end in code_regions(text))

    def test_a_backtick_fence_is_a_region(self) -> None:
        text = "before\n```\nquoted\n```\nafter"
        self.assertTrue(self._inside(text, "quoted"))
        self.assertFalse(self._inside(text, "before"))
        self.assertFalse(self._inside(text, "after"))

    def test_a_tilde_fence_is_a_region(self) -> None:
        self.assertTrue(self._inside("before\n~~~python\nquoted\n~~~\nafter", "quoted"))

    def test_an_unclosed_fence_runs_to_the_end(self) -> None:
        text = "before\n```\nquoted and `more`"
        regions = code_regions(text)
        self.assertTrue(self._inside(text, "more"))
        self.assertEqual(regions[-1][1], len(text))

    def test_inline_spans_of_one_and_two_backticks(self) -> None:
        text = "a `one` b ``two`` c"
        self.assertTrue(self._inside(text, "one"))
        self.assertTrue(self._inside(text, "two"))
        self.assertFalse(self._inside(text, " b "))

    def test_an_unclosed_backtick_run_makes_the_rest_of_the_line_code(self) -> None:
        self.assertTrue(self._inside("before `unclosed and after", "after"))
        self.assertFalse(self._inside("before `unclosed and after", "before"))


class TestLinkOnlyProblems(unittest.TestCase):
    """Direct unit tests of FR-019's bounds for the shapes a fixture does not reach."""

    @staticmethod
    def _edits(*items: tuple[str, str, str]) -> list[Any]:
        return [nightly._DraftEdit(path, action, content, "why") for path, action, content in items]

    def test_a_create_and_an_unknown_action_are_out_of_bounds(self) -> None:
        problems = nightly.link_only_problems(
            "missing-cross-link",
            self._edits(("a.md", "create", "x"), ("b.md", "rewrite", "y")),
            canonical="c.md",
            orphan=None,
            editable=("a.md",),
            originals={"a.md": ""},
            run_date="2026-11-17",
        )
        self.assertIn("a.md: create is not allowed", problems)
        self.assertIn("b.md: action 'rewrite' is not allowed", problems)

    def test_a_duplicate_update_and_a_stray_append_index_are_out_of_bounds(self) -> None:
        update = ("a.md", "update", "text [x](c.md)")
        problems = nightly.link_only_problems(
            "missing-cross-link",
            self._edits(update, update, ("index.md", "append-index", "- [x](c.md)")),
            canonical="c.md",
            orphan=None,
            editable=("a.md",),
            originals={"a.md": "text x"},
            run_date="2026-11-17",
        )
        self.assertIn("a.md: more than one update for this page", problems)
        self.assertIn("index.md: action 'append-index' is not allowed", problems)

    def test_a_missing_index_line_is_out_of_bounds(self) -> None:
        problems = nightly.link_only_problems(
            "weak-orphan",
            self._edits(),
            canonical=None,
            orphan="decisions/hidden.md",
            editable=(),
            originals={"decisions/hidden.md": ""},
            run_date="2026-11-17",
        )
        self.assertIn("index.md: lacks a required edit", problems)
        self.assertIn("log.md: lacks a required edit", problems)


class TestDraftableFindings(DraftingCase):
    def test_other_kinds_are_report_only(self) -> None:
        self.assertIsNone(nightly._draftable(Finding("stale-claim", "warning", ("a.md",), "gone"), self.paths))

    def test_a_cross_link_without_the_canonical_page_phrase_is_report_only(self) -> None:
        finding = Finding("missing-cross-link", "warning", ("decisions/c.md", "decisions/a.md"), "entity 'c'")
        self.assertIsNone(nightly._draftable(finding, self.paths))
        short = Finding("missing-cross-link", "warning", ("decisions/c.md",), "canonical page decisions/c.md")
        self.assertIsNone(nightly._draftable(short, self.paths))

    def test_a_weak_orphan_linked_from_the_index_is_report_only(self) -> None:
        self.write_index("decisions/hidden.md")
        finding = Finding("weak-orphan", "warning", ("decisions/hidden.md",), "one inbound link")
        self.assertIsNone(nightly._draftable(finding, self.paths))
        empty = Finding("weak-orphan", "warning", (), "one inbound link")
        self.assertIsNone(nightly._draftable(empty, self.paths))


class TestCuratePrompt(unittest.TestCase):
    def test_it_carries_the_shown_pages_the_editable_paths_and_the_curate_task(self) -> None:
        finding = Finding(
            "missing-cross-link",
            "warning",
            ("decisions/c.md", "decisions/a.md", "decisions/b.md"),
            "entity 'c' (canonical page decisions/c.md) is mentioned in 3 other pages",
        )
        shown = {"decisions/c.md": "canonical", "decisions/a.md": "a", "decisions/b.md": "b"}
        prompt = compose_curate_prompt(
            finding=finding,
            shown=shown,
            editable=("decisions/a.md", "decisions/b.md"),
            index_md="",
            run_date="2026-11-17",
            schema_files={"ingest-rules": "rules"},
        )
        self.assertEqual(prompt["task"], CURATE_TASK)
        self.assertEqual(prompt["wiki_state"]["candidate_pages"], shown)
        self.assertEqual(prompt["wiki_state"]["log_md"], "")
        self.assertEqual(prompt["finding"]["editable"], ["decisions/a.md", "decisions/b.md"])
        self.assertEqual(prompt["finding"]["canonical"], "decisions/c.md")
        self.assertIsNone(prompt["finding"]["orphan"])
        self.assertEqual(prompt["source"]["kind"], "finding")
        self.assertIn("2026-11-17", prompt["source"]["content"])
        self.assertIn("decisions/a.md", prompt["source"]["content"])
        self.assertEqual(prompt["schema_excerpts"]["ingest_rules"], "rules")

    def test_a_weak_orphan_prompt_names_the_orphan_and_shows_the_index(self) -> None:
        finding = Finding(
            "weak-orphan", "warning", ("decisions/hidden.md",), "page reachable via a single inbound link"
        )
        prompt = compose_curate_prompt(
            finding=finding,
            shown={"decisions/hidden.md": "orphan", "index.md": "index"},
            editable=(),
            index_md="index",
            run_date="2026-11-17",
            schema_files={},
        )
        self.assertIsNone(prompt["finding"]["canonical"])
        self.assertEqual(prompt["finding"]["orphan"], "decisions/hidden.md")
        self.assertEqual(prompt["wiki_state"]["index_md"], "index")
        self.assertIn("- [<title>](decisions/hidden.md)", prompt["system_instructions"])

    def test_the_renderer_branch_is_confined_to_curate(self) -> None:
        from wiki_studio.backends.copilot_cli import _render_plain_text_prompt

        ingest_prompt = {
            "version": 1,
            "system_instructions": "x",
            "task": "ingest-multi",
            "schema_excerpts": {},
            "source": {"kind": "file", "path": "p", "content": "c"},
            "wiki_state": {"index_md": "# i", "log_md": "", "candidate_pages": {"a.md": "text"}},
            "response_schema": "{}",
        }
        rendered = _render_plain_text_prompt(ingest_prompt)
        self.assertIn("Integrate the new source with what is already here", rendered)
        self.assertIn(
            "--- candidate pages (relevance-ranked subset of the wiki, "
            "selected by lexical overlap with the source) ---",
            rendered,
        )
        self.assertNotIn("Only the listed pages may be edited", rendered)

        finding = Finding("weak-orphan", "warning", ("decisions/hidden.md",), "orphan")
        curate_prompt = compose_curate_prompt(
            finding=finding,
            shown={"decisions/hidden.md": "orphan", "index.md": "index"},
            editable=(),
            index_md="index",
            run_date="2026-11-17",
            schema_files={},
        )
        curate_rendered = _render_plain_text_prompt(curate_prompt)
        self.assertIn("Only the listed pages may be edited", curate_rendered)
        self.assertIn("--- pages named by the finding", curate_rendered)
        self.assertNotIn("Integrate the new source with what is already here", curate_rendered)


if __name__ == "__main__":
    unittest.main()
