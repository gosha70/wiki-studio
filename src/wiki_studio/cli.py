# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# wiki-studio.cli — verb-dispatching CLI entrypoint for the wiki pipeline.
#
# A thin argument parser over wiki_studio.api: each verb resolves one WikiPaths
# (from --root / --wiki-dir / --proposals-dir, the WIKI_STUDIO_* variables, or the
# defaults), calls the matching library function and prints its result.
# Exceptions become exit codes in exactly one place, ``_report``.
#
# Invoked as ``wiki_studio <verb> ...`` (console script) or ``python -m wiki_studio``.
#
# Exit codes (stable across v1; exit code 7 added in Phase 0):
#   0 — successful run; proposal file written (accept or reject), or
#       structural lint clean, etc.
#   2 — backend not found (no resolver match, or named CLI not on PATH).
#   3 — backend invocation failed (non-zero exit, timeout, OS error).
#   4 — contract violation (backend response failed shape or semantic
#       cross-consistency validation).
#   5 — source file missing or unreadable.
#   6 — output directory write failure.
#   7 — source path outside the repo (use --allow-out-of-repo to override).
#   8 — verb not yet implemented (Phase N stub).

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import warnings
from dataclasses import replace
from pathlib import Path

from . import __version__, api
from .audit_flush import describe_flush
from .backends import ENV_BACKEND, ENV_BACKEND_DEPRECATED
from .contract import MANIFEST_PRESENT
from .errors import (
    BackendInvocationError,
    ContractViolationError,
    DriftWarning,
    IngestError,
    PathOutsideRootError,
    PromoteApplyError,
    PromoteValidationError,
)
from .fact_diff import FACT_ERROR_UNREADABLE
from .paths import (
    DEFAULT_LOCK_TIMEOUT,
    DEFAULT_PROPOSALS_DIR,
    DEFAULT_WIKI_DIR,
    ENV_ACTOR,
    ENV_LOCK_TIMEOUT,
    ENV_PROPOSALS_DIR,
    ENV_ROOT,
    ENV_SOURCE_ROOTS,
    ENV_WIKI_DIR,
    MANIFEST_NAME,
    WikiPaths,
)
from .wikilock import lock_path_for

# Exit codes new in Phase 0.
EXIT_PATH_OUT_OF_REPO = PathOutsideRootError.exit_code
EXIT_NOT_IMPLEMENTED = 8

_BACKEND_HELP_SUFFIX = f"Defaults to {ENV_BACKEND} env var ({ENV_BACKEND_DEPRECATED} is deprecated), then auto-detect."

_ALLOW_UNGUARDED_HELP = (
    "Apply update edits that carry no base_sha256 (proposals written before 0.6.0, drafts without a "
    ".base.json manifest). Compatibility mode with incomplete conflict protection: a stale draft can "
    "overwrite a newer page, and the paths are recorded as unguarded_paths in the receipt. Without it "
    "such an update exits 9; the safe remedy is to regenerate the proposal from a fresh `wiki-studio read`."
)
_BY_HELP = (
    "Who is acting, recorded as {record} with source flag. Without it the name comes from "
    f"{ENV_ACTOR} (source env), else none is recorded (source none); the OS user is never used. "
    "Attribution, not authentication: the host supplies authority."
)

# Message prefixes that distinguish the error classes on stderr (the exit
# code itself comes from the exception).
_ERROR_PREFIXES: tuple[tuple[type[IngestError], str], ...] = (
    (BackendInvocationError, "backend invocation failed: "),
    (ContractViolationError, "contract violation: "),
    (PromoteValidationError, "promote validation failed:\n"),
    (PromoteApplyError, "promote apply failed:\n"),
)


