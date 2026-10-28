# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wiki_studio.contract — the versioned knowledge contract a wiki declares (read side).

A wiki initialised by ``wiki-studio init`` carries a root manifest,
``<wiki>/.wiki-studio.json``: its identity (``wiki_id``), the page schema it
follows (``schema.id`` and ``schema.version``), the fingerprint of the project
schema overrides acknowledged at ``init`` and its policy. This module reads and
validates the manifest, loads the schema documents through one contained,
no-follow loader, computes the fingerprint, decides drift and compatibility,
and describes the build for ``info``. It never writes: ``promoter.py`` creates
and updates the manifest.

Vocabulary (``docs/knowledge-contract.md``): a **governed** wiki has a manifest
whose policy sets ``approval_required``; a **managed** wiki has a manifest with
the default policy; a **legacy** wiki has no manifest and behaves as in 0.6.0.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import stat
import uuid
from dataclasses import dataclass
from importlib import resources
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from . import __version__
from .errors import ContractViolationError
from .paths import MANIFEST_NAME, SCHEMA_DIR_NAME, ContainmentError, contain
from .schema import PROMPT_SCHEMA_DOCUMENTS, SCHEMA_ID, SCHEMA_VERSION

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from .paths import WikiPaths

PACKAGE_NAME = "wiki-studio"

# The manifest format this package reads and writes.
MANIFEST_VERSION = 1
# The schema identities this package supports.
SUPPORTED_SCHEMA_IDS: frozenset[str] = frozenset({SCHEMA_ID})

# Manifest keys.
KEY_MANIFEST_VERSION = "manifest_version"
KEY_WIKI_ID = "wiki_id"
KEY_SCHEMA = "schema"
KEY_SCHEMA_ID = "id"
KEY_SCHEMA_VERSION = "version"
KEY_SCHEMA_FINGERPRINT = "schema_fingerprint"
KEY_POLICY = "policy"
KEY_CREATED_BY = "created_by"
KEY_CREATED_BY_PACKAGE = "package"
KEY_CREATED_BY_VERSION = "version"

# Policy keys (FR-020) and the policy ``init`` writes.
POLICY_APPROVAL_REQUIRED = "approval_required"
POLICY_APPROVER_REQUIRED = "approver_required"
POLICY_AUTO_APPROVE_ON_PROMOTE = "auto_approve_on_promote"
POLICY_KEYS: tuple[str, ...] = (POLICY_APPROVAL_REQUIRED, POLICY_APPROVER_REQUIRED, POLICY_AUTO_APPROVE_ON_PROMOTE)
DEFAULT_POLICY: Mapping[str, bool] = MappingProxyType(dict.fromkeys(POLICY_KEYS, False))

# Modes and manifest states, as ``info`` reports them.
MODE_GOVERNED = "governed"
MODE_MANAGED = "managed"
MODE_LEGACY = "legacy"
MANIFEST_PRESENT = "present"
MANIFEST_MISSING = "missing"
MANIFEST_INSTRUCTION = "no manifest (legacy wiki); run `wiki-studio init` to add one"

# Where the schema rules a wiki follows come from (derived on read, never stored).
SCHEMA_SOURCE_PROJECT = "project"
SCHEMA_SOURCE_PACKAGED = "packaged"

