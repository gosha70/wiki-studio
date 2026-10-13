# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""WikiPaths: defaults, the flag > environment > default precedence, and the helpers (FR-004)."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from wikistudio.paths import (
    DEFAULT_PROPOSALS_DIR,
    DEFAULT_QUERY_LOG,
    DEFAULT_WIKI_DIR,
    ENV_PROPOSALS_DIR,
    ENV_ROOT,
    ENV_WIKI_DIR,
    WikiPaths,
    default_root,
    git_toplevel,
)


class TestDefaults(unittest.TestCase):
    def test_for_root_reproduces_the_original_layout(self) -> None:
        paths = WikiPaths.for_root(Path("/proj"))
        self.assertEqual(paths.root, Path("/proj"))
        self.assertEqual(paths.wiki_dir, Path("/proj") / DEFAULT_WIKI_DIR)
        self.assertEqual(paths.wiki_dir, Path("/proj/knowledge/wiki"))
        self.assertEqual(paths.proposals_dir, Path("/proj") / DEFAULT_PROPOSALS_DIR)
        self.assertEqual(paths.proposals_dir, Path("/proj/doc_internal/proposals"))
        self.assertEqual(paths.query_log, Path("/proj") / DEFAULT_QUERY_LOG)
        self.assertEqual(paths.query_log, Path("/proj/doc_internal/wiki-query-log.jsonl"))
        self.assertEqual(paths.audit_log, Path("/proj/knowledge/wiki/.audit/ingest-log.md"))
        self.assertEqual(paths.schema_dir, Path("/proj/knowledge/wiki/schema"))
        self.assertEqual(paths.applied_dir, Path("/proj/doc_internal/proposals/.applied"))

    def test_derived_locations_follow_an_overridden_wiki_dir(self) -> None:
        paths = WikiPaths.for_root(Path("/proj"), wiki_dir=Path("/elsewhere/kb"))
        self.assertEqual(paths.audit_log, Path("/elsewhere/kb/.audit/ingest-log.md"))
        self.assertEqual(paths.schema_dir, Path("/elsewhere/kb/schema"))
        # The query log stays under the root: it is project state, not wiki content.
        self.assertEqual(paths.query_log, Path("/proj") / DEFAULT_QUERY_LOG)

    def test_default_root_is_the_git_toplevel_of_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "sub" / "dir").mkdir(parents=True)
            subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
            self.assertEqual(git_toplevel(repo / "sub" / "dir"), repo.resolve())
            self.assertEqual(default_root(repo / "sub" / "dir"), repo.resolve())
            paths = WikiPaths.resolve(env={}, cwd=repo / "sub" / "dir")
            self.assertEqual(paths.root, repo.resolve())
            self.assertEqual(paths.wiki_dir, repo.resolve() / DEFAULT_WIKI_DIR)

    def test_default_root_falls_back_to_cwd_outside_git(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plain = Path(tmp) / "plain"
            plain.mkdir()
            self.assertIsNone(git_toplevel(plain))
            self.assertEqual(default_root(plain), plain.resolve())
            self.assertEqual(WikiPaths.resolve(env={}, cwd=plain).root, plain.resolve())


class TestPrecedence(unittest.TestCase):
    def setUp(self) -> None:
        self.cwd = Path("/cwd")

    def test_flags_beat_environment(self) -> None:
        env = {ENV_ROOT: "/env-root", ENV_WIKI_DIR: "/env-wiki", ENV_PROPOSALS_DIR: "/env-proposals"}
        paths = WikiPaths.resolve(
            root="/flag-root", wiki_dir="/flag-wiki", proposals_dir="/flag-proposals", env=env, cwd=self.cwd
        )
        self.assertEqual(paths.root, Path("/flag-root"))
        self.assertEqual(paths.wiki_dir, Path("/flag-wiki"))
        self.assertEqual(paths.proposals_dir, Path("/flag-proposals"))

    def test_environment_beats_defaults(self) -> None:
        env = {ENV_ROOT: "/env-root", ENV_WIKI_DIR: "/env-wiki", ENV_PROPOSALS_DIR: "/env-proposals"}
        paths = WikiPaths.resolve(env=env, cwd=self.cwd)
        self.assertEqual(paths.root, Path("/env-root"))
        self.assertEqual(paths.wiki_dir, Path("/env-wiki"))
        self.assertEqual(paths.proposals_dir, Path("/env-proposals"))
        self.assertEqual(paths.query_log, Path("/env-root") / DEFAULT_QUERY_LOG)
        self.assertEqual(paths.audit_log, Path("/env-wiki/.audit/ingest-log.md"))

    def test_each_location_resolves_independently(self) -> None:
        # Only the wiki is overridden: root and proposals keep their defaults.
        paths = WikiPaths.resolve(root="/r", env={ENV_WIKI_DIR: "/w"}, cwd=self.cwd)
        self.assertEqual(paths.root, Path("/r"))
        self.assertEqual(paths.wiki_dir, Path("/w"))
        self.assertEqual(paths.proposals_dir, Path("/r") / DEFAULT_PROPOSALS_DIR)

    def test_relative_explicit_values_are_taken_from_cwd(self) -> None:
        paths = WikiPaths.resolve(root="proj", wiki_dir="kb", env={ENV_PROPOSALS_DIR: "out"}, cwd=self.cwd)
        self.assertEqual(paths.root, Path("/cwd/proj"))
        self.assertEqual(paths.wiki_dir, Path("/cwd/kb"))
        self.assertEqual(paths.proposals_dir, Path("/cwd/out"))

    def test_empty_environment_values_are_ignored(self) -> None:
        paths = WikiPaths.resolve(root="/r", env={ENV_WIKI_DIR: "", ENV_PROPOSALS_DIR: ""}, cwd=self.cwd)
        self.assertEqual(paths.wiki_dir, Path("/r") / DEFAULT_WIKI_DIR)
        self.assertEqual(paths.proposals_dir, Path("/r") / DEFAULT_PROPOSALS_DIR)


class TestHelpers(unittest.TestCase):
    def test_with_wiki_dir_keeps_root_and_proposals(self) -> None:
        paths = WikiPaths.for_root(Path("/proj"))
        staged = paths.with_wiki_dir(Path("/tmp/stage"))
        self.assertEqual(staged.root, Path("/proj"))
        self.assertEqual(staged.proposals_dir, paths.proposals_dir)
        self.assertEqual(staged.query_log, paths.query_log)
        self.assertEqual(staged.wiki_dir, Path("/tmp/stage"))
        self.assertEqual(staged.audit_log, Path("/tmp/stage/.audit/ingest-log.md"))
        self.assertEqual(staged.schema_dir, Path("/tmp/stage/schema"))

    def test_wiki_label_is_root_relative_when_inside_the_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inside = WikiPaths.for_root(root)
            self.assertEqual(inside.wiki_label, DEFAULT_WIKI_DIR)
            self.assertEqual(inside.relative_to_root(root / "a" / "b.md"), "a/b.md")
            with tempfile.TemporaryDirectory() as other:
                outside = WikiPaths.for_root(root, wiki_dir=Path(other) / "kb")
                self.assertEqual(outside.wiki_label, "kb")

    def test_for_root_makes_relative_inputs_absolute(self) -> None:
        paths = WikiPaths.for_root(Path("rel"), wiki_dir=Path("kb"))
        self.assertTrue(paths.root.is_absolute())
        self.assertTrue(paths.wiki_dir.is_absolute())
        self.assertEqual(paths.root, Path.cwd() / "rel")

    def test_within_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = WikiPaths.for_root(root)
            self.assertTrue(paths.within_root(root / "x" / "y.md"))
            self.assertFalse(paths.within_root(Path("/")))


if __name__ == "__main__":
    unittest.main()
