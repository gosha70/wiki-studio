# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The accepted ``avoid:`` form survives memkernel's parse and render (0.5.0 FR-009).

The sequence is: wiki-studio reads the raw value, memkernel parses it
(``_unquote``) and renders it back (``_quote``), and wiki-studio reads the
rendered value. Accepted values must read back as the same terms. Unsupported
values must be refused on the first read; nothing is asserted about what
memkernel turns them into.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from wiki_studio.prose_lint import load_avoid_map


# Copied from gosha70/memkernel src/memkernel/wiki/pages.py at main 4a9597d,
# `_unquote` lines 45-49 (citation verified 2026-10-20, see the spec FR-009). Test fixture only.
def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


# Copied from gosha70/memkernel src/memkernel/wiki/pages.py at main 4a9597d,
# `_quote` lines 113-117 (citation verified 2026-10-20, see the spec FR-009). Test fixture only.
def _quote(value: str) -> str:
    if any(ch in value for ch in ":#\"'[]{}") or value != value.strip():
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


ACCEPTED = {
    "alignment check, origin check": ("alignment check", "origin check"),
    "it's, ok": ("it's", "ok"),
    '"x: y, z"': ("x: y", "z"),
    '"it\'s, ok"': ("it's", "ok"),
    "build #2, origin check": ("build #2", "origin check"),
    '"build #2"': ("build #2",),
}

UNSUPPORTED = (
    'the "old" gate',
    "C:\\cache",
    '"the \\"old\\" gate"',
    '"C:\\\\cache"',
    "'it''s, ok'",
    "'plain, term'",
)


class TestAvoidRoundTrip(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.wiki = Path(self._tmp.name) / "wiki"
        (self.wiki / "glossary").mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def read(self, raw: str) -> tuple[tuple[str, ...] | None, int]:
        """wiki-studio's read of ``avoid: <raw>``: the terms (or None) and the problem count."""
        (self.wiki / "glossary" / "origin-gate.md").write_text(
            "---\npage_type: glossary\nslug: origin-gate\ntitle: Origin gate\nstatus: stable\n"
            f"last_reviewed: 2026-10-20\navoid: {raw}\n---\n\n# Origin gate\n",
            encoding="utf-8",
        )
        avoid_map, problems = load_avoid_map(self.wiki)
        entry = avoid_map.get("origin-gate")
        return (entry.terms if entry else None), len(problems)

    def test_accepted_values_read_back_as_the_same_terms(self) -> None:
        for raw, terms in ACCEPTED.items():
            with self.subTest(raw=raw):
                self.assertEqual(self.read(raw), (terms, 0))
                rendered = _quote(_unquote(raw))
                self.assertEqual(self.read(rendered), (terms, 0), f"after memkernel: {rendered!r}")

    def test_unsupported_values_are_refused_on_the_first_read(self) -> None:
        for raw in UNSUPPORTED:
            with self.subTest(raw=raw):
                self.assertEqual(self.read(raw), (None, 1))


if __name__ == "__main__":
    unittest.main()