# Format versions of the files this build reads and writes, and its capabilities (FR-010).
# A phase adds its entries when it ships; a scope the circuit breaker cuts adds none.
RECEIPT_VERSION = 1
PATCH_SET_FORMAT_VERSION = 1
INGEST_LOG_FORMAT_VERSION = 1
APPROVAL_FORMAT_VERSION = 1
FINDINGS_FORMAT_VERSION = 1
FORMATS: Mapping[str, int] = MappingProxyType(
    {
        "patch_set": PATCH_SET_FORMAT_VERSION,
        "receipt": RECEIPT_VERSION,
        "ingest_log": INGEST_LOG_FORMAT_VERSION,
        "approval": APPROVAL_FORMAT_VERSION,
        "findings": FINDINGS_FORMAT_VERSION,
    }
)
CAPABILITY_WIKI_LOCK = "wiki-lock"
CAPABILITY_RECEIPTS = "receipts"
CAPABILITY_BASE_REVISION = "base-revision"
CAPABILITY_ROOT_MANIFEST = "root-manifest"
CAPABILITY_PAGE_ID = "page-id"
CAPABILITY_ATTRIBUTION = "attribution"
CAPABILITY_APPROVAL_RECORD = "approval-record"
CAPABILITY_SUPERSEDED_BY = "superseded-by"
CAPABILITY_FINDINGS = "findings"
CAPABILITY_RANKED_DISCOVERY = "ranked-discovery"
CAPABILITY_CONTEXT_BUDGET = "context-budget"
CAPABILITIES: tuple[str, ...] = (
    CAPABILITY_WIKI_LOCK,
    CAPABILITY_RECEIPTS,
    CAPABILITY_BASE_REVISION,
    CAPABILITY_ROOT_MANIFEST,
    CAPABILITY_PAGE_ID,
    CAPABILITY_ATTRIBUTION,
    CAPABILITY_APPROVAL_RECORD,
    CAPABILITY_SUPERSEDED_BY,
    CAPABILITY_FINDINGS,
    CAPABILITY_RANKED_DISCOVERY,
    CAPABILITY_CONTEXT_BUDGET,
)

UPDATE_SCHEMA_COMMAND = "wiki-studio init --update-schema"

_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_HEX = frozenset("0123456789abcdef")


# ── The manifest ──────────────────────────────────────────────


@dataclass(frozen=True)
class Manifest:
    """A validated root manifest. ``raw`` is the parsed JSON object, kept so a rewrite changes one key only."""

    manifest_version: int
    wiki_id: str
    schema_id: str
    schema_version: int
    schema_fingerprint: str
    policy: Mapping[str, bool]
    created_by: Mapping[str, str]
    raw: Mapping[str, Any]

    @property
    def mode(self) -> str:
        """``governed`` when the policy requires approval, else ``managed``."""
        return MODE_GOVERNED if self.policy[POLICY_APPROVAL_REQUIRED] else MODE_MANAGED


def manifest_path(paths: WikiPaths) -> Path:
    """``<wiki>/.wiki-studio.json``."""
    return paths.wiki_dir / MANIFEST_NAME