def _add_path_options(parser: argparse.ArgumentParser, *, suppress_defaults: bool) -> None:
    """The three global location options, the allowed source roots and the wiki-lock timeout.

    They live on the top-level parser and, with suppressed defaults, on every
    verb parser, so a value given after the verb is not clobbered by a
    missing one before it.
    """
    default = argparse.SUPPRESS if suppress_defaults else None
    parser.add_argument(
        "--source-root",
        type=Path,
        action="append",
        default=default,
        metavar="PATH",
        help="A directory outside the root whose files pages may reference with local links (images, data, "
        "source files); repeatable. A local link target must otherwise resolve inside the root. "
        f"Default: {ENV_SOURCE_ROOTS} ({os.pathsep!r}-separated), else none.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=default,
        help=f"Project root. Default: {ENV_ROOT}, else the git toplevel of the current directory, "
        "else the current directory.",
    )
    parser.add_argument(
        "--wiki-dir",
        type=Path,
        default=default,
        help=f"Wiki directory. Default: {ENV_WIKI_DIR}, else <root>/{DEFAULT_WIKI_DIR}.",
    )
    parser.add_argument(
        "--proposals-dir",
        type=Path,
        default=default,
        help=f"Proposals directory. Default: {ENV_PROPOSALS_DIR}, else <root>/{DEFAULT_PROPOSALS_DIR}.",
    )
    parser.add_argument(
        "--lock-timeout",
        type=float,
        default=default,
        metavar="SECONDS",
        help="Seconds to wait for the wiki lock that serialises wiki-studio writers on this machine "
        "(promote, propose, the ingest-log append, audit-flush); on expiry exit 10 with reason lock_timeout. "
        f"Default: {ENV_LOCK_TIMEOUT}, else {DEFAULT_LOCK_TIMEOUT:g}.",
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the verb-dispatching parser. ``--help`` text is the public CLI surface."""
    parser = argparse.ArgumentParser(
        prog="wiki-studio",
        description=(
            "Karpathy-pattern LLM Wiki maintainer. Verbs: "
            "init|ingest|propose|promote|approve|read|query|find|lint|findings|audit-flush|info. "
            "``wiki-studio <verb> --help`` for per-verb help."
        ),
        epilog=(
            "Exit codes (stable across v1): "
            "0 success; 2 backend not found; 3 backend invocation failed; "
            "4 contract violation; 5 source missing; 6 output write failure; "
            "7 source out of repo, or a page path outside the wiki; 8 verb not yet implemented (Phase N stub); "
            "9 promote validation failed, including a revision precondition (stale or unguarded update, "
            "create of an existing page), and approve refused (nothing written); "
            "10 promote apply failed (with a reason: lock_timeout, "
            "uncertain_outcome, wiki_mismatch, wiki_identity_unavailable, payload_changed); "
            "11 audit-flush error (not a git work tree; append-only invariant "
            "violated; working log malformed; git commit failed)."
        ),
    )
    parser.add_argument("--version", action="version", version=__version__)
    _add_path_options(parser, suppress_defaults=False)
    common = argparse.ArgumentParser(add_help=False)
    _add_path_options(common, suppress_defaults=True)
    sub = parser.add_subparsers(dest="verb", required=True, metavar="<verb>")

    # ── ingest ─────────────────────────────────────────────────
    p_ingest = sub.add_parser(
        "ingest",
        parents=[common],
        help="Run the ingest gate against a source file and write a proposal. "
        "Multi-page by default (a patch-set directory); "
        "--legacy-single-source runs the v1 single-page generator.",
    )
    p_ingest.add_argument(
        "source",
        type=Path,
        help="Path to the source file to ingest.",
    )
    p_ingest.add_argument(
        "--legacy-single-source",
        action="store_true",
        help="Run the v1 single-source proposal generator instead of the default multi-page ingest.",
    )
    p_ingest.add_argument(
        "--backend",
        default=None,
        help=f"Backend name. One of: claude, codex, pi, cursor, test. {_BACKEND_HELP_SUFFIX}",
    )
    p_ingest.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run. With --legacy-single-source: passes task=gate-only "
        "to the backend so it skips drafting the body (the rendered "
        "proposal has no body either way). Multi-page (default): the "
        "backend still drafts the pages and the patch-set is written; "
        "the audit record is marked as a dry run (no proposal hash).",
    )
    p_ingest.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=f"Override the output directory. Default: the proposals directory (<root>/{DEFAULT_PROPOSALS_DIR}/).",
    )
    p_ingest.add_argument(
        "--debug-unsafe-output",
        action="store_true",
        help="Disable stderr redaction in error messages. Default: "
        "redacted (sha256 fingerprint only). Use only for local "
        "debugging — backend stderr can echo source content.",
    )
    p_ingest.add_argument(
        "--allow-out-of-repo",
        action="store_true",
        help="Allow source paths outside the repository tree. Default: "
        "refuse (exit 7). Use only when ingesting external artifacts "
        "deliberately.",
    )
    p_ingest.add_argument(
        "--check",
        action="store_true",
        help="Gate-only pre-flight: run the ingest gate and exit with "
        "code 0 (accept) or non-zero (reject) with ZERO filesystem "
        "side effects — no proposal directory, no audit line, no "
        "snapshot. Mutually exclusive with --dry-run.",
    )

    # ── promote ────────────────────────────────────────────────
    p_promote = sub.add_parser(
        "promote",
        parents=[common],
        help="Apply a proposal patch-set to the wiki directory: validated, serialised against other "
        "wiki-studio writers on this machine by the wiki lock, rolled back on failure; not crash-safe "
        "across files. The ONLY code path that writes to the canonical wiki content tree, excluding .audit/. "
        "A receipt.json beside the proposal records the outcome; promoting the directory again finishes an "
        "interrupted archive step and never re-applies an edit.",
    )
    p_promote.add_argument(
        "proposal_dir",
        type=Path,
        help=f"Path to a <proposals-dir>/<date>-<slug>/ directory (default {DEFAULT_PROPOSALS_DIR}) "
        "produced by `wiki-studio ingest`.",
    )
    p_promote.add_argument(
        "--dry-run",
        action="store_true",
        help="Take the wiki lock, stage the wiki with the edits, check the revision preconditions against "
        "the live wiki, release the lock, then validate the staged copy. Writes no wiki content, no "
        "receipt and no proposal change. The result is point-in-time evidence: a real promote checks "
        "again. Exits 0 on a clean stage.",
    )
    p_promote.add_argument(
        "--allow-out-of-repo",
        action="store_true",
        help="Allow proposal directories outside the repository tree. "
        "Default: refuse (exit 7). The proposal dir's content is "
        "applied to the wiki directory, so accepting paths from "
        "outside the repo is an avoidable security surface.",
    )
    p_promote.add_argument("--allow-unguarded-updates", action="store_true", help=_ALLOW_UNGUARDED_HELP)
    p_promote.add_argument("--by", metavar="NAME", default=None, help=_BY_HELP.format(record="the receipt's actor"))

    # ── approve ────────────────────────────────────────────────
    p_approve = sub.add_parser(
        "approve",
        parents=[common],
        help="Record that each page's live revision is approved under the wiki's policy: one immutable record "
        "per decision under <wiki>/.audit/approvals/, written under the wiki lock. The whole batch is checked "
        "first and refused (exit 9, nothing written) for a draft, a page carrying superseded_by, a structural-lint "
        "violation, a --revision that is not the live one, or a missing approver when the policy requires one. "
        "A page already approved at its live bytes is reported as existing. Needs a manifest (run init first). "
        "Frontmatter never makes a page approved.",
    )
    p_approve.add_argument(
        "pages", nargs="+", metavar="page", help="Wiki-relative page path(s): concepts/<slug>.md, ..."
    )
    p_approve.add_argument(
        "--revision",
        metavar="SHA",
        default=None,
        help="The sha256 of the revision you reviewed (from `wiki-studio read --json`); the approval is refused "
        "when the live page differs. Only with exactly one page (exit 4 otherwise).",
    )
    p_approve.add_argument("--by", metavar="NAME", default=None, help=_BY_HELP.format(record="the record's approver"))

    # ── query ──────────────────────────────────────────────────
    p_query = sub.add_parser(
        "query",
        parents=[common],
        help="Answer a question by reading the wiki, index-first.",
    )
    p_query.add_argument(
        "question",
        help="The question to answer against the wiki.",
    )
    p_query.add_argument(
        "--file-back",
        action="store_true",
        help="In addition to printing the answer, run a multi-page "
        "ingest over a synthetic source built from the question + "
        "answer, producing a patch-set under the proposals directory. "
        "The curator reviews and runs `wiki-studio promote` to land it.",
    )
    p_query.add_argument(
        "--backend",
        default=None,
        help=f"Backend name (claude / codex / pi / cursor / test). {_BACKEND_HELP_SUFFIX}",
    )
    p_query.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Max number of wiki pages to load into the query prompt. Default 5 (DEFAULT_MAX_QUERY_PAGES).",
    )
    p_query.add_argument(
        "--debug-unsafe-output",
        action="store_true",
        help="Disable stderr redaction in error messages (see ingest).",
    )
    p_query.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="When --file-back: override the proposals directory.",
    )

    # ── lint ───────────────────────────────────────────────────
    p_lint = sub.add_parser(
        "lint",
        parents=[common],
        help="Run wiki linters. Default: structural (frontmatter, page "
        "types, slugs, placement, links, reachability). --health adds "
        "the knowledge-health pass (contradictions, stale claims, "
        "weak orphans, missing cross-links). --prose adds the prose "
        "pass (sentence length, semicolons, filler, section length, "
        "glossary term lock).",
    )
    p_lint.add_argument(
        "--health",
        action="store_true",
        help="Run knowledge-health checks on top of the structural "
        "linter. Default mode is advisory (exit 0 with stderr "
        "warnings); --strict flips to non-zero exit on findings.",
    )
    p_lint.add_argument(
        "--prose",
        action="store_true",
        help="Run the prose checks (plain technical English and the "
        "glossary term lock) on top of the structural linter. Default "
        "mode is advisory (exit 0 with stderr warnings); --strict "
        "flips to non-zero exit on findings.",
    )
    p_lint.add_argument(
        "--strict",
        action="store_true",
        help="Make advisory findings fatal (non-zero exit): "
        "audit-format violations (always run) and, with "
        "--health or --prose, any knowledge-health or prose finding.",
    )
    p_lint.add_argument(
        "--paths",
        nargs="*",
        default=None,
        help="With --health or --prose: scope to specific wiki-relative paths.",
    )
    p_lint.add_argument(
        "--backend",
        default=None,
        help="With --health: backend for the LLM-dependent "
        "contradiction check. When omitted, contradictions are "
        "skipped (the other three checks run without a backend).",
    )

    # ── findings ───────────────────────────────────────────────
    p_findings = sub.add_parser(
        "findings",
        parents=[common],
        help="Report what needs a curator's attention without calling a model: counts by kind, then each finding. "
        "Kinds: stale-claim, weak-orphan, missing-cross-link, avoid-format (the health checks without a backend), "
        "unapproved, approval-stale, approval-policy-changed (review state), superseded-still-indexed and "
        "no-page-id. Read-only; takes no lock; exits 0 on a completed run whatever it finds "
        "(lint --health --strict is the CI gate).",
    )
    p_findings.add_argument(
        "--json",
        action="store_true",
        help="Print findings_version, counts, pages_checked and findings as one JSON object.",
    )
    p_findings.add_argument(
        "--paths", nargs="+", default=None, metavar="PAGE", help="Scope every kind to these wiki-relative pages."
    )

    # ── audit-flush ────────────────────────────────────────────
    p_audit_flush = sub.add_parser(
        "audit-flush",
        parents=[common],
        help="Commit any pending (uncommitted) lines in "
        "<wiki-dir>/.audit/ingest-log.md. The ONLY pipeline "
        "command that runs git commit; never auto-invoked.",
    )
    p_audit_flush.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the pending line count and blob SHA without committing. "
        "Exits 0 after the divergence + malformed gates.",
    )

    # ── info ───────────────────────────────────────────────────
    p_info = sub.add_parser(
        "info",
        parents=[common],
        help="Print the resolved layout (root, wiki dir, proposals dir, logs, schema copy) and where each "
        "location came from: flag, WIKI_STUDIO_* variable or default; then the knowledge contract: package "
        "version, schema contract and fingerprints (drift), format versions, capabilities and the root "
        "manifest. Read-only; exits 0 (4 for a malformed or newer manifest).",
    )
    p_info.add_argument("--json", action="store_true", help="Print the same facts as one JSON object.")

    # ── init ───────────────────────────────────────────────────
    p_init = sub.add_parser(
        "init",
        parents=[common],
        help="Create the wiki directory with a minimal index.md and log.md when they are absent "
        "(promote needs both) and the root manifest .wiki-studio.json (wiki_id, schema contract, schema "
        "fingerprint, policy). Never overwrites; a wiki without a manifest gains one and nothing else changes; "
        "running it twice is a no-op. Exits 0.",
    )
    p_init.add_argument("--title", default=api.DEFAULT_WIKI_TITLE, help="Title for a new index.md and log.md.")
    p_init.add_argument(
        "--update-schema",
        action="store_true",
        help="Acknowledge changed project schema overrides (<wiki>/schema/ingest-rules.md, page-types.md, "
        "citation-rules.md): rewrite only the manifest's schema_fingerprint, atomically under the wiki lock.",
    )

    # ── propose ────────────────────────────────────────────────
    p_propose = sub.add_parser(
        "propose",
        parents=[common],
        help="Write a patch-set from files you wrote yourself, no model involved: --from DIR is laid out "
        "like the wiki (concepts/<slug>.md, decisions/<slug>.md, ...); DIR/index.md and DIR/log.md hold "
        "the lines to append, one per line. Validated like ingest output; --promote applies it at once. "
        "The first line of output is the proposal directory.",
    )
    p_propose.add_argument("--from", dest="source_dir", type=Path, required=True, help="Directory of files.")
    p_propose.add_argument("--name", help="Proposal directory name (default: <date>-<time>-<from-dir-name>, unique).")
    p_propose.add_argument("--rationale", default="", help="Why, recorded in plan.json and the audit archive.")
    p_propose.add_argument("--promote", action="store_true", help="Promote the patch-set right after writing it.")
    p_propose.add_argument(
        "--allow-out-of-repo",
        action="store_true",
        help="With --promote: allow the proposal directory to be outside the repository tree (a "
        "--proposals-dir elsewhere). Default: refuse (exit 7), as promote does.",
    )
    p_propose.add_argument(
        "--allow-unguarded-updates", action="store_true", help="With --promote: " + _ALLOW_UNGUARDED_HELP
    )
    p_propose.add_argument(
        "--by",
        metavar="NAME",
        default=None,
        help=_BY_HELP.format(record="plan.json's proposer (and, with --promote, the receipt's actor)"),
    )

    # ── read ───────────────────────────────────────────────────
    p_read = sub.add_parser(
        "read",
        parents=[common],
        help="Print one wiki page, read exactly once. Before replacing a page: read it, draft from that text, "
        "and record the sha256 that --json prints as the edit's base_sha256 (api.propose) or in the "
        "draft's .base.json (propose --from); promote then applies the replacement only while the live "
        "page still has that hash. Reads nothing outside the wiki (exit 7); a page that is not UTF-8 exits 4.",
    )
    p_read.add_argument("path", help="Wiki-relative page path: index.md, concepts/<slug>.md, ...")
    p_read.add_argument(
        "--json",
        action="store_true",
        help='Print {"path", "sha256", "content"} as one JSON object; content is the decoded text.',
    )

    # ── find ───────────────────────────────────────────────────
    p_find = sub.add_parser(
        "find",
        parents=[common],
        help="Print the pages query would load for a question (index.md first, then index-linked pages "
        "ranked by word overlap), without calling a model and without writing the query log.",
    )
    p_find.add_argument("question", help="The question, in plain words.")
    p_find.add_argument("--max-pages", type=int, default=api.DEFAULT_MAX_QUERY_PAGES, help="At most this many pages.")
    p_find.add_argument("--json", action="store_true", help="Print the result as one JSON object.")

    return parser


def _paths_from_args(args: argparse.Namespace) -> WikiPaths:
    """Resolve the layout once per run: flags, then WIKI_STUDIO_* variables, then defaults."""
    return WikiPaths.resolve(
        root=getattr(args, "root", None),
        wiki_dir=getattr(args, "wiki_dir", None),
        proposals_dir=getattr(args, "proposals_dir", None),
        lock_timeout=getattr(args, "lock_timeout", None),
        source_roots=getattr(args, "source_root", None),
    )


# ── Verb implementations (print only; the work is in wiki_studio.api) ──


def _print_fact_warnings(patch_dir: Path | None) -> None:
    """Print each edit's ``fact_warnings`` (or ``fact_check_error``) from ``<patch_dir>/plan.json`` to stderr.

    Advisory: never an exit code.
    """
    plan_path = patch_dir / "plan.json" if patch_dir is not None else None
    if plan_path is None or not plan_path.is_file():
        return
    for edit in json.loads(plan_path.read_text(encoding="utf-8")).get("edits", []):
        error = edit.get("fact_check_error")
        if error:
            # An unreadable live page means nothing was compared; any other error
            # (malformed sources) is partial and already says what was skipped.
            shown = f"not compared ({error})" if error.startswith(FACT_ERROR_UNREADABLE) else error
            print(f"fact-check: {edit['path']}: {shown}", file=sys.stderr)
        items = edit.get("fact_warnings") or []
        if items:
            print(f"fact-check: {edit['path']}: {len(items)} item(s) removed", file=sys.stderr)
            for item in items:
                print(f"  - {item}", file=sys.stderr)


def _do_ingest(args: argparse.Namespace) -> int:
    """Multi-page ingest by default; --legacy-single-source runs the v1 generator."""
    result = api.ingest(
        args.source,
        _paths_from_args(args),
        backend=args.backend,
        legacy_single_source=args.legacy_single_source,
        dry_run=args.dry_run,
        check=args.check,
        output_dir=args.output_dir,
        allow_out_of_repo=args.allow_out_of_repo,
        redact_output=not args.debug_unsafe_output,
    )
    if result.check:
        # Gate ran, zero side effects. Exit code reflects the disposition.
        return 0 if result.disposition == "accept" else 1
    if result.patch is not None and not result.patch.edits:
        # Multi-page gate rejected the source; surface the rationale.
        print(f"{result.written}  (gate rejected, 0 edits)")
        print(f"  rationale: {result.rationale}", file=sys.stderr)
        return 0
    print(str(result.written))
    _print_fact_warnings(result.written)
    return 0


def _archived_note(result: api.PromoteResult) -> str:
    """Where the proposal directory went, or how to finish when the archive step did not complete."""
    if result.archived_dir:
        return f"archived to {result.archived_dir}."
    return (
        "not archived (the archive step failed after the commit; the receipt records the outcome). "
        "Run promote on the same directory again to finish archiving; nothing is applied twice."
    )


def _print_promote_warnings(result: api.PromoteResult) -> None:
    """Findings that did not stop the promotion (unguarded updates), on stderr."""
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)


def _do_promote(args: argparse.Namespace) -> int:
    """Phase 2: patch-set application under the wiki lock — the only writer to the wiki directory."""
    paths = _paths_from_args(args)
    result = api.promote(
        args.proposal_dir,
        paths,
        dry_run=args.dry_run,
        allow_out_of_repo=args.allow_out_of_repo,
        entry_point=api.PROMOTE_ENTRY_POINT_CLI,
        allow_unguarded_updates=args.allow_unguarded_updates,
        by=args.by,
    )
    _print_promote_warnings(result)
    if result.dry_run:
        print(
            f"dry-run: staged snapshot validated; would apply {len(result.applied_paths)} edit(s); wiki tree "
            "unchanged (point-in-time evidence: a real promote checks again)."
        )
        for p in result.applied_paths:
            print(f"  + {p}")
        return 0
    if not result.applied_paths:
        print(f"no-op: {args.proposal_dir.name} already applied (no changes to write).")
        return 0
    print(f"applied {len(result.applied_paths)} edit(s) from {args.proposal_dir.name}; {_archived_note(result)}")
    for p in result.applied_paths:
        print(f"  + {paths.wiki_label}/{p}")
    _print_approved(result, paths)
    return 0


def _print_approved(result: api.PromoteResult, paths: WikiPaths) -> None:
    """The pages auto-approval approved (``auto_approve_on_promote``)."""
    for p in result.approved_paths:
        print(f"  approved {paths.wiki_label}/{p}")


def _do_approve(args: argparse.Namespace) -> int:
    """One approval record per page under the wiki lock; written by promoter.py only."""
    if args.revision is not None and len(args.pages) != 1:
        raise ContractViolationError(
            f"--revision names the reviewed revision of exactly one page, but {len(args.pages)} pages were given; "
            "approve them one at a time with --revision, or without it"
        )
    paths = _paths_from_args(args)
    expected = {args.pages[0]: args.revision} if args.revision is not None else None
    result = api.approve(args.pages, paths, by=args.by, expected=expected)
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    for record in result.published:
        print(f"approved: {paths.wiki_label}/{record}")
    for record in result.existing:
        print(f"already approved: {paths.wiki_label}/{record}")
    return 0


def _do_read(args: argparse.Namespace) -> int:
    """One page, read once: its text, or with --json the text and the sha256 of the bytes read."""
    result = api.read_page(args.path, _paths_from_args(args))
    if args.json:
        print(json.dumps({"path": result.path, "sha256": result.sha256, "content": result.text}, indent=2))
        return 0
    sys.stdout.write(result.text)
    return 0


def _do_query(args: argparse.Namespace) -> int:
    """Phase 3: index-first query against the wiki."""
    result = api.query(
        args.question,
        _paths_from_args(args),
        backend=args.backend,
        file_back=args.file_back,
        max_pages=args.max_pages,
        output_dir=args.output_dir,
        redact_output=not args.debug_unsafe_output,
    )
    answer = result.answer
    if answer.answer:
        print(answer.answer)
    else:
        print("(no answer — wiki does not contain enough information)")

    print("\n--- citations ---", file=sys.stderr)
    for c in answer.citations:
        print(f"  - {c.page}: {c.fragment}", file=sys.stderr)
    print(f"--- pages loaded: {len(answer.pages_loaded)} ---", file=sys.stderr)
    for p in answer.pages_loaded:
        print(f"  + {p}", file=sys.stderr)

    if args.file_back:
        if result.file_back_dir is None:
            print("(--file-back: empty patch-set; nothing to file back)", file=sys.stderr)
        else:
            print(f"--- file-back patch-set: {result.file_back_dir}", file=sys.stderr)
            _print_fact_warnings(result.file_back_dir)
    return 0


def _do_lint(args: argparse.Namespace) -> int:
    """Structural lint, the audit-format pass and, with --health / --prose, the knowledge-health and prose checks."""
    result = api.lint(
        _paths_from_args(args),
        health=args.health,
        strict=args.strict,
        only=args.paths,
        backend=args.backend,
        prose=args.prose,
    )
    for violation in result.violations:
        print(f"  ✗ {violation}", file=sys.stderr)
    print(f"\nlinted {result.pages_checked} pages, {len(result.violations)} violations")

    if result.audit_errors:
        print(f"\naudit-format: {len(result.audit_errors)} violation(s)", file=sys.stderr)
        for e in result.audit_errors:
            print(f"  [audit] {e}", file=sys.stderr)
    else:
        print("\naudit-format: clean.")

    health = result.health
    if health is not None:
        if not health.findings:
            print(f"\nknowledge-health: clean ({health.pages_checked} pages checked, 0 findings).")
        else:
            # Findings go to stderr so the structural linter's stdout stays canonical.
            print(
                f"\nknowledge-health: {len(health.findings)} finding(s) across {health.pages_checked} pages",
                file=sys.stderr,
            )
            for f in health.findings:
                print(f"  [{f.kind} / {f.severity}] {', '.join(f.pages)}: {f.description}", file=sys.stderr)

    prose = result.prose
    if prose is not None:
        if not prose.findings:
            print(f"\nprose: clean ({prose.pages_checked} pages checked, 0 findings).")
        else:
            print(f"\nprose: {len(prose.findings)} finding(s) across {prose.pages_checked} pages", file=sys.stderr)
            for finding in prose.findings:
                print(f"  {finding.path}:{finding.line} [{finding.check}] {finding.message}", file=sys.stderr)

    return 0 if result.passed else 1


def _do_findings(args: argparse.Namespace) -> int:
    """Model-free curation report: counts by kind, then each finding; exit 0 on a completed run."""
    result = api.findings(_paths_from_args(args), pages=args.paths)
    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
        return 0
    counts = ", ".join(f"{kind} {n}" for kind, n in result.counts.items() if n)
    print(f"findings: {len(result.findings)} across {result.pages_checked} pages" + (f" ({counts})" if counts else ""))
    for finding in result.findings:
        print(f"  [{finding.kind} / {finding.severity}] {', '.join(finding.pages)}: {finding.description}")
    return 0


def _do_audit_flush(args: argparse.Namespace) -> int:
    """Commit pending ingest-log lines (or dry-run report them)."""
    result = api.audit_flush(_paths_from_args(args), dry_run=args.dry_run)
    report = describe_flush(result)
    if report:
        print(report)
    return 0


_SOURCE_FLAG = "flag"
_SOURCE_DEFAULT = "default"
_SCHEMA_PACKAGED = "packaged"
_SCHEMA_PROJECT = "project"


def _location_source(flag_value: object, env_name: str) -> str:
    """Where a resolved location came from, in the precedence order ``WikiPaths.resolve`` uses."""
    if flag_value:
        return _SOURCE_FLAG
    if os.environ.get(env_name):
        return f"env {env_name}"
    return _SOURCE_DEFAULT


def _do_info(args: argparse.Namespace) -> int:
    """Print the resolved layout and the source of each location; writes nothing."""
    paths = _paths_from_args(args)
    root_source = _location_source(getattr(args, "root", None), ENV_ROOT)
    wiki_source = _location_source(getattr(args, "wiki_dir", None), ENV_WIKI_DIR)
    proposals_source = _location_source(getattr(args, "proposals_dir", None), ENV_PROPOSALS_DIR)
    # Any overridden location makes the layout custom: a moved root moves everything under it.
    sources = (root_source, wiki_source, proposals_source)
    layout = "default" if all(s == _SOURCE_DEFAULT for s in sources) else "custom"
    schema = _SCHEMA_PROJECT if paths.schema_dir.is_dir() else _SCHEMA_PACKAGED
    wiki_exists = paths.wiki_dir.is_dir()
    proposals_exist = paths.proposals_dir.is_dir()
    info = {
        "layout": layout,
        "root": str(paths.root),
        "root_source": root_source,
        "wiki_dir": str(paths.wiki_dir),
        "wiki_dir_source": wiki_source,
        "wiki_dir_exists": wiki_exists,
        "wiki_label": paths.wiki_label,
        "proposals_dir": str(paths.proposals_dir),
        "proposals_dir_source": proposals_source,
        "proposals_dir_exists": proposals_exist,
        "query_log": str(paths.query_log),
        "audit_log": str(paths.audit_log),
        "schema": schema,
        "schema_dir": str(paths.schema_dir),
        "lock_file": str(lock_path_for(paths.wiki_dir)),
        "lock_timeout": paths.lock_timeout,
        "source_roots": [str(p) for p in paths.source_roots],
    }
    # The 0.7.0 contract keys follow the 0.6.0 layout keys, which keep their names and meaning.
    contract = api.info(paths)
    info.update(contract.as_dict())
    for warning in contract.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if args.json:
        print(json.dumps(info, indent=2))
        return 0

    def state(exists: bool) -> str:
        return "exists" if exists else "missing"

    print(f"layout: {layout}")
    print(f"root: {paths.root}  ({root_source})")
    print(f"wiki-dir: {paths.wiki_dir}  ({wiki_source}; label '{paths.wiki_label}'; {state(wiki_exists)})")
    print(f"proposals-dir: {paths.proposals_dir}  ({proposals_source}; {state(proposals_exist)})")
    print(f"query-log: {paths.query_log}")
    print(f"audit-log: {paths.audit_log}")
    print(f"schema: {schema}" + (f" copy at {paths.schema_dir}" if schema == _SCHEMA_PROJECT else ""))
    print(f"lock-file: {lock_path_for(paths.wiki_dir)}  (timeout {paths.lock_timeout:g}s)")
    print("source-roots: " + (", ".join(str(p) for p in paths.source_roots) or "(none; links stay inside the root)"))
    print(f"package-version: {contract.package_version}")
    sc = contract.schema_contract
    print(f"schema-contract: {sc.schema_id} version {sc.version} ({sc.source} rules)")
    print(f"schema-fingerprint: {sc.fingerprint}")
    print(f"declared-fingerprint: {sc.declared_fingerprint or '(none)'}  (drift: {'yes' if sc.drift else 'no'})")
    print("formats: " + ", ".join(f"{name} {version}" for name, version in contract.formats.items()))
    print("capabilities: " + ", ".join(contract.capabilities))
    manifest = contract.manifest
    if manifest.state == MANIFEST_PRESENT:
        policy = ", ".join(f"{key}={str(value).lower()}" for key, value in (manifest.policy or {}).items())
        print(f"manifest: present, mode {manifest.mode}, manifest_version {manifest.manifest_version}")
        print(f"wiki-id: {manifest.wiki_id}")
        print(f"policy: {policy}")
    else:
        print(f"manifest: missing, mode {manifest.mode}; {manifest.instruction}")
    return 0


def _do_init(args: argparse.Namespace) -> int:
    """Create the scaffold the other verbs need; report what was created."""
    paths = _paths_from_args(args)
    result = api.init(paths, title=args.title, update_schema=args.update_schema)
    if result.created:
        print(f"initialised {paths.wiki_dir}: created {', '.join(result.created)}")
    else:
        print(f"already initialised: {paths.wiki_dir} has index.md and log.md")
    print(f"manifest: {result.manifest} ({paths.wiki_dir / MANIFEST_NAME})")
    return 0


def _default_proposal_name(source_dir: Path, proposals_dir: Path | None = None) -> str:
    """``<date>-<HHMMSS>-<dir-name>``, sanitised; ``-2``, ``-3``, ... if that directory already exists."""
    now = datetime.datetime.now()
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", source_dir.resolve().name).strip(".-") or "agent"
    base = f"{now.date().isoformat()}-{now.strftime('%H%M%S')}-{stem}"
    if proposals_dir is None:
        return base
    name, suffix = base, 2
    while (proposals_dir / name).exists() or (proposals_dir / ".applied" / name).exists():
        name, suffix = f"{base}-{suffix}", suffix + 1
    return name


def _do_propose(args: argparse.Namespace) -> int:
    """Patch-set from agent-written files (no backend); optionally promote it."""
    paths = _paths_from_args(args)
    edits = api.edits_from_dir(args.source_dir, paths, rationale=args.rationale)
    name = args.name or _default_proposal_name(args.source_dir, paths.proposals_dir)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DriftWarning)
        # Agent-written creates get a fresh page_id in the preview, so the commit carries the same bytes (FR-014).
        written = api.propose(
            edits,
            paths,
            name=name,
            source=str(args.source_dir),
            rationale=args.rationale,
            backend="cli",
            by=args.by,
            assign_page_ids=True,
        )
    drift = [str(w.message) for w in caught if issubclass(w.category, DriftWarning)]
    for message in drift:
        print(f"warning: {message}", file=sys.stderr)
    print(str(written))
    for edit in edits:
        print(f"  {edit.action} {edit.path}")
    # Before the optional promote, so the curator sees what an update drops before it lands.
    _print_fact_warnings(written)
    if not args.promote:
        return 0
    result = api.promote(
        written,
        paths,
        allow_out_of_repo=args.allow_out_of_repo,
        entry_point=api.PROMOTE_ENTRY_POINT_CLI,
        allow_unguarded_updates=args.allow_unguarded_updates,
        by=args.by,
    )
    # The drift warning was printed once already, by propose.
    _print_promote_warnings(replace(result, warnings=[w for w in result.warnings if w not in drift]))
    print(f"applied {len(result.applied_paths)} edit(s); {_archived_note(result)}")
    _print_approved(result, paths)
    return 0


def _do_find(args: argparse.Namespace) -> int:
    """Model-free page selection: what query would read."""
    paths = _paths_from_args(args)
    result = api.find(args.question, paths, max_pages=args.max_pages)
    if args.json:
        payload = {
            "question": result.question,
            "index": paths.relative_to_root(result.index),
            "pages": [{"path": p.path, "file": paths.relative_to_root(p.file), "title": p.title} for p in result.pages],
        }
        print(json.dumps(payload, indent=2))
        return 0
    print(f"{paths.relative_to_root(result.index)}  (always read first)")
    for page in result.pages:
        print(f"{paths.relative_to_root(page.file)}  {page.title}")
    if not result.pages:
        print("no index-linked page shares a word with the question; read the index.")
    return 0


_VERBS = (
    "ingest",
    "promote",
    "approve",
    "query",
    "lint",
    "findings",
    "audit-flush",
    "info",
    "init",
    "propose",
    "find",
    "read",
)

# Global options that take a value; their value is not a positional for the legacy shim.
_GLOBAL_VALUE_OPTIONS = ("--root", "--wiki-dir", "--proposals-dir", "--source-root", "--lock-timeout")


def _inject_legacy_v1_prefix(argv: list[str]) -> list[str]:
    """Backwards-compat shim for direct ``python3 -m wiki_studio <source>`` callers.

    Phase 0 introduced verb dispatch. Pre-Phase-0 callers (and the e2e
    test suite) invoke ``python3 -m wiki_studio <source> [--backend ...]``
    without any verb. Detect that shape — first non-flag arg is not a
    known verb — and inject ``ingest --legacy-single-source`` so the v1
    behavior is preserved at the Python entrypoint as well as at the
    ``wiki_studio`` console script.
    """
    if not argv:
        return argv
    # Top-level help/version: pass straight through so the parser shows
    # the verb-dispatching parser's epilog (with stable exit codes).
    if "-h" in argv or "--help" in argv or "--version" in argv:
        return argv
    # Walk past leading flags (and the values of the global location
    # options, which may precede the verb) to find the first positional arg.
    first_positional: str | None = None
    skip_next = False
    for token in argv:
        if skip_next:
            skip_next = False
            continue
        if token in _GLOBAL_VALUE_OPTIONS:
            skip_next = True
            continue
        if token.startswith("-"):
            continue
        first_positional = token
        break
    if first_positional in _VERBS:
        return argv
    # No verb in argv → legacy v1 invocation. Inject the prefix.
    return ["ingest", "--legacy-single-source", *argv]


def _report(exc: Exception) -> int:
    """The one place where exceptions become stderr messages and exit codes."""
    if isinstance(exc, IngestError):
        prefix = next((p for cls, p in _ERROR_PREFIXES if isinstance(exc, cls)), "")
        reason = getattr(exc, "reason", None)
        if reason:
            # "promote apply failed:\n" -> "promote apply failed [reason=lock_timeout]:\n"
            head, sep, tail = prefix.partition(":")
            prefix = f"{head} [reason={reason}]{sep}{tail}"
        print(f"error: {prefix}{exc}", file=sys.stderr)
        return exc.exit_code
    # ValueError: a flag combination the verb rejects (e.g. --check with --dry-run).
    print(f"error: {exc}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns the exit code; never raises (errors are mapped)."""
    if argv is None:
        argv = sys.argv[1:]
    argv = _inject_legacy_v1_prefix(list(argv))

    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "ingest": _do_ingest,
        "promote": _do_promote,
        "approve": _do_approve,
        "query": _do_query,
        "lint": _do_lint,
        "findings": _do_findings,
        "audit-flush": _do_audit_flush,
        "info": _do_info,
        "init": _do_init,
        "propose": _do_propose,
        "find": _do_find,
        "read": _do_read,
    }
    handler = dispatch.get(args.verb)
    if handler is None:
        parser.error(f"unknown verb: {args.verb}")
    try:
        return handler(args)
    except (IngestError, ValueError) as exc:
        return _report(exc)


if __name__ == "__main__":
    sys.exit(main())
