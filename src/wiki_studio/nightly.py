# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wiki_studio.nightly — the model-free curation pass and its report (FR-001).

One run reads the wiki and says what a curator should look at:

* structural lint (no health tier, no prose, not strict) and its audit-format
  errors (:func:`wiki_studio.api.lint`);
* the model-free findings (:func:`wiki_studio.api.findings`), with their
  counts by kind;
* the proposal directories still pending under the proposals directory.

It takes no backend, no lock and writes nothing: the result carries the
markdown report (:meth:`NightlyResult.render_markdown`), its JSON form
(:meth:`NightlyResult.as_dict`) and an exit code (1 when structural lint
failed, else 0). The report file is written only by :func:`write_report`,
and a path inside the wiki is refused by :func:`check_report_path`.
"""

from __future__ import annotations

import contextlib
import datetime
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import __version__
from .contract import NIGHTLY_FORMAT_VERSION

if TYPE_CHECKING:
    from .api import LintResult
    from .findings import Finding, FindingsResult
    from .paths import WikiPaths

REPORT_TITLE = "# wiki-studio nightly report"

# The exit code of a run whose structural lint failed (FR-004, FR-010).
EXIT_LINT_FAILED = 1


@dataclass(frozen=True)
class PendingProposal:
    """One proposal directory still pending: its ``name`` and its ``edits`` count (None when unknown)."""

    name: str
    edits: int | None

    def as_dict(self) -> dict[str, Any]:
        """``{"name", "edits"}`` as the JSON form records it (FR-006); ``edits`` is null when unreadable."""
        return {"name": self.name, "edits": self.edits}


@dataclass(frozen=True)
class NightlyResult:
    """One model-free pass: what it found, what needs a curator, and the report (FR-002).

    ``lint`` is the structural result (audit-format errors included), ``findings``
    the full model-free findings, ``needs_curator`` the findings the report lists
    for a person and ``pending`` the proposal directories still waiting.
    ``exit_code`` is 1 when structural lint failed, else 0 (FR-004).
    """

    run_at: str
    package_version: str
    wiki_dir: Path
    proposals_dir: Path
    lint: LintResult
    findings: FindingsResult
    needs_curator: tuple[Finding, ...]
    pending: tuple[PendingProposal, ...]
    warnings: tuple[str, ...]
    exit_code: int

    def as_dict(self) -> dict[str, Any]:
        """The JSON form (``nightly_version: 1``); consumers read keys by name, not by order (FR-002)."""
        return {
            "nightly_version": NIGHTLY_FORMAT_VERSION,
            "package_version": self.package_version,
            "run_at": self.run_at,
            "wiki_dir": str(self.wiki_dir),
            "proposals_dir": str(self.proposals_dir),
            "lint": {
                "passed": self.lint.passed,
                "violations": list(self.lint.violations),
                "audit_errors": list(self.lint.audit_errors),
            },
            "findings": self.findings.as_dict(),
            "needs_curator": {
                "findings": [finding.as_dict() for finding in self.needs_curator],
                "pending": [pending.as_dict() for pending in self.pending],
            },
            "warnings": list(self.warnings),
            "exit_code": self.exit_code,
        }

    def render_markdown(self) -> str:
        """The report: fixed headings in order, every empty part saying so (FR-003)."""
        lines = [
            REPORT_TITLE,
            "",
            f"- Run time (UTC): {self.run_at}",
            f"- Wiki directory: {self.wiki_dir}",
            f"- Proposals directory: {self.proposals_dir}",
            f"- Package version: {self.package_version}",
            "",
            "## Lint",
            "",
            *self._lint_lines(),
            "",
            "## Findings",
            "",
            *self._finding_lines(),
            "",
            "## Needs a curator",
            "",
            "### Findings",
            "",
            *self._curator_lines(),
            "",
            "### Pending proposals",
            "",
            *self._pending_lines(),
        ]
        return "\n".join(lines) + "\n"

    def _lint_lines(self) -> list[str]:
        if not self.lint.violations and not self.lint.audit_errors:
            return ["clean"]
        lines: list[str] = []
        if self.lint.violations:
            lines.append("Lint failed with structural violations:")
            lines.extend(f"- {violation}" for violation in self.lint.violations)
        else:
            lines.append("Lint passed.")
        if self.lint.audit_errors:
            if self.lint.violations:
                lines.append("")
            lines.append("Audit-format errors (reported; they do not fail lint):")
            lines.extend(f"- {error}" for error in self.lint.audit_errors)
        return lines

    def _finding_lines(self) -> list[str]:
        if not self.findings.findings:
            return ["none"]
        counts = ", ".join(f"{kind} {count}" for kind, count in self.findings.counts.items() if count)
        lines = [f"Counts: {counts}", ""] if counts else []
        lines.extend(
            f"- [{finding.kind} / {finding.severity}] {', '.join(finding.pages)}: {finding.description}"
            for finding in self.findings.findings
        )
        return lines

    def _curator_lines(self) -> list[str]:
        if not self.needs_curator:
            return ["none"]
        return [f"- [{finding.kind}] {', '.join(finding.pages)}" for finding in self.needs_curator]

    def _pending_lines(self) -> list[str]:
        if not self.pending:
            return ["none"]
        return [
            f"- {pending.name} (edits: {pending.edits})"
            if pending.edits is not None
            else f"- {pending.name} (edits unknown)"
            for pending in self.pending
        ]


def _utc_now() -> str:
    """UTC ISO 8601 to the second with ``Z`` (FR-002)."""
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _edits_count(plan_path: Path) -> int | None:
    """The number of entries in ``plan.json``'s ``edits`` list, or None when it cannot be read (FR-006)."""
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(plan, dict):
        return None
    edits = plan.get("edits")
    return len(edits) if isinstance(edits, list) else None


