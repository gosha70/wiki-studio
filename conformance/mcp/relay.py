# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Run a server command and record every byte it writes to stdout (FR-043 case 12).

``python relay.py RECORD -- COMMAND...``: the command inherits stdin and
stderr; its stdout is copied unchanged to this process's stdout and appended
to ``RECORD``, so the suite can check that the server wrote protocol frames
only while the SDK's client talks to it. Standalone (no package import), so it
runs from any working directory. Exits with the command's exit code.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys

_READ_CHUNK = 65536
_USAGE_EXIT = 2


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] != "--":
        print("usage: relay.py RECORD -- COMMAND...", file=sys.stderr)
        return _USAGE_EXIT
    record_path, command = argv[0], argv[2:]
    child = subprocess.Popen(command, stdout=subprocess.PIPE)
    assert child.stdout is not None

    def forward(signum: int, _frame: object) -> None:
        child.send_signal(signum)

    signal.signal(signal.SIGTERM, forward)
    source = child.stdout.fileno()
    sink = sys.stdout.buffer
    with open(record_path, "ab") as record:
        while True:
            chunk = os.read(source, _READ_CHUNK)
            if not chunk:
                break
            sink.write(chunk)
            sink.flush()
            record.write(chunk)
            record.flush()
    return child.wait()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
