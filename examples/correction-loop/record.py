# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Record one correction-loop run, bound to the bytes it executed (FR-014).

Standard library only. Preflight, which creates nothing: refuse unless the
working tree is clean, ``--out`` does not exist and ``poetry`` is on PATH;
record ``HEAD``'s full commit SHA. The attempt then starts by creating
``--out``: archive that SHA (never the name ``HEAD``) and extract it; hash
``demo.py``, this recorder and the protocol from the extracted tree and refuse
if the running recorder differs; build the wiki-studio wheel there with
``poetry build``; download memkernel 0.6.0 and check its sha256 against the
file PyPI publishes; install both into a fresh virtual environment and write
its ``pip freeze``; download the embedding model at the pinned revision and
refuse any other snapshot; run the extracted ``demo.py`` once, with
``MEMKERNEL_EMBEDDING_MODEL`` pointing at the snapshot and ``HF_HUB_OFFLINE=1``,
writing stdout and stderr to ``transcript.txt``; copy the wiki and proposals
trees to ``end-state/`` and hash them with the extracted
``conformance.mcp.run tree-hash``; write ``manifest.json`` and exit with the
demo's code. Every attempt writes ``manifest.json`` as soon as ``--out`` exists
(``outcome: running`` with the current ``stage``, rewritten at each stage), and
ends it as ``outcome: completed`` or ``outcome: failed`` with ``failed_stage``
and the error, for any exception including an interrupt. A manifest still
reading ``outcome: running`` means the process was killed in that ``stage``.

``--out`` must not exist: a second attempt is a new directory, and a failed
attempt is kept as it is. The protocol is in ``README.md``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

MK_VERSION = "0.6.0"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
PYPI_URL = f"https://pypi.org/pypi/memkernel/{MK_VERSION}/json"
WALL_TIME_LABEL = "machine time on a scripted path, not a measure of human adoption"

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_REL = Path("examples") / "correction-loop" / "demo.py"
RECORD_REL = Path("examples") / "correction-loop" / "record.py"
PROTOCOL_REL = Path("examples") / "correction-loop" / "README.md"
END_STATE_TREES = ("knowledge/wiki", "doc_internal/proposals")


class CannotRunError(Exception):
    """The recorder cannot produce a valid run directory (exit 2)."""


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tail(text: str, limit: int = 400) -> str:
    return " ".join(text.split())[-limit:]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command, cwd=str(cwd) if cwd else None, env=env, capture_output=True, text=True, check=False
        )
    except OSError as exc:
        raise CannotRunError(f"could not run {command[0]}: {exc}") from exc


