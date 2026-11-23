# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The hardened read-only git layer of the revision check (0.11.0 US4, FR-017 to FR-024).

Every case builds its own temporary repositories with git and runs
``revisions.check_sources`` against them; the cases are skipped only when git
is not on PATH. A spy on ``subprocess.run`` records each git process the layer
starts (its arguments and environment) and calls the real one, so the tests
can assert which calls ran, in which directory, and with what environment.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest import mock

from wiki_studio import revisions
from wiki_studio.paths import DEFAULT_GIT_CALL_LIMIT, ENV_GIT_CALL_LIMIT, ENV_SOURCE_ROOTS, WikiPaths
from wiki_studio.revisions import (
    CAUSE_COMMIT_NOT_FOUND,
    CAUSE_MALFORMED,
    CAUSE_NOT_AT_COMMIT,
    COMMIT_PEEL,
    ENV_CEILING_DIRECTORIES,
    GIT_CALL_TIMEOUT_SECONDS,
    KEPT_GIT_ENV,
    OUTCOME_CHANGED,
    OUTCOME_NOT_AT_REVISION,
    OUTCOME_NOT_CHECKED,
    OUTCOME_UNCHANGED,
    P1_ARGS,
    P2_ARGS,
    P4_HEAD,
    REASON_AMBIGUOUS,
    REASON_CALL_LIMIT,
    REASON_GIT_NOT_FOUND,
    REASON_NO_SHA,
    REASON_NO_USABLE_REPOSITORY,
    REASON_NOT_A_WORK_TREE,
    REASON_NOT_FOUND_SKIPPED,
    REASON_NOT_TOP,
    REASON_OWNERSHIP,
    REASON_PARTIAL,
    REASON_PATH_OUTSIDE,
    REASON_SHALLOW,
    REASON_TIMED_OUT,
    REASON_TOO_SHORT,
    ROLE_ROOT,
    ROLE_SOURCE_ROOT,
    STATE_OFF,
    STATE_ON,
    STATUS_SKIPPED,
    STATUS_USED,
    GitCallLimitError,
    GitRefusedError,
    GitRunner,
    RevisionCheck,
    SourceCheck,
    check_sources,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

GIT = shutil.which("git")
POSIX = os.name == "posix"
REPO_ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_JSON = REPO_ROOT / "eval" / "revisions" / "results" / "candidates.json"
_REAL_RUN = subprocess.run

# FR-022's formula over the study's recorded counts: the shipped plan is p1-p4 plus the winner's steps.
WINNER = "C2"
HEADROOM = 10
LIMIT_MULTIPLE = 100
TIMEOUT_FLOOR_SECONDS = 10

# The four ambiguity fixtures of FR-024 (the pitch review's note 2). The contents were found offline once by
# hashing 40,000 root commits and 40,000 blobs of the forms below and keeping 7-character prefix collisions;
# every test rebuilds the objects from these bytes with ``git hash-object -t <type> -w --stdin``.
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
COMMIT_TEMPLATE = (
    f"tree {EMPTY_TREE}\nauthor t <t@example.com> 0 +0000\ncommitter t <t@example.com> 0 +0000\n\n{{message}}\n"
)
# Two commits sharing a 7-character prefix.
TWIN_PREFIX = "037877a"
TWIN_A_MESSAGE = "m3784"
TWIN_A = "037877a8ca24c9a74fded45ba3d3c46636256f35"
TWIN_B_MESSAGE = "m13316"
TWIN_B = "037877a08c7e1b976c5bbcfcbd1bfb0461add39b"
# One commit and one blob sharing a 7-character prefix.
MIXED_PREFIX = "569ad4d"
MIXED_COMMIT_MESSAGE = "m16931"
MIXED_COMMIT = "569ad4da8017b598937f4d3ed17780b8d9356f54"
MIXED_BLOB_BYTES = b"b29391\n"
MIXED_BLOB = "569ad4da0ce24e02111967bafcdcc4d6571ebdc6"
TOO_SHORT_SHA = TWIN_PREFIX[:6]

ABSENT_COMMIT = "0123456789abcdef0123456789abcdef01234567"
UPPERCASE_SHA = "ABCDEF0123"
OWNERSHIP_STDERR = (
    "fatal: detected dubious ownership in repository at '{path}'\nTo add an exception for this directory, call:\n"
)
INJECTED_GIT_VARIABLES = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
)
SET_BY_THE_LAYER = frozenset({ENV_CEILING_DIRECTORIES, "GIT_TERMINAL_PROMPT"})


def object_id(kind: str, body: bytes) -> str:
    """Git's SHA-1 object id of ``body`` as an object of ``kind``."""
    return hashlib.sha1(f"{kind} {len(body)}\0".encode() + body, usedforsecurity=False).hexdigest()


