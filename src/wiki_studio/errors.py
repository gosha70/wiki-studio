# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# wiki-studio.errors — exception hierarchy with spec-defined exit codes.


class IngestError(Exception):
    """Base class for all wiki-ingest pipeline errors."""

    exit_code: int = 1


class BackendNotFoundError(IngestError):
    """No registered backend was found (auto-detect or explicit name). Exit 2."""

    exit_code: int = 2


class BackendInvocationError(IngestError):
    """Backend process exited non-zero. Exit 3."""

    exit_code: int = 3


class ContractViolationError(IngestError):
    """Backend response failed shape or semantic validation. Exit 4."""

    exit_code: int = 4


class SourceMissingError(IngestError):
    """Source file is missing or unreadable. Exit 5."""

    exit_code: int = 5


class PathOutsideRootError(IngestError):
    """A source or proposal path lies outside the project root; pass allow_out_of_repo to override. Exit 7."""

    exit_code: int = 7


class OutputWriteError(IngestError):
    """Could not write the proposal file to the output directory. Exit 6."""

    exit_code: int = 6


class PromoteValidationError(IngestError):
    """Phase-2 promote: staged-tree validation failed (per-edit semantic
    or structural-lint). The wiki tree is unchanged on disk; the curator
    fixes the patch-set and reruns. Exit 9."""

    exit_code: int = 9


class PromoteApplyError(IngestError):
    """Phase-2 promote: filesystem failure during stage→wiki commit
    (rare; usually means the wiki dir is read-only or a TOCTOU race),
    or a refusal of the lock and recovery protocol. Exit 10.

    ``reason`` is a stable machine-readable tag when the failure is one
    the protocol names: ``lock_timeout``, ``uncertain_outcome``,
    ``wiki_mismatch``, ``wiki_identity_unavailable`` or ``payload_changed``;
    None for a plain filesystem failure."""

    exit_code: int = 10

    def __init__(self, message: str, *, reason: str | None = None) -> None:
        super().__init__(message)
        self.reason = reason


# Stable ``PromoteApplyError.reason`` tags (exit 10).
REASON_LOCK_TIMEOUT = "lock_timeout"
REASON_UNCERTAIN_OUTCOME = "uncertain_outcome"
REASON_WIKI_MISMATCH = "wiki_mismatch"
REASON_WIKI_IDENTITY_UNAVAILABLE = "wiki_identity_unavailable"
REASON_PAYLOAD_CHANGED = "payload_changed"


class AuditFlushError(IngestError):
    """wiki audit-flush: not a git work tree; append-only invariant violated;
    working log malformed; or git commit failed. Exit 11."""

    exit_code: int = 11
