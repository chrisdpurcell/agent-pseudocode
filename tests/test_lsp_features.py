from __future__ import annotations

from pathlib import Path

from apseudo_lint.completions import completion_specs, token_at_position
from apseudo_lint.config import load_config
from apseudo_lint.lint import lint_snippet
from apseudo_lint.lsp import diagnostic_to_lsp
from apseudo_lint.model import Severity, Snippet

ROOT = Path(__file__).resolve().parents[1]


def test_completion_items_include_outcome_snippet() -> None:
    config = load_config(explicit=ROOT / ".apseudo-lint.toml")
    items = [item.as_lsp() for item in completion_specs(config)]
    accepted = next(item for item in items if item["label"] == "Accepted")
    assert accepted["insertTextFormat"] == 2
    assert "Accepted" in accepted["insertText"]


def test_lsp_lints_document_text() -> None:
    config = load_config(explicit=ROOT / ".apseudo-lint.toml")
    text = "process demo():\n    while ready:\n        do_work()\n    return Done()\n"
    diagnostics = lint_snippet(Snippet(Path("demo.apseudo"), text), config)
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "APSEUDO-WHILE-001" in codes
    assert "APSEUDO-OUTCOME-001" in codes
    lsp_diagnostic = diagnostic_to_lsp(diagnostics[0], text)
    assert lsp_diagnostic["severity"] in {1, 2, 3}


def test_word_at_position_supports_annotations() -> None:
    assert token_at_position("# @bounded", 0, 4) == "@bounded"


def test_diagnostic_severity_mapping_uses_errors() -> None:
    config = load_config(explicit=ROOT / ".apseudo-lint.toml")
    diagnostics = lint_snippet(
        Snippet(Path("demo.apseudo"), "process demo():\n    return Accepted()\n"), config
    )
    assert [diag for diag in diagnostics if diag.severity == Severity.ERROR] == []