def commit_body(message: str) -> bytes:
    return COMMIT_TEMPLATE.format(message=message).encode()


def git(cwd: Path, *argv: str, data: bytes | None = None) -> str:
    """A setup git call for the fixtures, with the layer's clean environment so no outer ``GIT_`` leaks in."""
    result = _REAL_RUN(
        [
            GIT or "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.com",
            "-c",
            "commit.gpgsign=false",
            "-c",
            f"core.hooksPath={os.devnull}",
            *argv,
        ],
        cwd=cwd,
        env=revisions.git_environment(None),
        input=data,
        capture_output=True,
        check=True,
    )
    return result.stdout.decode().strip()


def make_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q")
    return path


def commit_file(repo: Path, rel: str, text: str) -> str:
    """Write ``rel`` under ``repo``, commit it and return the new HEAD's full commit."""
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    git(repo, "add", "--", rel)
    git(repo, "commit", "-q", "-m", f"write {rel}")
    return git(repo, "rev-parse", "HEAD")


def write_object(repo: Path, kind: str, body: bytes) -> str:
    return git(repo, "hash-object", "-t", kind, "-w", "--stdin", data=body)


def write_page(wiki: Path, name: str, sources: Sequence[tuple[str, str | None]]) -> str:
    """A decision page citing ``sources`` (path, sha or None); returns its wiki-relative path."""
    lines = ["---", "page_type: decision", f"slug: {name}", f"title: {name}", "status: stable"]
    lines += ["last_reviewed: 2026-11-23", "sources:"]
    for path, sha in sources:
        lines.append(f"  - path: {path}")
        if sha is not None:
            lines.append(f"    sha: {sha}")
    lines += ["---", "", f"# {name}", ""]
    target = wiki / "decisions" / f"{name}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
    return f"decisions/{name}.md"


class Spy:
    """A stand-in for ``subprocess.run`` that records each call and then makes it (or returns ``fake``'s answer)."""

    def __init__(self, fake: Any = None) -> None:
        self.calls: list[tuple[list[str], dict[str, str]]] = []
        self.fake = fake

    def __call__(self, argv: Sequence[str], **kwargs: Any) -> Any:
        call = (list(argv), dict(kwargs.get("env") or {}))
        self.calls.append(call)
        if self.fake is not None:
            answer = self.fake(call[0], kwargs)
            if answer is not None:
                return answer
        return _REAL_RUN(argv, **kwargs)

    @staticmethod
    def directory(argv: Sequence[str]) -> str:
        return argv[list(argv).index("-C") + 1]

    @staticmethod
    def args(argv: Sequence[str]) -> list[str]:
        return list(argv)[list(argv).index("-C") + 2 :]

    def in_directory(self, directory: Path) -> list[list[str]]:
        return [self.args(argv) for argv, _ in self.calls if self.directory(argv) == str(directory)]

    def all_args(self) -> list[str]:
        return [arg for argv, _ in self.calls for arg in argv]