def _run_or_die(command: list[str], description: str, *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    completed = _run(command, cwd=cwd)
    if completed.returncode != 0:
        raise CannotRunError(
            f"{description} failed (exit {completed.returncode}): {_tail(completed.stderr or completed.stdout)}"
        )
    return completed


def _git_output(*arguments: str) -> str:
    return _run_or_die(
        ["git", "-C", str(REPO_ROOT), *arguments],
        f"git {arguments[0]}",
    ).stdout.strip()


def _extract_commit(tmp: Path, commit: str) -> Path:
    """The tree of ``commit`` (a full SHA, never the mutable name HEAD), extracted into a temporary directory.

    Everything that produces evidence (the wheel, the demo, the tree hash) runs from this tree, so the
    manifest's commit and hashes describe the bytes that executed, whatever happens to the working tree.
    """
    archive = tmp / "commit.tar"
    _run_or_die(
        ["git", "-C", str(REPO_ROOT), "archive", "--format=tar", "--output", str(archive), commit],
        f"git archive {commit}",
    )
    source = tmp / "source"
    source.mkdir()
    try:
        with tarfile.open(archive) as tar:
            try:
                tar.extractall(source, filter="data")
            except TypeError:  # Python < 3.11.4 has no extraction filter
                tar.extractall(source)
    except (tarfile.TarError, OSError) as exc:
        raise CannotRunError(f"could not extract the archive of {commit}: {exc}") from exc
    return source


def _build_wheel(tmp: Path, poetry: str, source: Path) -> Path:
    """The wheel built from the extracted commit only (``poetry build`` in that tree)."""
    _run_or_die([poetry, "build", "--output", str(tmp / "dist")], "poetry build", cwd=source)
    wheels = sorted((tmp / "dist").glob("*.whl"))
    if len(wheels) != 1:
        raise CannotRunError(
            f"poetry build wrote {len(wheels)} wheels, expected one: {[wheel.name for wheel in wheels]}"
        )
    return wheels[0]


def _published_sha256(filename: str) -> str:
    """The sha256 PyPI publishes for one file of the pinned memkernel release."""
    try:
        with urllib.request.urlopen(PYPI_URL, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise CannotRunError(f"PyPI could not be read at {PYPI_URL}: {exc}") from exc
    for entry in payload.get("urls", []):
        if entry.get("filename") == filename:
            digest = entry.get("digests", {}).get("sha256")
            if not digest:
                raise CannotRunError(f"PyPI publishes no sha256 for {filename}")
            return str(digest)
    raise CannotRunError(f"PyPI lists no file named {filename} for memkernel {MK_VERSION}")


def _download_memkernel(tmp: Path) -> tuple[Path, str, str]:
    """The memkernel wheel, its sha256, and PyPI's for the same file (refused on a mismatch)."""
    downloads = tmp / "downloads"
    _run_or_die(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            f"memkernel=={MK_VERSION}",
            "--no-deps",
            "--only-binary",
            ":all:",
            "--dest",
            str(downloads),
        ],
        "pip download memkernel",
    )
    wheels = sorted(downloads.glob(f"memkernel-{MK_VERSION}-*.whl")) or sorted(downloads.glob("*.whl"))
    if len(wheels) != 1:
        raise CannotRunError(f"pip download wrote {len(wheels)} memkernel wheels, expected one")
    downloaded, published = _sha256_file(wheels[0]), _published_sha256(wheels[0].name)
    if downloaded != published:
        raise CannotRunError(f"the downloaded {wheels[0].name} has sha256 {downloaded}, but PyPI publishes {published}")
    return wheels[0], downloaded, published


def _venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _install(venv: Path, wheel: Path, memkernel_wheel: Path) -> Path:
    """A fresh virtual environment with the built wheel and the downloaded memkernel wheel."""
    python = _venv_python(venv)
    _run_or_die([sys.executable, "-m", "venv", str(venv)], "python -m venv")
    pip = [str(python), "-m", "pip"]
    _run_or_die([*pip, "install", "--quiet", "--upgrade", "pip"], "pip install --upgrade pip")
    _run_or_die([*pip, "install", "--quiet", str(wheel), str(memkernel_wheel)], "pip install the two wheels")
    _run_or_die([*pip, "check"], "pip check")
    return python


def _environment(python: Path, out: Path) -> None:
    completed = _run_or_die([str(python), "-m", "pip", "freeze"], "pip freeze")
    (out / "environment.txt").write_text(completed.stdout, encoding="utf-8")


def _versions(python: Path) -> dict[str, str]:
    snippet = (
        "import json, platform\n"
        "import memkernel, wiki_studio\n"
        "print(json.dumps({'wiki_studio': wiki_studio.__version__, "
        "'memkernel': memkernel.__version__, 'python': platform.python_version(), "
        "'platform': platform.platform()}))\n"
    )
    completed = _run_or_die([str(python), "-c", snippet], "the version probe")
    try:
        return {key: str(value) for key, value in json.loads(completed.stdout).items()}
    except (ValueError, AttributeError) as exc:
        raise CannotRunError(f"the version probe printed no JSON: {_tail(completed.stdout)}") from exc


def _embedding_snapshot(python: Path, revision: str) -> Path:
    """Download the model at ``revision`` and refuse any other snapshot directory."""
    snippet = (
        "import sys\n"
        "from huggingface_hub import snapshot_download\n"
        f"print(snapshot_download({EMBEDDING_MODEL!r}, revision=sys.argv[1]))\n"
    )
    completed = _run_or_die([str(python), "-c", snippet, revision], "snapshot_download")
    snapshot = Path(completed.stdout.strip())
    if snapshot.name != revision:
        raise CannotRunError(f"the snapshot is {snapshot.name}, not the pinned revision {revision}")
    if not snapshot.is_dir():
        raise CannotRunError(f"the snapshot {snapshot} is not a directory")
    return snapshot


def _run_demo(python: Path, out: Path, tmp: Path, snapshot: Path, source: Path) -> tuple[int, dict[str, Any] | None]:
    """Run the demo once, never retried, with the pinned model and the hub offline."""
    workdir = tmp / "work"
    summary_path = tmp / "summary.json"
    env = os.environ.copy()
    env["MEMKERNEL_EMBEDDING_MODEL"] = str(snapshot)
    env["HF_HUB_OFFLINE"] = "1"
    try:
        with (out / "transcript.txt").open("w", encoding="utf-8") as transcript:
            completed = subprocess.run(
                [str(python), str(source / DEMO_REL), "--workdir", str(workdir), "--summary", str(summary_path)],
                cwd=str(source),
                env=env,
                stdout=transcript,
                stderr=subprocess.STDOUT,
                check=False,
            )
    except OSError as exc:
        raise CannotRunError(f"could not run the demo: {exc}") from exc
    summary = None
    if summary_path.is_file():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise CannotRunError(f"the demo wrote no JSON summary: {exc}") from exc
    return completed.returncode, summary


def _copy_end_state(workdir: Path, out: Path) -> Path:
    """The wiki and proposals trees as the run left them: no lock, cache or memkernel store."""
    end_state = out / "end-state"
    end_state.mkdir()
    for rel in END_STATE_TREES:
        source = workdir / rel
        if source.is_dir():
            shutil.copytree(
                source,
                end_state / rel,
                ignore=shutil.ignore_patterns(".wiki.wiki-studio.*", "__pycache__"),
            )
    return end_state


def _tree_hash(end_state: Path, source: Path) -> str:
    """The end-state hash, computed by the extracted commit's ``conformance.mcp.run`` (standard library only)."""
    completed = _run_or_die(
        [sys.executable, "-m", "conformance.mcp.run", "tree-hash", str(end_state)],
        "tree-hash",
        cwd=source,
    )
    return completed.stdout.strip()


def _elapsed(start: str, end: Any) -> float | None:
    if not isinstance(end, str):
        return None
    try:
        start_at = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_at = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError:
        return None
    return round(max(0.0, (end_at - start_at).total_seconds()), 1)


def _wall_times(install_started_at: str, summary: dict[str, Any] | None) -> dict[str, float | None]:
    """Install start to the approval and to the corrected recall, in seconds."""
    return {
        "install_to_first_approved_revision": _elapsed(
            install_started_at, summary.get("approval_completed_at") if summary else None
        ),
        "install_to_corrected_recall": _elapsed(
            install_started_at, summary.get("corrected_recall_at") if summary else None
        ),
    }


def _write_manifest(out: Path, manifest: dict[str, Any]) -> None:
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _record(out: Path, revision: str) -> int:
    # Preflight: a refusal here is not an attempt and creates nothing.
    started_at = _utc_now()
    if out.exists():
        raise CannotRunError(f"--out {out} already exists; a second attempt is a new directory")
    status = _run(["git", "-C", str(REPO_ROOT), "status", "--porcelain"])
    if status.returncode != 0:
        raise CannotRunError(f"git status failed: {_tail(status.stderr)}")
    if status.stdout.strip():
        raise CannotRunError(f"the working tree is not clean: {_tail(status.stdout)}")
    head = _git_output("rev-parse", "HEAD")
    poetry = shutil.which("poetry")
    if poetry is None:
        raise CannotRunError("poetry is not on PATH; the wheel must be built from the commit")

    # The attempt starts here: the run directory exists from now on, and every path out of this
    # block leaves a manifest.json naming the outcome and, on failure, the stage that failed.
    try:
        out.mkdir(parents=True)
    except FileExistsError as exc:
        raise CannotRunError(f"--out {out} already exists; a second attempt is a new directory") from exc
    manifest: dict[str, Any] = {
        "outcome": "running",
        "git_commit": head,
        "git_clean": True,
        "started_at": started_at,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_revision": revision,
        "wall_time_label": WALL_TIME_LABEL,
    }
    stage = "extract"

    def enter(name: str) -> None:
        # The manifest on disk always names the current stage: a crash or a kill that no handler
        # sees leaves outcome "running" and the stage it stopped in.
        nonlocal stage
        stage = name
        manifest["stage"] = name
        _write_manifest(out, manifest)

    enter("extract")
    try:
        with tempfile.TemporaryDirectory(prefix="wiki-studio-record-") as tmp_name:
            tmp = Path(tmp_name)
            source = _extract_commit(tmp, head)
            manifest["demo_sha256"] = _sha256_file(source / DEMO_REL)
            manifest["record_sha256"] = _sha256_file(source / RECORD_REL)
            manifest["protocol_sha256"] = _sha256_file(source / PROTOCOL_REL)
            if _sha256_file(Path(__file__).resolve()) != manifest["record_sha256"]:
                raise CannotRunError(f"the running record.py differs from the one in commit {head}")
            enter("build")
            wheel = _build_wheel(tmp, poetry, source)
            manifest["wheel_file"] = wheel.name
            manifest["wheel_sha256"] = _sha256_file(wheel)
            enter("download")
            memkernel_wheel, memkernel_sha256, published_sha256 = _download_memkernel(tmp)
            manifest["memkernel_file"] = memkernel_wheel.name
            manifest["memkernel_sha256"] = memkernel_sha256
            manifest["memkernel_pypi_sha256"] = published_sha256
            enter("install")
            install_started_at = _utc_now()
            python = _install(tmp / "venv", wheel, memkernel_wheel)
            _environment(python, out)
            versions = _versions(python)
            manifest["wiki_studio_version"] = versions.get("wiki_studio")
            manifest["memkernel_version"] = versions.get("memkernel")
            manifest["python_version"] = versions.get("python")
            manifest["platform"] = versions.get("platform")
            enter("embedding")
            snapshot = _embedding_snapshot(python, revision)
            enter("demo")
            exit_code, summary = _run_demo(python, out, tmp, snapshot, source)
            enter("end-state")
            end_state = _copy_end_state(tmp / "work", out)
            manifest["end_state_sha256"] = _tree_hash(end_state, source)
            manifest["exit_code"] = exit_code
            manifest["summary"] = summary
            manifest["wall_time_seconds"] = _wall_times(install_started_at, summary)
            manifest.pop("stage", None)
            manifest["outcome"] = "completed"
            manifest["finished_at"] = _utc_now()
            _write_manifest(out, manifest)
    except BaseException as exc:  # every way out, KeyboardInterrupt and SystemExit included, leaves a manifest
        manifest.pop("stage", None)
        manifest["outcome"] = "failed"
        manifest["failed_stage"] = stage
        manifest["error"] = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
        manifest["finished_at"] = _utc_now()
        _write_manifest(out, manifest)
        raise
    return exit_code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="record.py", description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="the run directory to create")
    parser.add_argument(
        "--embedding-revision",
        default=EMBEDDING_REVISION,
        help=f"the embedding model's revision (default: {EMBEDDING_REVISION})",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return _record(args.out.expanduser().absolute(), args.embedding_revision)
    except CannotRunError as exc:
        print(f"cannot run: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"cannot run: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