def _is_sha256_hex(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _malformed(where: str, key: str, problem: str) -> ContractViolationError:
    return ContractViolationError(f"{where}: malformed manifest: key '{key}' {problem}")


def _require(obj: Mapping[str, Any], key: str, where: str, label: str | None = None) -> Any:
    if key not in obj:
        raise _malformed(where, label or key, "is missing")
    return obj[key]


def _check_compatible(obj: Mapping[str, Any], where: str) -> None:
    """The compatibility rules (FR-011), checked before the rest of the shape: a newer format is not judged by ours."""
    version = _require(obj, KEY_MANIFEST_VERSION, where)
    if not _is_int(version) or version < 1:
        raise _malformed(where, KEY_MANIFEST_VERSION, f"must be a positive integer, got {version!r}")
    if version > MANIFEST_VERSION:
        raise ContractViolationError(
            f"{where}: manifest_version {version} is newer than wiki-studio {__version__} supports "
            f"(manifest_version {MANIFEST_VERSION}); upgrade wiki-studio to work on this wiki"
        )
    schema = _require(obj, KEY_SCHEMA, where)
    if not isinstance(schema, dict):
        raise _malformed(where, KEY_SCHEMA, f"must be an object, got {schema!r}")
    schema_id = _require(schema, KEY_SCHEMA_ID, where, f"{KEY_SCHEMA}.{KEY_SCHEMA_ID}")
    if not isinstance(schema_id, str):
        raise _malformed(where, f"{KEY_SCHEMA}.{KEY_SCHEMA_ID}", f"must be a string, got {schema_id!r}")
    if schema_id not in SUPPORTED_SCHEMA_IDS:
        raise ContractViolationError(
            f"{where}: schema.id {schema_id!r} is not a schema wiki-studio {__version__} supports "
            f"({', '.join(sorted(SUPPORTED_SCHEMA_IDS))}); this wiki follows another contract"
        )
    schema_version = _require(schema, KEY_SCHEMA_VERSION, where, f"{KEY_SCHEMA}.{KEY_SCHEMA_VERSION}")
    if not _is_int(schema_version) or schema_version < 1:
        raise _malformed(
            where, f"{KEY_SCHEMA}.{KEY_SCHEMA_VERSION}", f"must be a positive integer, got {schema_version!r}"
        )
    if schema_version > SCHEMA_VERSION:
        raise ContractViolationError(
            f"{where}: schema.version {schema_version} is newer than wiki-studio {__version__} supports "
            f"(schema.version {SCHEMA_VERSION}); upgrade wiki-studio to work on this wiki"
        )


def parse_manifest(data: bytes, where: str) -> Manifest:
    """Validate manifest bytes: compatibility first (FR-011), then every key (FR-006). Exit 4 names the key."""
    try:
        obj = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ContractViolationError(f"{where}: malformed manifest: not a UTF-8 JSON document ({exc})") from exc
    if not isinstance(obj, dict):
        raise ContractViolationError(f"{where}: malformed manifest: must be a JSON object")
    _check_compatible(obj, where)
    wiki_id = _require(obj, KEY_WIKI_ID, where)
    try:
        uuid.UUID(wiki_id)
    except (TypeError, ValueError, AttributeError) as exc:
        raise _malformed(where, KEY_WIKI_ID, f"must be a UUID string, got {wiki_id!r}") from exc
    fingerprint = _require(obj, KEY_SCHEMA_FINGERPRINT, where)
    if not _is_sha256_hex(fingerprint):
        raise _malformed(where, KEY_SCHEMA_FINGERPRINT, f"must be a lowercase sha256 hex digest, got {fingerprint!r}")
    policy = _require(obj, KEY_POLICY, where)
    if not isinstance(policy, dict):
        raise _malformed(where, KEY_POLICY, f"must be an object, got {policy!r}")
    for key in POLICY_KEYS:
        value = _require(policy, key, where, f"{KEY_POLICY}.{key}")
        if not isinstance(value, bool):
            raise _malformed(where, f"{KEY_POLICY}.{key}", f"must be true or false, got {value!r}")
    unknown = sorted(set(policy) - set(POLICY_KEYS))
    if unknown:
        raise _malformed(where, f"{KEY_POLICY}.{unknown[0]}", f"is not a policy key ({', '.join(POLICY_KEYS)})")
    created_by = _require(obj, KEY_CREATED_BY, where)
    if not isinstance(created_by, dict):
        raise _malformed(where, KEY_CREATED_BY, f"must be an object, got {created_by!r}")
    for key in (KEY_CREATED_BY_PACKAGE, KEY_CREATED_BY_VERSION):
        value = _require(created_by, key, where, f"{KEY_CREATED_BY}.{key}")
        if not isinstance(value, str):
            raise _malformed(where, f"{KEY_CREATED_BY}.{key}", f"must be a string, got {value!r}")
    schema = obj[KEY_SCHEMA]
    return Manifest(
        manifest_version=obj[KEY_MANIFEST_VERSION],
        wiki_id=wiki_id,
        schema_id=schema[KEY_SCHEMA_ID],
        schema_version=schema[KEY_SCHEMA_VERSION],
        schema_fingerprint=fingerprint,
        policy=MappingProxyType({key: policy[key] for key in POLICY_KEYS}),
        created_by=MappingProxyType({key: created_by[key] for key in (KEY_CREATED_BY_PACKAGE, KEY_CREATED_BY_VERSION)}),
        raw=MappingProxyType(obj),
    )


_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_FD_READS = os.open in os.supports_dir_fd


def _open_contained(wiki_dir: Path, rel: str) -> int:
    """Open ``<wiki>/<rel>`` component by component from the wiki directory itself, never following a link.

    The configured wiki spelling may be a symlink alias (Release A, FR-002);
    it is resolved once to the real directory, which is opened with
    ``O_NOFOLLOW``, and every component below it is opened relative to the
    previous descriptor with ``O_NOFOLLOW``, so a swap to a symlink after the
    containment check raises ``ELOOP`` instead of being followed.
    """
    fd = os.open(wiki_dir.resolve(), os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW)
    try:
        parts = rel.split("/")
        for part in parts[:-1]:
            nxt = os.open(part, os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return os.open(parts[-1], os.O_RDONLY | _O_NOFOLLOW, dir_fd=fd)
    finally:
        os.close(fd)


def _read_contained(rel: str, wiki_dir: Path, what: str, *, regular_only: bool) -> bytes | None:
    """Read ``<wiki>/<rel>`` through the wiki boundary with ``O_NOFOLLOW``; None when it does not exist.

    A symlink on the way (the file itself or a directory) is refused with
    ``ContractViolationError`` and its target is never opened. A non-regular
    entry is refused when ``regular_only``, else treated as absent.
    """
    shown = f"{wiki_dir / rel}"
    try:
        target = contain(rel, wiki_dir)
    except ContainmentError as exc:
        raise ContractViolationError(
            f"{what} {shown} is outside the wiki boundary ({exc}); refusing to read it"
        ) from exc
    try:
        fd = _open_contained(wiki_dir, rel) if _FD_READS else os.open(target, os.O_RDONLY | _O_NOFOLLOW)
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise ContractViolationError(f"{what} {shown} is a symlink; refusing to read through it") from exc
        raise ContractViolationError(f"could not read {what} {shown}: {exc}") from exc
    try:
        regular = stat.S_ISREG(os.fstat(fd).st_mode)
    except OSError:
        os.close(fd)
        raise
    if not regular:
        os.close(fd)
        if regular_only:
            raise ContractViolationError(f"{what} {shown} is not a regular file")
        return None
    with os.fdopen(fd, "rb") as handle:
        return handle.read()


def read_manifest_bytes(paths: WikiPaths) -> bytes | None:
    """The manifest's exact bytes, read once through the wiki boundary; None for a legacy wiki."""
    return _read_contained(MANIFEST_NAME, paths.wiki_dir, "manifest", regular_only=True)


def read_manifest(paths: WikiPaths) -> Manifest | None:
    """The validated, compatible manifest, or None for a legacy wiki. Raises ``ContractViolationError``."""
    data = read_manifest_bytes(paths)
    return None if data is None else parse_manifest(data, str(manifest_path(paths)))


def new_manifest(fingerprint: str) -> dict[str, Any]:
    """The manifest ``init`` writes: a fresh ``wiki_id``, this schema, ``fingerprint`` and the default policy."""
    return {
        KEY_MANIFEST_VERSION: MANIFEST_VERSION,
        KEY_WIKI_ID: str(uuid.uuid4()),
        KEY_SCHEMA: {KEY_SCHEMA_ID: SCHEMA_ID, KEY_SCHEMA_VERSION: SCHEMA_VERSION},
        KEY_SCHEMA_FINGERPRINT: fingerprint,
        KEY_POLICY: dict(DEFAULT_POLICY),
        KEY_CREATED_BY: {KEY_CREATED_BY_PACKAGE: PACKAGE_NAME, KEY_CREATED_BY_VERSION: __version__},
    }


def manifest_bytes(obj: Mapping[str, Any]) -> bytes:
    """How a manifest is serialised: indented JSON, UTF-8, one trailing newline."""
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


# ── The schema documents: one contained loader, one fingerprint ──


@dataclass(frozen=True)
class SchemaLoad:
    """The schema documents as loaded once.

    ``texts`` maps each prompt document name (``ingest-rules``, ``page-types``,
    ``citation-rules``) to the text in use, the project override or the
    packaged copy; ``overrides`` maps the file name of every project override
    present to the exact bytes read, which are both decoded into ``texts`` and
    hashed into the fingerprint.
    """

    texts: Mapping[str, str]
    overrides: Mapping[str, bytes]

    @property
    def source(self) -> str:
        """``project`` when any override exists, else ``packaged``."""
        return SCHEMA_SOURCE_PROJECT if self.overrides else SCHEMA_SOURCE_PACKAGED

    @property
    def fingerprint(self) -> str:
        """:func:`schema_fingerprint` of the overrides."""
        return schema_fingerprint(self.overrides)


def read_packaged_schema(name: str) -> str:
    """One schema document shipped as package data under ``wiki_studio/schema/``."""
    return resources.files(__package__).joinpath("schema", f"{name}.md").read_text(encoding="utf-8")


def load_schema(paths: WikiPaths) -> SchemaLoad:
    """Load the prompt schema documents; a project copy under ``<wiki>/schema/`` wins over the packaged one.

    Every candidate passes the wiki containment check and is opened with
    ``O_NOFOLLOW``: a symlinked override or schema directory is refused
    (``ContractViolationError``, exit 4) with its target unread (FR-007). An
    override that is not valid UTF-8 is refused the same way.
    """
    texts: dict[str, str] = {}
    overrides: dict[str, bytes] = {}
    for name in PROMPT_SCHEMA_DOCUMENTS:
        file_name = f"{name}.md"
        data = _read_contained(f"{SCHEMA_DIR_NAME}/{file_name}", paths.wiki_dir, "schema override", regular_only=False)
        if data is None:
            texts[name] = read_packaged_schema(name)
            continue
        try:
            texts[name] = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ContractViolationError(
                f"schema override {paths.schema_dir / file_name} is not valid UTF-8: {exc}"
            ) from exc
        overrides[file_name] = data
    return SchemaLoad(texts=MappingProxyType(texts), overrides=MappingProxyType(overrides))


def schema_fingerprint(overrides: Mapping[str, bytes]) -> str:
    """Lowercase hex SHA-256 over the overrides sorted by file name, each fed as UTF-8 name, NUL, raw bytes (FR-008).

    No override gives the SHA-256 of empty input. Raw bytes are hashed
    without normalisation: a line-ending change is a schema change.
    """
    digest = hashlib.sha256()
    for file_name in sorted(overrides):
        digest.update(file_name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(overrides[file_name])
    return digest.hexdigest()


# ── Drift and the write-side check ────────────────────────────


def drift_message(declared: str, current: str) -> str:
    """The one drift message: the declared and the current fingerprint and the remedy (FR-009)."""
    return (
        f"schema drift: the manifest declares schema_fingerprint {declared} but the project schema overrides "
        f"now hash to {current}; review the change and run `{UPDATE_SCHEMA_COMMAND}` to acknowledge it"
    )


def check_write_contract(paths: WikiPaths) -> list[str]:
    """The contract check every writing verb runs first (``propose``, ``promote``, ``approve``).

    A legacy wiki passes with no warning. A manifest that is malformed or
    newer than this package is refused (exit 4). Drift is refused (exit 4)
    on a governed wiki and returned as a warning on a managed one.
    """
    manifest = read_manifest(paths)
    if manifest is None:
        return []
    return drift_warnings(paths, manifest)


def drift_warnings(paths: WikiPaths, manifest: Manifest) -> list[str]:
    """Drift against an already read manifest: exit 4 on a governed wiki, the message as a warning on a managed one."""
    current = load_schema(paths).fingerprint
    if current == manifest.schema_fingerprint:
        return []
    message = drift_message(manifest.schema_fingerprint, current)
    if manifest.mode == MODE_GOVERNED:
        raise ContractViolationError(f"{message} (governed wiki: {POLICY_APPROVAL_REQUIRED} is true)")
    return [message]


# ── info ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class SchemaContractInfo:
    """``info``'s ``schema_contract``: the schema identity and version, where the rules come from, the fingerprints.

    ``schema_id`` and ``version`` are the manifest's when it has one, else
    this package's; ``fingerprint`` is the current one, ``declared_fingerprint``
    the manifest's (None for a legacy wiki).
    """

    schema_id: str
    version: int
    source: str
    fingerprint: str
    declared_fingerprint: str | None

    @property
    def drift(self) -> bool:
        """True when a declared fingerprint differs from the current one."""
        return self.declared_fingerprint is not None and self.declared_fingerprint != self.fingerprint

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.schema_id,
            "version": self.version,
            "source": self.source,
            "fingerprint": self.fingerprint,
            "declared_fingerprint": self.declared_fingerprint,
            "drift": self.drift,
        }


@dataclass(frozen=True)
class ManifestInfo:
    """``info``'s ``manifest``: present (version, ``wiki_id``, policy, mode) or missing (legacy, with a hint)."""

    state: str
    mode: str
    manifest_version: int | None = None
    wiki_id: str | None = None
    policy: Mapping[str, bool] | None = None
    instruction: str | None = None

    def as_dict(self) -> dict[str, Any]:
        if self.state == MANIFEST_MISSING:
            return {"state": self.state, "mode": self.mode, "instruction": self.instruction}
        return {
            "state": self.state,
            "manifest_version": self.manifest_version,
            "wiki_id": self.wiki_id,
            "policy": dict(self.policy or {}),
            "mode": self.mode,
        }


@dataclass(frozen=True)
class DiscoveryInfo:
    """``info``'s ``discovery`` (0.8.0, FR-010): FTS5 in this Python's SQLite, the default ranker and its hash.

    ``cache`` is the search cache's ``{path, state, reason}`` with ``state`` one of
    ``present``, ``missing`` or ``unusable`` (FR-018); None when no wiki was described.
    """

    fts5: bool
    sqlite_version: str
    fts5_reason: str | None
    default_ranker: str
    default_ranker_source: str
    ranker_config_hash: str
    cache: Mapping[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "fts5": self.fts5,
            "sqlite_version": self.sqlite_version,
            "fts5_reason": self.fts5_reason,
            "default_ranker": self.default_ranker,
            "default_ranker_source": self.default_ranker_source,
            "ranker_config_hash": self.ranker_config_hash,
            "cache": None if self.cache is None else dict(self.cache),
        }


@dataclass(frozen=True)
class InfoResult:
    """What ``api.info`` reports about the shipped build and this wiki's contract (FR-010).

    ``warnings`` carries the drift message when there is drift, the same one
    ``propose`` and ``promote`` give.
    """

    package_version: str
    schema_contract: SchemaContractInfo
    formats: Mapping[str, int]
    capabilities: tuple[str, ...]
    manifest: ManifestInfo
    warnings: tuple[str, ...] = ()
    discovery: DiscoveryInfo | None = None

    def as_dict(self) -> dict[str, Any]:
        """The keys ``info --json`` adds to the 0.6.0 layout keys (``discovery`` from 0.8.0, when described)."""
        data: dict[str, Any] = {
            "package_version": self.package_version,
            "schema_contract": self.schema_contract.as_dict(),
            "formats": dict(self.formats),
            "capabilities": list(self.capabilities),
            "manifest": self.manifest.as_dict(),
        }
        if self.discovery is not None:
            data["discovery"] = self.discovery.as_dict()
        return data


def describe(paths: WikiPaths) -> InfoResult:
    """Read the manifest and the schema overrides once and describe the contract (no lock, writes nothing)."""
    manifest = read_manifest(paths)
    schema = load_schema(paths)
    if manifest is None:
        contract = SchemaContractInfo(SCHEMA_ID, SCHEMA_VERSION, schema.source, schema.fingerprint, None)
        manifest_info = ManifestInfo(state=MANIFEST_MISSING, mode=MODE_LEGACY, instruction=MANIFEST_INSTRUCTION)
    else:
        contract = SchemaContractInfo(
            manifest.schema_id,
            manifest.schema_version,
            schema.source,
            schema.fingerprint,
            manifest.schema_fingerprint,
        )
        manifest_info = ManifestInfo(
            state=MANIFEST_PRESENT,
            mode=manifest.mode,
            manifest_version=manifest.manifest_version,
            wiki_id=manifest.wiki_id,
            policy=manifest.policy,
        )
    warnings: tuple[str, ...] = ()
    if contract.drift and contract.declared_fingerprint is not None:
        warnings = (drift_message(contract.declared_fingerprint, contract.fingerprint),)
    return InfoResult(
        package_version=__version__,
        schema_contract=contract,
        formats=FORMATS,
        capabilities=CAPABILITIES,
        manifest=manifest_info,
        warnings=warnings,
    )