@unittest.skipUnless(GIT, "git is not installed")
class RevisionCase(unittest.TestCase):
    """A temporary base with a root repository and its wiki."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name).resolve()
        self.root = make_repo(self.base / "root")
        self.root_head = commit_file(self.root, "README.md", "root\n")
        self.wiki = self.root / "wiki"

    def paths(self, *source_roots: Path, root: Path | None = None, limit: int | None = None) -> WikiPaths:
        top = self.root if root is None else root
        return WikiPaths.for_root(top, wiki_dir=self.wiki, source_roots=list(source_roots), git_call_limit=limit)

    def run_check(self, paths: WikiPaths, pages: Sequence[str], *, fake: Any = None) -> tuple[RevisionCheck, Spy]:
        spy = Spy(fake)
        with mock.patch.object(revisions.subprocess, "run", spy):
            result = check_sources(paths, pages)
        return result, spy

    def only(self, result: RevisionCheck) -> SourceCheck:
        self.assertEqual(len(result.sources), 1, result.sources)
        return result.sources[0]


class TestClassification(RevisionCase):
    """FR-019: each repository classified once, by p1 and p2, with its reason."""

    def test_a_full_clone_is_used_with_its_head(self) -> None:
        source = make_repo(self.base / "src")
        head = commit_file(source, "a.txt", "one\n")
        result, spy = self.run_check(self.paths(source), [])
        self.assertEqual(result.state, STATE_ON)
        self.assertEqual([r.role for r in result.repositories], [ROLE_ROOT, ROLE_SOURCE_ROOT])
        self.assertEqual([r.status for r in result.repositories], [STATUS_USED, STATUS_USED])
        self.assertEqual([r.head for r in result.repositories], [self.root_head, head])
        self.assertEqual(spy.in_directory(source), [list(P1_ARGS), list(P2_ARGS)])

    def test_a_plain_directory_is_not_a_git_work_tree(self) -> None:
        plain = self.base / "plain"
        plain.mkdir()
        result, _ = self.run_check(self.paths(plain), [])
        repo = result.repositories[1]
        self.assertEqual((repo.status, repo.reason, repo.head), (STATUS_SKIPPED, REASON_NOT_A_WORK_TREE, None))

    def test_a_shallow_clone_is_skipped(self) -> None:
        upstream = make_repo(self.base / "upstream")
        commit_file(upstream, "a.txt", "one\n")
        commit_file(upstream, "a.txt", "two\n")
        shallow = self.base / "shallow"
        git(self.base, "clone", "-q", "--depth", "1", upstream.as_uri(), str(shallow))
        result, _ = self.run_check(self.paths(shallow), [])
        self.assertEqual(result.repositories[1].reason, REASON_SHALLOW)

    def test_a_partial_clone_with_a_reachable_promisor_is_skipped_and_never_asked_for_objects(self) -> None:
        upstream = make_repo(self.base / "upstream")
        commit_file(upstream, "a.txt", "one\n")
        partial = self.base / "partial"
        git(self.base, "clone", "-q", "--no-hardlinks", str(upstream), str(partial))
        git(partial, "config", "core.repositoryformatversion", "1")
        git(partial, "config", "extensions.partialclone", "origin")
        git(partial, "config", "remote.origin.promisor", "true")
        only_upstream = commit_file(upstream, "b.txt", "later\n")
        page = write_page(self.wiki, "p", [("b.txt", only_upstream)])
        result, spy = self.run_check(self.paths(partial), [page])
        self.assertEqual(result.repositories[1].reason, REASON_PARTIAL)
        self.assertEqual(spy.in_directory(partial), [list(P1_ARGS), list(P2_ARGS)])
        self.assertEqual(
            (self.only(result).outcome, self.only(result).reason), (OUTCOME_NOT_CHECKED, REASON_NOT_FOUND_SKIPPED)
        )

    def test_a_subdirectory_source_root_is_not_the_top_and_its_commits_are_never_matched(self) -> None:
        upstream = make_repo(self.base / "upstream")
        head = commit_file(upstream, "sub/a.txt", "one\n")
        page = write_page(self.wiki, "p", [("a.txt", head)])
        result, _ = self.run_check(self.paths(upstream / "sub"), [page])
        repo = result.repositories[1]
        self.assertEqual((repo.status, repo.reason), (STATUS_SKIPPED, REASON_NOT_TOP))
        self.assertEqual(
            (self.only(result).outcome, self.only(result).reason), (OUTCOME_NOT_CHECKED, REASON_NOT_FOUND_SKIPPED)
        )
        self.assertIsNone(self.only(result).repository)

    def test_a_root_below_its_repository_top_is_used_and_paths_are_relative_to_it(self) -> None:
        project = self.root / "proj"
        first = commit_file(self.root, "proj/old.txt", "old\n")
        commit_file(self.root, "proj/new.txt", "added after the sha\n")
        self.wiki = project / "wiki"
        page = write_page(self.wiki, "p", [("new.txt", first), ("old.txt", first)])
        result, spy = self.run_check(self.paths(root=project), [page])
        self.assertEqual(result.repositories[0].status, STATUS_USED)
        outcomes = [(s.path, s.outcome, s.reason) for s in result.sources]
        self.assertEqual(
            outcomes, [("new.txt", OUTCOME_NOT_AT_REVISION, CAUSE_NOT_AT_COMMIT), ("old.txt", OUTCOME_UNCHANGED, None)]
        )
        p4 = [args for args in spy.in_directory(project) if args[: len(P4_HEAD)] == list(P4_HEAD)]
        self.assertEqual(len(p4), 1)
        self.assertIn("--relative", p4[0])


class TestOrderAndMatching(RevisionCase):
    """FR-019's order and FR-021's matching: the first usable repository that has the commit is named."""

    def test_root_first_then_flag_order_and_the_flag_replaces_the_variable(self) -> None:
        a, b, c, d = (make_repo(self.base / name) for name in "abcd")
        for repo in (a, b, c, d):
            commit_file(repo, "x.txt", repo.name)
        flagged = WikiPaths.resolve(
            root=str(self.root),
            wiki_dir=str(self.wiki),
            source_roots=[str(b), str(a)],
            env={ENV_SOURCE_ROOTS: os.pathsep.join([str(c), str(d)])},
        )
        from_env = WikiPaths.resolve(
            root=str(self.root), wiki_dir=str(self.wiki), env={ENV_SOURCE_ROOTS: os.pathsep.join([str(d), str(c)])}
        )
        flagged_result, _ = self.run_check(flagged, [])
        env_result, _ = self.run_check(from_env, [])
        self.assertEqual([r.path for r in flagged_result.repositories], [self.root, b, a])
        self.assertEqual([r.path for r in env_result.repositories], [self.root, d, c])

    def test_a_commit_only_in_a_source_root_is_matched_there(self) -> None:
        source = make_repo(self.base / "src")
        first = commit_file(source, "a.txt", "one\n")
        commit_file(source, "a.txt", "two\n")
        page = write_page(self.wiki, "p", [("a.txt", first[:12])])
        result, _ = self.run_check(self.paths(source), [page])
        check = self.only(result)
        self.assertEqual((check.outcome, check.commit), (OUTCOME_CHANGED, first))
        self.assertEqual(check.repository.path if check.repository else None, source)

    def test_a_commit_in_the_root_and_a_source_root_is_named_in_the_root(self) -> None:
        clone = self.base / "clone"
        git(self.base, "clone", "-q", "--no-hardlinks", str(self.root), str(clone))
        page = write_page(self.wiki, "p", [("README.md", self.root_head)])
        result, spy = self.run_check(self.paths(clone), [page])
        check = self.only(result)
        self.assertEqual(check.repository.role if check.repository else None, ROLE_ROOT)
        self.assertEqual(check.outcome, OUTCOME_UNCHANGED)
        self.assertNotIn(["rev-parse", "--verify", f"{self.root_head}{COMMIT_PEEL}"], spy.in_directory(clone))

    def test_a_commit_in_two_source_roots_is_named_in_the_first_in_order(self) -> None:
        upstream = make_repo(self.base / "upstream")
        head = commit_file(upstream, "a.txt", "one\n")
        first, second = self.base / "first", self.base / "second"
        for clone in (first, second):
            git(self.base, "clone", "-q", "--no-hardlinks", str(upstream), str(clone))
        page = write_page(self.wiki, "p", [("a.txt", head)])
        for order in ((first, second), (second, first)):
            result, _ = self.run_check(self.paths(*order), [page])
            named = self.only(result).repository
            self.assertEqual(named.path if named else None, order[0])

    def test_a_commit_in_no_repository_with_all_usable_is_not_at_revision(self) -> None:
        source = make_repo(self.base / "src")
        commit_file(source, "a.txt", "one\n")
        page = write_page(self.wiki, "p", [("a.txt", ABSENT_COMMIT)])
        result, _ = self.run_check(self.paths(source), [page])
        check = self.only(result)
        self.assertEqual(
            (check.outcome, check.reason, check.repository), (OUTCOME_NOT_AT_REVISION, CAUSE_COMMIT_NOT_FOUND, None)
        )

    def test_a_commit_in_no_repository_with_one_skipped_is_not_checked(self) -> None:
        plain = self.base / "plain"
        plain.mkdir()
        page = write_page(self.wiki, "p", [("a.txt", ABSENT_COMMIT)])
        result, _ = self.run_check(self.paths(plain), [page])
        self.assertEqual(
            (self.only(result).outcome, self.only(result).reason), (OUTCOME_NOT_CHECKED, REASON_NOT_FOUND_SKIPPED)
        )

    def test_any_other_p3_failure_skips_that_repository_and_the_search_moves_on(self) -> None:
        a, b = make_repo(self.base / "a"), make_repo(self.base / "b")
        commit_file(a, "x.txt", "a\n")
        target = commit_file(b, "x.txt", "b\n")
        page = write_page(self.wiki, "p", [("x.txt", target)])

        def broken_p3_in_a(argv: list[str], _kwargs: dict[str, Any]) -> Any:
            if Spy.directory(argv) == str(a) and Spy.args(argv)[:2] == ["rev-parse", "--verify"]:
                return subprocess.CompletedProcess(argv, 1, "", "fatal: something else went wrong\n")
            return None

        result, _ = self.run_check(self.paths(a, b), [page], fake=broken_p3_in_a)
        self.assertEqual(result.repositories[1].status, STATUS_SKIPPED)
        self.assertEqual(result.repositories[1].reason, "fatal: something else went wrong")
        named = self.only(result).repository
        self.assertEqual(named.path if named else None, b)

    def test_git_missing_turns_the_check_off_after_one_call(self) -> None:
        page = write_page(self.wiki, "p", [("a.txt", ABSENT_COMMIT), ("b.txt", "--output=x")])

        def no_git(_argv: list[str], _kwargs: dict[str, Any]) -> Any:
            raise FileNotFoundError(2, "No such file or directory", "git")

        result, spy = self.run_check(self.paths(self.base / "elsewhere"), [page], fake=no_git)
        self.assertEqual(len(spy.calls), 1)
        self.assertEqual((result.state, result.reason), (STATE_OFF, REASON_GIT_NOT_FOUND))
        self.assertEqual({r.reason for r in result.repositories}, {REASON_GIT_NOT_FOUND})
        self.assertEqual({s.outcome for s in result.sources}, {OUTCOME_NOT_CHECKED})
        self.assertEqual(result.summary(), f"revision check: off ({REASON_GIT_NOT_FOUND})")


class TestValidation(RevisionCase):
    """FR-020: a ``sha:`` or ``path:`` that may not reach git is decided without a git call carrying it."""

    def test_an_option_shaped_and_an_uppercase_sha_are_malformed_with_no_call(self) -> None:
        upper = UPPERCASE_SHA
        page = write_page(self.wiki, "p", [("README.md", "--output=x"), ("README.md", upper)])
        result, spy = self.run_check(self.paths(), [page])
        self.assertEqual(
            [(s.outcome, s.reason) for s in result.sources], [(OUTCOME_NOT_AT_REVISION, CAUSE_MALFORMED)] * 2
        )
        carried = " ".join(spy.all_args())
        self.assertNotIn("--output=x", carried)
        self.assertNotIn(upper, carried)

    def test_paths_escaping_the_root_and_a_source_root_are_not_checked_with_no_call_carrying_them(self) -> None:
        source = make_repo(self.base / "src")
        source_head = commit_file(source, "a.txt", "one\n")
        page = write_page(self.wiki, "p", [("../escape.txt", self.root_head), ("sub/../../x.txt", source_head)])
        result, spy = self.run_check(self.paths(source), [page])
        self.assertEqual(
            [(s.outcome, s.reason) for s in result.sources],
            [
                (OUTCOME_NOT_CHECKED, REASON_PATH_OUTSIDE.format(directory=self.root)),
                (OUTCOME_NOT_CHECKED, REASON_PATH_OUTSIDE.format(directory=source)),
            ],
        )
        carried = spy.all_args()
        self.assertFalse(any("escape.txt" in arg or "x.txt" in arg for arg in carried), carried)

    def test_a_no_sha_source_is_not_checked(self) -> None:
        page = write_page(self.wiki, "p", [("README.md", None)])
        result, _ = self.run_check(self.paths(), [page])
        self.assertEqual(result.not_checked(), {REASON_NO_SHA: 1})


class TestAmbiguity(RevisionCase):
    """FR-021 and the pitch review's note 2: git's commit-typed lookup, four fixtures."""

    def assert_collisions(self) -> None:
        self.assertEqual(object_id("commit", commit_body(TWIN_A_MESSAGE)), TWIN_A)
        self.assertEqual(object_id("commit", commit_body(TWIN_B_MESSAGE)), TWIN_B)
        self.assertEqual(TWIN_A[:7], TWIN_PREFIX)
        self.assertEqual(TWIN_B[:7], TWIN_PREFIX)
        self.assertNotEqual(TWIN_A, TWIN_B)
        self.assertEqual(object_id("commit", commit_body(MIXED_COMMIT_MESSAGE)), MIXED_COMMIT)
        self.assertEqual(object_id("blob", MIXED_BLOB_BYTES), MIXED_BLOB)
        self.assertEqual(MIXED_COMMIT[:7], MIXED_PREFIX)
        self.assertEqual(MIXED_BLOB[:7], MIXED_PREFIX)

    def setUp(self) -> None:
        super().setUp()
        self.assert_collisions()

    def test_a_unique_prefix_is_matched_to_its_full_commit(self) -> None:
        self.assertEqual(write_object(self.root, "commit", commit_body(TWIN_A_MESSAGE)), TWIN_A)
        page = write_page(self.wiki, "p", [("missing.txt", TWIN_PREFIX)])
        result, _ = self.run_check(self.paths(), [page])
        self.assertEqual((self.only(result).outcome, self.only(result).commit), (OUTCOME_UNCHANGED, TWIN_A))

    def test_a_prefix_of_two_commits_stops_the_search_without_a_finding(self) -> None:
        self.assertEqual(write_object(self.root, "commit", commit_body(TWIN_A_MESSAGE)), TWIN_A)
        self.assertEqual(write_object(self.root, "commit", commit_body(TWIN_B_MESSAGE)), TWIN_B)
        second = make_repo(self.base / "second")
        commit_file(second, "a.txt", "one\n")
        self.assertEqual(write_object(second, "commit", commit_body(TWIN_A_MESSAGE)), TWIN_A)
        # git prints both messages for an ambiguous prefix; "is ambiguous" must win.
        probe = GitRunner(1).run(self.root, ["rev-parse", "--verify", f"{TWIN_PREFIX}{COMMIT_PEEL}"], ceiling=None)
        self.assertNotEqual(probe.returncode, 0)
        self.assertIn("is ambiguous", probe.stderr)
        self.assertIn("Needed a single revision", probe.stderr)
        page = write_page(self.wiki, "p", [("missing.txt", TWIN_PREFIX)])
        result, spy = self.run_check(self.paths(second), [page])
        check = self.only(result)
        self.assertEqual(
            (check.outcome, check.reason), (OUTCOME_NOT_CHECKED, REASON_AMBIGUOUS.format(repository=self.root))
        )
        self.assertEqual(spy.in_directory(second), [list(P1_ARGS), list(P2_ARGS)])

    def test_a_prefix_of_one_commit_and_one_blob_resolves_the_commit(self) -> None:
        self.assertEqual(write_object(self.root, "commit", commit_body(MIXED_COMMIT_MESSAGE)), MIXED_COMMIT)
        self.assertEqual(write_object(self.root, "blob", MIXED_BLOB_BYTES), MIXED_BLOB)
        page = write_page(self.wiki, "p", [("missing.txt", MIXED_PREFIX)])
        result, _ = self.run_check(self.paths(), [page])
        self.assertEqual((self.only(result).outcome, self.only(result).commit), (OUTCOME_UNCHANGED, MIXED_COMMIT))

    def test_a_six_character_sha_is_too_short_and_never_reaches_git(self) -> None:
        self.assertEqual(write_object(self.root, "commit", commit_body(TWIN_A_MESSAGE)), TWIN_A)
        page = write_page(self.wiki, "p", [("missing.txt", TOO_SHORT_SHA)])
        result, spy = self.run_check(self.paths(), [page])
        self.assertEqual((self.only(result).outcome, self.only(result).reason), (OUTCOME_NOT_CHECKED, REASON_TOO_SHORT))
        self.assertFalse(any(TOO_SHORT_SHA in arg for arg in spy.all_args()))


class TestHardening(RevisionCase):
    """FR-017 and FR-018: the environment, the marker scripts and the allowlist."""

    def test_injected_git_variables_change_nothing_and_never_reach_git(self) -> None:
        source = make_repo(self.base / "src")
        first = commit_file(source, "a.txt", "one\n")
        commit_file(source, "a.txt", "two\n")
        other = make_repo(self.base / "other")
        commit_file(other, "a.txt", "other\n")
        page = write_page(self.wiki, "p", [("a.txt", first), ("README.md", self.root_head)])
        clean, _ = self.run_check(self.paths(source), [page])
        injected = {name: str(other / ".git") for name in INJECTED_GIT_VARIABLES}
        injected["GIT_WORK_TREE"] = str(other)
        injected["GIT_INDEX_FILE"] = str(other / ".git" / "index")
        injected["GIT_OBJECT_DIRECTORY"] = str(other / ".git" / "objects")
        injected["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = str(other / ".git" / "objects")
        injected["GIT_CONFIG_NOSYSTEM"] = "1"
        with mock.patch.dict(os.environ, injected):
            dirty, spy = self.run_check(self.paths(source), [page])
        self.assertEqual(dirty.as_dict(), clean.as_dict())
        self.assertEqual(dirty.sources, clean.sources)
        allowed = set(KEPT_GIT_ENV) | SET_BY_THE_LAYER
        for _argv, env in spy.calls:
            reaching = {name for name in env if name.startswith("GIT_")}
            self.assertLessEqual(reaching, allowed, reaching)
            self.assertEqual(env.get("GIT_CONFIG_NOSYSTEM"), "1")
            self.assertEqual((env.get("LC_ALL"), env.get("GIT_TERMINAL_PROMPT")), ("C", "0"))

    @unittest.skipUnless(POSIX, "marker scripts are POSIX shell scripts")
    def test_no_configured_program_runs_when_a_changed_source_is_checked(self) -> None:
        source = make_repo(self.base / "src")
        first = commit_file(source, "a.txt", "one\n")
        commit_file(source, "a.txt", "two\n")
        commit_file(source, ".gitattributes", "*.txt diff=marker\n")
        markers = self.base / "markers"
        markers.mkdir()
        scripts: dict[str, Path] = {}
        for name in ("fsmonitor", "external", "command", "textconv"):
            script = self.base / f"{name}.sh"
            script.write_text(f"#!/bin/sh\n: > '{markers / name}'\ncat \"$1\" 2>/dev/null\n", encoding="utf-8")
            script.chmod(0o755)
            scripts[name] = script
        git(source, "config", "diff.external", str(scripts["external"]))
        git(source, "config", "diff.marker.command", str(scripts["command"]))
        git(source, "config", "diff.marker.textconv", str(scripts["textconv"]))
        git(source, "config", "core.fsmonitor", str(scripts["fsmonitor"]))
        head = git(source, "rev-parse", "HEAD")
        # The traps are live: a plain porcelain diff runs a configured program.
        git(source, "diff", first, head, "--", "a.txt")
        self.assertTrue(any(markers.iterdir()), "the marker scripts did not fire on a plain diff")
        for marker in markers.iterdir():
            marker.unlink()
        page = write_page(self.wiki, "p", [("a.txt", first)])
        result, _ = self.run_check(self.paths(source), [page])
        self.assertEqual(self.only(result).outcome, OUTCOME_CHANGED)
        runner = GitRunner(10)
        diff = ["diff", "--no-ext-diff", "--no-textconv"]
        runner.run(source, [*diff, "--quiet", "-w", "--ignore-blank-lines", first, head, "--", "a.txt"], ceiling=None)
        runner.run(source, [*diff, "-U0", first, head, "--", "a.txt"], ceiling=None)
        runner.run(source, ["cat-file", "blob", f"{first}:./a.txt"], ceiling=None)
        self.assertEqual(sorted(markers.iterdir()), [])

    def test_a_request_outside_the_allowlist_raises_before_any_process(self) -> None:
        refused = (
            ["fetch", "origin"],
            ["rev-parse", "--verify", f"--output=x{COMMIT_PEEL}"],
            ["rev-parse", "--verify", "HEAD"],
            ["config", "--get", "core.fsmonitor"],
            ["diff", self.root_head, self.root_head, "--", "README.md"],
            ["diff", "--no-ext-diff", "--no-textconv", "-U0", "HEAD", self.root_head, "--", "README.md"],
            [*P4_HEAD, self.root_head, self.root_head, "--", "../README.md"],
            ["cat-file", "blob", f"{self.root_head[:7]}:./README.md"],
            ["cat-file", "-p", self.root_head],
            ["status"],
        )
        runner = GitRunner(100)
        spy = mock.Mock(side_effect=AssertionError("no process may start"))
        with mock.patch.object(revisions.subprocess, "run", spy):
            for args in refused:
                with self.subTest(args=args), self.assertRaises(GitRefusedError):
                    runner.run(self.root, args, ceiling=None)
        spy.assert_not_called()
        self.assertEqual(runner.calls, 0)


class TestCapTimeoutOwnership(RevisionCase):
    """FR-022's cap, a timeout and the ownership refusal."""

    def test_the_cap_reached_mid_run_leaves_the_rest_not_checked_and_no_call_follows(self) -> None:
        source = make_repo(self.base / "src")
        shas = [commit_file(source, "a.txt", f"{n}\n") for n in range(3)]
        page = write_page(self.wiki, "p", [("a.txt", sha) for sha in shas])
        limit = 5  # p1 and p2 for both repositories, then one p3: the next call is refused
        result, spy = self.run_check(self.paths(source, limit=limit), [page])
        self.assertEqual(len(spy.calls), limit)
        reason = REASON_CALL_LIMIT.format(limit=limit)
        self.assertEqual([(s.outcome, s.reason) for s in result.sources], [(OUTCOME_NOT_CHECKED, reason)] * 3)
        self.assertEqual(result.as_dict()["not_checked"], {reason: 3})
        self.assertEqual(
            result.summary(), "revision check: on (2 of 2 repositories used); 0 sources checked, 3 not checked"
        )

    def test_a_zero_cap_starts_no_process(self) -> None:
        result, spy = self.run_check(self.paths(limit=0), [write_page(self.wiki, "p", [("a.txt", ABSENT_COMMIT)])])
        self.assertEqual(spy.calls, [])
        self.assertEqual((result.state, result.reason), (STATE_OFF, REASON_NO_USABLE_REPOSITORY))
        self.assertEqual(result.repositories[0].reason, REASON_CALL_LIMIT.format(limit=0))

    def test_the_runner_refuses_past_its_limit_before_a_process(self) -> None:
        runner = GitRunner(0)
        with mock.patch.object(revisions.subprocess, "run") as run, self.assertRaises(GitCallLimitError):
            runner.run(self.root, P1_ARGS, ceiling=None)
        run.assert_not_called()

    def test_a_timeout_on_one_repository_skips_only_it(self) -> None:
        slow, fast = make_repo(self.base / "slow"), make_repo(self.base / "fast")
        commit_file(slow, "a.txt", "slow\n")
        target = commit_file(fast, "a.txt", "fast\n")
        page = write_page(self.wiki, "p", [("a.txt", target)])

        def time_out_in_slow(argv: list[str], kwargs: dict[str, Any]) -> Any:
            if Spy.directory(argv) == str(slow):
                raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
            return None

        result, spy = self.run_check(self.paths(slow, fast), [page], fake=time_out_in_slow)
        self.assertEqual([r.reason for r in result.repositories], [None, REASON_TIMED_OUT, None])
        self.assertEqual(len(spy.in_directory(slow)), 1)
        named = self.only(result).repository
        self.assertEqual(named.path if named else None, fast)

    def test_a_repository_git_refuses_for_ownership_is_skipped_with_that_reason(self) -> None:
        source = make_repo(self.base / "src")
        commit_file(source, "a.txt", "one\n")

        def refuse(argv: list[str], _kwargs: dict[str, Any]) -> Any:
            if Spy.directory(argv) == str(source):
                return subprocess.CompletedProcess(argv, 128, "", OWNERSHIP_STDERR.format(path=source))
            return None

        result, _ = self.run_check(self.paths(source), [], fake=refuse)
        repo = result.repositories[1]
        self.assertEqual((repo.status, repo.reason), (STATUS_SKIPPED, REASON_OWNERSHIP))


