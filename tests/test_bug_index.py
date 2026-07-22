"""Tests for docs/handoff/bugs/_regen_index.py.

The generator lives under docs/ rather than src/, so it is loaded by path
instead of imported as a package module. Its output is committed and covered by
the enabled lint-markdown CI gate, so these tests pin the two properties that
gate depends on: the MD060-compliant separator row and escaped cell content.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
BUGS = ROOT / "docs" / "handoff" / "bugs"


def load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_regen_index", BUGS / "_regen_index.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_frontmatter_strips_single_quotes() -> None:
    fields = load_generator().parse_frontmatter("---\nbug_id: '007'\nstatus: open\n---\n")
    assert fields == {"bug_id": "007", "status": "open"}


def test_parse_frontmatter_without_fence_is_empty() -> None:
    assert load_generator().parse_frontmatter("# Not a bug record\n") == {}


def test_escape_cell_neutralizes_emphasis_and_pipes() -> None:
    escape_cell = load_generator().escape_cell
    assert escape_cell("docs/*.md") == r"docs/\*.md"
    assert escape_cell("_read_message") == r"\_read\_message"
    assert escape_cell("a | b") == r"a \| b"


def test_build_index_emits_padded_separator_row(tmp_path: Path) -> None:
    (tmp_path / "001-example.md").write_text(
        "---\nbug_id: '001'\ndate: '2026-01-01'\ntitle: 'x'\nservices: [ci]\nstatus: open\n---\n",
        encoding="utf-8",
    )
    # "|---|" trips markdownlint MD060, which requires the compact style's
    # single space either side of every pipe.
    assert "| --- | --- | --- | --- | --- |" in load_generator().build_index(tmp_path)


def test_build_index_escapes_titles(tmp_path: Path) -> None:
    (tmp_path / "002-glob.md").write_text(
        "---\nbug_id: '002'\ndate: '2026-01-01'\n"
        "title: 'stale docs/*.md in _read_message'\nservices: [mcp]\nstatus: open\n---\n",
        encoding="utf-8",
    )
    row = load_generator().build_index(tmp_path).splitlines()[-1]
    assert r"docs/\*.md" in row
    assert r"\_read\_message" in row


def test_build_index_handles_empty_directory(tmp_path: Path) -> None:
    assert "_No bugs recorded._" in load_generator().build_index(tmp_path)


def test_committed_index_matches_generator() -> None:
    """The committed INDEX.md must be the generator's current output.

    Catches a hand-edited index and a generator change applied without
    regenerating, either of which would surface as CI-only lint drift.
    """
    expected = load_generator().build_index(BUGS)
    assert (BUGS / "INDEX.md").read_text(encoding="utf-8") == expected