def _pending_proposals(proposals_dir: Path) -> tuple[PendingProposal, ...]:
    """Directories directly under the proposals directory, hidden ones excluded, sorted by name (FR-006)."""
    try:
        entries = sorted(proposals_dir.iterdir(), key=lambda entry: entry.name)
    except FileNotFoundError:
        return ()
    return tuple(
        PendingProposal(entry.name, _edits_count(entry / "plan.json"))
        for entry in entries
        if not entry.name.startswith(".") and entry.is_dir()
    )


def run(paths: WikiPaths) -> NightlyResult:
    """Run the model-free pass: structural lint, then findings, then the pending listing (FR-001).

    No backend is resolved, no lock is taken and nothing is written; an
    exception from either read propagates and no report is produced.
    """
    from . import api  # deferred: api imports this module's result type

    run_at = _utc_now()
    lint_result = api.lint(paths)
    findings_result = api.findings(paths)
    pending = _pending_proposals(paths.proposals_dir)
    return NightlyResult(
        run_at=run_at,
        package_version=__version__,
        wiki_dir=paths.wiki_dir.resolve(),
        proposals_dir=paths.proposals_dir.resolve(),
        lint=lint_result,
        findings=findings_result,
        needs_curator=findings_result.findings,
        pending=pending,
        warnings=(),
        exit_code=0 if lint_result.passed else EXIT_LINT_FAILED,
    )


def check_report_path(report: str | os.PathLike[str], paths: WikiPaths) -> Path:
    """The fully resolved report path; ``ValueError`` when it is the wiki or lies inside it (FR-005).

    Every existing symlink is followed, so a path outside the wiki whose
    parent links into it is refused as well; a refusal names both paths.
    """
    resolved = Path(report).resolve()
    wiki_dir = paths.wiki_dir.resolve()
    if resolved == wiki_dir or resolved.is_relative_to(wiki_dir):
        raise ValueError(f"report path {resolved} is inside the wiki directory {wiki_dir}; it must lie outside it")
    return resolved


def write_report(text: str, path: str | os.PathLike[str]) -> None:
    """Write ``text`` as UTF-8 to ``path`` atomically: a temporary sibling, then ``os.replace`` (FR-005).

    Missing parents are created. On any ``OSError`` the temporary file is
    removed and the error re-raised, so a failed write leaves no partial
    report and no temporary file behind.
    """
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    handle_fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temp_path, target)
    except OSError:
        with contextlib.suppress(OSError):
            temp_path.unlink()
        raise