class TestRunState(RevisionCase):
    """The object and the line ``findings`` will carry (FR-026, FR-027)."""

    def test_as_dict_has_the_keys_and_counts(self) -> None:
        plain = self.base / "plain"
        plain.mkdir()
        page = write_page(self.wiki, "p", [("README.md", self.root_head), ("x.md", None), ("y.md", "abc")])
        result, _ = self.run_check(self.paths(plain), [page])
        data = result.as_dict()
        self.assertEqual(
            set(data), {"state", "reason", "repositories", "sources_checked", "sources_not_checked", "not_checked"}
        )
        self.assertEqual(
            data["repositories"][0],
            {"path": str(self.root), "role": ROLE_ROOT, "status": STATUS_USED, "reason": None, "head": self.root_head},
        )
        self.assertEqual(data["repositories"][1]["reason"], REASON_NOT_A_WORK_TREE)
        self.assertEqual((data["sources_checked"], data["sources_not_checked"]), (1, 2))
        self.assertEqual(data["not_checked"], {REASON_NO_SHA: 1, REASON_TOO_SHORT: 1})
        self.assertEqual(
            result.summary(), "revision check: on (1 of 2 repositories used); 1 sources checked, 2 not checked"
        )
        json.dumps(data)


class TestCallLimitConfiguration(unittest.TestCase):
    """FR-022: ``WIKI_STUDIO_GIT_CALL_LIMIT`` is parsed as the lock timeout is, and the defaults follow the formula."""

    def test_the_variable_sets_the_limit_and_the_argument_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(WikiPaths.resolve(root=root, env={}).git_call_limit, DEFAULT_GIT_CALL_LIMIT)
            self.assertEqual(WikiPaths.resolve(root=root, env={ENV_GIT_CALL_LIMIT: "7"}).git_call_limit, 7)
            self.assertEqual(WikiPaths.resolve(root=root, env={ENV_GIT_CALL_LIMIT: "0"}).git_call_limit, 0)
            self.assertEqual(
                WikiPaths.resolve(root=root, git_call_limit=3, env={ENV_GIT_CALL_LIMIT: "9"}).git_call_limit, 3
            )
            for bad in ("-1", "soon", "1.5", "+4"):
                with self.subTest(value=bad), self.assertRaises(ValueError):
                    WikiPaths.resolve(root=root, env={ENV_GIT_CALL_LIMIT: bad})
            with self.assertRaises(ValueError):
                WikiPaths.resolve(root=root, git_call_limit=-1, env={})

    def test_the_cap_and_the_timeout_equal_the_formula_over_the_recorded_counts(self) -> None:
        counts = json.loads(CANDIDATES_JSON.read_text(encoding="utf-8"))["process_counts"]
        processes = counts["with_candidate"][WINNER]["processes"]
        self.assertEqual(DEFAULT_GIT_CALL_LIMIT, math.ceil(processes * HEADROOM / LIMIT_MULTIPLE) * LIMIT_MULTIPLE)
        slowest = counts["slowest_call"]["seconds"]
        self.assertEqual(GIT_CALL_TIMEOUT_SECONDS, max(TIMEOUT_FLOOR_SECONDS, math.ceil(slowest * HEADROOM)))


if __name__ == "__main__":
    unittest.main()
